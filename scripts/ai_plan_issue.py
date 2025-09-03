#!/usr/bin/env python3
"""
Create a task breakdown plan for a GitHub Issue using an LLM (OpenAI) and post it as a comment.

Usage in Actions:
- Triggered when someone comments "/plan" on an issue (or via workflow_dispatch).
- Requires OPENAI_API_KEY; otherwise no-ops gracefully.

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


MODEL = os.environ.get("PLAN_MODEL", "gpt-4o-mini")

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
    """Install and import PyGithub only when we need to post to GitHub.

    This should not be called in dry-run mode so we avoid side effects.
    """
    global Github
    if Github is not None:
        return
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyGithub>=2.3.0"])  # noqa: S603,S607
    from github import Github as _Github  # type: ignore

    Github = _Github

def _parse_event_issue(event_path: Optional[str]) -> Optional[int]:
    if not event_path or not os.path.exists(event_path):
        return None
    with open(event_path, "r", encoding="utf-8") as f:
        event = json.load(f)
    if event.get("issue") and event["issue"].get("number"):
        return int(event["issue"]["number"])
    return None




def get_issue_context(dry_run: bool = False) -> tuple[int, Optional[str], Optional[str]]:

    """Return (issue_number, owner, repo_name).

    In non-dry-run mode we require GITHUB_REPOSITORY and an issue number. In
    dry-run mode we are permissive: missing repo or issue number will be
    tolerated and returned as None (or 0 for issue number) so the rest of the
    script can run without attempting network calls.
    """
    repo_slug = os.environ.get("GITHUB_REPOSITORY")

    # Default to the issue from the comment event (if available)
    issue_number: Optional[int] = None
    issue_number = _parse_event_issue(os.environ.get("GITHUB_EVENT_PATH"))

    if not issue_number:
        try:
            issue_number = int(os.environ.get("ISSUE_NUMBER", "0")) or None
        except ValueError:
            issue_number = None

    if not dry_run and not issue_number:
        raise SystemExit("No issue number found in event or inputs")

    owner = None
    repo_name = None
    if repo_slug:
        owner, repo_name = repo_slug.split("/", 1)
    elif not dry_run:
        raise SystemExit("GITHUB_REPOSITORY missing")

    # For dry-run, return permissive defaults (issue_number will be 0 if missing)
    return issue_number or 0, owner, repo_name


def call_llm(prompt: str) -> str:
    # OpenAI only
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        return (
            "No LLM key configured. Skipping plan generation.\n"
            "Set OPENAI_API_KEY secret to enable."
        )

    try:
        import requests  # type: ignore
    except Exception:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests>=2.31.0"])  # noqa: S603,S607
        import requests  # type: ignore  # noqa: E402

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an implementation plan for a GitHub issue using an LLM")
    parser.add_argument("--dry-run", action="store_true", help="Do not post comment; write plan to tmp/ai-plan-dryrun/")
    args = parser.parse_args()

    dry_run = args.dry_run or os.environ.get("DRY_RUN") == "1"

    token = os.environ.get("GITHUB_TOKEN")
    if not token and not dry_run:
        raise SystemExit("GITHUB_TOKEN missing")

    # Resolve issue/repo context first; in dry-run mode this is permissive and
    # will not raise if env vars are missing.
    issue_number, owner, repo_name = get_issue_context(dry_run=dry_run)

    gh = None
    repo = None
    issue = None
    # Only import/initialize PyGithub and fetch the real issue when we intend to
    # post (not dry-run) and a token is available.
    if not dry_run and token:
        ensure_pygithub()
        assert Github is not None, "PyGithub not initialized"
        gh = Github(token)
        repo = gh.get_repo(f"{owner}/{repo_name}")
        issue = repo.get_issue(number=issue_number)

    # Build prompt from issue title and body
    title = issue.title if issue is not None else os.environ.get("ISSUE_TITLE", "")
    body = issue.body or "" if issue is not None else os.environ.get("ISSUE_BODY", "")

    prompt = (
        f"Repo: {owner}/{repo_name}\nIssue #{issue_number}: {title}\n\n"
        f"Body:\n{body}\n\n"
        "Produce a concise, step-by-step implementation plan aligned to the repo layout."
    )

    plan = call_llm(prompt)

    # Optional schema validation: enforce only in non-dry-run mode
    if not dry_run:
        valid_schema, schema_msg = validate_plan_schema(plan)
        if not valid_schema:
            print(f"Plan does not conform to schema: {schema_msg}")
            if issue is not None:
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
        
        file_issue_part = f"{issue_number}" if issue_number != 0 else "unknown"
        out_file = os.path.join(out_dir, f"issue-{file_issue_part}-plan.txt")

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(comment)
        print(f"DRY-RUN: wrote plan to {out_file}")


if __name__ == "__main__":
    main()
