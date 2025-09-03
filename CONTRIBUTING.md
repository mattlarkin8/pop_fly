# Contributing — automation & docs generation

This repository includes automated helpers that call LLMs to generate implementation plans and documentation updates. Safety-first defaults are enforced: automation runs in dry-run mode by default, outputs are validated when possible, and CI only produces artifacts for review.

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
- A dedicated workflow runs `generate_docs.py --dry-run` on merges to `main` and uploads `tmp/docs-dryrun/` as an artifact for human review. The repository does not auto-apply docs edits by default.

Security & secrets
- Keep `OPENAI_API_KEY` and other secrets in repository secrets only. Do not print or commit secrets.
- CI exposes model keys only to protected branches and trusted workflows. DO NOT run LLM calls on untrusted forked PRs.

When to enable auto-apply
- Auto-apply (create PRs automatically) increases risk. To propose enabling it:
  1. Open an issue describing the proposed automation scope and safety checks (schemas, diff-size caps, allowed paths).
  2. Provide a runbook showing how to disable the automation and how to audit recent automated PRs.
 3. Get at least one approval from a project maintainer before adding any secrets or workflow changes to enable auto-apply.

Tests and contribution checklist
- Run unit tests and linters before opening a PR.
- Add or update tests when changing parser/patching logic (especially `apply_ops_to_markdown`).
- Include a short note in PR description if your change affects automation or schemas so reviewers can exercise the dry-run workflows.

Contact / help
- If you're unsure about enabling or changing automation, open an issue and tag `@maintainers` for guidance.
