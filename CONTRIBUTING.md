# Contributing — automation & docs generation

This repository includes automated helpers that call LLMs to generate implementation plans and documentation updates. Safety-first defaults are enforced: outputs are validated, edits are constrained to docs, and CI now runs automatic documentation generation on PR pushes (with an opt-out label). A dry-run workflow remains available for artifact-only previews.

Quick start
- Create and activate a virtualenv in the repo root:

  ```powershell
  python -m venv .venv
  & .venv\Scripts\Activate.ps1
  python -m pip install -r requirements-dev.txt
  ```

- Run tests:

  ```powershell
  python -m unittest discover -s tests -p "test_*.py"
  ```

Automation scripts (safety rules)
- `scripts/generate_docs.py`
  - Creates a documentation PR with safe, minimal edits to Markdown docs (README.md, PRD.md, and files under `docs/**`).
  - Automatically attempts to add the `docs` label to the PR it creates (non-fatal if label missing).
  - Supports `--dry-run` (or set `DRY_RUN=1`) — dry-run writes unified diffs to `tmp/docs-dryrun/` and does not push, create branches, or open PRs.
  - Validates model output against `docs/schema/docs_ops.json` if present and `jsonschema` is installed.

- `scripts/ai_plan_issue.py`
  - Supports `--dry-run` and writes plans to `tmp/ai-plan-dryrun/` when dry-run is enabled.
  - Optional schema validation against `docs/schema/plan_schema.json` if present.

Local testing
- To check what the automation would do without making changes, run each script with `--dry-run` and inspect the `tmp/` artifacts.
- Example:

  ```powershell
  python scripts/generate_docs.py --dry-run
  Get-ChildItem tmp\docs-dryrun\
  ```

Schema and validation
- JSON schemas live in `docs/schema/`.
  - `docs/schema/docs_ops.json` validates the structured operations for docs edits.
  - Add `docs/schema/plan_schema.json` to validate plan outputs if you want stricter checks for `ai_plan_issue.py`.

CI behavior
- CI installs `requirements-dev.txt` and runs unit tests.
- Auto-labeler: a workflow uses `.github/labeler.yml` to apply the `docs` label to PRs that touch documentation files (README.md, PRD.md, `docs/**`, and other `*.md`).
- Auto-docs generation: a workflow runs on PR open/synchronize/reopen and executes `scripts/generate_docs.py` to propose and open a separate documentation PR. This job is label-gated to skip when the source PR already has any label containing `docs` (e.g., `docs`, `docs:auto`).
- Dry-run preview: a separate workflow still runs `generate_docs.py --dry-run` and uploads `tmp/docs-dryrun/` artifacts for review when needed.

Security & secrets
- Keep `OPENAI_API_KEY` and other secrets in repository secrets only. Do not print or commit secrets.
- The auto-docs workflow requires `OPENAI_API_KEY` (and uses `GITHUB_TOKEN`) to create branches and PRs.
- CI exposes model keys only to protected branches and trusted workflows. DO NOT run LLM calls on untrusted forked PRs.

Controlling auto-apply (opt-out/opt-in)
- Default: documentation is generated automatically on PR pushes unless the PR carries a `docs`-related label.
- To opt-out for a PR (skip auto-docs), add the `docs` label (or any label containing `docs`).
- To force only a preview, run the dry-run workflow and review artifacts under `tmp/docs-dryrun/`.
- To adjust coverage, edit `.github/labeler.yml` (which defines what changes are considered documentation) and the docs editing rules in `.github/copilot-instructions.md` and `.github/assistant-guidelines.md`.

Tests and contribution checklist
- Run unit tests and linters before opening a PR.
- Add or update tests when changing parser/patching logic (especially `apply_ops_to_markdown`).
- Include a short note in PR description if your change affects automation or schemas so reviewers can exercise the dry-run workflows.

Contact / help
- If you're unsure about enabling or changing automation, open an issue and tag `@maintainers` for guidance.
