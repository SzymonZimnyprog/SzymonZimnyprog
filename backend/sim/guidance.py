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


# --------------------------------------------------------------------------- #
# Guidance-law library
# --------------------------------------------------------------------------- #
GUIDANCE_LAWS = ("PN", "APN", "PN_GRAVITY")


def _clamp(a_cmd: np.ndarray, max_lateral_g: float) -> np.ndarray:
    a_max = max_lateral_g * G0
    mag = float(np.linalg.norm(a_cmd))
    if mag > a_max and mag > 0.0:
        return a_cmd * (a_max / mag)
    return a_cmd


def augmented_pn_acceleration(
    r_m: np.ndarray,
    v_m: np.ndarray,
    r_t: np.ndarray,
    v_t: np.ndarray,
    target_accel: np.ndarray,
    nav_constant: float = 4.0,
    max_lateral_g: float = 40.0,
) -> np.ndarray:
    """Augmented PN: true-PN term plus N/2 of the target acceleration normal
    to the line of sight (effective against a manoeuvring target)."""
    rel_pos = r_t - r_m
    rng = float(np.linalg.norm(rel_pos))
    if rng < 1e-6:
        return np.zeros(3)
    r_hat = rel_pos / rng
    a_pn = pn_acceleration(r_m, v_m, r_t, v_t, nav_constant, max_lateral_g=1e9)
    a_t_perp = target_accel - float(np.dot(target_accel, r_hat)) * r_hat
    return _clamp(a_pn + 0.5 * nav_constant * a_t_perp, max_lateral_g)


def pn_gravity_acceleration(
    r_m: np.ndarray,
    v_m: np.ndarray,
    r_t: np.ndarray,
    v_t: np.ndarray,
    gravity: np.ndarray,
    nav_constant: float = 4.0,
    max_lateral_g: float = 40.0,
) -> np.ndarray:
    """True PN plus a gravity-bias term that cancels the component of gravity
    perpendicular to the line of sight, so the missile doesn't sag below it."""
    rel_pos = r_t - r_m
    rng = float(np.linalg.norm(rel_pos))
    if rng < 1e-6:
        return np.zeros(3)
    r_hat = rel_pos / rng
    a_pn = pn_acceleration(r_m, v_m, r_t, v_t, nav_constant, max_lateral_g=1e9)
    g_perp = gravity - float(np.dot(gravity, r_hat)) * r_hat
    return _clamp(a_pn - g_perp, max_lateral_g)


def guidance_command(
    law: str,
    r_m: np.ndarray,
    v_m: np.ndarray,
    r_t: np.ndarray,
    v_t: np.ndarray,
    *,
    nav_constant: float = 4.0,
    max_lateral_g: float = 40.0,
    target_accel: np.ndarray | None = None,
    gravity: np.ndarray | None = None,
) -> np.ndarray:
    """Dispatch to the selected guidance law (defaults to true PN)."""
    if law == "APN":
        ta = target_accel if target_accel is not None else np.zeros(3)
        return augmented_pn_acceleration(
            r_m, v_m, r_t, v_t, ta, nav_constant, max_lateral_g
        )
    if law == "PN_GRAVITY":
        g = gravity if gravity is not None else np.zeros(3)
        return pn_gravity_acceleration(
            r_m, v_m, r_t, v_t, g, nav_constant, max_lateral_g
        )
    return pn_acceleration(r_m, v_m, r_t, v_t, nav_constant, max_lateral_g)


def _unit(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-9 else np.zeros(3)


def seeker_measurement(
    r_m: np.ndarray,
    r_t: np.ndarray,
    rng: np.random.Generator,
    angular_sigma_rad: float = 0.0,
    range_frac_sigma: float = 0.0,
) -> np.ndarray:
    """Return a *measured* target position as seen by a noisy seeker.

    The seeker observes the target along the line of sight with a boresight
    (angular) error and a range error; both are zero-mean Gaussian. The
    interceptor then steers on this estimate, while the true geometry (and hence
    the real miss distance) is unaffected. This models a homing seeker's
    measurement noise, not the target itself.
    """
    rel = r_t - r_m
    rng_true = float(np.linalg.norm(rel))
    if rng_true < 1e-6:
        return r_t.copy()
    r_hat = rel / rng_true

    if angular_sigma_rad > 0.0:
        # Two orthonormal directions perpendicular to the LOS.
        ref = (np.array([1.0, 0.0, 0.0]) if abs(r_hat[0]) < 0.9
               else np.array([0.0, 1.0, 0.0]))
        e1 = _unit(np.cross(r_hat, ref))
        e2 = np.cross(r_hat, e1)
        d = rng.normal(0.0, angular_sigma_rad, size=2)
        r_hat = _unit(r_hat + d[0] * e1 + d[1] * e2)

    rng_meas = rng_true
    if range_frac_sigma > 0.0:
        rng_meas = rng_true * (1.0 + rng.normal(0.0, range_frac_sigma))
    rng_meas = max(rng_meas, 1.0)

    return r_m + r_hat * rng_meas
