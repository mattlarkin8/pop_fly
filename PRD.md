# Mortar Calc — Distance & Direction Calculator PRD

Version: 2.0  
Owner: You  
Date: 2025-09-01

## summary
A Python-based calculator for distance and direction between two points using MGRS numeric inputs (eastings/northings digits only), now with a local web UI and an HTTP API. Scope remains intentionally narrow: input is MGRS digits only for E/N (with optional elevation Z in meters); computation is planar Euclidean; output distance is meters; direction is NATO mils (6400 mils per circle). When both start and end elevations are provided, the tool also reports slant distance and delta Z. The tool assumes grid north equals true north for azimuth reporting. To keep operation simple and because our maximum computed distance is ≤4,000 m, MGRS zone and 100k grid square letters are intentionally ignored; both points are assumed to be within the same implicit 100k square.

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
- Given two MGRS-digit points with elevations, compute horizontal distance, azimuth (mils), slant distance, and delta Z.

## scope 
- Input format: MGRS digits only for eastings and northings (excluding MGRS zone and 100k letters); +x is east, +y is north; optional Z (meters) for elevation. Easting and northing components are 1–5 digits each and are expanded to meters by padding to 5 digits (e.g., 037 → 3700 m, 051 → 5100 m). Zone and 100k letters are intentionally ignored given the ≤4 km max range and assumption that both points share the same 100k grid square.
- Output: distance in meters; azimuth in NATO mils (grid). If Z present for both points, also output slant distance (m) and delta Z (m).
- Interfaces: CLI, importable Python function, local HTTP API, and a Web UI served by the backend.
- Accuracy target: ≤2 m error for distances ≤4 km under typical conditions.

## functional requirements 
1. input handling (all interfaces)
  - Units: meters (floats). Implicit scaling for E/N digits: 1–5 digits expanded to meters by padding to 5 digits.
  - Format: MGRS-digit pairs with optional Z as floats. Inputs may be provided as numeric strings to preserve leading zeros (recommended) or numbers.
  - Independence: start and end can be set independently. Persisted start may be used in CLI; Web UI uses browser localStorage (see below).

2. computation (shared by all interfaces)
  - Horizontal distance: `dx = E2 - E1; dy = N2 - N1; distance_m = sqrt(dx^2 + dy^2)`.
  - Elevation delta (if Z1 and Z2 provided): `delta_z_m = Z2 - Z1`.
  - Slant distance (if Z1 and Z2 provided): `slant_distance_m = sqrt(distance_m^2 + delta_z_m^2)`.
  - Bearing (deg): `(atan2(dx, dy) * 180/pi + 360) % 360` (north-referenced; grid assumed ≡ true).
  - Direction output (mils): `azimuth_mils = deg * 6400 / 360`.

3. output (all interfaces) 
  - Human-readable (no elevation): `Distance: 1234 m | Azimuth: 2190 mils`.
  - Human-readable (with elevation): `Distance: 1234 m | Azimuth: 2190 mils | Slant: 1250 m | ΔZ: +80 m`.
  - ΔZ presentation: always include an explicit sign prefix (+/-) in human-readable output.
  - JSON (no elevation): `{ "format": "mgrs-digits", "start": [E1, N1], "end": [E2, N2], "distance_m": 1234.0, "azimuth_mils": 2190.0 }`.
  - JSON (with elevation): `{ "format": "mgrs-digits", "start": [E1, N1, Z1], "end": [E2, N2, Z2], "distance_m": 1234.0, "slant_distance_m": 1250.0, "delta_z_m": 80.0, "azimuth_mils": 2190.0 }`.
  - Rounding rules: distances (including slant and ΔZ) rounded to `precision` (default 0); azimuth rounded to 0.1 mil.

4. cli interface (existing)
  - Command: `mortar-calc` (or `mortar_calc.py` if not installed).
  - Flags:
  - `--start "EEE,NNN" --end "EEE,NNN"` OR `--start "EEE,NNN,Z" --end "EEE,NNN,Z"` (E/N are 1–5 MGRS digits; Z in meters)
  - `--set-start "EEE,NNN"` (optional; saves a persistent default start point)
    - `--clear-start` (optional; removes any saved default start)
    - `--show-start` (optional; prints the saved default start, if any)
    - `--json` (optional)
    - `--precision <int>` (default: meters 0, mils 1)
  - Examples:
  - `mortar-calc --set-start "037,050,50"` (save start once, with elevation)
  - `mortar-calc --end "051,070,130"` (uses saved start; computes slant and ΔZ)
  - `mortar-calc --start "037,050" --end "051,070"` (horizontal only)
  - `mortar-calc --start "037,050,50" --end "051,070,130"` (horizontal + slant)

