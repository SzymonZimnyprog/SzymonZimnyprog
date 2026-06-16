"""Standalone (un-guided) missile flight-trajectory endpoints."""

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.sim.dynamics import Vehicle, propagate, propagate_staged
from backend.sim.models import (
    AirframeModel,
    MissileRequest,
    MotorRequest,
    build_vehicle_and_curve,
    launch_velocity,
)
from backend.sim.motor import simulate_motor
from backend.sim.multistage import staged_thrust

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


class FlightStage(BaseModel):
    motor: MotorRequest = MotorRequest()
    ignition_delay: float = Field(0.0, ge=0.0, le=60.0, description="coast, s")
    structural_mass: float = Field(5.0, ge=0.0, description="inert stage mass, kg")


class MultiStageFlightRequest(BaseModel):
    stages: list[FlightStage] = Field(..., min_length=1, max_length=5)
    payload: AirframeModel = AirframeModel()  # dry_mass = payload/bus mass
    launch_speed: float = Field(30.0, ge=0)
    elevation_deg: float = Field(85.0, ge=0, le=90)
    azimuth_deg: float = Field(0.0, ge=-180, le=360)
    drop_last_stage: bool = False
    dt: float = Field(0.02, gt=0, le=0.5)
    max_time: float = Field(600.0, gt=0, le=2000)


@router.post("/multistage")
def multistage_flight(req: MultiStageFlightRequest):
    """Fly a staged stack, jettisoning spent-stage mass at each separation."""
    results = []
    struct_masses = []
    delays = []
    for stage in req.stages:
        m = stage.motor
        prop = m.propellant.to_propellant()
        grain = m.grain.to_grain(prop.density)
        nozzle = m.nozzle.to_nozzle()
        results.append(
            simulate_motor(prop, grain, nozzle, m.altitude, m.dt, m.max_time)
        )
        struct_masses.append(stage.structural_mass)
        delays.append(stage.ignition_delay)

    thrust, _starts = staged_thrust(results, delays)

    total_prop = sum(r.propellant_mass_initial for r in results)
    total_struct = sum(struct_masses)
    initial_mass = req.payload.dry_mass + total_struct + total_prop

    # Jettison each spent stage at its burnout (keep the last stage unless asked).
    last = len(results) - 1
    separation_events = []
    for i in range(len(results)):
        if i == last and not req.drop_last_stage:
            continue
        separation_events.append((thrust.burnouts[i], struct_masses[i]))

    vehicle = Vehicle(airframe=req.payload.to_airframe(), thrust_curve=thrust)
    vel = launch_velocity(req.launch_speed, req.elevation_deg, req.azimuth_deg)
    traj, events = propagate_staged(
        vehicle,
        launch_position=np.zeros(3),
        launch_velocity=vel,
        initial_mass=initial_mass,
        separation_events=separation_events,
        dt=req.dt,
        max_time=req.max_time,
    )
    out = traj.as_dict()
    out["separations"] = events
    out["stage_starts"] = thrust.starts
    out["initial_mass"] = initial_mass
    out["total_impulse"] = sum(r.total_impulse for r in results)
    return out
