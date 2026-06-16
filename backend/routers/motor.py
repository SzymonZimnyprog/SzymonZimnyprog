"""Solid rocket motor internal-ballistics endpoints."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.sim.models import MotorRequest, PropellantModel
from backend.sim.motor import simulate_motor
from backend.sim.multistage import combine_stages
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
