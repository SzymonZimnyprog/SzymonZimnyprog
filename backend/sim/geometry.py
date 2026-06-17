"""Nozzle / grain cross-section geometry derived from the sizing parameters.

Turns the motor's numeric design (throat diameter, expansion ratio, chamber and
grain dimensions) into an axisymmetric profile that can be drawn as an
engineering cross-section -- a geometric mirror of the sizing calculation. Pure
geometry; no simulation state.
"""

from __future__ import annotations

import math


def nozzle_profile(
    throat_diameter: float,
    expansion_ratio: float,
    chamber_diameter: float,
    grain_length: float,
    core_diameter: float = 0.0,
    *,
    converging_half_angle_deg: float = 45.0,
    diverging_half_angle_deg: float = 15.0,
) -> dict:
    """Return the chamber + converging-diverging nozzle wall contour and key radii.

    The contour is the gas-side boundary, measured from the head end (x=0):
    a cylindrical chamber of length ``grain_length`` at the chamber radius, a
    converging cone to the throat, then a diverging cone to the exit. The exit
    radius follows the area ratio: ``Re = Rt * sqrt(expansion_ratio)``.
    """
    rt = throat_diameter / 2.0
    re = rt * math.sqrt(max(expansion_ratio, 1.0))
    rc = max(chamber_diameter / 2.0, rt)
    rcore = max(core_diameter / 2.0, 0.0)

    conv = math.radians(converging_half_angle_deg)
    div = math.radians(diverging_half_angle_deg)
    lc = (rc - rt) / math.tan(conv) if rc > rt else 0.0
    ld = (re - rt) / math.tan(div) if re > rt else 0.0
    lch = max(grain_length, 1e-6)

    x_chamber_end = lch
    x_throat = lch + lc
    x_exit = x_throat + ld

    profile_x = [0.0, x_chamber_end, x_throat, x_exit]
    profile_r = [rc, rc, rt, re]

    return {
        "throat_radius": rt,
        "exit_radius": re,
        "chamber_radius": rc,
        "core_radius": rcore,
        "throat_diameter": 2.0 * rt,
        "exit_diameter": 2.0 * re,
        "expansion_ratio": expansion_ratio,
        "converging_length": lc,
        "diverging_length": ld,
        "chamber_length": lch,
        "total_length": x_exit,
        "x_chamber_end": x_chamber_end,
        "x_throat": x_throat,
        "x_exit": x_exit,
        "profile_x": profile_x,
        "profile_r": profile_r,
    }
