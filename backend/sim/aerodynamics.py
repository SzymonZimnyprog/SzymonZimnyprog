"""Parametric aerodynamic drag model for a slender missile airframe.

A compact Mach-dependent drag-coefficient curve is used: low subsonic value,
a transonic rise peaking near M = 1.1, then a gradual supersonic decay. The
curve is scaled by a user ``cd0`` multiplier so the whole model stays
parametric. Reference area is the body cross-section.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def drag_coefficient(mach: float, cd0: float) -> float:
    """Zero-lift drag coefficient as a function of Mach number.

    ``cd0`` is the subsonic baseline; the transonic/supersonic shape is applied
    as a multiplicative factor on top of it.
    """
    m = abs(mach)
    if m < 0.8:
        shape = 1.0
    elif m < 1.2:
        # transonic drag rise, smooth ramp peaking ~ 2.6x baseline
        shape = 1.0 + 1.6 * math.sin((m - 0.8) / 0.4 * (math.pi / 2.0))
    else:
        # supersonic decay toward ~1.4x baseline
        shape = 1.4 + 1.2 * math.exp(-(m - 1.2) / 1.5)
    return cd0 * shape


@dataclass(frozen=True)
class Airframe:
    diameter: float          # body reference diameter, m
    cd0: float = 0.45        # subsonic baseline drag coefficient
    dry_mass: float = 5.0    # mass without propellant, kg

    @property
    def reference_area(self) -> float:
        return math.pi * (self.diameter / 2.0) ** 2

    def drag(self, density: float, speed: float, mach: float) -> float:
        """Drag force magnitude [N]."""
        cd = drag_coefficient(mach, self.cd0)
        return 0.5 * density * speed * speed * cd * self.reference_area
