# Mortar Calc

Distance and azimuth calculator for local MGRS digits (+optional Z) grids.

Quick usage (after installing into a Python 3.11+ env):

- Set a default start (MGRS digits):
  mortar-calc --set-start "037,050,5"
- Compute between two points (uses saved start when --start omitted):
  mortar-calc --end "051 070"
- JSON output:
  mortar-calc --end "150 300" --json
- Show/Clear persisted start:
  mortar-calc --show-start
  mortar-calc --clear-start

Inputs:
- Quoted tuples: "EEE,NNN" or "EEE,NNN,Z" where E/N are 1–5 digit MGRS digits (comma or space separator). Digits are expanded to meters: e.g., 037 → 3700 m, 051 → 5100 m. Z is meters.
- Units: meters; azimuth output in NATO mils (6400 mils/circle)

Outputs:
- Distance (m) and azimuth (mils). If both inputs have Z, prints slant distance and ΔZ with explicit sign.

Note: By default on Windows, settings are stored under %APPDATA%/Mortar Calc/config.json.
You can override the location for tests via MORTAR_CALC_CONFIG_DIR.

Web UI (local) — after installing web extras and building the frontend, run:
- mortar-calc-web, then open http://127.0.0.1:8000/
