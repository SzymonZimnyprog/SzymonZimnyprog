"""Many-on-many raid: defend against several threats at once.

A *raid* is a set of inbound threats engaged simultaneously from one battery.
Each threat is auto-aimed and assigned ``interceptors_per_threat`` interceptors
(a small salvo per threat, reusing :func:`backend.sim.salvo.simulate_salvo`).
The raid is "defeated" only if every threat is intercepted; any survivor is a
*leaker*. Purely kinematic closest-approach scoring, like the rest of the core.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .engagement import Interceptor, Target
from .salvo import simulate_salvo
from .wind import WindField


@dataclass
class RaidResult:
    threats: int = 0
    killed: int = 0
    leakers: int = 0
    interceptors_fired: int = 0
    duration: float = 0.0
    targets: list[dict] = field(default_factory=list)
    interceptors: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "threats": self.threats,
            "killed": self.killed,
            "leakers": self.leakers,
            "interceptors_fired": self.interceptors_fired,
            "duration": self.duration,
            "leak_fraction": (self.leakers / self.threats) if self.threats else 0.0,
            "interceptors_per_kill": (
                self.interceptors_fired / self.killed) if self.killed else None,
            "targets": self.targets,
            "interceptors": self.interceptors,
        }


def simulate_raid(
    interceptor: Interceptor,
    threats: list[Target],
    *,
    launch_speed: float,
    interceptors_per_threat: int = 1,
    stagger: float = 0.8,
    elevation_spread: float = 4.0,
    dt: float = 0.01,
    max_time: float = 120.0,
    lethal_radius: float = 5.0,
    wind: WindField | None = None,
) -> RaidResult:
    """Engage every threat with its own auto-aimed salvo; report the raid outcome."""
    res = RaidResult(threats=len(threats))
    for ti, threat in enumerate(threats):
        sv = simulate_salvo(
            interceptor, threat,
            launch_speed=launch_speed,
            count=interceptors_per_threat,
            stagger=stagger,
            elevation_spread=elevation_spread,
            auto_aim=True,
            dt=dt, max_time=max_time, lethal_radius=lethal_radius, wind=wind,
        ).as_dict()

        hit = sv["intercepted"]
        res.killed += 1 if hit else 0
        res.interceptors_fired += sv["count"]
        res.duration = max(res.duration, sv["duration"])

        best = None
        for sh in sv["shots"]:
            res.interceptors.append({
                "index": len(res.interceptors),
                "target_index": ti,
                "intercepted": sh["intercepted"],
                "miss_distance": sh["miss_distance"],
                "intercept_point": sh["intercept_point"],
                "track": sh["track"],
            })
            if sh["intercepted"] and (
                best is None or sh["miss_distance"] < best["miss_distance"]):
                best = sh

        res.targets.append({
            "index": ti,
            "intercepted": hit,
            "best_miss": sv["best_miss"],
            "assigned": sv["count"],
            "azimuth_deg": sv["azimuth_deg"],
            "intercept_point": best["intercept_point"] if best else None,
            "intercept_time": best["intercept_time"] if best else None,
            "track": sv["target_track"],
        })

    res.leakers = res.threats - res.killed
    return res
