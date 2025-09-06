from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees, hypot, isfinite
from typing import Tuple


@dataclass(frozen=True)
class Result:
    distance_m: float
    azimuth_mils: float
    # Which mil system was used (e.g., "nato"=6400, "ru"=6000)
    faction: str = "nato"


def _parse_pair_mgrs_digits(value: str) -> Tuple[float, float]:
    """
    Parse an MGRS-like shorthand pair such as "037,050" (3-digit easting, 3-digit northing)
    into meters by expanding each to 5 digits:
    - For each of the first two components (E, N), if the token is a 1-5 digit integer string,
      scale by 10**(5 - len(token)). Examples:
        "1" -> 10000 m, "12" -> 1200 m, "123" -> 12300 m, "1234" -> 12340 m, "12345" -> 12345 m

    This intentionally ignores MGRS zone and 100k grid square letters and assumes a local grid
    context where both points share the same square; only the numerical digits are provided.
    """
    raw = value.replace(",", " ").split()
    if len(raw) != 2:
        raise ValueError("Expected 'E N' for MGRS shorthand (two values only)")

    def expand(token: str) -> float:
        if not token.isdigit():
            raise ValueError("MGRS shorthand requires integer digit strings for E and N (1-5 digits)")
        if not (1 <= len(token) <= 5):
            raise ValueError("MGRS shorthand supports 1 to 5 digits for E/N components")
        scale = 10 ** (5 - len(token))
        return float(int(token) * scale)

    try:
        e = expand(raw[0])
        n = expand(raw[1])
        return (e, n)
    except ValueError as e:
        # Re-raise with a clearer message
        raise ValueError(str(e))


def _bearing_deg_from_deltas(dx: float, dy: float) -> float:
    # Bearing from north, clockwise: atan2(E, N)
    b = (degrees(atan2(dx, dy)) + 360.0) % 360.0
    return b


def _deg_to_mils(deg: float, mils_per_circle: float = 6400.0) -> float:
    return deg * mils_per_circle / 360.0


def compute_distance_bearing_xy(
    start: Tuple[float, float],
    end: Tuple[float, float],
    *,
    faction: str = "nato",
    mils_per_circle: float | None = None,
) -> Result:
    """Compute horizontal distance and azimuth in mils.

    Parameters
    ----------
    start, end: (E, N) coordinate pairs (meters)
    faction: "nato" (6400 mils) or "ru" (6000 mils). Case-insensitive.
    mils_per_circle: Override mils per circle explicitly (takes precedence over faction when provided).

    Returns
    -------
    Result with distance and azimuth_mils appropriate to the specified system.
    """
    if len(start) != 2 or len(end) != 2:
        raise ValueError("Start and end must be (E,N) pairs with two values each")

    e1, n1 = start[0], start[1]
    e2, n2 = end[0], end[1]

    for p in (e1, n1, e2, n2):
        if not isfinite(p):
            raise ValueError("Coordinate values must be finite numbers")

    dx = e2 - e1
    dy = n2 - n1
    horizontal = hypot(dx, dy)
    bearing_deg = _bearing_deg_from_deltas(dx, dy)
    # Determine mils per circle
    mpc: float
    if mils_per_circle is not None:
        mpc = float(mils_per_circle)
    else:
        f = faction.lower()
        if f in ("nato", "us", "otan"):
            mpc = 6400.0
            faction = "nato"
        elif f in ("ru", "russian", "warsaw", "wp"):
            mpc = 6000.0
            faction = "ru"
        else:
            raise ValueError("Unsupported faction; expected 'nato' or 'ru'")

    azimuth_mils = _deg_to_mils(bearing_deg, mpc)

    return Result(
        distance_m=horizontal,
        azimuth_mils=azimuth_mils,
        faction=faction,
    )
