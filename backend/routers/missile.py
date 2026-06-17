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
from backend.sim.optimize import golden_section_maximize
from backend.sim.stability import barrowman_stability

router = APIRouter()


class StabilityRequest(BaseModel):
    diameter: float = Field(0.16, gt=0, description="body diameter, m")
    nose_length: float = Field(0.6, gt=0, description="nose cone length, m")
    body_length: float = Field(2.5, gt=0, description="body tube length, m")
    nose_type: str = Field("ogive", description="ogive | cone | parabolic | haack")
    fin_count: int = Field(4, ge=0, le=8)
    fin_root_chord: float = Field(0.30, gt=0, description="fin root chord, m")
    fin_tip_chord: float = Field(0.15, ge=0, description="fin tip chord, m")
    fin_span: float = Field(0.12, gt=0, description="exposed semi-span, m")
    fin_sweep: float = Field(0.10, ge=0, description="LE sweep distance, m")
    fin_root_position: float | None = Field(
        None, description="nose-tip to fin-root LE, m (default: tail)"
    )
    dry_mass: float = Field(40.0, gt=0, description="empty mass, kg")
    dry_cg: float | None = Field(None, description="empty CG from nose tip, m")
    propellant_mass: float = Field(8.0, ge=0, description="loaded propellant, kg")
    propellant_cg: float | None = Field(None, description="propellant CG, m")


@router.post("/stability")
def stability(req: StabilityRequest):
    """Barrowman centre of pressure, CG and static margin (loaded & burnout)."""
    res = barrowman_stability(
        diameter=req.diameter,
        nose_length=req.nose_length,
        body_length=req.body_length,
        nose_type=req.nose_type,
        fin_count=req.fin_count,
        fin_root_chord=req.fin_root_chord,
        fin_tip_chord=req.fin_tip_chord,
        fin_span=req.fin_span,
        fin_sweep=req.fin_sweep,
        fin_root_position=req.fin_root_position,
        dry_mass=req.dry_mass,
        dry_cg=req.dry_cg,
        propellant_mass=req.propellant_mass,
        propellant_cg=req.propellant_cg,
    )
    return res.as_dict()


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


class LaunchOptimizeRequest(BaseModel):
    missile: MissileRequest = MissileRequest()
    objective: str = Field("apogee", description="apogee | range")
    elevation_lower: float = Field(20.0, ge=0, le=90)
    elevation_upper: float = Field(89.0, ge=0, le=90)


@router.post("/optimize_launch")
def optimize_launch(req: LaunchOptimizeRequest):
    """Find the launch elevation that maximises apogee or downrange range.

    The motor and airframe are fixed; only the launch elevation is varied, so
    the thrust curve is built once and reused across the search.
    """
    vehicle, curve, motor_res = build_vehicle_and_curve(
        req.missile.motor, req.missile.airframe
    )
    key = "apogee" if req.objective == "apogee" else "range"

    def fly(elevation: float):
        vel = launch_velocity(req.missile.launch_speed, elevation,
                              req.missile.azimuth_deg)
        return propagate(
            vehicle, launch_position=np.zeros(3), launch_velocity=vel,
            propellant_mass=curve.propellant_mass_initial,
            dt=req.missile.dt, max_time=req.missile.max_time,
        )

    def objective(elevation: float) -> float:
        return fly(elevation).as_dict()["summary"][key]

    best_el = golden_section_maximize(
        objective, req.elevation_lower, req.elevation_upper, iters=28
    )
    traj = fly(best_el)
    out = traj.as_dict()
    out["motor_summary"] = motor_res.as_dict()["summary"]
    out["elevation_deg"] = best_el
    out["objective"] = req.objective
    out["objective_value"] = out["summary"][key]
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
