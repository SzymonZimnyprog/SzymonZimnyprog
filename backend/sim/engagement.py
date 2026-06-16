"""Interceptor-vs-target engagement simulation.

Two point-mass vehicles are propagated together:

* the **target** flies a ballistic arc (gravity + drag) with an optional
  constant evasive manoeuvre acceleration;
* the **interceptor** boosts on its solid motor along the launch direction,
  then homes using proportional navigation (:mod:`backend.sim.guidance`) once
  its seeker activates.

The simulation reports the full time histories, the closest approach (miss
distance) and whether the miss distance fell inside the configured lethal
radius (a kinematic intercept criterion). It is a kinematics/guidance study --
there is no warhead or lethality model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .aerodynamics import Airframe
from .atmosphere import atmosphere
from .dynamics import GRAVITY, Vehicle, rk4_step
from .guidance import closing_speed, pn_acceleration


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else np.zeros(3)


def _closest_approach(r0: np.ndarray, r1: np.ndarray) -> float:
    """Minimum separation along the segment of relative position r0 -> r1.

    Treats the relative motion over one integration step as linear (closest
    point of approach), so the recorded miss distance is accurate even when the
    step is large compared with the closing speed."""
    d = r1 - r0
    dd = float(np.dot(d, d))
    if dd < 1e-12:
        return float(np.linalg.norm(r0))
    s = -float(np.dot(r0, d)) / dd
    s = max(0.0, min(1.0, s))
    return float(np.linalg.norm(r0 + s * d))


@dataclass
class Target:
    position: np.ndarray            # m, ENU
    velocity: np.ndarray            # m/s
    airframe: Airframe
    mass: float                     # kg
    maneuver_accel: np.ndarray = field(default_factory=lambda: np.zeros(3))


@dataclass
class Interceptor:
    vehicle: Vehicle
    launch_position: np.ndarray
    launch_velocity: np.ndarray     # initial velocity (boosted off the rail)
    propellant_mass: float
    nav_constant: float = 4.0
    max_lateral_g: float = 40.0
    seeker_delay: float = 0.3       # s before guidance engages
    seeker_range: float = 50000.0   # m max acquisition range


@dataclass
class EngagementResult:
    time: list[float] = field(default_factory=list)
    interceptor_position: list[list[float]] = field(default_factory=list)
    target_position: list[list[float]] = field(default_factory=list)
    separation: list[float] = field(default_factory=list)
    interceptor_speed: list[float] = field(default_factory=list)
    target_speed: list[float] = field(default_factory=list)
    interceptor_accel_cmd: list[float] = field(default_factory=list)

    intercepted: bool = False
    miss_distance: float = float("inf")
    intercept_time: float = 0.0
    intercept_point: list[float] = field(default_factory=list)
    closing_speed_at_intercept: float = 0.0

    def as_dict(self) -> dict:
        return {
            "time": self.time,
            "interceptor_position": self.interceptor_position,
            "target_position": self.target_position,
            "separation": self.separation,
            "interceptor_speed": self.interceptor_speed,
            "target_speed": self.target_speed,
            "interceptor_accel_cmd": self.interceptor_accel_cmd,
            "summary": {
                "intercepted": self.intercepted,
                "miss_distance": self.miss_distance,
                "intercept_time": self.intercept_time,
                "intercept_point": self.intercept_point,
                "closing_speed_at_intercept": self.closing_speed_at_intercept,
            },
        }


def _target_derivative(state: np.ndarray, target: Target) -> np.ndarray:
    vel = state[3:6]
    speed = float(np.linalg.norm(vel))
    atmo = atmosphere(state[2])
    mach = speed / atmo.speed_of_sound if atmo.speed_of_sound > 0 else 0.0
    drag_mag = target.airframe.drag(atmo.density, speed, mach)
    a_drag = -_unit(vel) * (drag_mag / target.mass)
    accel = a_drag + GRAVITY + target.maneuver_accel
    deriv = np.empty(6)
    deriv[0:3] = vel
    deriv[3:6] = accel
    return deriv


def _target_rk4(state: np.ndarray, dt: float, target: Target) -> np.ndarray:
    k1 = _target_derivative(state, target)
    k2 = _target_derivative(state + 0.5 * dt * k1, target)
    k3 = _target_derivative(state + 0.5 * dt * k2, target)
    k4 = _target_derivative(state + dt * k3, target)
    return state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def advance_target(target: Target, duration: float, dt: float = 0.05) -> Target:
    """Return a copy of the target propagated forward by ``duration`` seconds."""
    from dataclasses import replace

    if duration <= 0.0:
        return target
    state = np.empty(6)
    state[0:3] = target.position
    state[3:6] = target.velocity
    steps = max(1, int(round(duration / dt)))
    h = duration / steps
    for _ in range(steps):
        state = _target_rk4(state, h, target)
    return replace(target, position=state[0:3].copy(), velocity=state[3:6].copy())


def simulate_engagement(
    interceptor: Interceptor,
    target: Target,
    dt: float = 0.01,
    max_time: float = 120.0,
    lethal_radius: float = 5.0,
    sample_every: int = 5,
) -> EngagementResult:
    """Run the engagement until intercept, miss, ground impact or timeout."""
    m_state = np.empty(7)
    m_state[0:3] = interceptor.launch_position
    m_state[3:6] = interceptor.launch_velocity
    m_state[6] = interceptor.vehicle.total_mass(interceptor.propellant_mass)
    launch_dir = _unit(interceptor.launch_velocity)

    t_state = np.empty(6)
    t_state[0:3] = target.position
    t_state[3:6] = target.velocity

    res = EngagementResult()
    t = 0.0
    step = 0
    prev_sep = float("inf")
    prev_rel = t_state[0:3] - m_state[0:3]

    while t <= max_time:
        r_m, v_m = m_state[0:3], m_state[3:6]
        r_t, v_t = t_state[0:3], t_state[3:6]
        rel = r_t - r_m
        sep = float(np.linalg.norm(rel))
        # True closest approach over the step just taken (robust to dt).
        cpa = sep if step == 0 else _closest_approach(prev_rel, rel)

        # Guidance command.
        a_cmd = np.zeros(3)
        if t >= interceptor.seeker_delay and sep <= interceptor.seeker_range:
            a_cmd = pn_acceleration(
                r_m, v_m, r_t, v_t,
                nav_constant=interceptor.nav_constant,
                max_lateral_g=interceptor.max_lateral_g,
            )

        if step % sample_every == 0:
            res.time.append(t)
            res.interceptor_position.append(r_m.tolist())
            res.target_position.append(r_t.tolist())
            res.separation.append(sep)
            res.interceptor_speed.append(float(np.linalg.norm(v_m)))
            res.target_speed.append(float(np.linalg.norm(v_t)))
            res.interceptor_accel_cmd.append(float(np.linalg.norm(a_cmd)))

        # Track closest approach (using the analytic CPA for this step).
        if cpa < res.miss_distance:
            res.miss_distance = cpa
            res.intercept_time = t
            res.intercept_point = (0.5 * (r_m + r_t)).tolist()
            res.closing_speed_at_intercept = closing_speed(r_m, v_m, r_t, v_t)

        # Intercept criterion.
        if cpa <= lethal_radius:
            res.intercepted = True
            break

        # Miss detection: separation passed through a minimum and is growing.
        if sep > prev_sep and t > interceptor.seeker_delay:
            break
        prev_sep = sep
        prev_rel = rel.copy()

        # Stop if either vehicle hits the ground while descending.
        m_down = m_state[2] < 0.0 and m_state[5] < 0.0
        t_down = t_state[2] < 0.0 and t_state[5] < 0.0
        if m_down or t_down:
            break

        m_state = rk4_step(m_state, t, dt, interceptor.vehicle, a_cmd, launch_dir)
        t_state = _target_rk4(t_state, dt, target)
        t += dt
        step += 1

    return res
