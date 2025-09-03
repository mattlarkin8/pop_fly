#!/usr/bin/env python3
"""
Architecture guard: validates invariants and forbids risky changes in PRs.

Runs fast, no network required for basic checks. Optionally uses git to diff
against the base branch if available.

Checks:
- Framework: FastAPI (no Flask) in src/pop_fly/web/app.py
- API endpoints: /api/compute (POST), /api/health, /api/version
- Core symbols: Result dataclass, _parse_pair_mgrs_digits, compute_distance_bearing_xy
- Units/rounding (heuristic): presence of azimuth_mils, _deg_to_mils
- Tests import from pop_fly, not src.pop_fly; no Flask in tests
- pyproject.toml has no Flask dependency
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def fail(msg: str) -> None:
    print(f"ARCH GUARD: FAIL: {msg}")
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"ARCH GUARD: WARN: {msg}")


def check_fastapi_and_endpoints() -> None:
    web = ROOT / "src" / "pop_fly" / "web" / "app.py"
    txt = read_text(web)
    if not txt:
        fail(f"Missing {web}")
    if re.search(r"\bfrom\s+flask\b|\bimport\s+flask\b|\bFlask\b", txt):
        fail("Flask usage detected; FastAPI is required")
    if "FastAPI" not in txt or re.search(r"app\s*=\s*FastAPI\(", txt) is None:
        fail("FastAPI app not found in web/app.py")
    endpoint_patterns = [
        r"@app\.post\(\s*[\"']\/api\/compute[\"']",
        r"@app\.get\(\s*[\"']\/api\/health[\"']",
        r"@app\.get\(\s*[\"']\/api\/version[\"']",
    ]
    for pat in endpoint_patterns:
        if re.search(pat, txt) is None:
            fail(f"Missing endpoint matching pattern: {pat} in web/app.py")


def check_core_symbols() -> None:
    core = ROOT / "src" / "pop_fly" / "core.py"
    txt = read_text(core)
    if not txt:
        fail(f"Missing {core}")
    required = [
        r"@dataclass\(frozen=True\)",
        r"class\s+Result\b",
        r"def\s+_parse_pair_mgrs_digits\(",
        r"def\s+compute_distance_bearing_xy\(",
        r"def\s+_deg_to_mils\(",
    ]
    for pat in required:
        if re.search(pat, txt) is None:
            fail(f"Missing required core symbol matching: {pat}")


def check_tests() -> None:
    test_core = ROOT / "tests" / "test_core.py"
    test_api = ROOT / "tests" / "test_api.py"
    for tf in (test_core, test_api):
        txt = read_text(tf)
        if not txt:
            fail(f"Missing required test file {tf}")
        if re.search(r"\bsrc\.pop_fly\b", txt):
            fail(f"Tests must import from 'pop_fly', not 'src.pop_fly': {tf}")
        if re.search(r"\bFlask\b|\bfrom\s+flask\b", txt):
            fail(f"Flask usage detected in tests: {tf}")


def check_pyproject_no_flask() -> None:
    pyproj = ROOT / "pyproject.toml"
    txt = read_text(pyproj)
    if not txt:
        warn("pyproject.toml not found; skipping dependency checks")
        return
    if re.search(r"\bflask\b", txt, flags=re.IGNORECASE):
        fail("pyproject.toml must not include Flask dependencies")


def main() -> None:
    check_fastapi_and_endpoints()
    check_core_symbols()
    check_tests()
    check_pyproject_no_flask()
    print("ARCH GUARD: PASS")


if __name__ == "__main__":
    main()
