# Pop Fly

Distance and azimuth calculator for local MGRS digits (+optional Z) grids.

Quick usage (after installing into a Python 3.11+ env):

- Set a default start (MGRS digits):
  pop_fly --set-start "037,050,5"
- Compute between two points (uses saved start when --start omitted):
  pop_fly --end "051 070"
- JSON output:
  pop_fly --end "150 300" --json
- Show/Clear persisted start:
  pop_fly --show-start
  pop_fly --clear-start

Inputs:
- Quoted tuples: "EEE,NNN" or "EEE,NNN,Z" where E/N are 1–5 digit MGRS digits (comma or space separator). Digits are expanded to meters: e.g., 037 → 3700 m, 051 → 5100 m. Z is meters.
- Units: meters; azimuth output in NATO mils (6400 mils/circle)

Outputs:
- Distance (m) and azimuth (mils). If both inputs have Z, prints slant distance and ΔZ with explicit sign.

Note: By default on Windows, settings are stored under %APPDATA%/pop_fly/config.json.
You can override the location for tests via POP_FLY_CONFIG_DIR.

Web UI (local) — after installing web extras and building the frontend, run:
- pop_fly_web, then open http://127.0.0.1:8000/

Frontend auto-build before server start
- The `pop_fly_web` command now attempts to build the frontend before starting the API so the latest UI is served from `frontend/dist`.
- It runs `npm ci` (or `npm install` if no `package-lock.json`) and `npm run build` in `frontend/`.
- To skip this step (e.g., when using the Vite dev server), set:

  - PowerShell:
    $Env:POP_FLY_SKIP_FRONTEND_BUILD = "1"; pop_fly_web