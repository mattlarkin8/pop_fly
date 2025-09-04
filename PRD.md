# Pop Fly — Distance & Direction Calculator PRD

Version: 2.1
Owner: You  
Date: 2025-09-01

See also: [ROADMAP.md](./ROADMAP.md) for planned features and upcoming milestones.

## summary
A Python-based calculator for distance and direction between two points using MGRS numeric inputs (eastings/northings digits only), now with a local web UI and an HTTP API. Scope remains intentionally narrow: input is MGRS digits only for E/N; computation is planar Euclidean; output distance is meters; direction is NATO mils (6400 mils per circle). Elevation is not supported as of v2.0.0. The tool assumes grid north equals true north for azimuth reporting. To keep operation simple and because our maximum computed distance is ≤4,000 m, MGRS zone and 100k grid square letters are intentionally ignored; both points are assumed to be within the same implicit 100k square.

Components: 
- Library: pure Python core function for calculations.
- CLI: existing command-line tool.
- Web: local-only FastAPI backend exposing a small API and serving a React + TypeScript + React-Bootstrap single-page app.

## primary goals
- Accurately compute 2D horizontal distance and azimuth between two points from MGRS-digit inputs only.
- Provide a fast, offline CLI, a local-only HTTP API, and a small Python API for reuse.
- Offer robust validation and helpful error messages across CLI, API, and Web UI.

## stretch goals 
- Optional packaging into a single executable for easy distribution.
- Docker packaging for the API + static UI.
- Map or visual aids in the Web UI (out of scope for this release).

## users and scenarios
- FO/FDC or field user on a local grid who needs distance and azimuth quickly (≤4 km typical) via a web page or CLI.
- Engineer needing programmatic distance/bearing in scripts (Python API) or simple integrations (HTTP API).

Example scenarios:
- Given two points using MGRS digits (same implicit 100k grid), compute distance and azimuth (mils).

## scope 
- Input format: MGRS digits only for eastings and northings (excluding MGRS zone and 100k letters); +x is east, +y is north. Easting and northing components are 1–5 digits each and are expanded to meters by padding to 5 digits (e.g., 037 → 3700 m, 051 → 5100 m). Zone and 100k letters are intentionally ignored given the ≤4 km max range and assumption that both points share the same 100k grid square.
- Output: distance in meters; azimuth in NATO mils (grid).
- Interfaces: CLI, importable Python function, local HTTP API, and a Web UI served by the backend.
- Accuracy target: ≤2 m error for distances ≤4 km under typical conditions.

## functional requirements 
1. input handling (all interfaces)
  - Units: meters (floats). Implicit scaling for E/N digits: 1–5 digits expanded to meters by padding to 5 digits.
  - Format: MGRS-digit pairs with optional Z as floats. Inputs may be provided as numeric strings to preserve leading zeros (recommended) or numbers.
  - Independence: start and end can be set independently. Persisted start may be used in CLI; Web UI uses browser localStorage (see below).

2. computation (shared by all interfaces)
  - Horizontal distance: `dx = E2 - E1; dy = N2 - N1; distance_m = sqrt(dx^2 + dy^2)`.
  - Bearing (deg): `(atan2(dx, dy) * 180/pi + 360) % 360` (north-referenced; grid assumed ≡ true).
  - Direction output (mils): `azimuth_mils = deg * 6400 / 360`.

3. output (all interfaces) 
  - Human-readable: `Distance: 1234 m | Azimuth: 2190 mils`.
  - JSON: `{ "format": "mgrs-digits", "start": [E1, N1], "end": [E2, N2], "distance_m": 1234.0, "azimuth_mils": 2190.0 }`.
  - Rounding rules: distances rounded to `precision` (default 0); azimuth rounded to 0.1 mil.

4. cli interface (existing)
  - Command: `pop_fly` (or module entry if not installed).
  - Flags:
  - `--start "EEE,NNN" --end "EEE,NNN"` (E/N are 1–5 MGRS digits)
  - `--set-start "EEE,NNN"` (optional; saves a persistent default start point)
    - `--clear-start` (optional; removes any saved default start)
    - `--show-start` (optional; prints the saved default start, if any)
    - `--json` (optional)
    - `--precision <int>` (default: meters 0, mils 1)
  - Examples:
  - `pop_fly --set-start "037,050"` (save start once)
  - `pop_fly --start "037,050" --end "051,070"`

