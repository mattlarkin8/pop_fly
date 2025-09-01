from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees, hypot, isfinite, sqrt
from typing import Iterable, Tuple


@dataclass(frozen=True)
class Result:
    distance_m: float
    azimuth_mils: float
    slant_distance_m: float | None
    delta_z_m: float | None
    normalized_inputs: dict


def _parse_pair(value: str) -> Tuple[float, float] | Tuple[float, float, float]:
    # Accept comma or whitespace separators; allow optional Z
    raw = value.replace(",", " ").split()
    if len(raw) not in (2, 3):
        raise ValueError("Expected 'E N' or 'E N Z'")
    try:
        parts = tuple(float(p) for p in raw)
    except ValueError as e:
        raise ValueError("Coordinates must be numeric") from e
    for p in parts:
        if not isfinite(p):
            raise ValueError("Coordinate values must be finite numbers")
    return parts  # type: ignore[return-value]


def _bearing_deg_from_deltas(dx: float, dy: float) -> float:
    # Bearing from north, clockwise: atan2(E, N)
    b = (degrees(atan2(dx, dy)) + 360.0) % 360.0
    return b


def _deg_to_mils(deg: float) -> float:
    return deg * 6400.0 / 360.0


def compute_distance_bearing_xy(
    start: Tuple[float, float] | Tuple[float, float, float],
    end: Tuple[float, float] | Tuple[float, float, float],
) -> Result:
    if len(start) not in (2, 3) or len(end) not in (2, 3):
        raise ValueError("Start and end must be (E,N) or (E,N,Z)")

    e1, n1 = start[0], start[1]
    e2, n2 = end[0], end[1]

    for p in (e1, n1, e2, n2):
        if not isfinite(p):
            raise ValueError("Coordinate values must be finite numbers")

    dx = e2 - e1
    dy = n2 - n1
    horizontal = hypot(dx, dy)
    bearing_deg = _bearing_deg_from_deltas(dx, dy)
    azimuth_mils = _deg_to_mils(bearing_deg)

    slant: float | None = None
    dz: float | None = None
    if len(start) == 3 and len(end) == 3:
        z1, z2 = float(start[2]), float(end[2])
        if not (isfinite(z1) and isfinite(z2)):
            raise ValueError("Elevation values must be finite numbers")
        dz = z2 - z1
        slant = sqrt(horizontal * horizontal + dz * dz)

    return Result(
        distance_m=horizontal,
        azimuth_mils=azimuth_mils,
        slant_distance_m=slant,
        delta_z_m=dz,
        normalized_inputs={
            "start": list(start),
            "end": list(end),
        },
    )
