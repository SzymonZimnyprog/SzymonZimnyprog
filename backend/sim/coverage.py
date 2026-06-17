"""Defended-area / engagement-envelope mapping.

Sweeps an inbound target over a grid of downrange distance and altitude; at each
grid point the fire-control solver aims at the (nominal) track and the resulting
miss distance / intercept outcome is recorded. The result is a 2-D map of where
the battery can reach -- a standard systems-analysis "defended area" study,
purely kinematic.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from .engagement import Interceptor, Target
from .firecontrol import solve_firing_solution


def _inbound_velocity(position: np.ndarray, speed: float) -> np.ndarray:
    """Velocity of magnitude ``speed`` pointing from the target toward the site."""
    to_site = -position
    n = float(np.linalg.norm(to_site))
    if n < 1e-6:
        return np.array([0.0, 0.0, -speed])
    return to_site / n * speed


def defended_area(
    interceptor: Interceptor,
    target_template: Target,
    *,
    launch_speed: float,
    target_speed: float,
    downrange: list[float],
    altitudes: list[float],
    max_time: float = 120.0,
    lethal_radius: float = 5.0,
    miss_cap: float = 200.0,
) -> dict:
    """Return miss / hit grids over (downrange x altitude) for an inbound target.

    Each cell places the target at ``[downrange, 0, altitude]`` moving toward the
    launch site at ``target_speed`` and runs a (coarse) firing solution.
    """
    miss_grid: list[list[float]] = []
    hit_grid: list[list[int]] = []
    hits = 0
    total = 0
    for z in altitudes:
        miss_row: list[float] = []
        hit_row: list[int] = []
        for x in downrange:
            pos = np.array([float(x), 0.0, float(z)])
            vel = _inbound_velocity(pos, target_speed)
            target = replace(target_template, position=pos, velocity=vel)
            sol = solve_firing_solution(
                interceptor, target, launch_speed=launch_speed,
                coarse_steps=10, refine_iters=6, refine_azimuth=False,
                search_dt=0.05, final_dt=0.02, max_time=max_time,
                lethal_radius=lethal_radius,
            )
            miss_row.append(min(float(sol.miss_distance), miss_cap))
            hit_row.append(1 if sol.intercepted else 0)
            hits += int(sol.intercepted)
            total += 1
        miss_grid.append(miss_row)
        hit_grid.append(hit_row)

    return {
        "values_x": list(downrange),
        "values_y": list(altitudes),
        "miss": miss_grid,
        "hit": hit_grid,
        "hit_fraction": hits / total if total else 0.0,
        "miss_cap": miss_cap,
    }
