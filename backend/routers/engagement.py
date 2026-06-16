"""Interceptor-vs-target engagement endpoint."""

from fastapi import APIRouter

from backend.sim.engagement import simulate_engagement
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
