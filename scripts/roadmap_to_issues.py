#!/usr/bin/env python3
"""
Convert roadmap bullets into GitHub issues.

- Parses ROADMAP.md and extracts bullet items under Now/Next/Later.
- Creates or updates GitHub Issues with labels [roadmap, Now|Next|Later].
- Idempotent: updates existing issues if a matching title exists or an inline #123 reference is present.

Requires: GITHUB_TOKEN provided by GitHub Actions.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

try:
    from github import Github  # type: ignore
except Exception:
    Github = None  # lazy install


SECTION_RE = re.compile(r"^##\s+(Now|Next|Later)")
ITEM_RE = re.compile(r"^-\s+(.*)")
ISSUE_REF_RE = re.compile(r"#(\d+)")
STATUS_EMOJI = {
    "Done": "🟢",
    "In progress": "🟡",
    "Planned": "⚪",
}


@dataclass
class RoadmapItem:
    section: str  # Now|Next|Later
    title: str
    body: str
    # status is None when the item has no explicit status marker (emoji or word).
    status: Optional[str]
    issue_ref: Optional[int]


def parse_roadmap(md: str) -> List[RoadmapItem]:
    lines = md.splitlines()
    section: Optional[str] = None
    items: List[RoadmapItem] = []

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        m_section = SECTION_RE.match(line)
        if m_section:
            section = m_section.group(1)
            i += 1
            continue
        # If we encounter any other H2 ("## ...") that is not a roadmap section,
        # clear the current section so subsequent top-level bullets are not
        # incorrectly attributed to the previous Now/Next/Later section.
        if line.startswith("## ") and not m_section:
            section = None
            i += 1
            continue

        if section and ITEM_RE.match(line):
            # Parse main bullet as title and capture following indented sub-bullets
            main = ITEM_RE.match(line).group(1)  # type: ignore
            # Detect status emoji or word inside trailing parentheses, e.g. "Feature (🟡)" or "Feature (In progress)"
            status = ""
            title = main
            # Remove inline issue reference like "#123" before matching parentheses
            main_no_ref = ISSUE_REF_RE.sub("", main).strip()
            m_paren = re.match(r"^(.*)\s*\(([^)]+)\)\s*(?:#\d+)?\s*$", main_no_ref)
            if m_paren:
                inside = m_paren.group(2).strip()
                candidate_title = m_paren.group(1).strip()
                # If the parenthesized part looks like an emoji status or known status word, treat it as status
                if any(e in inside for e in ("🟢", "🟡", "⚪")) or inside.lower() in {"done", "in progress", "planned"}:
                    status = inside
                    title = candidate_title
            # Collect sub-bullets as body until next top-level bullet or section
            body_lines: List[str] = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt.startswith("## ") or ITEM_RE.match(nxt):
                    break
                if nxt.strip().startswith("- "):
                    body_lines.append(nxt.strip()[2:])
                elif nxt.strip():
                    body_lines.append(nxt.strip())
                j += 1
            body = "\n".join(body_lines).strip()
            issue_ref = None
            m_issue = ISSUE_REF_RE.search(main)
            if m_issue:
                issue_ref = int(m_issue.group(1))

            # Normalize status to one of Done / In progress / Planned, but only
            # if an explicit status marker (emoji or known word) was present.
            status_word: Optional[str] = None
            s_low = (status or "").lower()
            if status:
                if "🟢" in status or s_low == "done":
                    status_word = "Done"
                elif "🟡" in status or s_low == "in progress":
                    status_word = "In progress"
                elif "⚪" in status or s_low == "planned":
                    status_word = "Planned"

            items.append(RoadmapItem(section=section, title=title, body=body, status=status_word, issue_ref=issue_ref))
            i = j
            continue

        i += 1

    return items


def ensure_pygithub() -> None:
    global Github
    if Github is not None:
        return
    # Lazy install
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyGithub>=2.3.0"])  # noqa: S603,S607
    from github import Github as _Github  # type: ignore

    Github = _Github


def get_repo_context() -> Tuple[str, str]:
    # owner/repo from GITHUB_REPOSITORY
    gh_repo = os.environ.get("GITHUB_REPOSITORY")
    if not gh_repo or "/" not in gh_repo:
        raise SystemExit("GITHUB_REPOSITORY is not set or invalid")
    owner, repo = gh_repo.split("/", 1)
    return owner, repo


def upsert_issues(items: Iterable[RoadmapItem]) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN not provided")

    ensure_pygithub()

    owner, repo_name = get_repo_context()
    assert Github is not None, "PyGithub not initialized"
    gh = Github(token)
    repo = gh.get_repo(f"{owner}/{repo_name}")

    # Ensure labels (sections + status)
    status_labels = {"Done", "In progress", "Planned"}
    wanted_labels = {"roadmap", "Now", "Next", "Later"} | status_labels
    existing = {l.name for l in repo.get_labels()}
    # Color mapping for new labels (sensible defaults)
    label_colors = {
        "roadmap": "0e8a16",
        "Now": "0e8a16",
        "Next": "0052cc",
        "Later": "6f42c1",
        "Done": "0e8a16",
        "In progress": "dbab09",
        "Planned": "6a737d",
    }
    for lab in wanted_labels - existing:
        color = label_colors.get(lab, "6a737d")
        repo.create_label(name=lab, color=color)

    # Build title -> issue map for idempotency
    existing_issues = list(repo.get_issues(state="open")) + list(repo.get_issues(state="closed"))
    by_title = {iss.title.strip(): iss for iss in existing_issues}
    by_number = {iss.number: iss for iss in existing_issues}

    for it in items:
        # Skip items that do not have an explicit status marker unless the
        # environment variable ROADMAP_INCLUDE_UNANNOTATED=true is set. This
        # reduces accidental issue creation from unannotated bullets.
        include_unannotated = os.environ.get("ROADMAP_INCLUDE_UNANNOTATED", "false").lower() in ("1", "true", "yes")
        if it.status is None and not include_unannotated:
            print(f"Skipping unannotated roadmap item: '{it.title}' (section={it.section})")
            continue

        # Determine the desired status label for this item
        # At this point, it.status is not None (we skipped None above)
        status_label = it.status  # type: ignore

        target_issue = None
        if it.issue_ref and it.issue_ref in by_number:
            target_issue = by_number[it.issue_ref]
        elif it.title.strip() in by_title:
            target_issue = by_title[it.title.strip()]

        body_parts = [
            f"Section: {it.section}",
            "\nAcceptance / Notes:",
            it.body or "(fill in acceptance criteria)",
            "\nSource: ROADMAP.md",
        ]
        body = "\n".join(body_parts).strip()
        # Build label set: preserve unrelated existing labels, but ensure roadmap/section/status are present
        desired_base = {"roadmap", it.section, status_label}

        if target_issue:
            existing_labels = {l.name for l in target_issue.get_labels()}
            # Remove any old status labels to avoid stale statuses
            cleaned = existing_labels - status_labels
            new_labels = sorted(cleaned | desired_base)
            # If item is Done, close the issue; otherwise ensure it is open
            new_state = "closed" if status_label == "Done" else "open"
            target_issue.edit(body=body, labels=new_labels, state=new_state)
        else:
            # Create with labels; created issue is open by default
            target_issue = repo.create_issue(title=it.title.strip(), body=body, labels=sorted(desired_base))
            # Immediately close if roadmap marks it Done
            if status_label == "Done":
                target_issue.edit(state="closed")

        print(f"Upserted issue #{target_issue.number}: {target_issue.title} (status={status_label})")


def main() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    roadmap_path = os.path.join(root, "ROADMAP.md")
    with open(roadmap_path, "r", encoding="utf-8") as f:
        md = f.read()

    items = parse_roadmap(md)
    if not items:
        print("No roadmap items found; nothing to do.")
        return

    upsert_issues(items)


if __name__ == "__main__":
    main()
