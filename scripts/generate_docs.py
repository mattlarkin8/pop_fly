#!/usr/bin/env python3
"""
Generate documentation updates (README.md and PRD.md) after a PR is merged.

This script is intended to run in CI when a pull request is merged. It:
- finds the merged PR and changed files
- asks an LLM to propose README/PRD updates (returns structured JSON)
- creates a docs branch, commits changes, pushes, and opens a PR with the docs updates
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import re
import difflib

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


def call_llm_for_docs(
    pr_title: str,
    pr_body: str,
    changed_files: List[str],
    readme_text: str,
    prd_text: str,
) -> Dict[str, Any]:
    """Call OpenAI to produce a JSON payload with structured docs updates.

    Returns a dict like:
    {
      "docs": [
        {
          "path": "README.md" | "PRD.md",
          "ops": [
            {"type": "replace_section", "heading": str, "content": str},
            {"type": "append_to_section", "heading": str, "content": str},
            {"type": "upsert_section", "heading": str, "level": int, "content": str},
            {"type": "replace_block_by_marker", "name": str, "content": str}
          ]
        }
      ]
    }
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
        "You are a precise technical writer that produces minimal, targeted documentation edits. "
        "Given a merged PR, its changed files, and the current contents of README.md and PRD.md, propose small updates. "
        "Return ONLY valid minified JSON following this schema: "
        '{"docs":[{"path":"README.md"|"PRD.md","ops":['
        '  {"type":"replace_section","heading":string,"content":string}|'
        '  {"type":"append_to_section","heading":string,"content":string}|'
        '  {"type":"upsert_section","heading":string,"level":2|3|4|5|6,"content":string}|'
        '  {"type":"replace_block_by_marker","name":string,"content":string}'
        ']}]}'
        " Rules: Modify only existing sections or explicit markers. Do not rewrite entire files. Maintain headings and style. Limit to at most 6 ops per file."
    )

    user = (
        f"PR Title: {pr_title}\n\nPR Body:\n{pr_body}\n\nChanged files:\n" + "\n".join(changed_files) +
        "\n\nCurrent README.md:\n" + readme_text +
        "\n\nCurrent PRD.md:\n" + prd_text +
        "\n\nProduce ONLY the JSON described above."
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


def validate_docs_ops_schema(docs: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """Validate the structure of the LLM-produced docs ops against a local JSON schema.

    Returns (valid, message). If jsonschema is not installed, validation is skipped and returns (True, None).
    """
    schema_path = os.path.join(os.getcwd(), "docs", "schema", "docs_ops.json")
    if not os.path.exists(schema_path):
        return True, None
    try:
        from jsonschema import validate, ValidationError  # type: ignore
    except Exception:
        return True, "jsonschema not installed; skipping schema validation"

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    try:
        validate(instance={"docs": docs}, schema=schema)
    except ValidationError as e:
        return False, str(e)
    return True, None


Heading = Tuple[int, str, int]  # (level, title, line_index)


def _parse_headings(lines: List[str]) -> List[Heading]:
    headings: List[Heading] = []
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            headings.append((level, title, i))
    return headings


def _find_unique_heading(headings: List[Heading], title: str) -> Optional[Heading]:
    matches = [h for h in headings if h[1] == title]
    if len(matches) == 1:
        return matches[0]
    return None


def _section_span(lines: List[str], headings: List[Heading], target: Heading) -> Tuple[int, int, int]:
    level, _title, start_line = target
    # Section content starts after the heading line
    content_start = start_line + 1
    # Find next heading of same or higher level
    end_line = len(lines)
    for h_level, _h_title, h_line in headings:
        if h_line <= start_line:
            continue
        if h_level <= level:
            end_line = h_line
            break
    return start_line, content_start, end_line


def apply_ops_to_markdown(original: str, ops: List[Dict[str, Any]], file_label: str) -> Tuple[str, List[str], List[str]]:
    """Apply structured ops to Markdown content.

    Returns (new_content, warnings, errors)
    """
    warnings: List[str] = []
    errors: List[str] = []
    if not ops:
        return original, warnings, errors

    if len(ops) > 10:  # global cap safety
        errors.append(f"{file_label}: too many ops ({len(ops)})")
        return original, warnings, errors

    lines = original.splitlines()
    headings = _parse_headings(lines)
    edited_lines = lines[:]

    # Helper for marker-based replacement
    def replace_by_marker(name: str, content: str) -> None:
        start_marker = f"<!-- AUTO-DOC:{name} -->"
        end_marker = f"<!-- /AUTO-DOC:{name} -->"
        start_idx = None
        end_idx = None
        for i, ln in enumerate(edited_lines):
            if start_marker in ln:
                start_idx = i
                break
        if start_idx is None:
            errors.append(f"{file_label}: marker '{name}' not found")
            return
        for j in range(start_idx + 1, len(edited_lines)):
            if end_marker in edited_lines[j]:
                end_idx = j
                break
        if end_idx is None:
            errors.append(f"{file_label}: end marker for '{name}' not found")
            return
        new_block = [edited_lines[start_idx], content.rstrip("\n"), edited_lines[end_idx]]
        edited_lines[start_idx:end_idx + 1] = new_block

    # Apply ops in order
    for idx, op in enumerate(ops):
        op_type = op.get("type")
        if op_type not in {"replace_section", "append_to_section", "upsert_section", "replace_block_by_marker"}:
            errors.append(f"{file_label}: op[{idx}] unknown type '{op_type}'")
            continue

        if op_type == "replace_block_by_marker":
            name = op.get("name")
            content = op.get("content", "")
            if not name:
                errors.append(f"{file_label}: op[{idx}] missing 'name'")
                continue
            replace_by_marker(name, content)
            continue

        heading_title = op.get("heading")
        content = op.get("content", "")
        if not heading_title:
            errors.append(f"{file_label}: op[{idx}] missing 'heading'")
            continue

        # Recompute headings each time in case structure changes
        headings = _parse_headings(edited_lines)
        target = _find_unique_heading(headings, heading_title)

        if op_type == "upsert_section" and target is None:
            level = int(op.get("level", 2))
            level = min(max(level, 2), 6)
            # Append new section at EOF with heading and content
            new_sec = ["", "#" * level + " " + heading_title, content.rstrip("\n")]  # ensure spacing
            edited_lines.extend(new_sec)
            continue

        if target is None:
            warnings.append(f"{file_label}: heading '{heading_title}' not uniquely found; op[{idx}] skipped")
            continue

        h_start, content_start, h_end = _section_span(edited_lines, headings, target)

        if op_type == "replace_section":
            # Keep heading line, replace content lines
            new_chunk = [edited_lines[h_start], content.rstrip("\n")]
            edited_lines[h_start:h_end] = new_chunk
        elif op_type == "append_to_section":
            # Insert before the first subheading within this section, if present; otherwise at section end
            target_level = target[0]
            first_subheading_line: Optional[int] = None
            for h_level, _t, h_line in headings:
                if h_line <= h_start:
                    continue
                if h_line >= h_end:
                    break
                if h_level > target_level:  # a subheading of this section
                    first_subheading_line = h_line
                    break
            insert_at = first_subheading_line if first_subheading_line is not None else h_end
            to_insert = content.rstrip("\n")
            insertion: List[str] = []
            # Ensure a blank line before insertion if previous line is not blank
            if insert_at > 0 and edited_lines[insert_at - 1].strip() != "":
                insertion.append("")
            insertion.append(to_insert)
            # Ensure a blank line after insertion if next line is not blank (e.g., heading follows)
            if insert_at < len(edited_lines) and edited_lines[insert_at:insert_at + 1] and (
                edited_lines[insert_at].strip() != ""
            ):
                insertion.append("")
            edited_lines[insert_at:insert_at] = insertion
        elif op_type == "upsert_section":
            # Exists: same as replace
            new_chunk = [edited_lines[h_start], content.rstrip("\n")]
            edited_lines[h_start:h_end] = new_chunk

    new_text = "\n".join(edited_lines) + ("" if original.endswith("\n") else "")

    # Simple guard against large deletions (>40%)
    if len(new_text) < 0.6 * len(original):
        errors.append(f"{file_label}: edit would shrink file by >40%; aborting edits")
        return original, warnings, errors

    return new_text, warnings, errors


def git(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate docs updates from a merged PR using an LLM")
    parser.add_argument("--dry-run", action="store_true", help="Do not push or create PR; write diffs to tmp/docs-dryrun/")
    args = parser.parse_args()

    dry_run = args.dry_run or os.environ.get("DRY_RUN") == "1"

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        # Allow running in dry-run locally without a token
        if not dry_run:
            raise SystemExit("GITHUB_TOKEN missing")

    ensure_pygithub()
    if Github is None:
        if not dry_run:
            raise SystemExit("PyGithub is not available after installation attempt")
    gh = Github(token) if token and Github is not None else None

    repo_slug = os.environ.get("GITHUB_REPOSITORY")
    if not repo_slug and not dry_run:
        raise SystemExit("GITHUB_REPOSITORY missing")

    owner, repo_name = (repo_slug.split("/", 1) if repo_slug else (None, None))
    repo = gh.get_repo(repo_slug) if gh is not None and repo_slug else None

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

    # Read current docs to include as context
    readme_path = os.path.join(os.getcwd(), "README.md")
    prd_path = os.path.join(os.getcwd(), "PRD.md")
    readme_text = open(readme_path, "r", encoding="utf-8").read() if os.path.exists(readme_path) else ""
    prd_text = open(prd_path, "r", encoding="utf-8").read() if os.path.exists(prd_path) else ""

    # Ask LLM for doc updates (structured ops)
    llm_result = call_llm_for_docs(pr_obj.title, pr_obj.body or "", changed_files, readme_text, prd_text)
    docs = llm_result.get("docs", [])
    note = llm_result.get("note")

    # Validate against local JSON schema if present
    valid_schema, schema_msg = validate_docs_ops_schema(docs)
    if not valid_schema:
        msg = f"LLM returned docs that do not match schema: {schema_msg}"
        print(msg)
        if not dry_run and pr_obj is not None:
            pr_obj.create_issue_comment(msg)
        return

    if not docs:
        print("No docs updates returned by LLM.")
        if note:
            print("Note:", note)
        # Still create a comment on the PR that no docs were suggested
        if not dry_run and pr_obj is not None:
            pr_obj.create_issue_comment("No documentation updates were suggested by the automated doc generation step.")
        return

    # Validate and apply docs changes
    allowed = {"README.md", "PRD.md"}
    repo_root = os.getcwd()

    # Create a branch (skip if dry-run)
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    branch = f"docs/update-pr-{pr_number}-{ts}"
    if not dry_run:
        git(["git", "fetch", "origin", "main"])
        git(["git", "checkout", "-b", branch, "origin/main"])
    else:
        print(f"DRY-RUN: would create branch {branch}")

    applied: List[str] = []
    per_file_ops: Dict[str, List[Dict[str, Any]]] = {}
    for entry in docs:
        path = entry.get("path")
        ops = entry.get("ops")
        if not path or path not in allowed or not isinstance(ops, list):
            print(f"Skipping invalid doc entry: {entry}")
            continue
        per_file_ops.setdefault(path, []).extend(ops)

    if not per_file_ops:
        print("No applicable doc ops found.")
        pr_obj.create_issue_comment("Docs automation found no applicable operations to apply.")
        return

    file_results: Dict[str, Tuple[str, List[str], List[str], str]] = {}
    any_errors = False
    for path, ops in per_file_ops.items():
        original_text = open(path, "r", encoding="utf-8").read() if os.path.exists(path) else ""
        new_text, warnings, errors = apply_ops_to_markdown(original_text, ops, path)
        if errors:
            any_errors = True
        # Prepare diff preview
        diff_lines = list(difflib.unified_diff(
            original_text.splitlines(), new_text.splitlines(), fromfile=f"a/{path}", tofile=f"b/{path}", lineterm=""
        ))
        diff_preview = "\n".join(diff_lines[:200])  # limit preview size
        file_results[path] = (new_text, warnings, errors, diff_preview)

    if any_errors:
        msg_lines = [
            "Docs automation could not safely apply updates. No changes were committed.",
            "Errors:" 
        ]
        for p, (_t, _w, errs, _d) in file_results.items():
            for e in errs:
                msg_lines.append(f"- {e}")
        if note:
            msg_lines.append(f"Note from model: {note}")
        if not dry_run and pr_obj is not None:
            pr_obj.create_issue_comment("\n".join(msg_lines))
        print("Errors encountered; aborting without commit.")
        return

    # Write results to working tree
    for path, (new_text, warnings, _errs, _diff) in file_results.items():
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(new_text)
        if warnings:
            print(f"Warnings for {path}:\n" + "\n".join(f"- {w}" for w in warnings))
        applied.append(path)

    if applied:
        if not dry_run:
            git(["git", "add", "-A"])
            git(["git", "config", "user.name", "github-actions"])
            git(["git", "config", "user.email", "github-actions@users.noreply.github.com"])
            git(["git", "commit", "-m", f"docs: update README/PRD for PR #{pr_number}"])
            git(["git", "push", "origin", branch])

            # Create PR
            title = f"docs: update docs for PR #{pr_number} — {pr_obj.title}"
            # Build a short diff preview for body
            body_lines = [
                f"Automated documentation updates based on merged PR #{pr_number}.",
                "",
                "Files updated:",
            ] + [f"- {p}" for p in applied]
            body_lines.append("")
            body_lines.append("Preview (truncated unified diff):")
            for p, (_t, _w, _e, diff_prev) in file_results.items():
                if not diff_prev:
                    continue
                body_lines.append(f"\n```diff\n{diff_prev}\n```\n")
            if note:
                body_lines.append(f"\nModel note: {note}")
            body_lines.append("\nIf these updates look good, merge this PR.")
            body = "\n".join(body_lines)
            try:
                new_pr = repo.create_pull(title=title, body=body, head=branch, base=repo.default_branch)
                pr_obj.create_issue_comment(f"Automated docs PR created: #{new_pr.number}")
                print(f"Created docs PR: {new_pr.html_url}")
            except Exception as e:
                print("Failed to create docs PR:", e)
        else:
            # Write diffs to tmp/docs-dryrun
            out_dir = os.path.join(os.getcwd(), "tmp", "docs-dryrun")
            os.makedirs(out_dir, exist_ok=True)
            for p, (_t, _w, _e, diff_prev) in file_results.items():
                fname = os.path.join(out_dir, p.replace("/", "_") + ".diff.txt")
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(diff_prev or "")
            print(f"DRY-RUN: wrote diffs to {out_dir}")
    else:
        print("No valid doc entries applied.")
        if not dry_run and pr_obj is not None:
            pr_obj.create_issue_comment("No valid documentation updates were applied by automation.")


if __name__ == "__main__":
    main()
