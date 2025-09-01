from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError, version as pkg_version
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, ValidationError, model_validator

from ..core import Result, compute_distance_bearing_xy


def _round_distance(value: float, precision: int) -> float:
    return round(float(value), int(precision))


class ComputeRequest(BaseModel):
    start: list[float] = Field(..., description="[E, N] or [E, N, Z]")
    end: list[float] = Field(..., description="[E, N] or [E, N, Z]")
    precision: int = Field(0, ge=0, le=6, description="Decimal places for distances; azimuth uses 1 decimal")

    @model_validator(mode="after")
    def check_lengths_and_values(self) -> "ComputeRequest":
        for name, arr in ("start", self.start), ("end", self.end):
            if len(arr) not in (2, 3):
                raise ValueError(f"{name} must have 2 or 3 numbers")
            for v in arr:
                if not (float("-inf") < float(v) < float("inf")):
                    raise ValueError(f"{name} contains non-finite value")
        return self


class ComputeResponse(BaseModel):
    format: str
    start: list[float]
    end: list[float]
    distance_m: float
    azimuth_mils: float
    slant_distance_m: Optional[float] = None
    delta_z_m: Optional[float] = None


app = FastAPI(title="Mortar Calc API", docs_url="/docs")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/version")
def get_version() -> dict:
    try:
        v = pkg_version("mortar-calc")
    except PackageNotFoundError:
        v = "0.0.0"
    return {"version": v}


@app.post("/api/compute", response_model=ComputeResponse, response_model_exclude_none=True)
def compute(req: ComputeRequest) -> ComputeResponse:
    try:
        start_t = tuple(req.start)  # type: ignore[assignment]
        end_t = tuple(req.end)  # type: ignore[assignment]
        res: Result = compute_distance_bearing_xy(start_t, end_t)  # type: ignore[arg-type]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    precision = req.precision
    payload = {
        "format": "xy",
        "start": list(start_t),
        "end": list(end_t),
        "distance_m": _round_distance(res.distance_m, precision),
        "azimuth_mils": round(res.azimuth_mils, 1),
    }
    if res.slant_distance_m is not None and res.delta_z_m is not None:
        payload["slant_distance_m"] = _round_distance(res.slant_distance_m, precision)
        payload["delta_z_m"] = _round_distance(res.delta_z_m, precision)

    return ComputeResponse(**payload)


def main() -> None:
    import uvicorn

    host = os.getenv("MORTAR_CALC_HOST", "127.0.0.1")
    port_str = os.getenv("MORTAR_CALC_PORT", "8000")
    try:
        port = int(port_str)
    except ValueError:
        port = 8000
    uvicorn.run("mortar_calc.web.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":  # pragma: no cover
    main()
