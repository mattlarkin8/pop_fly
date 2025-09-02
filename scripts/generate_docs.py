#!/usr/bin/env python3
"""
Generate documentation updates (README.md and PRD.md) after a PR is merged.

This script is intended to run in CI when a pull request is merged. It:
- finds the merged PR and changed files
- asks an LLM to propose README/PRD updates (returns structured JSON)
- creates a docs branch, commits changes, pushes, and opens a PR with the docs updates
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List

try:
    from github import Github
except Exception:
    Github = None


def ensure_pygithub() -> None:
    global Github
    if Github is not None:
        return
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyGithub>=2.3.0"])  # noqa: S603,S607
    from github import Github as _Github  # type: ignore

    Github = _Github


def call_llm_for_docs(pr_title: str, pr_body: str, changed_files: List[str]) -> Dict[str, Any]:
    """Call OpenAI to produce a JSON payload with docs updates.

    Returns a dict like: {"docs": [{"path":"README.md","action":"update","content":"..."}, ...]}
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"docs": [], "note": "OPENAI_API_KEY not set"}

    try:
        import requests
    except Exception:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests>=2.31.0"])  # noqa: S603,S607
        import requests

    system = (
        "You are a technical writer. Given a merged pull request and a list of changed files, propose updates to README.md and PRD.md. "
        "Return ONLY valid JSON with schema: {\"docs\": [ {\"path\": string, \"action\": \"create\"|\"update\", \"content\": string } ] }. "
        "Limit paths to README.md or PRD.md. Keep changes concise and focused."
    )

    user = (
        f"PR Title: {pr_title}\n\nPR Body:\n{pr_body}\n\nChanged files:\n" + "\n".join(changed_files) + "\n\nProduce JSON now."
    )

    payload = {
        "model": os.environ.get("PLAN_MODEL", "gpt-4-turbo-preview"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
    }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    if content.startswith("```"):
        lines = [ln for ln in content.splitlines() if not ln.strip().startswith("```")]
        content = "\n".join(lines).strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {"docs": [], "note": "model returned non-JSON"}
    return data


def git(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def main() -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN missing")

    ensure_pygithub()
    gh = Github(token)

    repo_slug = os.environ.get("GITHUB_REPOSITORY")
    if not repo_slug:
        raise SystemExit("GITHUB_REPOSITORY missing")

    owner, repo_name = repo_slug.split("/", 1)
    repo = gh.get_repo(repo_slug)

    # Determine PR number from event payload
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not os.path.exists(event_path):
        raise SystemExit("GITHUB_EVENT_PATH missing")
    with open(event_path, "r", encoding="utf-8") as f:
        event = json.load(f)

    pr = event.get("pull_request")
    if not pr or not pr.get("merged"):
        print("No merged pull request found in event, exiting.")
        return

    pr_number = int(pr["number"])
    pr_obj = repo.get_pull(pr_number)
    changed_files = [f.filename for f in pr_obj.get_files()]

    # Ask LLM for doc updates
    llm_result = call_llm_for_docs(pr_obj.title, pr_obj.body or "", changed_files)
    docs = llm_result.get("docs", [])
    note = llm_result.get("note")

    if not docs:
        print("No docs updates returned by LLM.")
        if note:
            print("Note:", note)
        # Still create a comment on the PR that no docs were suggested
        pr_obj.create_issue_comment("No documentation updates were suggested by the automated doc generation step.")
        return

    # Validate and apply docs changes
    allowed = {"README.md", "PRD.md"}
    repo_root = os.getcwd()

    # Create a branch
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    branch = f"docs/update-pr-{pr_number}-{ts}"
    git(["git", "fetch", "origin", "main"])
    git(["git", "checkout", "-b", branch, "origin/main"])

    applied: List[str] = []
    for entry in docs:
        path = entry.get("path")
        action = entry.get("action")
        content = entry.get("content")
        if not path or path not in allowed or action not in {"create", "update"}:
            print(f"Skipping invalid doc entry: {entry}")
            continue
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        applied.append(path)

    if applied:
        git(["git", "add", "-A"])
        git(["git", "config", "user.name", "github-actions"])
        git(["git", "config", "user.email", "github-actions@users.noreply.github.com"])
        git(["git", "commit", "-m", f"docs: update README/PRD for PR #{pr_number}"])
        git(["git", "push", "origin", branch])

        # Create PR
        title = f"docs: update docs for PR #{pr_number} — {pr_obj.title}"
        body = (
            f"Automated documentation updates based on merged PR #{pr_number}.\n\n"
            "Files updated:\n" + "\n".join(f"- {p}" for p in applied) + "\n\n" +
            "If these updates look good, merge this PR."
        )
        try:
            new_pr = repo.create_pull(title=title, body=body, head=branch, base=repo.default_branch)
            pr_obj.create_issue_comment(f"Automated docs PR created: #{new_pr.number}")
            print(f"Created docs PR: {new_pr.html_url}")
        except Exception as e:
            print("Failed to create docs PR:", e)
    else:
        print("No valid doc entries applied.")
        pr_obj.create_issue_comment("No valid documentation updates were applied by automation.")


if __name__ == "__main__":
    main()
