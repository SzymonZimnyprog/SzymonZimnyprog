"""U.S. Standard Atmosphere 1976 (geopotential layers up to 86 km).

Provides temperature, pressure, density and speed of sound as a function of
geometric altitude. Used by the flight-dynamics integrator for drag and by the
motor model for ambient pressure (pressure thrust term).

All quantities are SI: metres, kelvin, pascal, kg/m^3, m/s.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Physical constants
G0 = 9.80665          # standard gravity, m/s^2
R_AIR = 287.05287     # specific gas constant for air, J/(kg*K)
GAMMA_AIR = 1.4       # ratio of specific heats for air
R_EARTH = 6356766.0   # nominal earth radius for geopotential conversion, m

# Layer base data: (base geopotential altitude [m], base temperature [K],
# lapse rate [K/m], base pressure [Pa]).
_LAYERS = [
    (0.0, 288.15, -0.0065, 101325.0),
    (11000.0, 216.65, 0.0, 22632.06),
    (20000.0, 216.65, 0.001, 5474.889),
    (32000.0, 228.65, 0.0028, 868.0187),
    (47000.0, 270.65, 0.0, 110.9063),
    (51000.0, 270.65, -0.0028, 66.93887),
    (71000.0, 214.65, -0.002, 3.956420),
]
_TOP = 84852.0  # top geopotential altitude of the modelled region, m


@dataclass(frozen=True)
class AtmoState:
    altitude: float        # geometric altitude, m
    temperature: float     # K
    pressure: float        # Pa
    density: float         # kg/m^3
    speed_of_sound: float  # m/s


def _geopotential(z_geometric: float) -> float:
    """Convert geometric altitude to geopotential altitude."""
    return R_EARTH * z_geometric / (R_EARTH + z_geometric)


def atmosphere(z_geometric: float) -> AtmoState:
    """Return the atmospheric state at a geometric altitude.

    Below sea level the sea-level layer is extrapolated; above the modelled top
    the values are clamped to the top of the 71 km layer (thin enough that the
    difference is negligible for flight dynamics).
    """
    h = _geopotential(max(z_geometric, 0.0))
    h = min(h, _TOP)

    base_h, base_t, lapse, base_p = _LAYERS[0]
    for layer in _LAYERS:
        if h >= layer[0]:
            base_h, base_t, lapse, base_p = layer
        else:
            break

    dh = h - base_h
    temp = base_t + lapse * dh

    if abs(lapse) < 1e-12:
        pressure = base_p * math.exp(-G0 * dh / (R_AIR * base_t))
    else:
        pressure = base_p * (temp / base_t) ** (-G0 / (lapse * R_AIR))

    density = pressure / (R_AIR * temp)
    sos = math.sqrt(GAMMA_AIR * R_AIR * temp)
    return AtmoState(z_geometric, temp, pressure, density, sos)


def density(z_geometric: float) -> float:
    return atmosphere(z_geometric).density


def pressure(z_geometric: float) -> float:
    return atmosphere(z_geometric).pressure


def speed_of_sound(z_geometric: float) -> float:
    return atmosphere(z_geometric).speed_of_sound