5. http api (new) 
  - Framework: FastAPI; bind local-only (defaults to 127.0.0.1:8000; override with POP_FLY_HOST / POP_FLY_PORT).
  - Endpoints:
  - `POST /api/compute` → request `{ start: [E, N], end: [E, N], precision?: int }` → response JSON as described above with rounding.
    - `GET /api/health` → `{ "status": "ok" }`.
    - `GET /api/version` → `{ "version": "x.y.z" }`.
  - Validation: start and end must be arrays of length exactly 2; E/N entries must be numeric strings (recommended, to preserve leading zeros) or numbers representing 1–5 digits prior to expansion; values must be finite.
    - Shape/type errors are rejected by Pydantic with HTTP 422.
    - Business-rule errors (e.g., non-digit E/N tokens, out-of-range lengths) are returned as HTTP 400 with a message.
  - Static hosting: production build of the frontend served at `/` and assets at `/assets/*` by FastAPI.

6. web ui (new) 
  - Stack: React + TypeScript + Vite + React-Bootstrap (Bootstrap 5 CSS).
  - Functionality:
    - Inputs for Start (E,N) and End (E,N).
    - Precision selector.
    - Save Start to browser localStorage and toggle "Use saved start".
    - Compute calls `POST /api/compute`; display human-readable line and optional raw JSON view.
  - Validation: numeric-only, finite; clear inline error messages.
  - Dev flow: Vite dev server proxies `/api/*` to FastAPI; prod build is served by FastAPI.

7. library api (existing) 
  - Function: `compute_distance_bearing_xy(start: tuple[float, float], end: tuple[float, float]) -> Result`
    - Result dataclass:
      - `distance_m: float` (horizontal)
      - `azimuth_mils: float`

## non-functional requirements
- Performance: single run <100 ms; API request/response minimal overhead.
- Portability: Windows/macOS/Linux; Python 3.11+.
- Reliability: predictable output; clear errors with exit codes (CLI) and HTTP 4xx/5xx (API).
- Maintainability: compact, well-tested code with minimal dependencies; frontend kept simple.
- Security: local-only server (bind 127.0.0.1), no auth, no CORS in production (same-origin).

## assumptions 
- 2D horizontal distance is always computed; elevation is not supported.
- Local grid axes: +x east, +y north.
- Grid north is assumed equal to true north; azimuths are reported as grid and treated as true for this tool.
- Distances ≤ ~4 km so planar approximation is appropriate.
 - Web server is used locally on a developer/operator machine; not exposed publicly.

## constraints 
- Offline-only at runtime (no external services). Package installation may fetch dependencies during setup.
- No external CRS libraries required for core XY mode.
- No database for this phase; Web UI persistence is browser localStorage only.

## design 
### coordinate parsing (MGRS digits only)
- Parse `EEE,NNN` pairs (and optional `Z`) where E/N are 1–5 digits; expand digits to meters by padding to 5 digits (e.g., `037 → 3700 m`, `00000 → 0 m`). Zone and 100k letters are intentionally ignored to keep the tool simple and because they’re unnecessary when distances ≤4 km and both points share the same 100k square.
- Validate finite numeric values in all interfaces.

### computation (planar)
- Distance: `sqrt((E2-E1)^2 + (N2-N1)^2)`.
- Bearing (deg): `(atan2(ΔE, ΔN) * 180/pi + 360) % 360`.
- Convert to mils: `deg * 6400 / 360`.

### units
- Distance: meters only.
- Direction: NATO mils only (6400 per circle).

### error handling
- Missing or malformed inputs → descriptive error (CLI) or HTTP 400 (API).
- Non-finite values → error.

### web architecture
- FastAPI serves API routes and, in production, the built React app.
- Dev mode uses Vite dev server with proxy to FastAPI for `/api/*`.
- On server startup, the backend attempts to build the frontend (runs `npm ci` or `npm install` and `npm run build` in `frontend/`); skip via `POP_FLY_SKIP_FRONTEND_BUILD=1`.
- Persistence for default start in Web UI uses browser localStorage only.

## dependencies 
- Core/CLI: standard library only (`math`, `argparse`, `json`, `dataclasses`, `typing`, `pathlib`, `os`).
- Backend (web optional): `fastapi`, `uvicorn`.
- Frontend: React + TypeScript + Vite, `react-bootstrap`, `bootstrap`.

## cli ux 
- Clear usage/help with examples.
- Echo parsed inputs when `--json` is used.
- Persisted start storage: platform-appropriate config path (Windows: `%APPDATA%/pop_fly/config.json`; macOS: `~/Library/Application Support/pop_fly/config.json`; Linux: `$XDG_CONFIG_HOME/pop_fly/config.json` or `~/.config/pop_fly/config.json`).
- When a persisted start exists and `--start` is omitted, use saved start; if neither is present, return a clear error.
- Persisted start is 2D only.

