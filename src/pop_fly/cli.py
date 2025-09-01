from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Tuple

from .core import Result, _parse_pair_mgrs_digits, compute_distance_bearing_xy


APP_NAME = "pop_fly"


def _config_path() -> Path:
    # Windows: %APPDATA%/pop_fly/config.json
    override = os.getenv("POP_FLY_CONFIG_DIR")
    if override:
        return Path(override) / "config.json"
    if os.name == "nt":
        base = os.getenv("APPDATA")
        if not base:
            base = str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_NAME / "config.json"
    # macOS
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME / "config.json"
    # Linux / other
    xdg = os.getenv("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else (Path.home() / ".config")
    return base / "pop_fly" / "config.json"


def _load_saved_start() -> tuple[float, float] | tuple[float, float, float] | None:
    path = _config_path()
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            start = data.get("start")
            if isinstance(start, list) and len(start) in (2, 3):
                return tuple(float(x) for x in start)  # type: ignore[return-value]
    except Exception:
        pass
    return None


def _save_start(start: tuple[float, float] | tuple[float, float, float]) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"start": list(start)}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _clear_start() -> None:
    path = _config_path()
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass


def _format_signed(value: float, precision: int = 0) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}{abs(value):.{precision}f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pop_fly", description="Distance and azimuth calculator (MGRS digits only; optional Z)")
    parser.add_argument("--start", type=str, help="Quoted 'EEE,NNN' or 'EEE,NNN,Z' (1-5 digit E/N; Z in meters)", required=False)
    parser.add_argument("--end", type=str, help="Quoted 'EEE,NNN' or 'EEE,NNN,Z' (1-5 digit E/N; Z in meters)", required=False)
    parser.add_argument("--set-start", dest="set_start", type=str, help="Persist a default start 'EEE,NNN' or 'EEE,NNN,Z'", required=False)
    parser.add_argument("--clear-start", action="store_true", help="Clear persisted start")
    parser.add_argument("--show-start", action="store_true", help="Show persisted start if present")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--precision", type=int, default=0, help="Decimal places for distances (default 0); azimuth mils uses 1")

    args = parser.parse_args(argv)

    if args.clear_start:
        _clear_start()
        if not (args.start or args.end or args.set_start or args.show_start):
            return 0

    if args.show_start:
        saved = _load_saved_start()
        if saved is None:
            print("No persisted start found.")
        else:
            print(f"Persisted start: {saved}")
        # continue if compute requested

    if args.set_start:
        try:
            start = _parse_pair_mgrs_digits(args.set_start)
        except Exception as e:
            print(f"Error: {e}")
            return 2
        _save_start(start)
        if not (args.start or args.end):
            return 0

    start_tuple: tuple[float, float] | tuple[float, float, float] | None = None
    end_tuple: tuple[float, float] | tuple[float, float, float] | None = None

    if args.start:
        try:
            start_tuple = _parse_pair_mgrs_digits(args.start)
        except Exception as e:
            print(f"Error: {e}")
            return 2
    else:
        start_tuple = _load_saved_start()

    if args.end:
        try:
            end_tuple = _parse_pair_mgrs_digits(args.end)
        except Exception as e:
            print(f"Error: {e}")
            return 2

    if start_tuple is None:
        print("Error: missing --start and no persisted start set")
        return 2
    if end_tuple is None:
        print("Error: missing --end")
        return 2

    res: Result = compute_distance_bearing_xy(start_tuple, end_tuple)

    if args.json:
        payload = {
            "format": "mgrs-digits",
            "start": list(start_tuple),
            "end": list(end_tuple),
            "distance_m": round(res.distance_m, args.precision),
            "azimuth_mils": round(res.azimuth_mils, 1),
        }
        if res.slant_distance_m is not None and res.delta_z_m is not None:
            payload["slant_distance_m"] = round(res.slant_distance_m, args.precision)
            payload["delta_z_m"] = round(res.delta_z_m, args.precision)
        print(json.dumps(payload, indent=2))
    else:
        dist = f"{res.distance_m:.{args.precision}f}"
        az = f"{res.azimuth_mils:.1f}"
        if res.slant_distance_m is not None and res.delta_z_m is not None:
            slant = f"{res.slant_distance_m:.{args.precision}f}"
            dz = _format_signed(res.delta_z_m, args.precision)
            print(f"Distance: {dist} m | Azimuth: {az} mils | Slant: {slant} m | ΔZ: {dz} m")
        else:
            print(f"Distance: {dist} m | Azimuth: {az} mils")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
