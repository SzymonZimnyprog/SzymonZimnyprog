"""Atmospheric wind field.

Wind enters the dynamics through the *air-relative* velocity: aerodynamic drag
acts on ``v_air = v_ground - v_wind`` rather than the ground velocity, so a
crosswind drags the vehicle downwind and a head/tail wind changes the drag it
feels. Only horizontal wind is modelled (no vertical gusts).

The wind is given as a steady speed blowing *from* a compass bearing (the
meteorological convention: a "270°" / westerly wind blows toward the east),
with an optional power-law boundary-layer profile that strengthens it with
altitude. A zero-speed field is a true no-op, so wind-free runs are unchanged.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

_ZERO = np.zeros(3)


@dataclass(frozen=True)
class WindField:
    speed: float = 0.0           # m/s at the reference altitude
    from_deg: float = 270.0      # compass bearing the wind blows FROM (deg)
    reference_alt: float = 10.0  # m, where ``speed`` is defined
    shear: float = 0.0           # power-law exponent (0 = uniform with altitude)

    def at(self, altitude: float) -> np.ndarray:
        """Wind velocity vector (ENU, m/s) at a geometric altitude."""
        if self.speed <= 0.0:
            return _ZERO
        spd = self.speed
        if self.shear > 0.0:
            ref = max(self.reference_alt, 1e-3)
            factor = (max(altitude, 1.0) / ref) ** self.shear
            spd *= min(factor, 10.0)  # clamp the runaway tail at high altitude
        # "from" bearing -> velocity points the opposite way (toward from+180).
        b = math.radians(self.from_deg)
        return np.array([-spd * math.sin(b), -spd * math.cos(b), 0.0])

    def is_active(self) -> bool:
        return self.speed > 0.0
