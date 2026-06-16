"""Solid propellant thermochemistry and burn-rate model.

The propellant is described by a small set of standard, publicly documented
parameters used in textbook internal-ballistics models (Sutton, *Rocket
Propulsion Elements*; Nakka's amateur-rocketry notes). Nothing here describes
how to manufacture an energetic material -- these are the bulk physical
constants a simulator needs to integrate chamber pressure and thrust.

Burn rate follows Saint-Robert's (Vieille's) law::

    r = a * Pc**n

By convention the coefficient ``a`` is supplied in mm/s when the chamber
pressure is expressed in MPa (the form tabulated in the literature). It is
converted internally to SI (m/s, Pa).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

R_UNIVERSAL = 8.31446  # J/(mol*K)


@dataclass(frozen=True)
class Propellant:
    name: str
    density: float          # grain density, kg/m^3
    a: float                # burn-rate coefficient, mm/s at 1 MPa
    n: float                # burn-rate pressure exponent, dimensionless
    gamma: float            # ratio of specific heats of combustion gas
    t_flame: float          # adiabatic flame (chamber) temperature, K
    molar_mass: float       # combustion gas mean molar mass, kg/mol
    c_star_eff: float = 0.95  # characteristic-velocity (combustion) efficiency

    def burn_rate(self, chamber_pressure_pa: float) -> float:
        """Linear burn rate [m/s] at the given chamber pressure [Pa]."""
        p_mpa = max(chamber_pressure_pa, 0.0) / 1.0e6
        return (self.a / 1000.0) * (p_mpa ** self.n)

    @property
    def r_specific(self) -> float:
        """Specific gas constant of the combustion products, J/(kg*K)."""
        return R_UNIVERSAL / self.molar_mass

    @property
    def vandenkerckhove(self) -> float:
        """Vandenkerckhove function Gamma(gamma)."""
        g = self.gamma
        return math.sqrt(g) * (2.0 / (g + 1.0)) ** ((g + 1.0) / (2.0 * (g - 1.0)))

    @property
    def c_star(self) -> float:
        """Characteristic velocity c* [m/s], including combustion efficiency."""
        ideal = math.sqrt(self.r_specific * self.t_flame) / self.vandenkerckhove
        return ideal * self.c_star_eff


# Illustrative presets. KNSB ("rocket candy") values follow Nakka's published
# amateur-rocketry characterisation; the APCP entry uses representative
# textbook figures. They are example inputs for the simulator, not a recipe.
PRESETS: dict[str, Propellant] = {
    "KNSB": Propellant(
        name="KNSB (potassium nitrate / sorbitol, 65/35)",
        density=1841.0,
        a=8.26,
        n=0.319,
        gamma=1.131,
        t_flame=1600.0,
        molar_mass=0.03998,
        c_star_eff=0.95,
    ),
    "KNDX": Propellant(
        name="KNDX (potassium nitrate / dextrose, 65/35)",
        density=1879.0,
        a=8.875,
        n=0.619,
        gamma=1.131,
        t_flame=1710.0,
        molar_mass=0.04200,
        c_star_eff=0.95,
    ),
    "APCP": Propellant(
        name="APCP (generic composite, illustrative)",
        density=1750.0,
        a=5.13,
        n=0.35,
        gamma=1.21,
        t_flame=3000.0,
        molar_mass=0.0250,
        c_star_eff=0.96,
    ),
}
