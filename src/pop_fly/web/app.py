from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError, version as pkg_version
import subprocess

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel, Field, model_validator

from ..core import Result, compute_distance_bearing_xy, _parse_pair_mgrs_digits


def _round_distance(value: float, precision: int) -> float:
    # Mirror CLI rounding behavior exactly
    return round(value, precision)


class ComputeRequest(BaseModel):
    # Accept numbers or strings to preserve leading zeros
    start: list[float | str] = Field(..., description="[E, N] where E/N are 1-5 digit MGRS digits")
    end: list[float | str] = Field(..., description="[E, N] where E/N are 1-5 digit MGRS digits")
    precision: int = Field(0, ge=0, le=6, description="Decimal places for distances; azimuth uses 1 decimal")

    @model_validator(mode="after")
    def check_lengths_and_values(self) -> "ComputeRequest":
        for name, arr in ("start", self.start), ("end", self.end):
            # Enforce at least two values at schema level (422 on too-short),
            # but allow extra to be handled as business-rule error (400) in route.
            if len(arr) < 2:
                raise ValueError(f"{name} must have at least 2 values [E, N]")
            for idx, v in enumerate(arr[:2]):
                try:
                    # Accept numeric strings as well
                    _ = float(v)  # type: ignore[arg-type]
                except Exception:
                    raise ValueError(f"{name}[{idx}] must be a number or numeric string")
        return self


class ComputeResponse(BaseModel):
    format: str
    start: list[float]
    end: list[float]
    distance_m: float
    azimuth_mils: float


app = FastAPI(title="pop_fly API", docs_url="/docs")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/version")
def get_version() -> dict:
    try:
        v = pkg_version("pop_fly")
    except PackageNotFoundError:
        v = "0.0.0"
    return {"version": v}


@app.post("/api/compute", response_model=ComputeResponse, response_model_exclude_none=True)
def compute(req: ComputeRequest) -> ComputeResponse:
    try:
        # Business rule: exactly two values only (no elevation). Return 400.
        if len(req.start) != 2 or len(req.end) != 2:
            raise HTTPException(status_code=400, detail="Start and end must have exactly two values [E, N]; elevation is no longer supported")
        # Build strings for the MGRS-digit parser while preserving leading zeros on E/N.
        def to_mgrs_str(parts: list[float | str]) -> str:
            e_raw = parts[0]
            n_raw = parts[1]
            e_token = str(e_raw).strip() if isinstance(e_raw, str) else str(int(float(e_raw)))
            n_token = str(n_raw).strip() if isinstance(n_raw, str) else str(int(float(n_raw)))
            # Strip any decimals from tokens; only integer digits allowed for E/N
            if "." in e_token:
                e_token = e_token.split(".")[0]
            if "." in n_token:
                n_token = n_token.split(".")[0]
            s = f"{e_token} {n_token}"
            return s

        start_t = _parse_pair_mgrs_digits(to_mgrs_str(list(req.start)))
        end_t = _parse_pair_mgrs_digits(to_mgrs_str(list(req.end)))
        res: Result = compute_distance_bearing_xy(start_t, end_t)  # type: ignore[arg-type]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    precision = req.precision
    payload = {
        "format": "mgrs-digits",
        "start": list(start_t),
        "end": list(end_t),
        "distance_m": _round_distance(res.distance_m, precision),
        "azimuth_mils": round(res.azimuth_mils, 1),
    }

    return ComputeResponse(**payload)


def main() -> None:
    import uvicorn

    host = os.getenv("POP_FLY_HOST", "127.0.0.1")
    port_str = os.getenv("POP_FLY_PORT", "8000")
    try:
        port = int(port_str)
    except ValueError:
        port = 8000

    # Optional: build frontend before starting the server so latest UI is served
    if os.getenv("POP_FLY_SKIP_FRONTEND_BUILD", "0") != "1":
        try:
            project_root = Path(__file__).resolve().parents[3]
            fe_dir = project_root / "frontend"
            pkg_json = fe_dir / "package.json"
            if pkg_json.is_file():
                npm_exe = "npm.cmd" if os.name == "nt" else "npm"
                lockfile = fe_dir / "package-lock.json"
                install_cmd = [npm_exe, "ci"] if lockfile.is_file() else [npm_exe, "install"]
                # Install deps (quiet-ish) and build
                subprocess.run(install_cmd, cwd=str(fe_dir), check=False)
                subprocess.run([npm_exe, "run", "build"], cwd=str(fe_dir), check=False)
        except Exception:
            # Non-fatal: continue to start API even if build fails
            pass
    uvicorn.run("pop_fly.web.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":  # pragma: no cover
    main()

# Mount static frontend if built (after defining routes so /api takes precedence)
try:
    project_root = Path(__file__).resolve().parents[3]
    dist_dir = project_root / "frontend" / "dist"
    if dist_dir.is_dir():
        app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")
except Exception:
    # Ignore static mounting failures; API still works
    pass
