"""Solid rocket motor internal-ballistics endpoints."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.sim.models import MotorRequest, PropellantModel
from backend.sim.motor import simulate_motor
from backend.sim.multistage import combine_stages
from backend.sim.optimize import solve_to_target
from backend.sim.propellant import PRESETS

router = APIRouter()

# Parameters that may be swept, mapped to (sub-model, field, cast).
_SWEEPABLE: dict[str, tuple[str, str, type]] = {
    "nozzle.throat_diameter": ("nozzle", "throat_diameter", float),
    "nozzle.expansion_ratio": ("nozzle", "expansion_ratio", float),
    "grain.outer_diameter": ("grain", "outer_diameter", float),
    "grain.core_diameter": ("grain", "core_diameter", float),
    "grain.segment_length": ("grain", "segment_length", float),
    "grain.segments": ("grain", "segments", int),
    "propellant.n": ("propellant", "n", float),
    "altitude": ("", "altitude", float),
}

SweepParam = Literal[
    "nozzle.throat_diameter",
    "nozzle.expansion_ratio",
    "grain.outer_diameter",
    "grain.core_diameter",
    "grain.segment_length",
    "grain.segments",
    "propellant.n",
    "altitude",
]


class MotorSweepRequest(BaseModel):
    base: MotorRequest = MotorRequest()
    parameter: SweepParam = "nozzle.throat_diameter"
    values: list[float] = Field(..., min_length=1, max_length=60)


class Stage(BaseModel):
    motor: MotorRequest = MotorRequest()
    ignition_delay: float = Field(0.0, ge=0.0, le=60.0,
                                  description="coast after previous burnout, s")


class MultiStageRequest(BaseModel):
    stages: list[Stage] = Field(..., min_length=1, max_length=5)


@router.get("/presets")
def list_propellant_presets():
    """Available propellant presets and their parameters."""
    return {
        key: PropellantModel.from_preset(key).model_dump()
        for key in PRESETS
    }


@router.post("/simulate")
def simulate(req: MotorRequest):
    """Run the internal-ballistics simulation and return the thrust curve."""
    prop = req.propellant.to_propellant()
    grain = req.grain.to_grain(prop.density)
    nozzle = req.nozzle.to_nozzle()
    res = simulate_motor(prop, grain, nozzle, req.altitude, req.dt, req.max_time)
    return res.as_dict()


def _run_summary(req: MotorRequest) -> dict:
    prop = req.propellant.to_propellant()
    grain = req.grain.to_grain(prop.density)
    nozzle = req.nozzle.to_nozzle()
    res = simulate_motor(prop, grain, nozzle, req.altitude, req.dt, req.max_time)
    return res.as_dict()["summary"]


@router.post("/multistage")
def multistage(req: MultiStageRequest):
    """Build the combined thrust profile of a sequential multi-stage stack."""
    results = []
    delays = []
    for stage in req.stages:
        m = stage.motor
        prop = m.propellant.to_propellant()
        grain = m.grain.to_grain(prop.density)
        nozzle = m.nozzle.to_nozzle()
        results.append(
            simulate_motor(prop, grain, nozzle, m.altitude, m.dt, m.max_time)
        )
        delays.append(stage.ignition_delay)
    return combine_stages(results, delays).as_dict()


@router.post("/sweep")
def sweep(req: MotorSweepRequest):
    """Re-run the motor across a range of one parameter (design exploration)."""
    if req.parameter not in _SWEEPABLE:
        raise HTTPException(status_code=400, detail="Unsupported sweep parameter")
    sub, field, cast = _SWEEPABLE[req.parameter]
    points = []
    for raw in req.values:
        variant = req.base.model_copy(deep=True)
        target = getattr(variant, sub) if sub else variant
        setattr(target, field, cast(raw))
        points.append({"value": cast(raw), "summary": _run_summary(variant)})
    return {"parameter": req.parameter, "points": points}


# --------------------------------------------------------------------------- #
# Design studio: optimisation, 2-D sweep heatmaps, sensitivity
# --------------------------------------------------------------------------- #
OptimizeMetric = Literal[
    "total_impulse",
    "peak_pressure",
    "average_thrust",
    "peak_thrust",
    "burn_time",
    "specific_impulse",
]


def _set_param(base: MotorRequest, parameter: str, value: float) -> MotorRequest:
    sub, field, cast = _SWEEPABLE[parameter]
    variant = base.model_copy(deep=True)
    target = getattr(variant, sub) if sub else variant
    setattr(target, field, cast(value))
    return variant


def _get_param(base: MotorRequest, parameter: str) -> float:
    sub, field, _cast = _SWEEPABLE[parameter]
    target = getattr(base, sub) if sub else base
    return float(getattr(target, field))


class MotorOptimizeRequest(BaseModel):
    base: MotorRequest = MotorRequest()
    parameter: SweepParam = "nozzle.throat_diameter"
    metric: OptimizeMetric = "peak_pressure"
    target: float = Field(7.0e6, description="desired value of the metric")
    lower: float = Field(..., description="lower bound on the parameter")
    upper: float = Field(..., description="upper bound on the parameter")


@router.post("/optimize")
def optimize(req: MotorOptimizeRequest):
    """Solve a design variable so a chosen metric meets a target value."""
    if req.parameter not in _SWEEPABLE:
        raise HTTPException(status_code=400, detail="Unsupported parameter")
    if req.upper <= req.lower:
        raise HTTPException(status_code=400, detail="upper must exceed lower")

    def metric_at(x: float) -> float:
        return _run_summary(_set_param(req.base, req.parameter, x))[req.metric]

    value = solve_to_target(metric_at, req.target, req.lower, req.upper)
    summary = _run_summary(_set_param(req.base, req.parameter, value))
    return {
        "parameter": req.parameter,
        "metric": req.metric,
        "target": req.target,
        "value": value,
        "achieved": summary[req.metric],
        "summary": summary,
    }


class MotorSweep2DRequest(BaseModel):
    base: MotorRequest = MotorRequest()
    param_x: SweepParam = "nozzle.throat_diameter"
    param_y: SweepParam = "grain.core_diameter"
    values_x: list[float] = Field(..., min_length=2, max_length=30)
    values_y: list[float] = Field(..., min_length=2, max_length=30)
    metric: OptimizeMetric = "total_impulse"


@router.post("/sweep2d")
def sweep2d(req: MotorSweep2DRequest):
    """Evaluate a metric on a 2-D grid of two design parameters (heatmap)."""
    for p in (req.param_x, req.param_y):
        if p not in _SWEEPABLE:
            raise HTTPException(status_code=400, detail=f"Unsupported parameter {p}")
    grid: list[list[float]] = []
    for vy in req.values_y:
        row = []
        for vx in req.values_x:
            variant = _set_param(req.base, req.param_x, vx)
            variant = _set_param(variant, req.param_y, vy)
            row.append(_run_summary(variant)[req.metric])
        grid.append(row)
    return {
        "param_x": req.param_x,
        "param_y": req.param_y,
        "values_x": req.values_x,
        "values_y": req.values_y,
        "metric": req.metric,
        "z": grid,
    }


class SensitivityRequest(BaseModel):
    base: MotorRequest = MotorRequest()
    parameters: list[SweepParam] = Field(
        default_factory=lambda: [
            "nozzle.throat_diameter",
            "grain.core_diameter",
            "grain.outer_diameter",
            "grain.segment_length",
            "propellant.n",
        ]
    )
    metric: OptimizeMetric = "total_impulse"
    delta: float = Field(0.1, gt=0, le=0.9, description="fractional perturbation")


@router.post("/sensitivity")
def sensitivity(req: SensitivityRequest):
    """Tornado sensitivity: how the metric responds to +/- delta on each param."""
    baseline = _run_summary(req.base)[req.metric]
    rows = []
    for p in req.parameters:
        if p not in _SWEEPABLE:
            continue
        cur = _get_param(req.base, p)
        lo = _run_summary(_set_param(req.base, p, cur * (1.0 - req.delta)))[req.metric]
        hi = _run_summary(_set_param(req.base, p, cur * (1.0 + req.delta)))[req.metric]
        rows.append({
            "parameter": p,
            "low": lo,
            "high": hi,
            "swing": abs(hi - lo),
        })
    rows.sort(key=lambda r: r["swing"], reverse=True)
    return {"metric": req.metric, "baseline": baseline, "delta": req.delta,
            "rows": rows}
