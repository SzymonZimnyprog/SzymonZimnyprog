"""Fire-control solver: find a launch direction that intercepts the target.

Given a fully-built :class:`~backend.sim.engagement.Interceptor` (motor and
airframe already fixed) and a :class:`~backend.sim.engagement.Target`, search
the launch *elevation* (and optionally refine *azimuth*) that minimises the
miss distance. The motor thrust curve does not depend on the launch direction,
so the interceptor vehicle is built once and only the initial velocity vector
is varied per evaluation -- the search runs many cheap engagement integrations
rather than re-simulating the motor each time.

This turns the simulator into a closed interception *system*: point the target,
get back the firing solution and the resulting engagement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

from .engagement import (
    EngagementResult,
    Interceptor,
    Target,
    simulate_engagement,
)


def _launch_velocity(
    speed: float, elevation_deg: float, azimuth_deg: float
) -> np.ndarray:
    el = math.radians(elevation_deg)
    az = math.radians(azimuth_deg)
    horizontal = speed * math.cos(el)
    return np.array([
        horizontal * math.sin(az),
        horizontal * math.cos(az),
        speed * math.sin(el),
    ])


def bearing_to_target(
    launch_position: np.ndarray, target_position: np.ndarray
) -> float:
    """Compass-style azimuth (deg) from launch point toward the target (E/N)."""
    d = target_position - launch_position
    return math.degrees(math.atan2(d[0], d[1]))


@dataclass
class FireSolution:
    intercepted: bool = False
    elevation_deg: float = 0.0
    azimuth_deg: float = 0.0
    miss_distance: float = float("inf")
    intercept_time: float = 0.0
    intercept_point: list[float] = field(default_factory=list)
    envelope: list[dict] = field(default_factory=list)  # [{elevation, miss, hit}]
    engagement: dict = field(default_factory=dict)       # best EngagementResult

    def as_dict(self) -> dict:
        return {
            "intercepted": self.intercepted,
            "elevation_deg": self.elevation_deg,
            "azimuth_deg": self.azimuth_deg,
            "miss_distance": self.miss_distance,
            "intercept_time": self.intercept_time,
            "intercept_point": self.intercept_point,
            "envelope": self.envelope,
            "engagement": self.engagement,
        }


def _evaluate(
    interceptor: Interceptor,
    target: Target,
    speed: float,
    elevation: float,
    azimuth: float,
    dt: float,
    max_time: float,
    lethal_radius: float,
) -> EngagementResult:
    candidate = replace(
        interceptor, launch_velocity=_launch_velocity(speed, elevation, azimuth)
    )
    return simulate_engagement(
        candidate, target, dt=dt, max_time=max_time, lethal_radius=lethal_radius
    )


def solve_firing_solution(
    interceptor: Interceptor,
    target: Target,
    *,
    launch_speed: float,
    elevation_bounds: tuple[float, float] = (10.0, 85.0),
    coarse_steps: int = 16,
    refine_iters: int = 18,
    refine_azimuth: bool = True,
    search_dt: float = 0.02,
    final_dt: float = 0.01,
    max_time: float = 120.0,
    lethal_radius: float = 5.0,
) -> FireSolution:
    """Search launch elevation (and optionally azimuth) for minimum miss."""
    azimuth = bearing_to_target(interceptor.launch_position, target.position)

    def miss_at(elevation: float, az: float) -> tuple[float, EngagementResult]:
        res = _evaluate(
            interceptor, target, launch_speed, elevation, az,
            search_dt, max_time, lethal_radius,
        )
        return res.miss_distance, res

    # ---- coarse elevation scan --------------------------------------------
    lo, hi = elevation_bounds
    elevations = [lo + (hi - lo) * i / (coarse_steps - 1) for i in range(coarse_steps)]
    envelope: list[dict] = []
    best_el = elevations[0]
    best_miss = float("inf")
    for el in elevations:
        miss, res = miss_at(el, azimuth)
        envelope.append({"elevation": el, "miss": miss, "hit": res.intercepted})
        if miss < best_miss:
            best_miss, best_el = miss, el

    # ---- golden-section refinement around the best bracket ----------------
    step = (hi - lo) / (coarse_steps - 1)
    a, b = max(lo, best_el - step), min(hi, best_el + step)
    gr = (math.sqrt(5.0) - 1.0) / 2.0
    c = b - gr * (b - a)
    d = a + gr * (b - a)
    fc = miss_at(c, azimuth)[0]
    fd = miss_at(d, azimuth)[0]
    for _ in range(refine_iters):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - gr * (b - a)
            fc = miss_at(c, azimuth)[0]
        else:
            a, c, fc = c, d, fd
            d = a + gr * (b - a)
            fd = miss_at(d, azimuth)[0]
    best_el = 0.5 * (a + b)

    # ---- optional small azimuth refinement (lateral lead) -----------------
    if refine_azimuth:
        best_az = azimuth
        best_az_miss = miss_at(best_el, azimuth)[0]
        for delta in (-6.0, -3.0, -1.5, 1.5, 3.0, 6.0):
            miss = miss_at(best_el, azimuth + delta)[0]
            if miss < best_az_miss:
                best_az_miss, best_az = miss, azimuth + delta
        azimuth = best_az

    # ---- final high-resolution run at the solution ------------------------
    final = _evaluate(
        interceptor, target, launch_speed, best_el, azimuth,
        final_dt, max_time, lethal_radius,
    )
    s = final.as_dict()["summary"]
    return FireSolution(
        intercepted=s["intercepted"],
        elevation_deg=best_el,
        azimuth_deg=azimuth,
        miss_distance=s["miss_distance"],
        intercept_time=s["intercept_time"],
        intercept_point=s["intercept_point"],
        envelope=sorted(envelope, key=lambda e: e["elevation"]),
        engagement=final.as_dict(),
    )
