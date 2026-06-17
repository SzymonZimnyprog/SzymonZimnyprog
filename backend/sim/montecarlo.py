"""Monte-Carlo kill-probability under target-track uncertainty.

The launcher computes its firing solution from the *estimated* (nominal) target
track, then the *true* target is drawn many times by adding Gaussian noise to
that estimate. Each trial flies the same firing solution against its perturbed
true target; the kill probability is the fraction whose miss distance falls
inside the lethal radius.

This quantifies how sensitive the (deterministic) intercept is to sensor/track
error -- a standard systems-analysis question, still purely kinematic.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

from .engagement import Interceptor, Target, simulate_engagement
from .firecontrol import solve_firing_solution


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
class MonteCarloResult:
    trials: int = 0
    hits: int = 0
    pk: float = 0.0
    elevation_deg: float = 0.0
    azimuth_deg: float = 0.0
    mean_miss: float = 0.0
    median_miss: float = 0.0
    p90_miss: float = 0.0
    histogram_edges: list[float] = field(default_factory=list)
    histogram_counts: list[int] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "trials": self.trials,
            "hits": self.hits,
            "pk": self.pk,
            "elevation_deg": self.elevation_deg,
            "azimuth_deg": self.azimuth_deg,
            "mean_miss": self.mean_miss,
            "median_miss": self.median_miss,
            "p90_miss": self.p90_miss,
            "histogram_edges": self.histogram_edges,
            "histogram_counts": self.histogram_counts,
        }


def montecarlo_pk(
    interceptor: Interceptor,
    target: Target,
    *,
    launch_speed: float,
    trials: int = 200,
    position_sigma: float = 200.0,
    velocity_sigma: float = 20.0,
    seed: int = 0,
    dt: float = 0.05,
    max_time: float = 120.0,
    lethal_radius: float = 5.0,
) -> MonteCarloResult:
    """Estimate Pk by flying one firing solution against perturbed true targets."""
    # Aim once at the estimated (nominal) track. A coarse search is enough here
    # since the seeker homes during flight; this keeps the one-off solve cheap.
    solution = solve_firing_solution(
        interceptor, target, launch_speed=launch_speed,
        coarse_steps=12, refine_iters=8, search_dt=0.05, final_dt=dt,
        max_time=max_time, lethal_radius=lethal_radius,
    )
    fixed = replace(
        interceptor,
        launch_velocity=_launch_velocity(
            launch_speed, solution.elevation_deg, solution.azimuth_deg
        ),
    )

    rng = np.random.default_rng(seed)
    misses = np.empty(trials)
    hits = 0
    for i in range(trials):
        true_target = replace(
            target,
            position=target.position + rng.normal(0.0, position_sigma, 3),
            velocity=target.velocity + rng.normal(0.0, velocity_sigma, 3),
        )
        eng = simulate_engagement(
            fixed, true_target, dt=dt, max_time=max_time,
            lethal_radius=lethal_radius,
            seed=int(rng.integers(0, 2**32 - 1)),
        )
        miss = eng.miss_distance
        misses[i] = miss
        if eng.intercepted:
            hits += 1

    res = MonteCarloResult(
        trials=trials,
        hits=hits,
        pk=hits / trials if trials else 0.0,
        elevation_deg=solution.elevation_deg,
        azimuth_deg=solution.azimuth_deg,
        mean_miss=float(np.mean(misses)),
        median_miss=float(np.median(misses)),
        p90_miss=float(np.percentile(misses, 90)),
    )

    upper = max(float(np.percentile(misses, 95)), lethal_radius * 2.0, 1.0)
    counts, edges = np.histogram(
        np.clip(misses, 0.0, upper), bins=20, range=(0.0, upper)
    )
    res.histogram_edges = edges.tolist()
    res.histogram_counts = counts.astype(int).tolist()
    return res
