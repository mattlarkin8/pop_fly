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
from typing import Any, Dict, Optional

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
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN missing")

    ensure_pygithub()

    issue_number, owner, repo_name = get_issue_context()
    assert Github is not None, "PyGithub not initialized"
    gh = Github(token)
    repo = gh.get_repo(f"{owner}/{repo_name}")
    issue = repo.get_issue(number=issue_number)

    # Build prompt from issue title and body
    title = issue.title
    body = issue.body or ""

    prompt = (
        f"Repo: {owner}/{repo_name}\nIssue #{issue_number}: {title}\n\n"
        f"Body:\n{body}\n\n"
        "Produce a concise, step-by-step implementation plan aligned to the repo layout."
    )

    plan = call_llm(prompt)

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    comment = f"Automated plan ({timestamp}):\n\n{plan}"
    issue.create_comment(comment)
    print("Posted plan comment.")


if __name__ == "__main__":
    main()
