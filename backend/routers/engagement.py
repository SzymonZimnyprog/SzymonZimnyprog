"""Interceptor-vs-target engagement endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.sim.coverage import defended_area
from backend.sim.engagement import simulate_engagement
from backend.sim.firecontrol import solve_firing_solution
from backend.sim.models import (
    EngagementRequest,
    InterceptorModel,
    TargetModel,
    WindModel,
)
from backend.sim.montecarlo import montecarlo_pk
from backend.sim.raid import simulate_raid
from backend.sim.salvo import simulate_salvo

router = APIRouter()


def _linspace(lo: float, hi: float, n: int) -> list[float]:
    n = max(2, int(n))
    return [lo + (hi - lo) * i / (n - 1) for i in range(n)]


class DefendedAreaRequest(BaseModel):
    engagement: EngagementRequest = EngagementRequest()
    target_speed: float = Field(300.0, gt=0, description="inbound speed, m/s")
    downrange_min: float = Field(3000.0, ge=0)
    downrange_max: float = Field(30000.0, gt=0)
    downrange_steps: int = Field(8, ge=2, le=14)
    altitude_min: float = Field(1000.0, ge=0)
    altitude_max: float = Field(13000.0, gt=0)
    altitude_steps: int = Field(6, ge=2, le=14)


class SalvoRequest(BaseModel):
    engagement: EngagementRequest = EngagementRequest()
    count: int = Field(3, ge=1, le=8)
    stagger: float = Field(1.0, ge=0.0, le=30.0, description="s between launches")
    elevation_spread: float = Field(6.0, ge=0.0, le=40.0, description="deg total")
    auto_aim: bool = True


def _default_raid_threats() -> list[TargetModel]:
    """A small inbound raid fanned across downrange, altitude and bearing."""
    return [
        TargetModel(position=[16000.0, -4000.0, 9000.0],
                    velocity=[-300.0, 70.0, -30.0]),
        TargetModel(position=[18000.0, 0.0, 7000.0],
                    velocity=[-320.0, 0.0, -25.0]),
        TargetModel(position=[15000.0, 5000.0, 10000.0],
                    velocity=[-290.0, -90.0, -35.0]),
    ]


class RaidRequest(BaseModel):
    interceptor: InterceptorModel = Field(default_factory=InterceptorModel)
    threats: list[TargetModel] = Field(default_factory=_default_raid_threats)
    interceptors_per_threat: int = Field(1, ge=1, le=4)
    stagger: float = Field(0.8, ge=0.0, le=30.0, description="s between salvo shots")
    elevation_spread: float = Field(4.0, ge=0.0, le=40.0, description="deg total")
    dt: float = Field(0.01, gt=0, le=0.1)
    max_time: float = Field(120.0, gt=0, le=600)
    lethal_radius: float = Field(5.0, gt=0)
    wind: WindModel = Field(default_factory=WindModel)


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
        seed=req.seed,
        wind=req.wind.to_wind(),
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
        wind=req.wind.to_wind(),
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
        wind=eng.wind.to_wind(),
    )
    out = result.as_dict()
    out["interceptor_motor_summary"] = motor_res.as_dict()["summary"]
    return out


@router.post("/raid")
def raid(req: RaidRequest):
    """Defend against a many-on-many raid: one auto-aimed salvo per threat."""
    interceptor, motor_res = req.interceptor.build()
    threats = [t.to_target() for t in req.threats]
    result = simulate_raid(
        interceptor,
        threats,
        launch_speed=req.interceptor.launch_speed,
        interceptors_per_threat=req.interceptors_per_threat,
        stagger=req.stagger,
        elevation_spread=req.elevation_spread,
        dt=req.dt,
        max_time=req.max_time,
        lethal_radius=req.lethal_radius,
        wind=req.wind.to_wind(),
    )
    out = result.as_dict()
    out["interceptor_motor_summary"] = motor_res.as_dict()["summary"]
    return out


@router.post("/defended_area")
def defended_area_endpoint(req: DefendedAreaRequest):
    """Map intercept miss/outcome over a grid of target downrange and altitude."""
    eng = req.engagement
    interceptor, _motor = eng.interceptor.build()
    template = eng.target.to_target()
    xs = _linspace(req.downrange_min, req.downrange_max, req.downrange_steps)
    zs = _linspace(req.altitude_min, req.altitude_max, req.altitude_steps)
    return defended_area(
        interceptor, template,
        launch_speed=eng.interceptor.launch_speed,
        target_speed=req.target_speed,
        downrange=xs, altitudes=zs,
        max_time=eng.max_time, lethal_radius=eng.lethal_radius,
    )


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
