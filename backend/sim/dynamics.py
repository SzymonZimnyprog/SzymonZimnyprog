"""3-DOF point-mass flight dynamics with RK4 integration.

State vector is ``[x, y, z, vx, vy, vz, m]`` in an East-North-Up flat-earth
frame (z is altitude). Forces modelled:

* thrust along the velocity direction (or the launch direction before lift-off),
  taken from a motor :class:`~backend.sim.motor.ThrustCurve`;
* aerodynamic drag opposing velocity (:mod:`backend.sim.aerodynamics`);
* constant gravity;
* an externally commanded lateral acceleration (from guidance), applied
  perpendicular to the velocity.

Mass is integrated from the motor mass-flow so specific impulse and burnout are
consistent with the thrust curve.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .aerodynamics import Airframe
from .atmosphere import G0, atmosphere
from .motor import ThrustCurve
from .wind import WindField

GRAVITY = np.array([0.0, 0.0, -G0])


@dataclass
class Vehicle:
    airframe: Airframe
    thrust_curve: ThrustCurve | None = None

    def total_mass(self, propellant_remaining: float) -> float:
        return self.airframe.dry_mass + max(propellant_remaining, 0.0)


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else np.zeros(3)


def derivative(
    state: np.ndarray,
    t: float,
    vehicle: Vehicle,
    lateral_accel: np.ndarray,
    launch_dir: np.ndarray,
    wind: WindField | None = None,
) -> np.ndarray:
    """Return d(state)/dt for the 7-element point-mass state."""
    pos = state[0:3]
    vel = state[3:6]
    mass = max(state[6], 1e-3)

    ground_speed = float(np.linalg.norm(vel))
    # Aerodynamics act on the air-relative velocity (drag, Mach).
    v_air = vel if wind is None else vel - wind.at(pos[2])
    air_speed = float(np.linalg.norm(v_air))
    atmo = atmosphere(pos[2])
    mach = air_speed / atmo.speed_of_sound if atmo.speed_of_sound > 0 else 0.0

    # Thrust (along the flight path / body axis, approximated by ground velocity).
    thrust_mag = 0.0
    mdot = 0.0
    if vehicle.thrust_curve is not None:
        thrust_mag = vehicle.thrust_curve.thrust_at(t)
        mdot = vehicle.thrust_curve.mass_flow_at(t)
    thrust_dir = _unit(vel) if ground_speed > 1.0 else _unit(launch_dir)
    a_thrust = thrust_dir * (thrust_mag / mass)

    # Drag (opposes the air-relative velocity).
    drag_mag = vehicle.airframe.drag(atmo.density, air_speed, mach)
    a_drag = -_unit(v_air) * (drag_mag / mass)

    accel = a_thrust + a_drag + GRAVITY + lateral_accel

    deriv = np.empty(7)
    deriv[0:3] = vel
    deriv[3:6] = accel
    deriv[6] = -mdot
    return deriv


def rk4_step(
    state: np.ndarray,
    t: float,
    dt: float,
    vehicle: Vehicle,
    lateral_accel: np.ndarray,
    launch_dir: np.ndarray,
    wind: WindField | None = None,
) -> np.ndarray:
    """Single classical Runge-Kutta 4 step.

    The guidance command ``lateral_accel`` and ``launch_dir`` are held constant
    across the step (computed once per outer iteration).
    """
    half = 0.5 * dt
    la, ld = lateral_accel, launch_dir
    k1 = derivative(state, t, vehicle, la, ld, wind)
    k2 = derivative(state + half * k1, t + half, vehicle, la, ld, wind)
    k3 = derivative(state + half * k2, t + half, vehicle, la, ld, wind)
    k4 = derivative(state + dt * k3, t + dt, vehicle, la, ld, wind)
    return state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


@dataclass
class TrajectoryResult:
    time: list[float] = field(default_factory=list)
    position: list[list[float]] = field(default_factory=list)
    velocity: list[list[float]] = field(default_factory=list)
    speed: list[float] = field(default_factory=list)
    mach: list[float] = field(default_factory=list)
    mass: list[float] = field(default_factory=list)
    altitude: list[float] = field(default_factory=list)

    apogee: float = 0.0
    max_speed: float = 0.0
    max_mach: float = 0.0
    range_: float = 0.0
    flight_time: float = 0.0

    def as_dict(self) -> dict:
        return {
            "time": self.time,
            "position": self.position,
            "velocity": self.velocity,
            "speed": self.speed,
            "mach": self.mach,
            "mass": self.mass,
            "altitude": self.altitude,
            "summary": {
                "apogee": self.apogee,
                "max_speed": self.max_speed,
                "max_mach": self.max_mach,
                "range": self.range_,
                "flight_time": self.flight_time,
            },
        }


def propagate(
    vehicle: Vehicle,
    launch_position: np.ndarray,
    launch_velocity: np.ndarray,
    propellant_mass: float,
    dt: float = 0.02,
    max_time: float = 300.0,
    sample_every: int = 5,
    wind: WindField | None = None,
) -> TrajectoryResult:
    """Free-flight (un-guided) trajectory until ground impact or time limit."""
    state = np.empty(7)
    state[0:3] = launch_position
    state[3:6] = launch_velocity
    state[6] = vehicle.total_mass(propellant_mass)
    launch_dir = (
        _unit(launch_velocity)
        if np.linalg.norm(launch_velocity) > 0
        else np.array([0.0, 0.0, 1.0])
    )

    res = TrajectoryResult()
    t = 0.0
    step = 0
    launch_origin = launch_position.copy()
    no_lateral = np.zeros(3)

    while t <= max_time:
        if step % sample_every == 0:
            _record(res, state, t, launch_origin)
        # stop just after the vehicle returns to the ground while descending
        if state[2] < 0.0 and state[5] < 0.0 and t > 0.0:
            break
        state = rk4_step(state, t, dt, vehicle, no_lateral, launch_dir, wind)
        t += dt
        step += 1

    _finalise(res, t)
    return res


def propagate_staged(
    vehicle: Vehicle,
    launch_position: np.ndarray,
    launch_velocity: np.ndarray,
    initial_mass: float,
    separation_events: list[tuple[float, float]],
    dt: float = 0.02,
    max_time: float = 300.0,
    sample_every: int = 5,
    wind: WindField | None = None,
) -> tuple[TrajectoryResult, list[dict]]:
    """Un-guided staged flight: drop spent-stage mass at separation events.

    ``vehicle.thrust_curve`` should be a StagedThrust. ``separation_events`` is a
    list of ``(time, mass_to_drop)`` applied to the vehicle mass as each spent
    stage is jettisoned. Returns the trajectory and the recorded events.
    """
    state = np.empty(7)
    state[0:3] = launch_position
    state[3:6] = launch_velocity
    state[6] = initial_mass
    launch_dir = (
        _unit(launch_velocity)
        if np.linalg.norm(launch_velocity) > 0
        else np.array([0.0, 0.0, 1.0])
    )

    res = TrajectoryResult()
    pending = sorted(separation_events, key=lambda e: e[0])
    events: list[dict] = []
    t = 0.0
    step = 0
    origin = launch_position.copy()
    no_lateral = np.zeros(3)

    while t <= max_time:
        if step % sample_every == 0:
            _record(res, state, t, origin)
        if state[2] < 0.0 and state[5] < 0.0 and t > 0.0:
            break
        state = rk4_step(state, t, dt, vehicle, no_lateral, launch_dir, wind)
        t += dt
        step += 1
        # Apply any separations crossed during this step.
        while pending and t >= pending[0][0]:
            sep_t, mass_drop = pending.pop(0)
            state[6] = max(state[6] - mass_drop, 0.1)
            events.append({
                "time": sep_t,
                "altitude": float(state[2]),
                "mass_after": float(state[6]),
            })

    _finalise(res, t)
    return res, events


def _record(res: TrajectoryResult, state: np.ndarray, t: float, origin: np.ndarray):
    pos = state[0:3]
    vel = state[3:6]
    speed = float(np.linalg.norm(vel))
    atmo = atmosphere(pos[2])
    mach = speed / atmo.speed_of_sound if atmo.speed_of_sound > 0 else 0.0
    res.time.append(t)
    res.position.append(pos.tolist())
    res.velocity.append(vel.tolist())
    res.speed.append(speed)
    res.mach.append(mach)
    res.mass.append(float(state[6]))
    res.altitude.append(float(pos[2]))
    res.apogee = max(res.apogee, float(pos[2]))
    res.max_speed = max(res.max_speed, speed)
    res.max_mach = max(res.max_mach, mach)
    ground_range = float(np.linalg.norm((pos - origin)[0:2]))
    res.range_ = max(res.range_, ground_range)


def _finalise(res: TrajectoryResult, t: float):
    res.flight_time = t
