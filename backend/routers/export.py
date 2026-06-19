"""CAD (STL / OpenSCAD) and Simulink/MATLAB export endpoints.

Each endpoint returns a downloadable text artefact with the appropriate
``Content-Disposition`` so it can be saved directly from the web app, or
fetched programmatically by a CAD/MATLAB toolchain.
"""

import numpy as np
from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from backend.export import guidance_kit, openscad, simulink
from backend.export.stl import airframe_stl, grain_stl, nozzle_stl
from backend.sim.dynamics import propagate
from backend.sim.engagement import simulate_engagement
from backend.sim.models import (
    AirframeModel,
    EngagementRequest,
    InterceptorModel,
    MissileRequest,
    MotorRequest,
    build_vehicle_and_curve,
    launch_velocity,
)
from backend.sim.motor import simulate_motor

router = APIRouter()


def _download(content: str, filename: str, media_type: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class AirframeCadRequest(BaseModel):
    airframe: AirframeModel = AirframeModel()
    body_length: float = Field(2.5, gt=0, description="body tube length, m")
    nose_length: float = Field(0.6, gt=0, description="nose cone length, m")
    fin_count: int = Field(4, ge=0, le=8)
    fin_span: float = Field(0.12, gt=0, description="fin span, m")
    fin_root: float = Field(0.30, gt=0, description="fin root chord, m")


# --------------------------------------------------------------------------- #
# CAD: STL
# --------------------------------------------------------------------------- #
@router.post("/cad/grain.stl")
def grain_stl_export(req: MotorRequest):
    grain = req.grain.to_grain(req.propellant.density)
    return _download(grain_stl(grain), "grain.stl", "model/stl")


@router.post("/cad/nozzle.stl")
def nozzle_stl_export(req: MotorRequest):
    nozzle = req.nozzle.to_nozzle()
    content = nozzle_stl(nozzle, gamma=req.propellant.gamma,
                         chamber_radius=req.grain.outer_diameter / 2.0)
    return _download(content, "nozzle.stl", "model/stl")


@router.post("/cad/airframe.stl")
def airframe_stl_export(req: AirframeCadRequest):
    content = airframe_stl(req.airframe.diameter, req.body_length, req.nose_length)
    return _download(content, "airframe.stl", "model/stl")


# --------------------------------------------------------------------------- #
# CAD: OpenSCAD (parametric, editable)
# --------------------------------------------------------------------------- #
@router.post("/cad/grain.scad")
def grain_scad_export(req: MotorRequest):
    grain = req.grain.to_grain(req.propellant.density)
    return _download(openscad.grain_scad(grain), "grain.scad", "text/plain")


@router.post("/cad/nozzle.scad")
def nozzle_scad_export(req: MotorRequest):
    nozzle = req.nozzle.to_nozzle()
    content = openscad.nozzle_scad(nozzle, chamber_diameter=req.grain.outer_diameter)
    return _download(content, "nozzle.scad", "text/plain")


@router.post("/cad/airframe.scad")
def airframe_scad_export(req: AirframeCadRequest):
    content = openscad.airframe_scad(
        req.airframe.diameter, req.body_length, req.nose_length,
        fin_count=req.fin_count, fin_span=req.fin_span, fin_root=req.fin_root,
    )
    return _download(content, "airframe.scad", "text/plain")


# --------------------------------------------------------------------------- #
# Simulink / MATLAB
# --------------------------------------------------------------------------- #
@router.post("/simulink/thrust_curve.csv")
def thrust_curve_csv_export(req: MotorRequest):
    prop = req.propellant.to_propellant()
    grain = req.grain.to_grain(prop.density)
    nozzle = req.nozzle.to_nozzle()
    res = simulate_motor(prop, grain, nozzle, req.altitude, req.dt, req.max_time)
    return _download(simulink.thrust_curve_csv(res), "thrust_curve.csv", "text/csv")


@router.post("/simulink/motor.eng")
def motor_eng_export(req: MotorRequest):
    prop = req.propellant.to_propellant()
    grain = req.grain.to_grain(prop.density)
    nozzle = req.nozzle.to_nozzle()
    res = simulate_motor(prop, grain, nozzle, req.altitude, req.dt, req.max_time)
    motor_length_mm = grain.segment_length * grain.segments * 1000.0
    # Rough loaded mass: propellant + ~40% casing/nozzle/closure allowance.
    total_mass = res.propellant_mass_initial * 1.4
    content = simulink.rasp_eng(
        res,
        name="SZ-MOTOR",
        diameter_mm=grain.outer_diameter * 1000.0,
        length_mm=motor_length_mm,
        propellant_mass=res.propellant_mass_initial,
        total_mass=total_mass,
    )
    return _download(content, "motor.eng", "text/plain")


@router.post("/simulink/trajectory.csv")
def trajectory_csv_export(req: MissileRequest):
    vehicle, curve, _motor = build_vehicle_and_curve(req.motor, req.airframe)
    vel = launch_velocity(req.launch_speed, req.elevation_deg, req.azimuth_deg)
    traj = propagate(
        vehicle, launch_position=np.zeros(3), launch_velocity=vel,
        propellant_mass=curve.propellant_mass_initial, dt=req.dt,
        max_time=req.max_time,
    )
    return _download(simulink.trajectory_csv(traj.as_dict()),
                     "trajectory.csv", "text/csv")


@router.post("/simulink/engagement.csv")
def engagement_csv_export(req: EngagementRequest):
    interceptor, _ = req.interceptor.build()
    target = req.target.to_target()
    res = simulate_engagement(
        interceptor, target, dt=req.dt, max_time=req.max_time,
        lethal_radius=req.lethal_radius,
    )
    return _download(simulink.trajectory_csv(res.as_dict()),
                     "engagement.csv", "text/csv")


@router.get("/simulink/driver.m")
def matlab_driver_export():
    return _download(simulink.matlab_driver(), "szymon_sim_driver.m", "text/plain")


# --------------------------------------------------------------------------- #
# Guidance & sensors kit (bridge to real guidance software)
# --------------------------------------------------------------------------- #
@router.post("/guidance/spec.json")
def guidance_spec_export(req: InterceptorModel):
    """Structured sensor + GNC specification for the interceptor."""
    return guidance_kit.sensor_spec(req)


@router.post("/guidance/sensors.md")
def guidance_sensors_md_export(req: InterceptorModel):
    """Human-readable sensor spec + porting notes (Markdown)."""
    return _download(guidance_kit.sensor_spec_markdown(req),
                     "guidance_sensors.md", "text/markdown")


@router.post("/guidance/pn_reference.c")
def guidance_pn_reference_export(req: InterceptorModel):
    """Reference proportional-navigation steering law in C for this config."""
    return _download(guidance_kit.pn_reference_c(req),
                     "pn_guidance.c", "text/x-csrc")

