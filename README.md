# Pop Fly

Distance and azimuth calculator for local MGRS digits (2D only; no elevation) with selectable mil systems (NATO 6400 or RU/Warsaw 6000) and persisted faction preference.

Quick usage (after installing into a Python 3.11+ env):

- Set a default start (MGRS digits):
  pop_fly --set-start "037,050"
- Persist a default faction (NATO 6400 is default; RU/Warsaw 6000 optional):
  pop_fly --set-faction ru
- Compute between two points (uses saved start when --start omitted):
  pop_fly --end "051 070"
- Override faction just for this run:
  pop_fly --end "051 070" --faction ru
- JSON output:
  pop_fly --end "150 300" --json
- Show/Clear persisted start:
  pop_fly --show-start   (Shows persisted faction if set.)
  pop_fly --clear-start

Inputs:
- Quoted pairs: "EEE,NNN" where E/N are 1–5 digit MGRS digits (comma or space separator). Digits are expanded to meters: e.g., 037 → 3700 m, 051 → 5100 m.
- Units: meters; azimuth output in mils using the selected faction:
  - NATO: 6400 mils / circle (default)
  - RU / Warsaw: 6000 mils / circle

Outputs:
- Distance (m) and azimuth (mils). JSON and human-readable output include the `faction` used.

Note: By default on Windows, settings are stored under %APPDATA%/pop_fly/config.json.
This file now stores both `start` (array) and optional `faction` ("nato" or "ru").
You can override the location for tests via POP_FLY_CONFIG_DIR.

Web UI (local) — after installing web extras and building the frontend, run:
- pop_fly_web, then open http://127.0.0.1:8000/

Frontend auto-build before server start
- The `pop_fly_web` command now attempts to build the frontend before starting the API so the latest UI is served from `frontend/dist`.
- It runs `npm ci` (or `npm install` if no `package-lock.json`) and `npm run build` in `frontend/`.
- To skip this step (e.g., when using the Vite dev server), set:

  - PowerShell:
    $Env:POP_FLY_SKIP_FRONTEND_BUILD = "1"; pop_fly_web

## HTTP API

When the server is running, the API is available by default at `http://127.0.0.1:8000`:

- GET `/api/health` → `{ "status": "ok" }`
- GET `/api/version` → `{ "version": "x.y.z" }`
- POST `/api/compute`
  - Body: `{ "start": [E, N], "end": [E, N], "precision": int, "faction"?: "nato" | "ru" }`
  - E/N may be numeric strings to preserve leading zeros (1–5 digits expanded to meters).
  - Response: `{ "format": "mgrs-digits", "start": [...], "end": [...], "distance_m": number, "azimuth_mils": number, "faction": "nato" | "ru" }`
  - Rounding: distances to `precision` (default 0); azimuth to 0.1 mil.
  - If `faction` omitted, defaults to `nato`.

Notes on errors:
- Too few elements in `start`/`end` (e.g., `[E]`) → HTTP 422 (schema validation).
- Extra elements (e.g., `[E, N, Z]`) → HTTP 400 (elevation is no longer supported).
- Well-formed requests that fail business rules (e.g., non-digit E/N tokens) return HTTP 400 with a message.

## Environment variables

- POP_FLY_CONFIG_DIR: override persisted CLI config location (`config.json` in this directory).
- POP_FLY_HOST / POP_FLY_PORT: host/port for the web server (defaults: `127.0.0.1` / `8000`).
- POP_FLY_SKIP_FRONTEND_BUILD: set to `1` to skip building the frontend before starting the server.


## Automation

We use a small set of automation scripts (some LLM-backed) to help generate implementation plans, scaffold features, and propose documentation edits. Safety is a first-class concern: scripts support dry-run modes, CI runs generators in dry-run by default, and multiple policy checks and caps prevent unsafe or broad changes.

Key automation scripts (brief)

- `scripts/architecture_guard.py` — CI-time invariant checks (FastAPI presence, endpoints, core symbols, tests import policy, no Flask). Exits non-zero to block merges on violations.

- `scripts/generate_docs.py` — Post-merge docs updater. Calls an LLM to propose structured ops (validated against `docs/schema/docs_ops.json`), applies safe, minimal edits to `README.md` and `PRD.md`, and creates a docs PR. In dry-run it writes diffs to `tmp/docs-dryrun/`.

- `scripts/ai_plan_issue.py` — Generates a concise plan when someone comments `/plan` on an issue and posts it as a comment. Validates output against `docs/schema/plan_schema.json` (when present) and supports dry-run outputs in `tmp/ai-plan-dryrun/`.

- `scripts/roadmap_to_issues.py` — Converts `ROADMAP.md` bullets (Now/Next/Later) into GitHub Issues with labels and status; idempotent upsert by title or inline `#<num>` reference. Use `ROADMAP_INCLUDE_UNANNOTATED=1` to include unannotated bullets.

- `scripts/update_pr_checklist.py` — Keeps a PR body updated with a checklist derived from the linked issue’s latest plan; checks items off by scanning commit messages and writes the checklist between `<!-- PLAN-CHECKLIST:START -->`/`<!-- PLAN-CHECKLIST:END -->` markers.

- `scripts/scaffold_from_plan.py` — Guarded scaffolding from a `feature-plan.md` on a feature branch. Respects a profile-based policy (`.github/automation_policy.json`) that defines allowed files/dirs, budgets, forbidden imports/paths, and optional PR-label gating. Commits scaffolded edits to the same branch and creates/updates a PR; if no changes are generated, opens a PR containing the plan.

Common env vars for automation

- `GITHUB_TOKEN`: required for GitHub API writes.
- `GITHUB_REPOSITORY`, `GITHUB_EVENT_PATH`, `GITHUB_EVENT_NAME`: provided by Actions runtime.
- `OPENAI_API_KEY`: required for LLM-backed steps.
- `PLAN_MODEL`: model override for scripts (defaults set inside scripts; e.g., `gpt-4o-mini`).
- `DRY_RUN=1`: where supported, prevents writes and saves artifacts under `tmp/`.

- The `generate-docs` workflow now includes a workflow_dispatch that allows for manual runs. A manual run requires an input `pr_number` to select which PR to run the workflow on.

### Notes

- The automation scripts are deliberately conservative: schema validation, per-file op caps, file/line budgets, allowed-path enforcement, forbidden-import checks, and dry-run modes are used to avoid accidental large-scale changes.
- Dry-run artifacts live under `tmp/` (for example `tmp/docs-dryrun/` and `tmp/ai-plan-dryrun/`) for CI inspection.

## Testing

### Developer setup

```powershell
python -m venv .venv
& .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

### Example end-to-end (RU mils)

```powershell
pop_fly --set-start "037,050"
pop_fly --set-faction ru
pop_fly --end "051 070" --json   # azimuth now in 6000-mil system
```

Dry-run behavior & CI

- Use `--dry-run` or `DRY_RUN=1` to prevent network writes; artifacts are written under `tmp/` (for example `tmp/docs-dryrun/` and `tmp/ai-plan-dryrun/`).
- The repository CI runs the docs generator in dry-run mode on merges and uploads artifacts for review. To enable full auto-apply in CI, a guarded workflow and repository secrets (GITHUB_TOKEN, OPENAI_API_KEY) must be configured and reviewed by the team.
