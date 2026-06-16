"""Interceptor-vs-target engagement endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.sim.engagement import simulate_engagement
from backend.sim.firecontrol import solve_firing_solution
from backend.sim.models import EngagementRequest
from backend.sim.montecarlo import montecarlo_pk
from backend.sim.salvo import simulate_salvo

router = APIRouter()


class SalvoRequest(BaseModel):
    engagement: EngagementRequest = EngagementRequest()
    count: int = Field(3, ge=1, le=8)
    stagger: float = Field(1.0, ge=0.0, le=30.0, description="s between launches")
    elevation_spread: float = Field(6.0, ge=0.0, le=40.0, description="deg total")
    auto_aim: bool = True


class MonteCarloRequest(BaseModel):
    engagement: EngagementRequest = EngagementRequest()
    trials: int = Field(150, ge=10, le=1000)
    position_sigma: float = Field(200.0, ge=0.0, description="track pos error, m")
    velocity_sigma: float = Field(20.0, ge=0.0, description="track vel error, m/s")
    seed: int = Field(0, ge=0)


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


@router.post("/salvo")
def salvo(req: SalvoRequest):
    """Fire a staggered salvo of interceptors at one target (layered defence)."""
    eng = req.engagement
    interceptor, motor_res = eng.interceptor.build()
    target = eng.target.to_target()
    result = simulate_salvo(
        interceptor,
        target,
        launch_speed=eng.interceptor.launch_speed,
        count=req.count,
        stagger=req.stagger,
        elevation_spread=req.elevation_spread,
        auto_aim=req.auto_aim,
        dt=eng.dt,
        max_time=eng.max_time,
        lethal_radius=eng.lethal_radius,
    )
    out = result.as_dict()
    out["interceptor_motor_summary"] = motor_res.as_dict()["summary"]
    return out


@router.post("/montecarlo")
def montecarlo(req: MonteCarloRequest):
    """Estimate kill probability under Gaussian target-track uncertainty."""
    eng = req.engagement
    interceptor, _motor = eng.interceptor.build()
    target = eng.target.to_target()
    result = montecarlo_pk(
        interceptor,
        target,
        launch_speed=eng.interceptor.launch_speed,
        trials=req.trials,
        position_sigma=req.position_sigma,
        velocity_sigma=req.velocity_sigma,
        seed=req.seed,
        max_time=eng.max_time,
        lethal_radius=eng.lethal_radius,
    )
    return result.as_dict()
