"""Pydantic request/response schemas and builders.

These bridge the JSON API and the dataclass-based simulation core. Every
physical input is exposed as a validated, defaulted field so the whole system
is parametric from the web app, CAD exporter and Simulink driver.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, Field

from .aerodynamics import Airframe
from .dynamics import Vehicle
from .engagement import Interceptor, Target
from .grain import Grain, GrainType
from .motor import Nozzle
from .propellant import PRESETS, Propellant
from .wind import WindField


# --------------------------------------------------------------------------- #
# Propellant
# --------------------------------------------------------------------------- #
class PropellantModel(BaseModel):
    name: str = "Custom propellant"
    density: float = Field(1841.0, gt=0, description="grain density, kg/m^3")
    a: float = Field(8.26, gt=0, description="burn-rate coeff, mm/s at 1 MPa")
    n: float = Field(0.319, ge=0, lt=1, description="burn-rate pressure exponent")
    gamma: float = Field(1.131, gt=1, le=1.7, description="ratio of specific heats")
    t_flame: float = Field(1600.0, gt=0, description="flame temperature, K")
    molar_mass: float = Field(0.03998, gt=0, description="gas molar mass, kg/mol")
    c_star_eff: float = Field(0.95, gt=0, le=1)

    def to_propellant(self) -> Propellant:
        return Propellant(
            name=self.name, density=self.density, a=self.a, n=self.n,
            gamma=self.gamma, t_flame=self.t_flame, molar_mass=self.molar_mass,
            c_star_eff=self.c_star_eff,
        )

    @classmethod
    def from_preset(cls, key: str) -> "PropellantModel":
        p = PRESETS[key]
        return cls(
            name=p.name, density=p.density, a=p.a, n=p.n, gamma=p.gamma,
            t_flame=p.t_flame, molar_mass=p.molar_mass, c_star_eff=p.c_star_eff,
        )


# --------------------------------------------------------------------------- #
# Grain + nozzle + motor
# --------------------------------------------------------------------------- #
class GrainModel(BaseModel):
    grain_type: GrainType = GrainType.BATES
    outer_diameter: float = Field(0.075, gt=0, description="m")
    core_diameter: float = Field(0.025, ge=0, description="m")
    segment_length: float = Field(0.12, gt=0, description="m")
    segments: int = Field(4, ge=1, le=20)
    inhibited_ends: bool = False

    def to_grain(self, density: float) -> Grain:
        return Grain(
            grain_type=self.grain_type,
            outer_diameter=self.outer_diameter,
            core_diameter=self.core_diameter,
            segment_length=self.segment_length,
            segments=self.segments,
            inhibited_ends=self.inhibited_ends,
            density=density,
        )


class NozzleModel(BaseModel):
    throat_diameter: float = Field(0.018, gt=0, description="m")
    expansion_ratio: float = Field(6.0, ge=1, description="Ae/At")
    efficiency: float = Field(0.97, gt=0, le=1)

    def to_nozzle(self) -> Nozzle:
        return Nozzle(
            throat_diameter=self.throat_diameter,
            expansion_ratio=self.expansion_ratio,
            efficiency=self.efficiency,
        )


class MotorRequest(BaseModel):
    propellant: PropellantModel = PropellantModel()
    grain: GrainModel = GrainModel()
    nozzle: NozzleModel = NozzleModel()
    altitude: float = Field(0.0, description="ambient altitude for pressure thrust, m")
    dt: float = Field(0.001, gt=0, le=0.05)
    max_time: float = Field(60.0, gt=0, le=600)


# --------------------------------------------------------------------------- #
# Airframe
# --------------------------------------------------------------------------- #
class AirframeModel(BaseModel):
    diameter: float = Field(0.18, gt=0, description="body reference diameter, m")
    cd0: float = Field(0.45, gt=0, description="subsonic drag coefficient")
    dry_mass: float = Field(45.0, gt=0, description="mass without propellant, kg")

    def to_airframe(self) -> Airframe:
        return Airframe(diameter=self.diameter, cd0=self.cd0, dry_mass=self.dry_mass)


# --------------------------------------------------------------------------- #
# Standalone missile trajectory
# --------------------------------------------------------------------------- #
class WindModel(BaseModel):
    speed: float = Field(0.0, ge=0, le=120, description="wind speed, m/s")
    from_deg: float = Field(
        270.0, ge=0, le=360, description="compass bearing wind blows FROM"
    )
    reference_alt: float = Field(10.0, gt=0, description="altitude of ``speed``, m")
    shear: float = Field(
        0.0, ge=0, le=1, description="power-law profile exponent (0 = uniform)"
    )

    def to_wind(self) -> WindField:
        return WindField(
            speed=self.speed, from_deg=self.from_deg,
            reference_alt=self.reference_alt, shear=self.shear,
        )


class MissileRequest(BaseModel):
    motor: MotorRequest = MotorRequest()
    airframe: AirframeModel = AirframeModel()
    launch_speed: float = Field(30.0, ge=0, description="rail exit speed, m/s")
    elevation_deg: float = Field(80.0, ge=0, le=90, description="launch elevation")
    azimuth_deg: float = Field(0.0, ge=-180, le=360, description="launch azimuth")
    dt: float = Field(0.02, gt=0, le=0.5)
    max_time: float = Field(300.0, gt=0, le=1200)
    wind: WindModel = WindModel()


def launch_velocity(
    speed: float, elevation_deg: float, azimuth_deg: float
) -> np.ndarray:
    el = np.radians(elevation_deg)
    az = np.radians(azimuth_deg)
    horizontal = speed * np.cos(el)
    return np.array([
        horizontal * np.sin(az),
        horizontal * np.cos(az),
        speed * np.sin(el),
    ])


def build_vehicle_and_curve(motor_req: MotorRequest, airframe_model: AirframeModel):
    """Run the motor sim and assemble a guided Vehicle + thrust curve."""
    from .motor import simulate_motor, thrust_curve_from_result

    prop = motor_req.propellant.to_propellant()
    grain = motor_req.grain.to_grain(prop.density)
    nozzle = motor_req.nozzle.to_nozzle()
    motor_res = simulate_motor(prop, grain, nozzle, motor_req.altitude,
                               motor_req.dt, motor_req.max_time)
    curve = thrust_curve_from_result(motor_res)
    vehicle = Vehicle(airframe=airframe_model.to_airframe(), thrust_curve=curve)
    return vehicle, curve, motor_res


# --------------------------------------------------------------------------- #
# Engagement
# --------------------------------------------------------------------------- #
class TargetModel(BaseModel):
    position: list[float] = Field([15000.0, 0.0, 8000.0], description="ENU, m")
    velocity: list[float] = Field([-300.0, 0.0, -30.0], description="m/s")
    diameter: float = Field(0.4, gt=0)
    cd0: float = Field(0.3, gt=0)
    mass: float = Field(300.0, gt=0)
    maneuver_accel: list[float] = Field([0.0, 0.0, 0.0], description="m/s^2")

    def to_target(self) -> Target:
        return Target(
            position=np.array(self.position, dtype=float),
            velocity=np.array(self.velocity, dtype=float),
            airframe=Airframe(diameter=self.diameter, cd0=self.cd0, dry_mass=self.mass),
            mass=self.mass,
            maneuver_accel=np.array(self.maneuver_accel, dtype=float),
        )


def _default_interceptor_motor() -> MotorRequest:
    """A composite-propellant boost motor sized for the default engagement."""
    return MotorRequest(
        propellant=PropellantModel.from_preset("APCP"),
        grain=GrainModel(
            grain_type=GrainType.BATES,
            outer_diameter=0.14,
            core_diameter=0.05,
            segment_length=0.35,
            segments=5,
        ),
        nozzle=NozzleModel(throat_diameter=0.03, expansion_ratio=8.0),
    )


def _default_interceptor_airframe() -> AirframeModel:
    return AirframeModel(diameter=0.16, cd0=0.3, dry_mass=40.0)


class InterceptorModel(BaseModel):
    motor: MotorRequest = Field(default_factory=_default_interceptor_motor)
    airframe: AirframeModel = Field(default_factory=_default_interceptor_airframe)
    launch_position: list[float] = Field([0.0, 0.0, 0.0], description="ENU, m")
    launch_speed: float = Field(40.0, ge=0)
    elevation_deg: float = Field(45.0, ge=0, le=90)
    azimuth_deg: float = Field(90.0, ge=-180, le=360)
    nav_constant: float = Field(4.0, ge=2, le=6)
    max_lateral_g: float = Field(60.0, gt=0, le=100)
    guidance_law: str = Field("PN", description="PN | APN | PN_GRAVITY")
    seeker_delay: float = Field(0.5, ge=0)
    seeker_range: float = Field(60000.0, gt=0)
    seeker_angular_noise: float = Field(
        0.0, ge=0, le=100, description="seeker boresight 1-sigma, mrad"
    )
    seeker_range_noise: float = Field(
        0.0, ge=0, le=0.5, description="range 1-sigma, fraction of range"
    )
    seeker_update_rate: float = Field(
        0.0, ge=0, le=1000, description="seeker measurement rate, Hz (0 = continuous)"
    )
    seeker_track_alpha: float = Field(
        0.0, ge=0, le=1, description="alpha-beta tracker gain (0 = off)"
    )

    def build(self) -> tuple[Interceptor, object]:
        vehicle, curve, motor_res = build_vehicle_and_curve(self.motor, self.airframe)
        vel = launch_velocity(self.launch_speed, self.elevation_deg, self.azimuth_deg)
        interceptor = Interceptor(
            vehicle=vehicle,
            launch_position=np.array(self.launch_position, dtype=float),
            launch_velocity=vel,
            propellant_mass=curve.propellant_mass_initial,
            nav_constant=self.nav_constant,
            max_lateral_g=self.max_lateral_g,
            guidance_law=self.guidance_law,
            seeker_delay=self.seeker_delay,
            seeker_range=self.seeker_range,
            seeker_angular_noise=self.seeker_angular_noise / 1000.0,  # mrad -> rad
            seeker_range_noise=self.seeker_range_noise,
            seeker_update_rate=self.seeker_update_rate,
            seeker_track_alpha=self.seeker_track_alpha,
        )
        return interceptor, motor_res


class EngagementRequest(BaseModel):
    interceptor: InterceptorModel = InterceptorModel()
    target: TargetModel = TargetModel()
    dt: float = Field(0.01, gt=0, le=0.1)
    max_time: float = Field(120.0, gt=0, le=600)
    lethal_radius: float = Field(5.0, gt=0)
    wind: WindModel = WindModel()
    seed: int | None = Field(
        None, description="RNG seed for seeker noise (reproducible runs)"
    )