## web ui ux 
- Single-page app with a form: Start (E,N,[Z]), End (E,N,[Z]), precision, Save/Use saved start controls.
- Results panel renders human-readable output and optional JSON tab.
- Invalid inputs highlighted with inline messages.
- Runs at `http://127.0.0.1:8000/` by default (configurable via POP_FLY_HOST/POP_FLY_PORT).

## validation and testing 
- Unit tests (existing): core computations; CLI behaviors (persistence, formatting).
- API tests: FastAPI TestClient for happy paths (XY, XY+Z), zero distance, rounding, invalid payloads (400).
- Frontend tests (optional): light smoke tests for ΔZ sign formatting and form validation.
- Manual smoke: Web UI save/use start, compute with/without Z, error display, refresh persistence.

## automation (workflows & scripts)
- Architecture guard (scripts/architecture_guard.py): CI-time invariant checks to prevent prohibited tech or contract drift; blocks merges on violation.
- Docs generator (scripts/generate_docs.py): On merged PRs, proposes and applies small README/PRD edits through structured ops validated against `docs/schema/docs_ops.json`. Creates a docs PR; in dry-run writes previews to tmp/.
- Issue planning (scripts/ai_plan_issue.py): On `/plan` issue comment, posts a concise plan; validates against `docs/schema/plan_schema.json` when not in dry-run.
- Roadmap sync (scripts/roadmap_to_issues.py): Converts ROADMAP.md bullets to issues with section/status labels; idempotent; optional inclusion of unannotated bullets via env.
- PR checklist (scripts/update_pr_checklist.py): Maintains a task checklist in PR body based on the linked issue’s latest plan and commit messages.
- Scaffold from plan (scripts/scaffold_from_plan.py): Optional guarded code generation from `feature-plan.md` under profile constraints (allowed paths, budgets, forbidden imports/paths, optional required PR label).

Env vars: OPENAI_API_KEY (LLM), PLAN_MODEL, GITHUB_TOKEN/REPOSITORY/EVENT_PATH, DRY_RUN, ROADMAP_INCLUDE_UNANNOTATED, AUTOMATION_PROFILE. Safety policies: dry-run modes, schema validation, per-file op caps, file/line budgets, allowed path enforcement, forbidden import checks, and PR label gating.

## acceptance criteria 
- CLI: returns distance (m) and azimuth (mils); with both Z values, returns slant_distance_m and delta_z_m; JSON and human-readable outputs follow rules above; exit code 2 on usage errors; ΔZ sign explicit.
- API: `POST /api/compute` returns JSON matching the CLI’s JSON structure and rounding; `GET /api/health` and `/api/version` function; invalid inputs return HTTP 400 with message.
- Web UI: users can enter start/end, set precision, save/use start in localStorage, compute results; human-readable output matches CLI formatting, and optional raw JSON view is correct.
- Server runs locally at 127.0.0.1:8000 serving both API and static UI in production.

## milestones & timeline 
1. Day 1: FastAPI API (`/api/compute`, `/api/health`, `/api/version`) with tests; Vite React TS scaffold; basic API client/types.
2. Day 2: React-Bootstrap UI (form, validation, localStorage), wiring to API; dev proxy; manual smoke.
3. Day 3: Production integration (serve static via FastAPI), README updates, polish, optional frontend smoke tests.

## risks & mitigations 
- Grid ≡ true north assumption: clearly documented in help/README and UI.
- Rounding drift between CLI and API: unify rounding rules in backend and test both.
- Dev-time CORS friction: use Vite proxy to avoid CORS; in production serve same-origin.
- Scope creep on UI styling: stick to React-Bootstrap defaults and minimal theming.

## appendix: quick formulas 
- Distance: `sqrt(ΔE^2 + ΔN^2)`
- Grid bearing (deg): `(atan2(ΔE, ΔN) * 180/π + 360) % 360`
- NATO mils: `mils = deg * 6400 / 360`

## examples 
- Azimuth: `pop_fly --start "037,050" --end "051,070"`
- Persisted start workflow:
  - `pop_fly --set-start "037,050"`
  - `pop_fly --end "051,070"`

## automated docs generation
A new workflow and script for automated documentation generation have been introduced. This includes a safe Markdown applier and tests to ensure that section-anchored updates are accurately reflected in the documentation, leveraging LLM context for precision.