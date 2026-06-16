"""Standalone (un-guided) missile flight-trajectory endpoint."""

import numpy as np
from fastapi import APIRouter

from backend.sim.dynamics import propagate
from backend.sim.models import (
    MissileRequest,
    build_vehicle_and_curve,
    launch_velocity,
)

router = APIRouter()


@router.post("/simulate")
def simulate(req: MissileRequest):
    """Boosted/ballistic trajectory of a single missile (no guidance)."""
    vehicle, curve, motor_res = build_vehicle_and_curve(req.motor, req.airframe)
    vel = launch_velocity(req.launch_speed, req.elevation_deg, req.azimuth_deg)
    traj = propagate(
        vehicle,
        launch_position=np.zeros(3),
        launch_velocity=vel,
        propellant_mass=curve.propellant_mass_initial,
        dt=req.dt,
        max_time=req.max_time,
    )
    out = traj.as_dict()
    out["motor_summary"] = motor_res.as_dict()["summary"]
    return out
