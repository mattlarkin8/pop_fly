# Mortar Calc

Distance and azimuth calculator for local XY (+optional Z) grids.

Quick usage (after installing into a Python 3.11+ env):

- Set a default start:
  mortar-calc --set-start "100,200,5"
- Compute between two points (uses saved start when --start omitted):
  mortar-calc --end "150 300"
- JSON output:
  mortar-calc --end "150 300" --json
- Show/Clear persisted start:
  mortar-calc --show-start
  mortar-calc --clear-start

Inputs:
- Quoted tuples: "E,N" or "E,N,Z" (comma or space separator)
- Units: meters; azimuth output in NATO mils (6400 mils/circle)

Outputs:
- Distance (m) and azimuth (mils). If both inputs have Z, prints slant distance and ΔZ with explicit sign.

Note: By default on Windows, settings are stored under %APPDATA%/Mortar Calc/config.json.
You can override the location for tests via MORTAR_CALC_CONFIG_DIR.
