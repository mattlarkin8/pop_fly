from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

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


def _load_config() -> dict:
    path = _config_path()
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {}


def _save_config(new_data: dict) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_config()
    existing.update(new_data)
    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def _load_saved_start() -> tuple[float, float] | None:
    data = _load_config()
    start = data.get("start")
    if isinstance(start, list) and len(start) == 2:
        try:
            return (float(start[0]), float(start[1]))
        except Exception:
            return None
    return None


def _save_start(start: tuple[float, float]) -> None:
    _save_config({"start": list(start)})


def _load_saved_faction() -> str | None:
    data = _load_config()
    fac = data.get("faction")
    if isinstance(fac, str) and fac.lower() in {"nato", "ru"}:
        return fac.lower()
    return None


def _save_faction(faction: str) -> None:
    _save_config({"faction": faction.lower()})


def _clear_start() -> None:
    path = _config_path()
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pop_fly", description="Distance and azimuth calculator (MGRS digits only; two values E,N)")
    parser.add_argument("--start", type=str, help="Quoted 'EEE,NNN' (1-5 digit E/N)", required=False)
    parser.add_argument("--end", type=str, help="Quoted 'EEE,NNN' (1-5 digit E/N)", required=False)
    parser.add_argument("--set-start", dest="set_start", type=str, help="Persist a default start 'EEE,NNN' (two values only)", required=False)
    parser.add_argument("--clear-start", action="store_true", help="Clear persisted start")
    parser.add_argument("--show-start", action="store_true", help="Show persisted start if present")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--precision", type=int, default=0, help="Decimal places for distances (default 0); azimuth mils uses 1")
    parser.add_argument("--faction", type=str, choices=["nato", "ru"], help="Select mil system for this run (overrides persisted)")
    parser.add_argument("--set-faction", dest="set_faction", type=str, choices=["nato", "ru"], help="Persist default faction (nato|ru)")

    args = parser.parse_args(argv)

    if args.clear_start:
        _clear_start()
        if not (args.start or args.end or args.set_start or args.show_start):
            return 0

    if args.show_start:
        saved = _load_saved_start()
        fac_saved = _load_saved_faction()
        if saved is None and fac_saved is None:
            print("No persisted start/faction found.")
        else:
            if saved is not None:
                print(f"Persisted start: {saved}")
            if fac_saved is not None:
                print(f"Persisted faction: {fac_saved}")
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

    if args.set_faction:
        _save_faction(args.set_faction)
        if not (args.start or args.end or args.set_start):
            return 0

    start_tuple: tuple[float, float] | None = None
    end_tuple: tuple[float, float] | None = None

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

    # Resolve faction: CLI arg > persisted > default nato
    faction = args.faction or _load_saved_faction() or "nato"
    res: Result = compute_distance_bearing_xy(start_tuple, end_tuple, faction=faction)

    if args.json:
        payload = {
            "format": "mgrs-digits",
            "start": list(start_tuple),
            "end": list(end_tuple),
            "distance_m": round(res.distance_m, args.precision),
            "azimuth_mils": round(res.azimuth_mils, 1),
            "faction": res.faction,
        }
        print(json.dumps(payload, indent=2))
    else:
        dist = f"{res.distance_m:.{args.precision}f}"
        az = f"{res.azimuth_mils:.1f}"
        system = "6400" if res.faction == "nato" else "6000"
        print(f"Distance: {dist} m | Azimuth: {az} mils ({res.faction.upper()} {system})")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
