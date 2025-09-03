# Roadmap

This document tracks planned and in-progress work beyond the PRD’s current release scope. The PRD (`PRD.md`) stays stable and outcome-focused for the active release; this roadmap is a living plan we’ll update as priorities shift.

Status legend: 🟢 Done · 🟡 In progress · ⚪ Planned
Last updated: 2025-09-02

## Automation hooks
- Roadmap sync: pushing changes to `ROADMAP.md` auto-creates/updates GitHub issues per bullet with labels [`roadmap`, `Now|Next|Later`]. Inline `#123` references are respected.
- Issue planning: comment `/plan` on an issue (or run the workflow manually) to post a concise AI-generated task plan; optional JSON schema validation uses `docs/schema/plan_schema.json` if present.
- Guarded scaffolding: push a branch `feature/plan-**` or comment `/implement` to open/update a PR based on the plan. The scaffolder only writes within `src/`, `tests/`, `frontend/`, and `scripts/`, and skips risky edits.
- PR checklist: a workflow keeps a task checklist in the PR body in sync with the plan and commit messages.
- CI: Python unit tests run (3.11) and the frontend build runs on every PR/push; expanding to a Python version matrix and coverage is tracked below.
- Post-merge docs: a docs generator proposes targeted README/PRD edits (dry-run artifacts uploaded). Enabling auto-PR behind a label will be considered.

## Now (target: next minor release)
- API/CLI parity tests for rounding and formats (🟡 In progress)
  - Acceptance: shared cases in `tests/` prove CLI and `/api/compute` return identical values for distance, azimuth, slant, and ΔZ with the same precision.
- Input validation and friendly errors (🟡 In progress)
  - Acceptance: invalid E/N/Z tokens and malformed MGRS-digit pairs return 400 (API) and non-zero exit (CLI) with actionable messages; covered by unit tests.
- OpenAPI polish and examples (⚪ Planned)
  - Acceptance: `/docs` shows example requests/responses matching `src/pop_fly/web/app.py::ComputeResponse`; version and health documented.
- CI: build + test matrix (⚪ Planned)
  - Acceptance: CI builds frontend, runs Python unit tests on 3.11+, and publishes artifacts (dist + coverage). Fails on lint/test errors.
- Docs automation: auto-PR behind label (🟡 In progress)
  - Acceptance: when a merged PR carries label `docs:auto`, the docs generator opens a PR with proposed README/PRD edits (guarded by schema validation and shrink-safety), otherwise remains dry-run only.

## Next
- CI: Python version matrix and coverage reporting (⚪ Planned)
  - Acceptance: CI runs Python tests on 3.11–3.13, posts a coverage summary to the job log, and uploads coverage XML and frontend `dist/` as artifacts.
- OpenAPI: route tags and in-line examples (⚪ Planned)
  - Acceptance: routes are tagged (health/version/compute), and both schema- and route-level examples appear under `/docs`, improving discoverability and client generation.
- Frontend UX: presets, copy/share, JSON view (⚪ Planned)
  - Acceptance: inputs with leading zeros preserved, shareable URLs, and a toggle to view raw JSON.
- Web theme: OD green color scheme (⚪ Planned)
  - Acceptance: apply an OD green palette via Bootstrap theme variables or CSS variables; maintain WCAG AA contrast for text and controls; no layout regressions.
- Web UI: sidebar for target position storage (⚪ Planned)
  - Acceptance: sidebar allows saving, naming, listing, selecting, and deleting target positions; data persisted in browser localStorage; leading zeros preserved for E/N; "Use target" action fills Start/End; optional JSON export/import.

## Later
- Packaging & deployment (Docker/OCI, release bundles) (⚪ Planned)
  - Acceptance: single `docker run` brings up API + static UI; version endpoint reports build info (commit/date).

## Milestones (themes)
- v0.2 — Confidence: tests and developer ergonomics
- v0.3 — Inputs and units: full MGRS + conversions
- v0.4 — Visualization and scale: maps, batch, packaging

## Cross-references
- Core math and parsing: `src/pop_fly/core.py` (see `_parse_pair_mgrs_digits`, `_bearing_deg_from_deltas`, `_deg_to_mils`).
- CLI behavior and persistence: `src/pop_fly/cli.py`.
- API contract and models: `src/pop_fly/web/app.py`.
- Tests: `tests/test_core.py`, `tests/test_cli.py`, `tests/test_api.py`.
- Product scope and current goals: `PRD.md`.

## How to propose or track items
- File or link GitHub issues for each roadmap bullet; reference them inline here (e.g., #123).
- Keep bullets outcome-oriented with a one-line acceptance note; collapse to 🟢 Done with a PR link when complete.
