"""Solid rocket motor internal-ballistics endpoints."""

from fastapi import APIRouter

from backend.sim.models import MotorRequest, PropellantModel
from backend.sim.motor import simulate_motor
from backend.sim.propellant import PRESETS

router = APIRouter()


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
