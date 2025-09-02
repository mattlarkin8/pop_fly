# Roadmap

This document tracks planned and in-progress work beyond the PRD’s current release scope. The PRD (`PRD.md`) stays stable and outcome-focused for the active release; this roadmap is a living plan we’ll update as priorities shift.

Status legend: 🟢 Done · 🟡 In progress · ⚪ Planned
Last updated: 2025-09-01

## Now (target: next minor release)
- API/CLI parity tests for rounding and formats (⚪ Planned)
  - Acceptance: shared cases in `tests/` prove CLI and `/api/compute` return identical values for distance, azimuth, slant, and ΔZ with the same precision.
- Input validation and friendly errors (⚪ Planned)
  - Acceptance: invalid E/N/Z tokens and malformed MGRS-digit pairs return 400 (API) and non-zero exit (CLI) with actionable messages; covered by unit tests.
- OpenAPI polish and examples (⚪ Planned)
  - Acceptance: `/docs` shows example requests/responses matching `src/pop_fly/web/app.py::ComputeResponse`; version and health documented.
- CI: build + test matrix (⚪ Planned)
  - Acceptance: CI builds frontend, runs Python unit tests on 3.11+, and publishes artifacts (dist + coverage). Fails on lint/test errors.

## Next
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
