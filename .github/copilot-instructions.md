## High-level plan
- Summarize architecture and component boundaries.
- List concrete developer workflows (build/test/run/debug) with exact commands and environment hints.
- Call out project-specific patterns and parsing rules with code references.
- Note integration points and environment variables.

## Checklist of what this file covers
- Big-picture architecture and why (CLI, library, FastAPI web + React frontend).  
- How to run and test locally (venv, entry points, test discovery).  
- Project-specific parsing/units/rounding rules with code pointers.  
- Config, env vars, and static hosting details.  

## Architecture (big picture)
- Core library: pure Python computational functions in `src/pop_fly/core.py` (stateless, stdlib only). Key function: `compute_distance_bearing_xy(start, end)` which returns a `Result` dataclass. See `tests/test_core.py` for examples.
- CLI: thin wrapper in `src/pop_fly/cli.py` that parses MGRS-digit shorthand, persists a saved start to a platform-specific config file, and formats human/JSON output. Entry point declared in `pyproject.toml` as `pop_fly = "pop_fly.cli:main"`.
- Web API + static UI: FastAPI app in `src/pop_fly/web/app.py` exposes `/api/compute`, `/api/health`, `/api/version`. In production it attempts to mount the built frontend at `frontend/dist`.
- Frontend: Vite + React + TypeScript located under `frontend/`. Dev mode uses Vite dev server (proxy) -> FastAPI for `/api/*`.

## Developer workflows (commands & hints)
- Python version: requires Python 3.11+. Virtualenv used in repo is `.venv/` in workspace root in typical dev setup.
- Run unit tests (same as the workspace task):
  - Activate virtualenv on Windows PowerShell: `& .venv\Scripts\Activate.ps1`
  - Run tests: `python -m unittest discover -s tests -p "test_*.py"` (the workspace task `run tests` runs this exact command).
- Install developer dependencies (recommended) after creating/activating a virtualenv:
  - `python -m pip install -r requirements-dev.txt`
  - This replaces ad-hoc `pip install` calls in automation scripts; prefer installing once in your dev environment.
