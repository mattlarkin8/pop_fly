#!/usr/bin/env python3
"""
Create a task breakdown plan for a GitHub Issue using an LLM and post it as a comment.

Usage in Actions:
- Triggered when someone comments "/plan" on an issue (or via workflow_dispatch).
- Requires one of OPENAI_API_KEY or ANTHROPIC_API_KEY; otherwise no-ops gracefully.

Security notes:
- Reads issue via GITHUB_TOKEN. Does not write code, only comments a suggested plan.
- Keeps output concise and actionable.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
import argparse
import difflib

try:
    from github import Github  # type: ignore
except Exception:
    Github = None


MODEL = os.environ.get("PLAN_MODEL", "gpt-5-mini")

SYSTEM_PROMPT = (
    "You are an expert software project planner. Given a GitHub issue, produce a short, actionable plan: "
    "- bullet task list (5-10 items max), each task 1-2 sentences\n"
    "- include file hints from the repo structure if relevant\n"
    "- note risks and test ideas\n"
    "Keep it tight and implementable."
)


def validate_plan_schema(plan_text: str) -> Tuple[bool, Optional[str]]:
    """Validate LLM-produced plan text against docs/schema/plan_schema.json if present.

    If schema is missing, returns (True, None). If schema exists, expects the plan to be valid JSON matching schema.
    """
    schema_path = os.path.join(os.getcwd(), "docs", "schema", "plan_schema.json")
    if not os.path.exists(schema_path):
        return True, None
    try:
        from jsonschema import validate, ValidationError  # type: ignore
    except Exception:
        return True, "jsonschema not installed; skipping schema validation"

    try:
        payload = json.loads(plan_text)
    except json.JSONDecodeError:
        return False, "Model output is not valid JSON but schema exists at docs/schema/plan_schema.json"

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    try:
        validate(instance=payload, schema=schema)
    except ValidationError as e:
        return False, str(e)
    return True, None


def ensure_pygithub() -> None:
    global Github
    if Github is not None:
        return
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyGithub>=2.3.0"])  # noqa: S603,S607
    from github import Github as _Github  # type: ignore

    Github = _Github


def get_issue_context() -> tuple[int, str, str]:
    repo_slug = os.environ.get("GITHUB_REPOSITORY")
    if not repo_slug:
        raise SystemExit("GITHUB_REPOSITORY missing")

    # Default to the issue from the comment event
    issue_number: Optional[int] = None
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_name and event_path and os.path.exists(event_path):
        with open(event_path, "r", encoding="utf-8") as f:
            event = json.load(f)
        if event.get("issue") and event["issue"].get("number"):
            issue_number = int(event["issue"]["number"])
    if not issue_number:
        # allow manual override via input
        issue_number = int(os.environ.get("ISSUE_NUMBER", "0")) or None
    if not issue_number:
        raise SystemExit("No issue number found in event or inputs")

    owner, repo = repo_slug.split("/", 1)
    return issue_number, owner, repo


def call_llm(prompt: str) -> str:
    # Try OpenAI first
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not openai_key and not anthropic_key:
        return (
            "No LLM key configured. Skipping plan generation.\n"
            "Set OPENAI_API_KEY or ANTHROPIC_API_KEY secrets to enable."
        )

    try:
        import requests  # type: ignore
    except Exception:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests>=2.31.0"])  # noqa: S603,S607
        import requests  # type: ignore  # noqa: E402

    if openai_key:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
        data: Dict[str, Any] = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        r = requests.post(url, headers=headers, json=data, timeout=60)
        r.raise_for_status()
        j = r.json()
        content = j["choices"][0]["message"]["content"].strip()
        return content

    # Fallback to Anthropic
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": anthropic_key,
        "content-type": "application/json",
        "anthropic-version": "2023-06-01",
    }
    data = {
        "model": os.environ.get("PLAN_ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620"),
        "max_tokens": 1200,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    r = requests.post(url, headers=headers, json=data, timeout=60)
    r.raise_for_status()
    j = r.json()
    content = "".join(part.get("text", "") for part in j["content"])  # type: ignore
    return content.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an implementation plan for a GitHub issue using an LLM")
    parser.add_argument("--dry-run", action="store_true", help="Do not post comment; write plan to tmp/ai-plan-dryrun/")
    args = parser.parse_args()

    dry_run = args.dry_run or os.environ.get("DRY_RUN") == "1"

    token = os.environ.get("GITHUB_TOKEN")
    if not token and not dry_run:
        raise SystemExit("GITHUB_TOKEN missing")

    ensure_pygithub()

    issue_number, owner, repo_name = get_issue_context()
    assert Github is not None, "PyGithub not initialized"
    gh = Github(token) if token else None
    repo = gh.get_repo(f"{owner}/{repo_name}") if gh is not None else None
    issue = repo.get_issue(number=issue_number) if repo is not None else None

    # Build prompt from issue title and body
    title = issue.title if issue is not None else os.environ.get("ISSUE_TITLE", "")
    body = issue.body or "" if issue is not None else os.environ.get("ISSUE_BODY", "")

    prompt = (
        f"Repo: {owner}/{repo_name}\nIssue #{issue_number}: {title}\n\n"
        f"Body:\n{body}\n\n"
        "Produce a concise, step-by-step implementation plan aligned to the repo layout."
    )

    plan = call_llm(prompt)

    # Optional schema validation
    valid_schema, schema_msg = validate_plan_schema(plan)
    if not valid_schema:
        print(f"Plan does not conform to schema: {schema_msg}")
        if not dry_run and issue is not None:
            issue.create_comment(f"Automated plan generation failed schema validation: {schema_msg}")
        return

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    comment = f"Automated plan ({timestamp}):\n\n{plan}"
    if not dry_run and issue is not None:
        issue.create_comment(comment)
        print("Posted plan comment.")
    else:
        out_dir = os.path.join(os.getcwd(), "tmp", "ai-plan-dryrun")
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, f"issue-{issue_number}-plan.txt")
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(comment)
        print(f"DRY-RUN: wrote plan to {out_file}")


if __name__ == "__main__":
    main()
