# Mortar Calc — Distance & Direction Calculator PRD

Version: 1.2  
Owner: You  
Date: 2025-08-31

## summary
A Python tool that, given two points as local easting/northing (XY) coordinates in meters, computes the horizontal distance and direction from the start point to the end point. Scope is intentionally narrow: input is XY only (with optional elevation Z in meters); computation is planar Euclidean; output distance is meters; direction is NATO mils (6400 mils per circle). When both start and end elevations are provided, the tool also reports slant distance and delta Z. The tool assumes grid north equals true north for azimuth reporting.

## primary goals
- Accurately compute 2D horizontal distance and azimuth between two points from XY inputs only.
- Provide a fast, offline CLI for quick calculations and a small Python API for reuse.
- Offer robust validation and helpful error messages.

## stretch goals
- Map rendering or UI beyond a simple CLI.

## users and scenarios
- FO/FDC or field user working on a training range/local grid who has two XY points and needs distance and azimuth quickly (≤4 km typical).
- Engineer needing programmatic distance/bearing in scripts with a known local Cartesian grid.

Example scenarios:
- Given two XY points in meters on the same local grid, compute distance and azimuth (mils).
- Given two XY points with elevations, compute horizontal distance, azimuth (mils), slant distance, and delta Z.

## scope
- Input format: XY (meters) only; +x is east, +y is north; optional Z (meters) for elevation.
- Output: distance in meters; azimuth in NATO mils (grid). If Z present for both points, also output slant distance (m) and delta Z (m).
- Interfaces: CLI and importable Python function.
- Accuracy target: ≤2 m error for distances ≤4 km under typical conditions.

## functional requirements
1. input handling
  - Accept start and end via CLI flags or positional args.
  - Supported format:
    - Quoted tuple: `--start "E,N" --end "E,N"` or `--start "E,N,Z" --end "E,N,Z"` (commas or space separator).
  - Units: meters (floats). No implicit scaling.
  - Independence: start and end can be set independently. If a persisted start exists (see CLI), `--end` alone is sufficient.
  - Persisted start (optional): allow saving a default start point on the machine and using it across runs.
2. computation
  - Horizontal distance: `dx = E2 - E1; dy = N2 - N1; distance_m = sqrt(dx^2 + dy^2)`.
  - Elevation delta (if Z1 and Z2 provided): `delta_z_m = Z2 - Z1`.
  - Slant distance (if Z1 and Z2 provided): `slant_distance_m = sqrt(distance_m^2 + delta_z_m^2)`.
  - Bearing (deg): `(atan2(dx, dy) * 180/pi + 360) % 360` (north-referenced; grid assumed ≡ true).
  - Direction output (mils): `azimuth_mils = deg * 6400 / 360`.
3. output
  - Human-readable (no elevation): `Distance: 1234 m | Azimuth: 2190 mils`.
  - Human-readable (with elevation): `Distance: 1234 m | Azimuth: 2190 mils | Slant: 1250 m | ΔZ: +80 m`.
  - ΔZ presentation: always include an explicit sign prefix (+/-) in human-readable output.
  - JSON (no elevation): `{ "format": "xy", "start": [E1, N1], "end": [E2, N2], "distance_m": 1234.0, "azimuth_mils": 2190.0 }`.
  - JSON (with elevation): `{ "format": "xy", "start": [E1, N1, Z1], "end": [E2, N2, Z2], "distance_m": 1234.0, "slant_distance_m": 1250.0, "delta_z_m": 80.0, "azimuth_mils": 2190.0 }`.
4. cli interface
  - Command: `mortar-calc` (or `mortar_calc.py` if not installed).
  - Flags:
    - `--start "E,N" --end "E,N"` OR `--start "E,N,Z" --end "E,N,Z"`
    - `--set-start "E,N"` (optional; saves a persistent default start point)
    - `--clear-start` (optional; removes any saved default start)
    - `--show-start` (optional; prints the saved default start, if any)
    - `--json` (optional)
    - `--precision <int>` (default: meters 0, mils 1)
  - Examples:
    - `mortar-calc --set-start "1000,2000,50"` (save start once, with elevation)
    - `mortar-calc --end "1500,3200,130"` (uses saved start; computes slant and ΔZ)
    - `mortar-calc --start "1000,2000" --end "1500,3200"` (horizontal only)
    - `mortar-calc --start "1000,2000,50" --end "1500,3200,130"` (horizontal + slant)
