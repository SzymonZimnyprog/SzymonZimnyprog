"""Proportional navigation (PN) guidance law.

Given the relative geometry between the interceptor (missile, ``m``) and the
target (``t``), the true-PN acceleration command is::

    Omega   = (R x V) / (R . R)          # line-of-sight angular rate vector
    Vc      = -(R . V) / |R|             # closing speed (positive when closing)
    a_cmd   = N * Vc * (Omega x R_hat)    # perpendicular to the LOS

where ``R = r_t - r_m`` and ``V = v_t - v_m``. The command magnitude is limited
to the airframe's structural lateral-acceleration capability.

This is the classical homing-guidance law from Zarchan, *Tactical and Strategic
Missile Guidance* -- a control algorithm, not a weapon design.
"""

from __future__ import annotations

import numpy as np

from .atmosphere import G0


def pn_acceleration(
    r_m: np.ndarray,
    v_m: np.ndarray,
    r_t: np.ndarray,
    v_t: np.ndarray,
    nav_constant: float = 4.0,
    max_lateral_g: float = 40.0,
) -> np.ndarray:
    """Return the commanded lateral acceleration vector [m/s^2]."""
    rel_pos = r_t - r_m
    rel_vel = v_t - v_m
    range_ = float(np.linalg.norm(rel_pos))
    if range_ < 1e-6:
        return np.zeros(3)

    r_hat = rel_pos / range_
    closing_speed = -float(np.dot(rel_pos, rel_vel)) / range_
    los_rate = np.cross(rel_pos, rel_vel) / float(np.dot(rel_pos, rel_pos))

    a_cmd = nav_constant * closing_speed * np.cross(los_rate, r_hat)

    a_max = max_lateral_g * G0
    mag = float(np.linalg.norm(a_cmd))
    if mag > a_max and mag > 0.0:
        a_cmd = a_cmd * (a_max / mag)
    return a_cmd


def closing_speed(r_m: np.ndarray, v_m: np.ndarray,
                  r_t: np.ndarray, v_t: np.ndarray) -> float:
    rel_pos = r_t - r_m
    rng = float(np.linalg.norm(rel_pos))
    if rng < 1e-9:
        return 0.0
    return -float(np.dot(rel_pos, v_t - v_m)) / rng
