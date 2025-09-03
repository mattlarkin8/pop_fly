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
import re

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
    assert Github is not None, "PyGithub failed to import"
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
    # Load policy
    policy_path = repo_root / ".github" / "automation_policy.json"
    profile_name = os.environ.get("AUTOMATION_PROFILE", "minor")
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
    except Exception:
        policy = {"profiles": {"minor": {}}}
    prof = policy.get("profiles", {}).get(profile_name, {})
    # Enforce profile-level gating: some profiles (for example 'major') may
    # require that a GitHub pull request already exists and is labeled before
    # automated scaffolding may proceed. This prevents large-scope automation
    # from running without explicit human sign-off.
    required_label = prof.get("requires_label")
    if required_label:
        try:
            existing_prs = repo.get_pulls(state='open', head=f'{repo.owner.login}:{branch_name}')
        except Exception:
            existing_prs = []
        if not existing_prs or existing_prs.totalCount == 0:
            print(
                f"Profile '{profile_name}' requires an open PR labeled '{required_label}' for branch '{branch_name}'."
                " Create a PR for the branch and add the label before running the scaffolder."
            )
            return
        # Check labels on the first matching PR
        pr = existing_prs[0]
        try:
            pr_labels = [lbl.name for lbl in pr.get_labels()]
        except Exception:
            # Fallback: PyGithub sometimes exposes .labels as an attribute
            try:
                pr_labels = [lbl.name for lbl in pr.labels]
            except Exception:
                pr_labels = []
        if required_label not in pr_labels:
            print(
                f"Profile '{profile_name}' requires PR label '{required_label}' on PR #{getattr(pr, 'number', '?')} for branch '{branch_name}'. Aborting."
            )
            return
    allowed_files_set = set((repo_root / p).resolve() for p in prof.get("allowed_files", []))
    allowed_dirs_extra = [repo_root / p for p in prof.get("allowed_dirs", [])]
    if allowed_dirs_extra:
        allowed_dirs.extend(allowed_dirs_extra)
    max_files = int(prof.get("max_files", 4))
    max_total_lines = int(prof.get("max_lines", 80))
    allow_new_files = bool(prof.get("allow_new_files", False))
    forbidden_imports = list(prof.get("forbidden_imports", []))
    forbidden_paths = set(prof.get("forbidden_paths", []))

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
        model = os.environ.get("PLAN_MODEL", "gpt-4o")
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
            "Rules: keep changes minimal; do not delete files; include full file content for create/update; Python 3.11.\n"
            "Hard constraints: edit only src/pop_fly/core.py, src/pop_fly/web/app.py, tests/test_core.py, tests/test_api.py; no new files; no framework switches; no changes to dependencies or entry points; preserve public API and core symbols as-is.\n"
            "Budget: ≤ 80 changed lines across ≤ 4 files. If you cannot meet this, return {\"changes\": []}."
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
    total_lines_written = 0
    change_count = 0
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
            # Enforce strict allowed files and no file creation outside them
            # Enforce allowed files/dirs per profile
            if allowed_files_set:
                if target not in allowed_files_set:
                    continue
            else:
                # If no allowed_files specified, ensure it's under the allowed dirs
                if not any(str(target).startswith(str(ad)) for ad in allowed_dirs):
                    continue
            # File creation policy
            if action == "create" and not target.exists() and not allow_new_files:
                continue
            # Enforce budgets
            change_count += 1
            if change_count > max_files:
                print("Skipping change: exceeds file count budget")
                break
            line_count = content.count("\n") + 1 if content else 0
            if total_lines_written + line_count > max_total_lines:
                print("Skipping change: exceeds line budget")
                break
            target.parent.mkdir(parents=True, exist_ok=True)
            # Write full content for both create and update
            with open(target, "w", encoding="utf-8", newline="") as wf:
                wf.write(content)
            applied_files.append(str(target.relative_to(repo_root)))
            total_lines_written += line_count
        except Exception as e:
            print(f"Skipping change due to error: {e}")

    # Quick static validations before commit
    failures: list[str] = []
    # Forbidden imports (Flask)
    for path in applied_files:
        p = repo_root / path
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            txt = ""
        for bad in forbidden_imports:
            if re.search(rf"\b{re.escape(bad)}\b", txt or "", flags=re.IGNORECASE):
                failures.append(f"Forbidden import '{bad}' detected in {path}")
    # Required symbols present after edits (best-effort)
    core_txt = (repo_root / "src/pop_fly/core.py").read_text(encoding="utf-8")
    if not re.search(r"def\s+compute_distance_bearing_xy\(", core_txt):
        failures.append("compute_distance_bearing_xy is required in core.py")
    if not re.search(r"def\s+_parse_pair_mgrs_digits\(", core_txt):
        failures.append("_parse_pair_mgrs_digits is required in core.py")
    web_txt = (repo_root / "src/pop_fly/web/app.py").read_text(encoding="utf-8")
    if not re.search(r"FastAPI\(", web_txt) or not re.search(r"@app.post\(\"/api/compute\"\)", web_txt):
        failures.append("FastAPI app or /api/compute endpoint missing in web/app.py")

    # Guard against test deletions and dependency changes in working tree
    try:
        diff_name_status = git(["git", "diff", "--name-status"]).splitlines()
    except Exception:
        diff_name_status = []
    for line in diff_name_status:
        # Format: M	path or D	path
        parts = line.split() if line else []
        if len(parts) >= 2 and parts[0] == "D" and parts[1].startswith("tests/"):
            failures.append("Deletion in tests/ is forbidden")
        if len(parts) >= 2 and parts[1] in forbidden_paths and parts[0] != "":
            failures.append(f"Changes to {parts[1]} are forbidden")

    if failures:
        print("\nValidation failures:\n- " + "\n- ".join(failures))
        print("Aborting commit/push due to validation failures.")
        return

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
