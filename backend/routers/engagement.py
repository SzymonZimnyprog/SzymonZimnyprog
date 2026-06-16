"""Interceptor-vs-target engagement endpoints."""

from fastapi import APIRouter

from backend.sim.engagement import simulate_engagement
from backend.sim.firecontrol import solve_firing_solution
from backend.sim.models import EngagementRequest

router = APIRouter()


@router.post("/simulate")
def simulate(req: EngagementRequest):
    """Run a full proportional-navigation interception engagement."""
    interceptor, motor_res = req.interceptor.build()
    target = req.target.to_target()
    res = simulate_engagement(
        interceptor,
        target,
        dt=req.dt,
        max_time=req.max_time,
        lethal_radius=req.lethal_radius,
    )
    out = res.as_dict()
    out["interceptor_motor_summary"] = motor_res.as_dict()["summary"]
    return out


@router.post("/solve")
def solve(req: EngagementRequest):
    """Compute a firing solution: the launch elevation/azimuth that intercepts.

    The interceptor's ``elevation_deg`` / ``azimuth_deg`` inputs are treated as
    a starting guess and overridden by the solver; everything else (motor,
    airframe, target) is used as given.
    """
    interceptor, motor_res = req.interceptor.build()
    target = req.target.to_target()
    solution = solve_firing_solution(
        interceptor,
        target,
        launch_speed=req.interceptor.launch_speed,
        final_dt=req.dt,
        max_time=req.max_time,
        lethal_radius=req.lethal_radius,
    )
    out = solution.as_dict()
    out["interceptor_motor_summary"] = motor_res.as_dict()["summary"]
    return out
