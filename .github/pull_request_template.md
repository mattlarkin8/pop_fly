## Summary

Describe the change briefly.

## Architecture compliance (required)
- [ ] Framework unchanged (FastAPI)
- [ ] Public API unchanged (/api/compute POST, /api/health, /api/version)
- [ ] Units and rounding preserved (meters; azimuth in NATO mils, 0.1 precision)
- [ ] Core contracts intact (_parse_pair_mgrs_digits, compute_distance_bearing_xy, Result)
- [ ] Dependencies unchanged (no new frameworks)
- [ ] Profile used: (minor | moderate | major) — indicate which automation profile was used for scaffolding
- [ ] Tests: Only adjust tests that are within the approved scope of the selected profile; list test files and specific assertions changed in the section below

## Testing
Describe tests added/updated and results. If tests were adjusted, list the affected test files and the specific assertions modified (include rationale and links to the plan where applicable).

## Risks
List any risks and mitigations.