- Run the CLI directly (dev): `python -m pop_fly.cli --start "037,050" --end "051,070"` or install editable and run `pop_fly --start "037,050" --end "051,070"`.
- Run the web server locally (dev or prod): use the entry point `pop_fly_web` (declared in `pyproject.toml`) or run uvicorn directly: `uvicorn pop_fly.web.app:app --host 127.0.0.1 --port 8000` (the app's `main()` function uses `uvicorn.run`).

## Important environment variables and config paths
- POP_FLY_CONFIG_DIR: if set, overrides persisted config location. Otherwise `src/pop_fly/cli.py` resolves platform paths:
  - Windows: `%APPDATA%/pop_fly/config.json` (fallback to `%USERPROFILE%/AppData/Roaming/...`).
  - macOS: `~/Library/Application Support/pop_fly/config.json`.
  - Linux: `$XDG_CONFIG_HOME/pop_fly/config.json` or `~/.config/pop_fly/config.json`.
- POP_FLY_HOST / POP_FLY_PORT: FastAPI `main()` reads these when running the built server.

## Project-specific conventions & patterns (do not change these without tests)
- MGRS-digit shorthand parsing: `src/pop_fly/core.py::_parse_pair_mgrs_digits` expands each E/N token (1–5 digit integer string) by scaling to 5-digit meters: scale = 10**(5-len(token)). Example: `"037,050"` -> E=3700 m, N=5000 m. The third token (Z) is treated as meters and NOT scaled. Reference: `_parse_pair_mgrs_digits`.
- Bearing computation: uses atan2(dx, dy) with north-reference, converted to NATO mils via deg * 6400 / 360. See `_bearing_deg_from_deltas` and `_deg_to_mils`.
- Rounding rules observed in the repo:
  - Distances and slant/deltaZ: rounded to `precision` (CLI and API accept `precision` integer).
  - Azimuth: rounded to one decimal place (0.1 mil) in both CLI and API.
- Signed delta-Z formatting: CLI uses `_format_signed` to always show explicit `+`/`-` for ΔZ in human output.

## API contract (FastAPI)
- POST /api/compute
  - Body: `{ "start": [E, N] or [E, N, Z], "end": [...], "precision": int }`. E/N may be numeric strings to preserve leading zeros.
  - Response: JSON with `format`, `start`, `end`, `distance_m`, `azimuth_mils`, optional `slant_distance_m`, `delta_z_m`. See `src/pop_fly/web/app.py::ComputeResponse`.
  - Validation: 400 on malformed inputs; server code reuses `_parse_pair_mgrs_digits` for canonicalization.

## Tests and verification
- Core unit tests in `tests/test_core.py` exercise cardinals, zero distance, and elevation cases. Use these to validate any change to math or rounding.
- CLI tests exist in `tests/test_cli.py` and API tests (if added) should target `src/pop_fly/web/app.py` behavior, ensuring rounding parity between CLI and API.

## Where to look for examples
- CLI parsing, persistence, and human/JSON output: `src/pop_fly/cli.py`.
- Core math, parsing, and Result object: `src/pop_fly/core.py`.
- API validation, pydantic models, and static mount logic: `src/pop_fly/web/app.py`.
- Test examples: `tests/test_core.py`, `tests/test_cli.py`.
- Packaging & entry points: `pyproject.toml` (look for `[project.scripts]`).

## Debugging tips
- To reproduce CLI behavior locally without installing: run `python -m pop_fly.cli ...` inside the activated venv.
- To test API handlers without starting the server, import `pop_fly.web.app` and exercise `compute()` via TestClient from `fastapi.testclient`.
- If static frontend isn't served in production, verify `frontend/dist` exists; the app mounts that directory if present.
 
Local dev setup (recommended):
1. Create a virtualenv in repo root: `python -m venv .venv`
2. Activate (PowerShell): `& .venv\Scripts\Activate.ps1`
3. Install dev deps: `python -m pip install -r requirements-dev.txt`
4. Run tests: `python -m unittest discover -s tests -p "test_*.py"`

## Small gotchas
- The library intentionally ignores MGRS zone and 100k letters — inputs are only the numeric digits. Ensure callers provide values in the same implicit 100k grid.
- Elevation (Z) must be provided for both start and end to compute slant and ΔZ; otherwise only horizontal distance and azimuth are returned.
- Azimuth uses grid-as-true convention; this is documented in PRD and used throughout code/tests.

## Issue comment safeguards

- Before posting an automation-triggering comment (for example `/plan` or `/implement`), read the issue's recent comments and skip posting if any of the following are true:
  - A recent comment (last 24 hours) is exactly `/plan` or `/implement`.
  - A recent comment contains the string `Automated plan (` indicating the workflow already produced a plan.
- Debounce: if the assistant itself posted a `/plan` within the last 2 minutes, do not post again automatically.
- Single-responsibility: post at most one trigger comment per issue unless explicitly asked to retry; wait for the workflow result and show the maintainer the generated plan before re-triggering.
- When a skip occurs, post a single informative comment (once) explaining why the trigger was skipped and what the user can do to force a rerun (for example, add a comment `force:/plan` or re-run the workflow).

## Documentation editing rules (Markdown docs)

These rules align with our docs automation (see `scripts/generate_docs.py`) and should be followed for any manual or automated edits to Markdown docs.

- Scope and targets
  - Default targets are Markdown docs. E.g. `README.md`, `PRD.md`, `**/*.md`.
  - Prefer section-level or marker-based edits; avoid rewriting entire documents.
  - Avoid editing non-doc files or Markdown outside this scope unless explicitly requested or clearly part of the PR’s doc changes.

- Allowed operations (structured)
  - Use heading/marker-based ops that mirror automation capabilities:
    - replace_section(heading, content)
    - append_to_section(heading, content)
    - upsert_section(heading, level, content)
    - replace_block_by_marker(name, content) using markers: `<!-- AUTO-DOC:NAME -->` ... `<!-- /AUTO-DOC:NAME -->`
  - When multiple sections share the same heading, include an optional 1-based `occurrence` to disambiguate which instance to edit. If `occurrence` is omitted, automation will default to the first matching heading and emit a warning. Prefer specifying `occurrence` when ambiguity is likely.

- Safety and style constraints
  - Keep changes minimal and localized; preserve heading text, hierarchy, and surrounding formatting.
  - Limit to at most 6 operations per file in one pass (be conservative to ease review).
  - Don’t shrink a file by more than ~40%; large deletions require human review and explicit approval.
  - Maintain existing tone and style; keep relative links intact; don’t alter anchors unless necessary.
  - Preserve code fences and languages; for Windows examples, prefer PowerShell syntax and separate commands per line.
  - Avoid placeholders like “TBD”/“TODO”; prefer concrete, testable statements or omit.
  - It’s acceptable to update existing sections even when headings are duplicated, provided edits stay scoped to the selected section. Use `occurrence` to target the right one.

- Validation and parity with automation
  - When producing machine-readable edits, conform to the JSON schema in `docs/schema/docs_ops.json` (which supports an optional `occurrence` field) and the op types above.
  - Prefer marker replacements for recurring, auto-managed blocks.
  - After edits, generate a small unified diff for review; summarize warnings (e.g., skipped ambiguous headings).