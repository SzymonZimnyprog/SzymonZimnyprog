import type {
  EngagementRequest,
  MissileRequest,
  MotorRequest,
} from "./api";

export const KNSB: MotorRequest["propellant"] = {
  name: "KNSB (potassium nitrate / sorbitol)",
  density: 1841,
  a: 8.26,
  n: 0.319,
  gamma: 1.131,
  t_flame: 1600,
  molar_mass: 0.03998,
  c_star_eff: 0.95,
};

export const APCP: MotorRequest["propellant"] = {
  name: "APCP (generic composite, illustrative)",
  density: 1750,
  a: 5.13,
  n: 0.35,
  gamma: 1.21,
  t_flame: 3000,
  molar_mass: 0.025,
  c_star_eff: 0.96,
};

export const defaultMotor: MotorRequest = {
  propellant: { ...KNSB },
  grain: {
    grain_type: "BATES",
    outer_diameter: 0.075,
    core_diameter: 0.025,
    segment_length: 0.12,
    segments: 4,
    inhibited_ends: false,
  },
  nozzle: { throat_diameter: 0.018, expansion_ratio: 6, efficiency: 0.97 },
  altitude: 0,
  dt: 0.001,
  max_time: 60,
};

export const defaultMissile: MissileRequest = {
  motor: { ...defaultMotor },
  airframe: { diameter: 0.18, cd0: 0.45, dry_mass: 45 },
  launch_speed: 30,
  elevation_deg: 80,
  azimuth_deg: 0,
  dt: 0.02,
  max_time: 300,
};

export const defaultStack = [
  {
    motor: {
      propellant: { ...APCP },
      grain: {
        grain_type: "TUBULAR" as const,
        outer_diameter: 0.14,
        core_diameter: 0.05,
        segment_length: 0.3,
        segments: 3,
        inhibited_ends: false,
      },
      nozzle: { throat_diameter: 0.03, expansion_ratio: 8, efficiency: 0.97 },
      altitude: 0,
      dt: 0.001,
      max_time: 60,
    },
    ignition_delay: 0,
  },
  {
    motor: {
      propellant: { ...APCP },
      grain: {
        grain_type: "BATES" as const,
        outer_diameter: 0.12,
        core_diameter: 0.06,
        segment_length: 0.4,
        segments: 2,
        inhibited_ends: false,
      },
      nozzle: { throat_diameter: 0.018, expansion_ratio: 10, efficiency: 0.97 },
      altitude: 0,
      dt: 0.001,
      max_time: 60,
    },
    ignition_delay: 1.5,
  },
];

export const defaultEngagement: EngagementRequest = {
  interceptor: {
    motor: {
      propellant: { ...APCP },
      grain: {
        grain_type: "BATES",
        outer_diameter: 0.14,
        core_diameter: 0.05,
        segment_length: 0.35,
        segments: 5,
        inhibited_ends: false,
      },
      nozzle: { throat_diameter: 0.03, expansion_ratio: 8, efficiency: 0.97 },
      altitude: 0,
      dt: 0.001,
      max_time: 60,
    },
    airframe: { diameter: 0.16, cd0: 0.3, dry_mass: 40 },
    launch_position: [0, 0, 0],
    launch_speed: 40,
    elevation_deg: 45,
    azimuth_deg: 90,
    nav_constant: 4,
    max_lateral_g: 60,
    seeker_delay: 0.5,
    seeker_range: 60000,
    seeker_angular_noise: 0,
    seeker_range_noise: 0,
    seeker_update_rate: 0,
  },
  target: {
    position: [15000, 0, 8000],
    velocity: [-300, 0, -30],
    diameter: 0.4,
    cd0: 0.3,
    mass: 300,
    maneuver_accel: [0, 0, 0],
  },
  dt: 0.01,
  max_time: 120,
  lethal_radius: 5,
};
