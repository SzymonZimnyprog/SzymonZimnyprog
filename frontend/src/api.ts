const BASE = "/api";

// --------------------------------------------------------------------------- //
// Items (original demo resource)
// --------------------------------------------------------------------------- //
export interface Item {
  id: number;
  name: string;
  description: string;
}

export async function fetchItems(): Promise<Item[]> {
  const res = await fetch(`${BASE}/items/`);
  if (!res.ok) throw new Error("Failed to fetch items");
  return res.json();
}

export async function createItem(
  name: string,
  description: string
): Promise<Item> {
  const res = await fetch(`${BASE}/items/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });
  if (!res.ok) throw new Error("Failed to create item");
  return res.json();
}

export async function deleteItem(id: number): Promise<void> {
  const res = await fetch(`${BASE}/items/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete item");
}

// --------------------------------------------------------------------------- //
// Simulation parameter types
// --------------------------------------------------------------------------- //
export interface Propellant {
  name: string;
  density: number;
  a: number;
  n: number;
  gamma: number;
  t_flame: number;
  molar_mass: number;
  c_star_eff: number;
}

export type GrainType = "BATES" | "END_BURNER" | "TUBULAR" | "ROD";

export interface Grain {
  grain_type: GrainType;
  outer_diameter: number;
  core_diameter: number;
  segment_length: number;
  segments: number;
  inhibited_ends: boolean;
}

export interface Nozzle {
  throat_diameter: number;
  expansion_ratio: number;
  efficiency: number;
}

export interface MotorRequest {
  propellant: Propellant;
  grain: Grain;
  nozzle: Nozzle;
  altitude: number;
  dt: number;
  max_time: number;
}

export interface Airframe {
  diameter: number;
  cd0: number;
  dry_mass: number;
}

export interface MissileRequest {
  motor: MotorRequest;
  airframe: Airframe;
  launch_speed: number;
  elevation_deg: number;
  azimuth_deg: number;
  dt: number;
  max_time: number;
}

export interface Interceptor {
  motor: MotorRequest;
  airframe: Airframe;
  launch_position: number[];
  launch_speed: number;
  elevation_deg: number;
  azimuth_deg: number;
  nav_constant: number;
  max_lateral_g: number;
  seeker_delay: number;
  seeker_range: number;
}

export interface Target {
  position: number[];
  velocity: number[];
  diameter: number;
  cd0: number;
  mass: number;
  maneuver_accel: number[];
}

export interface EngagementRequest {
  interceptor: Interceptor;
  target: Target;
  dt: number;
  max_time: number;
  lethal_radius: number;
}

// --------------------------------------------------------------------------- //
// Simulation result types
// --------------------------------------------------------------------------- //
export interface MotorResult {
  time: number[];
  thrust: number[];
  chamber_pressure: number[];
  mass_flow: number[];
  burn_area: number[];
  kn: number[];
  propellant_mass: number[];
  summary: {
    burn_time: number;
    total_impulse: number;
    specific_impulse: number;
    peak_thrust: number;
    average_thrust: number;
    peak_pressure: number;
    propellant_mass_initial: number;
    impulse_class: string;
    kn_initial: number;
    kn_max: number;
    port_to_throat: number;
    web_thickness: number;
    warnings: string[];
  };
}

export interface TrajectoryResult {
  time: number[];
  position: number[][];
  velocity: number[][];
  speed: number[];
  mach: number[];
  mass: number[];
  altitude: number[];
  summary: {
    apogee: number;
    max_speed: number;
    max_mach: number;
    range: number;
    flight_time: number;
  };
  motor_summary: MotorResult["summary"];
}

export interface EngagementResult {
  time: number[];
  interceptor_position: number[][];
  target_position: number[][];
  separation: number[];
  interceptor_speed: number[];
  target_speed: number[];
  interceptor_accel_cmd: number[];
  summary: {
    intercepted: boolean;
    miss_distance: number;
    intercept_time: number;
    intercept_point: number[];
    closing_speed_at_intercept: number;
  };
  interceptor_motor_summary: MotorResult["summary"];
}

// --------------------------------------------------------------------------- //
// Simulation API calls
// --------------------------------------------------------------------------- //
async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Request to ${path} failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export const simulateMotor = (req: MotorRequest) =>
  postJson<MotorResult>("/motor/simulate", req);

export const simulateMissile = (req: MissileRequest) =>
  postJson<TrajectoryResult>("/missile/simulate", req);

export const simulateEngagement = (req: EngagementRequest) =>
  postJson<EngagementResult>("/engagement/simulate", req);

export interface FireSolution {
  intercepted: boolean;
  elevation_deg: number;
  azimuth_deg: number;
  miss_distance: number;
  intercept_time: number;
  intercept_point: number[];
  envelope: { elevation: number; miss: number; hit: boolean }[];
  engagement: EngagementResult;
  interceptor_motor_summary: MotorResult["summary"];
}

export const solveEngagement = (req: EngagementRequest) =>
  postJson<FireSolution>("/engagement/solve", req);

export interface SalvoShot {
  index: number;
  launch_time: number;
  elevation_deg: number;
  intercepted: boolean;
  miss_distance: number;
  intercept_time: number;
}

export interface SalvoResult {
  count: number;
  hits: number;
  intercepted: boolean;
  best_miss: number;
  azimuth_deg: number;
  success_fraction: number;
  shots: SalvoShot[];
  interceptor_motor_summary: MotorResult["summary"];
}

export interface SalvoRequest {
  engagement: EngagementRequest;
  count: number;
  stagger: number;
  elevation_spread: number;
  auto_aim: boolean;
}

export const salvoEngagement = (req: SalvoRequest) =>
  postJson<SalvoResult>("/engagement/salvo", req);

export interface MotorSweepResult {
  parameter: string;
  points: { value: number; summary: MotorResult["summary"] }[];
}

export interface MotorSweepRequest {
  base: MotorRequest;
  parameter: string;
  values: number[];
}

export const sweepMotor = (req: MotorSweepRequest) =>
  postJson<MotorSweepResult>("/motor/sweep", req);

export async function fetchPropellantPresets(): Promise<
  Record<string, Propellant>
> {
  const res = await fetch(`${BASE}/motor/presets`);
  if (!res.ok) throw new Error("Failed to fetch propellant presets");
  return res.json();
}

// --------------------------------------------------------------------------- //
// Export download helpers
// --------------------------------------------------------------------------- //
export async function downloadExport(
  path: string,
  body: unknown,
  filename: string
): Promise<void> {
  const init: RequestInit = body
    ? {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }
    : { method: "GET" };
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) throw new Error(`Export ${path} failed`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
