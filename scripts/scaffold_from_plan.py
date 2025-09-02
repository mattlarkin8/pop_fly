#!/usr/bin/env python3
"""
Create a branch and PR from an issue's plan comment.

- Triggered by comment '/scaffold' or manual dispatch.
- Finds the latest automated plan comment (from ai_plan_issue.py) or uses the issue body.
- Creates a branch with a README checklist commit and opens a PR linking the issue.
- Does not modify source code; only scaffolds a task list and wiring.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Optional

try:
    from github import Github  # type: ignore
except Exception:
    Github = None

PLAN_MARKER = "Automated plan ("
BRANCH_PREFIX = "scaffold/issue-"


def ensure_pygithub() -> None:
    global Github
    if Github is not None:
        return
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyGithub>=2.3.0"])  # noqa: S603,S607
    from github import Github as _Github  # type: ignore

    Github = _Github


def get_issue_number_from_event() -> Optional[int]:
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_name and event_path and os.path.exists(event_path):
        with open(event_path, "r", encoding="utf-8") as f:
            event = json.load(f)
        if event.get("issue") and event["issue"].get("number"):
            return int(event["issue"]["number"])
    val = os.environ.get("INPUT_ISSUE") or os.environ.get("ISSUE_NUMBER")
    return int(val) if val else None


def find_plan_text(issue) -> str:
    # Look for latest plan comment
    comments = list(issue.get_comments())
    for comment in reversed(comments):
        body = comment.body or ""
        if PLAN_MARKER in body:
            # Strip marker header
            idx = body.find("\n\n")
            return body[idx + 2 :].strip() if idx != -1 else body
    # Fallback to issue body
    return (issue.body or "No plan found. Add a plan via '/plan' first.").strip()


def git(cmd: list[str]) -> str:
    out = subprocess.check_output(cmd, text=True)
    return out.strip()


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN missing")

    ensure_pygithub()

    repo_slug = os.environ.get("GITHUB_REPOSITORY")
    if not repo_slug:
        raise SystemExit("GITHUB_REPOSITORY missing")
    owner, repo_name = repo_slug.split("/", 1)

    issue_number = get_issue_number_from_event()
    if not issue_number:
        raise SystemExit("No issue number found in event or inputs")

    assert Github is not None, "PyGithub not initialized"
    gh = Github(token)
    repo = gh.get_repo(f"{owner}/{repo_name}")
    issue = repo.get_issue(number=issue_number)

    base_branch = os.environ.get("BASE_BRANCH", os.environ.get("GITHUB_REF_NAME", "main"))
    branch = f"{BRANCH_PREFIX}{issue_number}"

    # Prepare local git
    git(["git", "config", "user.name", "github-actions"])
    git(["git", "config", "user.email", "github-actions@users.noreply.github.com"])
    git(["git", "fetch", "origin", base_branch])
    git(["git", "checkout", "-B", branch, f"origin/{base_branch}"])

    # Create or update a planning checklist file on the branch
    plan_text = find_plan_text(issue)
    planning_dir = os.path.join(".github", "scaffolds")
    os.makedirs(planning_dir, exist_ok=True)
    checklist_path = os.path.join(planning_dir, f"issue-{issue_number}.md")

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    content = f"""# Plan for Issue #{issue_number}: {issue.title}

Generated: {timestamp}

## Tasks

{plan_text}

---
This PR scaffolds a checklist. Convert bullets into commits and code changes. Ensure unit tests pass.
"""
    with open(checklist_path, "w", encoding="utf-8") as f:
        f.write(content)

    git(["git", "add", checklist_path])
    # Commit only if there are staged changes
    try:
        git(["git", "commit", "-m", f"Scaffold checklist for issue #{issue_number}"])
    except subprocess.CalledProcessError:
        # Nothing to commit
        pass

    git(["git", "push", "-u", "origin", branch])

    # Open or update PR
    prs = repo.get_pulls(state="open", head=f"{owner}:{branch}")
    pr = None
    for p in prs:
        if p.head.ref == branch:
            pr = p
            break
    title = f"Scaffold: {issue.title} (#{issue_number})"
    body = (
        f"This PR scaffolds tasks for #{issue_number}.\n\n"
        "- Converts the plan into a checklist file under `.github/scaffolds/`.\n"
        "- Please implement items, add tests, and ensure CI passes before merge.\n"
    )
    if pr:
        pr.edit(title=title, body=body)
    else:
        pr = repo.create_pull(title=title, body=body, head=branch, base=base_branch)
    # Link issue
    issue.create_comment(f"Scaffolded PR: #{pr.number}")
    if "roadmap" not in [l.name for l in issue.get_labels()]:
        issue.add_to_labels("roadmap")

    print(f"Opened/updated PR #{pr.number} from {branch}")


if __name__ == "__main__":
    main()