5. http api (new) 
  - Framework: FastAPI; bind local-only (127.0.0.1:8000).
  - Endpoints:
    - `POST /api/compute` → request `{ start: [..], end: [..], precision?: int }` → response JSON as described above with rounding.
    - `GET /api/health` → `{ "status": "ok" }`.
    - `GET /api/version` → `{ "version": "x.y.z" }`.
  - Validation: start and end must be arrays of length 2 or 3; E/N entries must be numeric strings (recommended, to preserve leading zeros) or numbers and represent 1–5 digits prior to expansion; values must be finite; 400 on invalid input.
  - Static hosting: production build of the frontend served at `/` and assets at `/assets/*` by FastAPI.

6. web ui (new) 
  - Stack: React + TypeScript + Vite + React-Bootstrap (Bootstrap 5 CSS).
  - Functionality:
    - Inputs for Start (E,N,[Z]) and End (E,N,[Z]).
    - Precision selector.
    - Save Start to browser localStorage and toggle "Use saved start".
    - Compute calls `POST /api/compute`; display human-readable line and optional raw JSON view.
  - Validation: numeric-only, finite; clear inline error messages.
  - ΔZ formatting: explicit `+/-` sign when both Z values are present.
  - Dev flow: Vite dev server proxies `/api/*` to FastAPI; prod build is served by FastAPI.

7. library api (existing) 
  - Function: `compute_distance_bearing_xy(start: tuple[float, float] | tuple[float, float, float], end: tuple[float, float] | tuple[float, float, float]) -> Result`
  - Result dataclass:
    - `distance_m: float` (horizontal)
    - `slant_distance_m: float | None`
    - `delta_z_m: float | None`
    - `azimuth_mils: float`
    - `normalized_inputs: dict` (echoed XY(Z) values)

## non-functional requirements
- Performance: single run <100 ms; API request/response minimal overhead.
- Portability: Windows/macOS/Linux; Python 3.11+.
- Reliability: predictable output; clear errors with exit codes (CLI) and HTTP 4xx/5xx (API).
- Maintainability: compact, well-tested code with minimal dependencies; frontend kept simple.
- Security: local-only server (bind 127.0.0.1), no auth, no CORS in production (same-origin).

## assumptions 
- 2D horizontal distance is always computed; elevation is optional and only used for slant distance when both Z values are present.
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
- Persistence for default start in Web UI uses browser localStorage only.

## dependencies 
- Core/CLI: standard library only (`math`, `argparse`, `json`, `dataclasses`, `typing`, `pathlib`, `os`).
- Backend (web optional): `fastapi`, `uvicorn`.
- Frontend: React + TypeScript + Vite, `react-bootstrap`, `bootstrap`.

## cli ux 
- Clear usage/help with examples.
- Echo parsed inputs when `--json` is used.
- Persisted start storage: platform-appropriate config path (Windows: `%APPDATA%/Mortar Calc/config.json`; macOS: `~/Library/Application Support/Mortar Calc/config.json`; Linux: `$XDG_CONFIG_HOME/mortar-calc/config.json` or `~/.config/mortar-calc/config.json`).
- When a persisted start exists and `--start` is omitted, use saved start; if neither is present, return a clear error.
- When a persisted start includes Z and an `--end` with Z is provided, compute slant/ΔZ; otherwise compute horizontal only.

## web ui ux 
- Single-page app with a form: Start (E,N,[Z]), End (E,N,[Z]), precision, Save/Use saved start controls.
- Results panel renders human-readable output and optional JSON tab.
- Invalid inputs highlighted with inline messages.
- Runs at `http://127.0.0.1:8000/` by default.

## validation and testing 
- Unit tests (existing): core computations; CLI behaviors (persistence, formatting).
- API tests: FastAPI TestClient for happy paths (XY, XY+Z), zero distance, rounding, invalid payloads (400).
- Frontend tests (optional): light smoke tests for ΔZ sign formatting and form validation.
- Manual smoke: Web UI save/use start, compute with/without Z, error display, refresh persistence.

## acceptance criteria 
- CLI: returns distance (m) and azimuth (mils); with both Z values, returns slant_distance_m and delta_z_m; JSON and human-readable outputs follow rules above; exit code 2 on usage errors; ΔZ sign explicit.
- API: `POST /api/compute` returns JSON matching the CLI’s JSON structure and rounding; `GET /api/health` and `/api/version` function; invalid inputs return HTTP 400 with message.
- Web UI: users can enter start/end (with optional Z), set precision, save/use start in localStorage, compute results; human-readable output matches CLI formatting (including signed ΔZ), and optional raw JSON view is correct.
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
- Azimuth: `mortar-calc --start "037,050" --end "051,070"`
- Persisted start workflow:
  - `mortar-calc --set-start "037,050"`
  - `mortar-calc --end "051,070"`
