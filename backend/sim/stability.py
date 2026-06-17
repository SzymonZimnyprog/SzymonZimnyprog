"""Aerodynamic stability: centre of pressure, centre of gravity, static margin.

Implements the classic **Barrowman** method (the standard public model used
throughout amateur and educational rocketry) for the subsonic centre of
pressure of a nose + cylindrical body + trapezoidal fin set, plus a simple
longitudinal centre-of-gravity estimate from the loaded/empty masses. The
static margin (the CP-to-CG distance in body calibers) is the headline
stability metric.

All positions are measured from the nose tip, in metres. This is a geometry/
aerodynamics analysis -- no control or weapon content.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# Nose-cone CP location as a fraction of nose length (Barrowman, subsonic).
_NOSE_CP_FACTOR = {
    "ogive": 0.466,
    "cone": 0.666,
    "parabolic": 0.500,
    "haack": 0.437,
}
_NOSE_CN = 2.0  # normal-force-coefficient slope of any nose (per radian)


@dataclass
class StabilityResult:
    x_cp: float = 0.0               # centre of pressure from nose tip, m
    x_cg_loaded: float = 0.0        # CG with full propellant, m
    x_cg_empty: float = 0.0         # CG at burnout, m
    static_margin_loaded: float = 0.0   # calibers
    static_margin_empty: float = 0.0    # calibers
    cn_alpha: float = 0.0           # total normal-force slope, /rad
    cn_nose: float = 0.0
    cn_fins: float = 0.0
    x_cp_nose: float = 0.0
    x_cp_fins: float = 0.0
    body_length_total: float = 0.0
    diameter: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "x_cp": self.x_cp,
            "x_cg_loaded": self.x_cg_loaded,
            "x_cg_empty": self.x_cg_empty,
            "static_margin_loaded": self.static_margin_loaded,
            "static_margin_empty": self.static_margin_empty,
            "cn_alpha": self.cn_alpha,
            "cn_nose": self.cn_nose,
            "cn_fins": self.cn_fins,
            "x_cp_nose": self.x_cp_nose,
            "x_cp_fins": self.x_cp_fins,
            "body_length_total": self.body_length_total,
            "diameter": self.diameter,
            "warnings": self.warnings,
        }


def barrowman_stability(
    *,
    diameter: float,
    nose_length: float,
    body_length: float,
    nose_type: str = "ogive",
    fin_count: int = 4,
    fin_root_chord: float = 0.30,
    fin_tip_chord: float = 0.15,
    fin_span: float = 0.12,
    fin_sweep: float = 0.10,
    fin_root_position: float | None = None,
    dry_mass: float = 40.0,
    dry_cg: float | None = None,
    propellant_mass: float = 0.0,
    propellant_cg: float | None = None,
) -> StabilityResult:
    """Barrowman CP + simple CG -> static margin (loaded and at burnout).

    ``fin_root_position`` is the distance from the nose tip to the fin-root
    leading edge (defaults to fins at the tail). ``dry_cg`` / ``propellant_cg``
    are measured from the nose tip; sensible defaults place the dry CG near
    mid-length and the propellant CG aft.
    """
    res = StabilityResult()
    d = diameter
    R = d / 2.0
    total_len = nose_length + body_length
    res.diameter = d
    res.body_length_total = total_len

    # ---- Centre of pressure (Barrowman) ---------------------------------- #
    factor = _NOSE_CP_FACTOR.get(nose_type.lower(), 0.466)
    cn_nose = _NOSE_CN
    x_cp_nose = factor * nose_length

    s = fin_span
    cr = fin_root_chord
    ct = fin_tip_chord
    cn_fins = 0.0
    x_cp_fins = 0.0
    if fin_count > 0 and s > 0 and (cr + ct) > 0:
        # mid-chord sweep length
        m = fin_sweep + 0.5 * (ct - cr)
        l_f = math.sqrt(s * s + m * m)
        kfb = 1.0 + R / (s + R)  # body-fin interference
        cn_fins = kfb * (
            (4.0 * fin_count * (s / d) ** 2)
            / (1.0 + math.sqrt(1.0 + (2.0 * l_f / (cr + ct)) ** 2))
        )
        if fin_root_position is None:
            fin_root_position = total_len - cr  # fins at the tail
        x_f = (fin_sweep / 3.0) * ((cr + 2.0 * ct) / (cr + ct)) + (1.0 / 6.0) * (
            (cr + ct) - (cr * ct) / (cr + ct)
        )
        x_cp_fins = fin_root_position + x_f

    cn_total = cn_nose + cn_fins
    x_cp = (cn_nose * x_cp_nose + cn_fins * x_cp_fins) / cn_total
    res.cn_nose = cn_nose
    res.cn_fins = cn_fins
    res.cn_alpha = cn_total
    res.x_cp_nose = x_cp_nose
    res.x_cp_fins = x_cp_fins
    res.x_cp = x_cp

    # ---- Centre of gravity ----------------------------------------------- #
    if dry_cg is None:
        dry_cg = 0.55 * total_len
    if propellant_cg is None:
        propellant_cg = 0.85 * total_len  # propellant sits in the aft motor
    res.x_cg_empty = dry_cg
    total_mass = dry_mass + propellant_mass
    res.x_cg_loaded = (
        (dry_mass * dry_cg + propellant_mass * propellant_cg) / total_mass
        if total_mass > 0 else dry_cg
    )

    # ---- Static margin (calibers) ---------------------------------------- #
    res.static_margin_loaded = (x_cp - res.x_cg_loaded) / d
    res.static_margin_empty = (x_cp - res.x_cg_empty) / d

    # ---- Warnings -------------------------------------------------------- #
    worst = min(res.static_margin_loaded, res.static_margin_empty)
    best = max(res.static_margin_loaded, res.static_margin_empty)
    if worst < 1.0:
        res.warnings.append(
            f"Marginal/unstable: static margin drops to {worst:.2f} cal "
            "(aim for 1–2 cal). Move CG forward or grow the fins."
        )
    if best > 2.5:
        res.warnings.append(
            f"Over-stable: static margin reaches {best:.2f} cal — the rocket "
            "will weathercock strongly into wind."
        )
    if cn_fins <= 0.0:
        res.warnings.append("No fin contribution — the body alone is unstable.")
    return res
