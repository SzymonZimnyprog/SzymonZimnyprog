"""Multi-stage / boost-sustain solid motor stacks.

A stack is an ordered list of stages, each a fully independent solid motor
(propellant + grain + nozzle). Stages fire sequentially: stage ``i`` ignites a
configurable ``ignition_delay`` seconds after the previous stage burns out
(delay 0 = immediate, >0 = coast between stages). This builds the combined
thrust-vs-time profile a multi-stage interceptor (e.g. a boosted sustainer)
would deliver.

The combining logic operates on already-simulated
:class:`~backend.sim.motor.MotorResult` objects, so it is independent of the
API layer and the burn-rate model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .motor import MotorResult, _impulse_class


@dataclass
class StageTiming:
    index: int
    start_time: float          # absolute ignition time, s
    burn_time: float           # s
    total_impulse: float       # N*s
    propellant_mass: float     # kg
    impulse_class: str


@dataclass
class StackResult:
    time: list[float] = field(default_factory=list)        # combined, s
    thrust: list[float] = field(default_factory=list)      # combined, N
    stage_starts: list[float] = field(default_factory=list)
    stages: list[StageTiming] = field(default_factory=list)

    total_impulse: float = 0.0
    burn_time: float = 0.0             # last burnout, s
    propellant_mass_total: float = 0.0
    peak_thrust: float = 0.0
    impulse_class: str = ""

    def as_dict(self) -> dict:
        return {
            "time": self.time,
            "thrust": self.thrust,
            "stage_starts": self.stage_starts,
            "stages": [
                {
                    "index": s.index,
                    "start_time": s.start_time,
                    "burn_time": s.burn_time,
                    "total_impulse": s.total_impulse,
                    "propellant_mass": s.propellant_mass,
                    "impulse_class": s.impulse_class,
                }
                for s in self.stages
            ],
            "summary": {
                "total_impulse": self.total_impulse,
                "burn_time": self.burn_time,
                "propellant_mass_total": self.propellant_mass_total,
                "peak_thrust": self.peak_thrust,
                "impulse_class": self.impulse_class,
                "stage_count": len(self.stages),
            },
        }


def combine_stages(
    results: list[MotorResult],
    ignition_delays: list[float],
    max_samples: int = 2000,
) -> StackResult:
    """Concatenate sequential stage thrust curves onto a common time base.

    The combined curve is downsampled to at most ``max_samples`` points for
    transport; the reported peak thrust and total impulse are taken from the
    full-resolution data.
    """
    stack = StackResult()
    times: list[float] = []
    thrusts: list[float] = []
    clock = 0.0
    for i, res in enumerate(results):
        delay = ignition_delays[i] if i < len(ignition_delays) else 0.0
        start = clock + (delay if i > 0 else 0.0)

        for j in range(len(res.time)):
            times.append(start + res.time[j])
            thrusts.append(res.thrust[j])

        stack.stage_starts.append(start)
        stack.stages.append(StageTiming(
            index=i,
            start_time=start,
            burn_time=res.burn_time,
            total_impulse=res.total_impulse,
            propellant_mass=res.propellant_mass_initial,
            impulse_class=res.impulse_class,
        ))

        stack.total_impulse += res.total_impulse
        stack.propellant_mass_total += res.propellant_mass_initial
        clock = start + res.burn_time

    stack.burn_time = clock
    stack.peak_thrust = max(thrusts) if thrusts else 0.0
    stack.impulse_class = _impulse_class(stack.total_impulse)

    stride = max(1, (len(times) + max_samples - 1) // max_samples)
    stack.time = times[::stride]
    stack.thrust = thrusts[::stride]
    if times and stack.time[-1] != times[-1]:
        stack.time.append(times[-1])
        stack.thrust.append(thrusts[-1])
    return stack