5. library api
  - Function: `compute_distance_bearing_xy(start: tuple[float, float] | tuple[float, float, float], end: tuple[float, float] | tuple[float, float, float]) -> Result`
  - Result dataclass:
    - `distance_m: float` (horizontal)
    - `slant_distance_m: float | None`
    - `delta_z_m: float | None`
    - `azimuth_mils: float`
    - `normalized_inputs: dict` (echoed XY(Z) values)

## non-functional requirements
- Performance: single run <100 ms; no network calls.
- Portability: Windows/macOS/Linux; Python 3.11+.
- Reliability: predictable output; clear errors with exit codes.
- Maintainability: compact, well-tested code with minimal dependencies.

## assumptions
- 2D horizontal distance is always computed; elevation is optional and only used for slant distance when both Z values are present.
- Local grid axes: +x east, +y north.
- Grid north is assumed equal to true north; azimuths are reported as grid and treated as true for this tool.
- Distances ≤ ~4 km so planar approximation is appropriate.

## constraints
- Offline-only (no external services).
- No external CRS libraries required for core XY mode.

## design
### coordinate parsing (XY only)
- Parse `E,N` pairs or separate flags into floats.
- Validate finite numeric values.

### computation (planar)
- Distance: `sqrt((E2-E1)^2 + (N2-N1)^2)`.
- Bearing (deg): `(atan2(E2-E1, N2-N1) * 180/pi + 360) % 360`.
- Convert to mils: `deg * 6400 / 360`.

### units
- Distance: meters only.
- Direction: NATO mils only (6400 per circle).

### error handling
- Missing or malformed XY inputs → descriptive error.
- Non-finite values → error.

## dependencies
- Standard library only: `math`, `argparse`, `json`, `dataclasses`, `typing`, `pathlib`, `os`.

## cli ux
- Clear usage/help with examples.
- Echo parsed inputs when `--json` is used.
- Persisted start storage: platform-appropriate config path (Windows: `%APPDATA%/Mortar Calc/config.json`; macOS: `~/Library/Application Support/Mortar Calc/config.json`; Linux: `$XDG_CONFIG_HOME/mortar-calc/config.json` or `~/.config/mortar-calc/config.json`).
- When a persisted start exists and `--start` is omitted, use saved start; if neither is present, return a clear error.
- When a persisted start includes Z and an `--end` with Z is provided, compute slant/ΔZ; otherwise compute horizontal only.

## validation and testing
- Unit tests:
  - Same point: horizontal distance 0; azimuth 0.0 mils by convention; slant 0 when both Z provided and equal.
  - Simple vectors where bearing is known (e.g., due east/west/north/south and 45° diagonals).
  - Elevation present: verify `slant_distance_m = sqrt(horizontal^2 + ΔZ^2)` and `delta_z_m` sign.
  - One Z missing: only horizontal distance and azimuth are reported; slant/delta Z omitted.
  - Invalid inputs produce clear errors and non-zero exit code.
  - Persisted start: set (with Z), use without `--start`, show/clear behavior, and error when missing.

## acceptance criteria
- CLI returns distance (m) and azimuth (mils) for valid XY inputs.
- When both Z values are provided, CLI also returns slant_distance_m and delta_z_m.
- JSON output includes `distance_m` and `azimuth_mils`; includes `slant_distance_m` and `delta_z_m` only when both Z values are present.
- Descriptive errors; exit code 2 on usage errors.
- Persisted start works across runs: after `--set-start`, a run with only `--end` computes successfully and echoes the used start.
 - Human-readable ΔZ is printed with an explicit plus or minus sign.

## milestones & timeline
1. Day 1: XY parser + validation; distance/bearing; CLI skeleton; tests (happy path).
2. Day 2: JSON output; precision handling; error paths; docs and packaging.

## risks & mitigations
- We assume grid ≡ true north; document this assumption clearly in help and README so users understand the model.

## appendix: quick formulas
- Distance: `sqrt(ΔE^2 + ΔN^2)`
- Grid bearing (deg): `(atan2(ΔE, ΔN) * 180/π + 360) % 360`
- NATO mils: `mils = deg * 6400 / 360`

## examples
- Azimuth: `mortar-calc --start "1000,2000" --end "1500,3200"`
- Persisted start workflow:
  - `mortar-calc --set-start "1000,2000"`
  - `mortar-calc --end "1500,3200"`
