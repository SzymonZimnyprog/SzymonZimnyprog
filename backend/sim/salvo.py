"""Salvo / layered-defence engagement: fire several interceptors at one target.

Models a *shoot-look-shoot* salvo: ``count`` interceptors are launched from the
same site at a fixed time ``stagger`` apart, with their launch elevations spread
symmetrically about a nominal solution. Each later shot sees the target where it
has moved to by its launch time. The salvo succeeds if any shot intercepts.

This is the layered-defence layer on top of the single-shot fire-control
solver -- still a purely kinematic study.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

from .engagement import Interceptor, Target, advance_target, simulate_engagement
from .firecontrol import bearing_to_target, solve_firing_solution


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


@dataclass
class SalvoResult:
    count: int = 0
    hits: int = 0
    intercepted: bool = False
    best_miss: float = float("inf")
    azimuth_deg: float = 0.0
    shots: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "count": self.count,
            "hits": self.hits,
            "intercepted": self.intercepted,
            "best_miss": self.best_miss,
            "azimuth_deg": self.azimuth_deg,
            "success_fraction": (self.hits / self.count) if self.count else 0.0,
            "shots": self.shots,
        }


def simulate_salvo(
    interceptor: Interceptor,
    target: Target,
    *,
    launch_speed: float,
    count: int = 3,
    stagger: float = 1.0,
    elevation_spread: float = 6.0,
    auto_aim: bool = True,
    dt: float = 0.01,
    max_time: float = 120.0,
    lethal_radius: float = 5.0,
) -> SalvoResult:
    """Fire ``count`` staggered interceptors and report each shot's outcome."""
    azimuth = bearing_to_target(interceptor.launch_position, target.position)

    if auto_aim:
        nominal = solve_firing_solution(
            interceptor, target, launch_speed=launch_speed,
            max_time=max_time, lethal_radius=lethal_radius,
        )
        nominal_el = nominal.elevation_deg
        azimuth = nominal.azimuth_deg
    else:
        nominal_el = math.degrees(
            math.atan2(interceptor.launch_velocity[2],
                       np.linalg.norm(interceptor.launch_velocity[0:2]))
        )

    res = SalvoResult(count=count, azimuth_deg=azimuth)
    for i in range(count):
        launch_time = i * stagger
        offset = 0.0 if count == 1 else (i - (count - 1) / 2.0) / (count - 1)
        elevation = nominal_el + elevation_spread * offset
        moved_target = advance_target(target, launch_time)
        shot_interceptor = replace(
            interceptor,
            launch_velocity=_launch_velocity(launch_speed, elevation, azimuth),
        )
        eng = simulate_engagement(
            shot_interceptor, moved_target, dt=dt, max_time=max_time,
            lethal_radius=lethal_radius,
        )
        summary = eng.as_dict()["summary"]
        hit = summary["intercepted"]
        res.shots.append({
            "index": i,
            "launch_time": launch_time,
            "elevation_deg": elevation,
            "intercepted": hit,
            "miss_distance": summary["miss_distance"],
            "intercept_time": launch_time + summary["intercept_time"],
        })
        if hit:
            res.hits += 1
        res.best_miss = min(res.best_miss, summary["miss_distance"])

    res.intercepted = res.hits > 0
    return res
