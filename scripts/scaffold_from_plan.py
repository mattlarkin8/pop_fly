#!/usr/bin/env python3
"""
Create a branch and PR from a feature plan.

- Triggered by a push to a branch matching 'feature/plan-**'.
- Reads the 'feature-plan.md' file from the branch.
- In the future, this script will use an AI to generate code from the plan.
- For now, it creates a PR with the plan.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

try:
    from github import Github
except ImportError:
    Github = None

def ensure_pygithub() -> None:
    """Ensures PyGithub is installed."""
    global Github
    if Github is not None:
        return
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyGithub>=2.3.0"])
    from github import Github as _Github
    Github = _Github

def git(cmd: list[str]) -> str:
    """Executes a git command and returns its output."""
    return subprocess.check_output(cmd, text=True).strip()

def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Scaffold from a feature plan.")
    parser.add_argument("--branch", type=str, required=True, help="The feature branch with the plan.")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN missing. Use POP_FLY_PAT for this script.")

    repo_slug = os.environ.get("GITHUB_REPOSITORY")
    if not repo_slug:
        raise SystemExit("GITHUB_REPOSITORY missing")

    ensure_pygithub()
    gh = Github(token)
    repo = gh.get_repo(repo_slug)

    branch_name = args.branch
    plan_path = "feature-plan.md"

    if not os.path.exists(plan_path):
        print(f"Plan file '{plan_path}' not found on branch '{branch_name}'. Exiting.")
        return

    with open(plan_path, "r", encoding="utf-8") as f:
        plan_content = f.read()

    # Use a generative AI to turn the plan into concrete file changes.
    # Strategy:
    # 1) Provide the plan and current project structure to the LLM.
    # 2) Ask for a strict JSON response describing file edits to apply.
    # 3) Apply safe changes only within src/, tests/, frontend/, or scripts/.
    # 4) Commit and push edits back to the same branch.

    from pathlib import Path  # local import to avoid top-level edits
    import json  # local import to avoid top-level edits

    repo_root = Path(".").resolve()
    allowed_dirs = [repo_root / "src", repo_root / "tests", repo_root / "frontend", repo_root / "scripts"]

    def list_project_structure(root: Path) -> str:
        lines = ["Project Structure (subset):"]
        ignore = {".git", ".venv", "__pycache__", ".vscode", "node_modules", "dist"}
        for p in sorted(root.rglob("*")):
            if any(part in ignore for part in p.parts):
                continue
            try:
                rel = p.relative_to(root)
            except Exception:
                continue
            depth = len(rel.parts) - 1
            indent = "  " * max(depth, 0)
            lines.append(f"{indent}{rel.as_posix()}{'/' if p.is_dir() else ''}")
        return "\n".join(lines)

    def call_llm_for_changes(plan_md: str, structure: str) -> dict:
        model = os.environ.get("PLAN_MODEL", "gpt-4-turbo-preview")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return {"changes": [], "note": "OPENAI_API_KEY not set; skipped generation."}

        # Lazy import and install requests if missing
        try:
            import requests  # type: ignore
        except Exception:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "requests>=2.31.0"])  # noqa: S603,S607
            import requests  # type: ignore  # noqa: E402

        system_prompt = (
            "You are a senior software engineer. Convert the provided feature plan into concrete file edits.\n"
            "Return ONLY valid JSON with this exact schema: {\"changes\": [ {\"path\": string, \"action\": \"create\"|\"update\", \"content\": string } ]}.\n"
            "Rules: keep changes minimal; target only src/, tests/, frontend/, scripts/; do not delete files; include full file content for create/update; be consistent with Python 3.11 and existing project conventions."
        )

        user_prompt = (
            "Feature Plan (Markdown):\n\n" + plan_md + "\n\n" +
            "Repo structure: \n\n" + structure + "\n\n" +
            "Produce JSON now."
        )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 3000,
        }

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=180)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

        # Some models might wrap JSON in code fences; strip if present
        content = content.strip()
        if content.startswith("```"):
            # remove first fence line and last fence line if present
            lines = [ln for ln in content.splitlines() if not ln.strip().startswith("```")]
            content = "\n".join(lines).strip()
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # Best-effort: if it returned non-JSON, skip generation
            return {"changes": [], "note": "Model returned non-JSON; skipped generation."}
        if not isinstance(data, dict) or "changes" not in data or not isinstance(data["changes"], list):
            return {"changes": [], "note": "Unexpected schema; skipped generation."}
        return data

    structure = list_project_structure(repo_root)
    llm_result = call_llm_for_changes(plan_content, structure)

    applied_files: list[str] = []
    for change in llm_result.get("changes", []):
        try:
            rel_path = str(change.get("path", "")).strip()
            action = str(change.get("action", "")).strip().lower()
            content = change.get("content", "")
            if not rel_path or action not in {"create", "update"}:
                continue
            target = (repo_root / rel_path).resolve()
            # Safety: must be under repo and within allowed dirs
            if not str(target).startswith(str(repo_root)):
                continue
            if not any(str(target).startswith(str(ad)) for ad in allowed_dirs):
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            # Write full content for both create and update
            with open(target, "w", encoding="utf-8", newline="") as wf:
                wf.write(content)
            applied_files.append(str(target.relative_to(repo_root)))
        except Exception as e:
            print(f"Skipping change due to error: {e}")

    # Commit and push if there are changes
    try:
        status = git(["git", "status", "--porcelain"]).strip()
        if status:
            git(["git", "add", "-A"])
            git(["git", "config", "user.name", "github-actions"])
            git(["git", "config", "user.email", "github-actions@users.noreply.github.com"])
            git(["git", "commit", "-m", "chore: scaffold code from feature plan"])
            # Push back to the same branch
            git(["git", "push", "origin", branch_name])
    except subprocess.CalledProcessError as e:
        print(f"Git commit/push failed: {e}")

    # Prepare PR content
    pr_title = f"feat: Implement feature from plan '{branch_name}'"
    if applied_files:
        changed_list = "\n".join(f"- {p}" for p in applied_files)
        pr_body = (
            "This PR includes AI-scaffolded changes based on the plan.\n\n"
            "Changed files:\n" + changed_list + "\n\n---\n\n" + plan_content
        )
    else:
        note = llm_result.get("note", "No changes were generated.")
        pr_body = (
            f"No scaffolded changes were generated automatically ({note}).\n\n"
            "Plan for reference:\n\n---\n\n" + plan_content
        )
    
    try:
        # Check if a PR already exists for this branch
        existing_prs = repo.get_pulls(state='open', head=f'{repo.owner.login}:{branch_name}')
        if existing_prs.totalCount > 0:
            print(f"A pull request already exists for branch '{branch_name}'.")
            # Optionally, update the existing PR
            pr = existing_prs[0]
            pr.edit(title=pr_title, body=pr_body)
            print(f"Updated existing PR: {pr.html_url}")
            return

        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=repo.default_branch,
        )
        print(f"Created pull request: {pr.html_url}")
    except Exception as e:
        print(f"Failed to create or update pull request: {e}")
        # This can happen if the branch is up-to-date with the base
        # or other permission issues.
        print("This might be because the branch has no new commits to merge.")


if __name__ == "__main__":
    main()
