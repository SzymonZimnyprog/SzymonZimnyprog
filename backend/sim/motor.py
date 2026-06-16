"""Solid rocket motor internal-ballistics simulation.

Quasi-steady (equilibrium chamber pressure) lumped-parameter model:

* burn-rate law           r = a * Pc**n            (propellant.Propellant)
* mass generation         mdot_gen = rho_p * Ab * r
* choked nozzle mass flow mdot_noz = Pc * At / c*
* equilibrium pressure    Pc = (rho_p * Ab * a_si * c* / At) ** (1/(1-n))
* thrust                  F  = Cf * At * Pc

The thrust coefficient ``Cf`` includes the ideal expansion term plus a
pressure-thrust correction for the (altitude dependent) ambient pressure. The
nozzle exit Mach number is obtained from the area-ratio relation by bisection.

This is the standard textbook model (Sutton, *Rocket Propulsion Elements*); it
captures thrust curve shape, total impulse and specific impulse to engineering
accuracy without resolving the chamber transient.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .atmosphere import G0, atmosphere
from .grain import Grain, GrainType
from .propellant import Propellant


@dataclass(frozen=True)
class Nozzle:
    throat_diameter: float        # m
    expansion_ratio: float        # Ae / At, dimensionless
    efficiency: float = 0.97      # thrust (divergence/scallop) efficiency

    @property
    def throat_area(self) -> float:
        return math.pi * (self.throat_diameter / 2.0) ** 2

    @property
    def exit_area(self) -> float:
        return self.throat_area * self.expansion_ratio


def exit_mach(area_ratio: float, gamma: float) -> float:
    """Supersonic exit Mach number for a given area ratio Ae/At."""
    if area_ratio <= 1.0:
        return 1.0
    g = gamma

    def area_ratio_of_mach(m: float) -> float:
        return (1.0 / m) * (
            (2.0 / (g + 1.0)) * (1.0 + 0.5 * (g - 1.0) * m * m)
        ) ** ((g + 1.0) / (2.0 * (g - 1.0)))

    lo, hi = 1.0001, 50.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if area_ratio_of_mach(mid) > area_ratio:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def thrust_coefficient(
    chamber_pressure: float,
    ambient_pressure: float,
    nozzle: Nozzle,
    gamma: float,
) -> tuple[float, float]:
    """Return (Cf, exit_pressure) for the given operating point."""
    g = gamma
    eps = nozzle.expansion_ratio
    me = exit_mach(eps, g)
    pe_ratio = (1.0 + 0.5 * (g - 1.0) * me * me) ** (-g / (g - 1.0))
    pe = chamber_pressure * pe_ratio

    momentum = math.sqrt(
        (2.0 * g * g / (g - 1.0))
        * (2.0 / (g + 1.0)) ** ((g + 1.0) / (g - 1.0))
        * (1.0 - pe_ratio ** ((g - 1.0) / g))
    )

    # Summerfield separation criterion: a grossly over-expanded nozzle separates
    # internally rather than producing the full (unphysical) negative pressure
    # thrust. Once pe drops below ~0.35 * pa the effective exit pressure is held
    # at the separation value.
    pe_eff = pe
    if ambient_pressure > 0.0 and pe < 0.35 * ambient_pressure:
        pe_eff = 0.35 * ambient_pressure
    pressure_term = (pe_eff - ambient_pressure) / chamber_pressure * eps
    cf = (momentum + pressure_term) * nozzle.efficiency
    return max(cf, 0.0), pe


@dataclass
class MotorResult:
    time: list[float] = field(default_factory=list)
    thrust: list[float] = field(default_factory=list)            # N
    chamber_pressure: list[float] = field(default_factory=list)  # Pa
    mass_flow: list[float] = field(default_factory=list)         # kg/s
    burn_area: list[float] = field(default_factory=list)         # m^2
    kn: list[float] = field(default_factory=list)                # Ab/At
    propellant_mass: list[float] = field(default_factory=list)   # kg

    burn_time: float = 0.0            # s
    total_impulse: float = 0.0        # N*s
    specific_impulse: float = 0.0     # s (sea level / ambient used)
    peak_thrust: float = 0.0          # N
    average_thrust: float = 0.0       # N
    peak_pressure: float = 0.0        # Pa
    propellant_mass_initial: float = 0.0  # kg
    impulse_class: str = ""           # e.g. "H", "I"
    kn_initial: float = 0.0           # Ab/At at ignition
    kn_max: float = 0.0               # peak Ab/At
    port_to_throat: float = 0.0       # initial port area / throat area
    web_thickness: float = 0.0        # m
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "time": self.time,
            "thrust": self.thrust,
            "chamber_pressure": self.chamber_pressure,
            "mass_flow": self.mass_flow,
            "burn_area": self.burn_area,
            "kn": self.kn,
            "propellant_mass": self.propellant_mass,
            "summary": {
                "burn_time": self.burn_time,
                "total_impulse": self.total_impulse,
                "specific_impulse": self.specific_impulse,
                "peak_thrust": self.peak_thrust,
                "average_thrust": self.average_thrust,
                "peak_pressure": self.peak_pressure,
                "propellant_mass_initial": self.propellant_mass_initial,
                "impulse_class": self.impulse_class,
                "kn_initial": self.kn_initial,
                "kn_max": self.kn_max,
                "port_to_throat": self.port_to_throat,
                "web_thickness": self.web_thickness,
                "warnings": self.warnings,
            },
        }


def _impulse_class(total_impulse: float) -> str:
    """NAR/Tripoli motor letter class for a total impulse [N*s]."""
    if total_impulse <= 0.0:
        return ""
    # Class A upper bound is 2.5 N*s; each subsequent letter doubles.
    letters = "ABCDEFGHIJKLMNOPQRSTU"
    upper = 2.5
    for letter in letters:
        if total_impulse <= upper:
            return letter
        upper *= 2.0
    return ">U"


def simulate_motor(
    propellant: Propellant,
    grain: Grain,
    nozzle: Nozzle,
    altitude: float = 0.0,
    dt: float = 0.001,
    max_time: float = 60.0,
) -> MotorResult:
    """March the grain regression forward and build the thrust curve."""
    ambient = atmosphere(altitude).pressure
    at = nozzle.throat_area
    c_star = propellant.c_star
    n = propellant.n
    rho = grain.density
    # SI burn-rate coefficient: r[m/s] = a_si * Pc[Pa]**n
    a_si = (propellant.a / 1000.0) / (1.0e6 ** n)

    res = MotorResult()
    res.propellant_mass_initial = grain.propellant_mass(0.0)

    web = 0.0
    t = 0.0
    impulse = 0.0
    web_max = grain.web_thickness

    while t <= max_time:
        ab = grain.burn_area(web)
        if ab <= 0.0 or web >= web_max:
            break

        # Equilibrium chamber pressure.
        pc = (rho * ab * a_si * c_star / at) ** (1.0 / (1.0 - n))
        r = a_si * (pc ** n)
        mdot = rho * ab * r
        cf, _pe = thrust_coefficient(pc, ambient, nozzle, propellant.gamma)
        thrust = cf * at * pc

        res.time.append(t)
        res.thrust.append(thrust)
        res.chamber_pressure.append(pc)
        res.mass_flow.append(mdot)
        res.burn_area.append(ab)
        res.kn.append(ab / at)
        res.propellant_mass.append(rho * grain.volume(web))

        impulse += thrust * dt
        web += r * dt
        t += dt

    # Append a clean tail-off sample at burnout.
    if res.time:
        res.time.append(res.time[-1] + dt)
        for series in (
            res.thrust, res.chamber_pressure, res.mass_flow,
            res.burn_area, res.kn,
        ):
            series.append(0.0)
        res.propellant_mass.append(max(0.0, rho * grain.volume(web)))

    res.burn_time = res.time[-1] if res.time else 0.0
    res.total_impulse = impulse
    res.peak_thrust = max(res.thrust) if res.thrust else 0.0
    res.peak_pressure = max(res.chamber_pressure) if res.chamber_pressure else 0.0
    burned_mass = res.propellant_mass_initial - (
        res.propellant_mass[-1] if res.propellant_mass else 0.0
    )
    if burned_mass > 1e-9:
        res.specific_impulse = impulse / (burned_mass * G0)
    if res.burn_time > 0.0:
        res.average_thrust = impulse / res.burn_time
    res.impulse_class = _impulse_class(impulse)

    # Design diagnostics.
    res.web_thickness = grain.web_thickness
    res.kn_initial = grain.burn_area(0.0) / at
    res.kn_max = max(res.kn) if res.kn else 0.0
    res.port_to_throat = grain.port_area(0.0) / at
    res.warnings = _design_warnings(res, grain)
    return res


def _design_warnings(res: MotorResult, grain: Grain) -> list[str]:
    warnings: list[str] = []
    if res.total_impulse <= 0.0:
        warnings.append(
            "Motor does not pressurise — raise Kn (smaller throat or more "
            "burning area)."
        )
    if res.peak_pressure > 10.0e6:
        warnings.append(
            f"High chamber pressure ({res.peak_pressure / 1e6:.1f} MPa) — "
            "verify casing strength."
        )
    cored = grain.grain_type in (GrainType.BATES, GrainType.TUBULAR)
    if cored and grain.core_radius > 0 and 0.0 < res.port_to_throat < 2.0:
        warnings.append(
            f"Low port/throat ratio ({res.port_to_throat:.1f} < 2) — erosive "
            "burning risk; widen the core."
        )
    if grain.core_radius >= grain.outer_radius and cored:
        warnings.append("Core diameter >= outer diameter — invalid grain.")
    return warnings


@dataclass(frozen=True)
class ThrustCurve:
    """Sampled thrust vs time used to drive the flight dynamics."""

    time: list[float]
    thrust: list[float]
    mass_flow: list[float]
    propellant_mass_initial: float

    def thrust_at(self, t: float) -> float:
        return _interp(self.time, self.thrust, t)

    def mass_flow_at(self, t: float) -> float:
        return _interp(self.time, self.mass_flow, t)

    @property
    def burn_time(self) -> float:
        return self.time[-1] if self.time else 0.0


def thrust_curve_from_result(res: MotorResult) -> ThrustCurve:
    return ThrustCurve(
        time=list(res.time),
        thrust=list(res.thrust),
        mass_flow=list(res.mass_flow),
        propellant_mass_initial=res.propellant_mass_initial,
    )


def _interp(xs: list[float], ys: list[float], x: float) -> float:
    if not xs:
        return 0.0
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return 0.0
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    span = xs[hi] - xs[lo]
    if span <= 0.0:
        return ys[lo]
    frac = (x - xs[lo]) / span
    return ys[lo] + frac * (ys[hi] - ys[lo])
