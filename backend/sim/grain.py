"""Parametric solid-propellant grain geometry and surface regression.

Two classic grain types are supported:

* ``BATES`` -- one or more cylindrical segments with a central circular bore.
  The bore burns radially outward and the (un-inhibited) end faces burn
  axially. This is the workhorse geometry for amateur and many research motors.
* ``END_BURNER`` -- a solid cylinder burning on one face only (near-constant
  thrust, low Kn).

Each grain exposes ``burn_area(web)`` and ``volume(web)`` as a function of the
regressed *web distance* ``web`` (metres of propellant consumed normal to the
burning surface). The motor model marches ``web`` forward in time.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class GrainType(str, Enum):
    BATES = "BATES"
    END_BURNER = "END_BURNER"


@dataclass(frozen=True)
class Grain:
    grain_type: GrainType
    outer_diameter: float       # m
    core_diameter: float        # m (ignored for END_BURNER)
    segment_length: float       # m (single segment)
    segments: int = 1
    inhibited_ends: bool = False  # if True, end faces do not burn (BATES)
    density: float = 1841.0       # kg/m^3 (for mass bookkeeping)

    # ---- derived constants -------------------------------------------------
    @property
    def outer_radius(self) -> float:
        return self.outer_diameter / 2.0

    @property
    def core_radius(self) -> float:
        return self.core_diameter / 2.0

    @property
    def web_thickness(self) -> float:
        """Maximum web distance before burnout."""
        if self.grain_type == GrainType.END_BURNER:
            return self.segment_length
        radial = self.outer_radius - self.core_radius
        if self.inhibited_ends:
            return radial
        # ends also limit life: each segment burns from both faces.
        axial = self.segment_length / 2.0
        return min(radial, axial)

    # ---- geometry as a function of regression ------------------------------
    def burn_area(self, web: float) -> float:
        """Total instantaneous burning surface area [m^2] at web distance."""
        w = max(0.0, min(web, self.web_thickness))
        if self.grain_type == GrainType.END_BURNER:
            return math.pi * self.outer_radius ** 2

        r_core = self.core_radius + w
        r_out = self.outer_radius
        if r_core >= r_out:
            return 0.0

        if self.inhibited_ends:
            length = self.segment_length
            core_lateral = 2.0 * math.pi * r_core * length
            return self.segments * core_lateral

        length = self.segment_length - 2.0 * w
        if length <= 0.0:
            return 0.0
        core_lateral = 2.0 * math.pi * r_core * length
        end_faces = 2.0 * math.pi * (r_out ** 2 - r_core ** 2)
        return self.segments * (core_lateral + end_faces)

    def port_area(self, web: float) -> float:
        """Cross-sectional flow (port) area through the bore [m^2]."""
        if self.grain_type == GrainType.END_BURNER:
            return math.pi * self.outer_radius ** 2
        w = max(0.0, min(web, self.web_thickness))
        r_core = min(self.core_radius + w, self.outer_radius)
        return math.pi * r_core ** 2

    def volume(self, web: float) -> float:
        """Remaining propellant volume [m^3] at web distance."""
        w = max(0.0, min(web, self.web_thickness))
        if self.grain_type == GrainType.END_BURNER:
            length = max(self.segment_length - w, 0.0)
            return math.pi * self.outer_radius ** 2 * length

        r_core = min(self.core_radius + w, self.outer_radius)
        if self.inhibited_ends:
            length = self.segment_length
        else:
            length = max(self.segment_length - 2.0 * w, 0.0)
        ring = math.pi * (self.outer_radius ** 2 - r_core ** 2)
        return self.segments * ring * length

    def initial_volume(self) -> float:
        return self.volume(0.0)

    def propellant_mass(self, web: float = 0.0) -> float:
        return self.density * self.volume(web)
