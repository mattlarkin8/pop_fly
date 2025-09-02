#!/usr/bin/env python3
"""
Update PR description with a checklist derived from the linked issue plan, and check items off based on commits.

Heuristics:
- Find the linked issue number from PR title or body (e.g., 'Fixes #123', '(#123)', 'Closes #123').
- Fetch the latest plan comment from that issue (posted by ai_plan_issue.py) or fallback to its body.
- Normalize plan to GitHub checkboxes:
  - '- [ ] Task'
  - Keep to 5–15 items, truncate otherwise.
- Mark a task done if any commit message on the PR references the task line (case-insensitive contains) or '#<task-index>'.
- Write back the PR body with a fenced section between markers to allow idempotent updates.
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import List, Optional

try:
    from github import Github  # type: ignore
except Exception:
    Github = None

CHECKLIST_START = "<!-- PLAN-CHECKLIST:START -->"
CHECKLIST_END = "<!-- PLAN-CHECKLIST:END -->"
ISSUE_REF_RE = re.compile(r"#(\d+)")


def ensure_pygithub() -> None:
    global Github
    if Github is not None:
        return
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyGithub>=2.3.0"])  # noqa: S603,S607
    from github import Github as _Github  # type: ignore

    Github = _Github


def get_pr_context():
    repo_slug = os.environ.get("GITHUB_REPOSITORY")
    if not repo_slug:
        raise SystemExit("GITHUB_REPOSITORY missing")
    owner, repo = repo_slug.split("/", 1)

    pr_number: Optional[int] = None
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    event_name = os.environ.get("GITHUB_EVENT_NAME")
    if event_name and event_path and os.path.exists(event_path):
        with open(event_path, "r", encoding="utf-8") as f:
            event = json.load(f)
        if event.get("pull_request") and event["pull_request"].get("number"):
            pr_number = int(event["pull_request"]["number"])
    if not pr_number:
        pr_number = int(os.environ.get("INPUT_PR", "0") or 0) or None
    if not pr_number:
        raise SystemExit("No PR number available")
    return owner, repo, pr_number


def find_issue_number(pr_title: str, pr_body: str) -> Optional[int]:
    for text in (pr_title or "", pr_body or ""):
        m = ISSUE_REF_RE.search(text)
        if m:
            return int(m.group(1))
    return None


def extract_tasks(plan_text: str) -> List[str]:
    lines = [l.strip(" \t-") for l in plan_text.splitlines() if l.strip()]
    # Take bullets or numbered items as tasks
    tasks: List[str] = []
    for l in lines:
        if l.startswith(('[', '*', '•')):
            # Already a checkbox or bullet; strip markers
            l = re.sub(r"^\*+\s*", "", l)
            l = re.sub(r"^\[.?\]\s*", "", l)
        tasks.append(l)
    # De-dup and clip
    seen = set()
    uniq = []
    for t in tasks:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    return uniq[:15] if len(uniq) > 15 else uniq


def build_checklist(tasks: List[str], commit_messages: List[str]) -> str:
    done = set()
    lower_msgs = [m.lower() for m in commit_messages]
    for idx, task in enumerate(tasks, start=1):
        key = task.lower()
        tag = f"#{idx}"
        for msg in lower_msgs:
            if key in msg or tag in msg:
                done.add(idx)
                break
    lines = ["## Implementation Tasks"]
    for idx, task in enumerate(tasks, start=1):
        mark = "[x]" if idx in done else "[ ]"
        lines.append(f"- {mark} {task}")
    return "\n".join(lines)


def upsert_section(body: str, content: str) -> str:
    if CHECKLIST_START in body and CHECKLIST_END in body:
        pre = body.split(CHECKLIST_START, 1)[0]
        post = body.split(CHECKLIST_END, 1)[1]
        return f"{pre}{CHECKLIST_START}\n{content}\n{CHECKLIST_END}{post}"
    return f"{body}\n\n{CHECKLIST_START}\n{content}\n{CHECKLIST_END}\n"


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN missing")

    ensure_pygithub()

    owner, repo_name, pr_number = get_pr_context()
    assert Github is not None, "PyGithub not initialized"
    gh = Github(token)
    repo = gh.get_repo(f"{owner}/{repo_name}")
    pr = repo.get_pull(pr_number)

    issue_num = find_issue_number(pr.title, pr.body or "")
    plan_text = ""
    if issue_num:
        issue = repo.get_issue(number=issue_num)
        # pick the latest plan comment
        comments = list(issue.get_comments())
        for c in reversed(comments):
            if c.body and c.body.startswith("Automated plan (" ):
                plan_text = c.body.split("\n\n", 1)[-1].strip()
                break
        if not plan_text:
            plan_text = (issue.body or "").strip()

    if not plan_text:
        print("No plan found; leaving PR unchanged.")
        return

    tasks = extract_tasks(plan_text)
    # Collect commit messages on the PR
    commit_messages = [c.commit.message for c in pr.get_commits()]
    checklist = build_checklist(tasks, commit_messages)

    new_body = upsert_section(pr.body or "", checklist)
    pr.edit(body=new_body)
    print("PR checklist updated.")


if __name__ == "__main__":
    main()
