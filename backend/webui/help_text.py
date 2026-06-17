"""Guidance text for every input — *how to choose the value*, not just what it is.

Grounded in standard public engineering references (Sutton, *Rocket Propulsion
Elements*; Zarchan, *Tactical and Strategic Missile Guidance*; Nakka's amateur
solid-motor notes). Surfaced as hover tooltips next to each field so the UI is
self-documenting. Keep each entry to a sentence or two with a usable range.
"""

from __future__ import annotations

# Propellant ---------------------------------------------------------------- #
PROPELLANT = {
    "a": "Burn-rate coefficient (r = a·Pcⁿ), in mm/s at 1 MPa. Set by the "
    "propellant chemistry — use a preset. KNSB≈8.3, KNDX≈8.9, APCP≈5. Higher a "
    "→ faster burn → more thrust but shorter burn.",
    "n": "Burn-rate pressure exponent. 0.2–0.5 for stable propellants; KN-sugar "
    "≈0.32, APCP≈0.35. Keep < 0.5 — as n→1 the motor becomes pressure-unstable "
    "(small area changes run away).",
    "density": "Solid grain density (kg/m³). Use the preset value; ~1750–1850 "
    "for KN-sugar and APCP. Higher density packs more impulse into a given case.",
    "gamma": "Ratio of specific heats of the exhaust (cp/cv), 1.1–1.3. Lower for "
    "metallised/heavy exhaust, higher for light gas. Affects c* and nozzle Cf — "
    "take it from the preset.",
    "t_flame": "Adiabatic flame temperature (K). KN-sugar ≈1600, APCP ≈3000. "
    "Hotter → higher c* and Isp, but harder on the nozzle throat.",
    "molar_mass": "Mean exhaust molar mass (kg/mol). Lower (lighter gas) → "
    "higher c* and Isp. ~0.025 for APCP, ~0.040 for KN-sugar. Use the preset.",
    "c_star_eff": "Combustion efficiency, fraction of ideal c* actually reached. "
    "0.92–0.98 for real motors; 0.95 is a safe default. Lower it to model poor "
    "mixing or incomplete combustion.",
}

# Grain --------------------------------------------------------------------- #
GRAIN = {
    "grain_type": "Grain geometry sets the thrust shape. BATES: neutral, the "
    "general-purpose choice. TUBULAR: progressive (thrust rises). ROD: "
    "regressive (thrust falls). END_BURNER: long, low, near-constant thrust.",
    "outer_diameter": "Grain outer diameter (m) — essentially the motor case "
    "bore. Bigger → more propellant and burn area → more thrust. Must fit your "
    "airframe; keep a few mm under the body diameter.",
    "core_diameter": "Initial bore/port diameter (m). Larger core → more "
    "initial burn area (higher start thrust) and a higher port-area/throat "
    "ratio (less erosive burning). Keep core/throat ≳ 2. 0 ⇒ end-burner.",
    "segment_length": "Length of one grain segment (m). Total grain length = "
    "segment_length × segments. Longer → more propellant and longer burn.",
    "segments": "Number of stacked BATES segments (1–20). More segments → "
    "longer burn and a flatter thrust curve; also adds end-faces (burn area).",
    "inhibited_ends": "If true, the segment end-faces don't burn (inhibitor "
    "coating). Use to suppress the initial thrust spike and flatten the curve.",
}

# Nozzle -------------------------------------------------------------------- #
NOZZLE = {
    "throat_diameter": "Nozzle throat diameter (m) — the master pressure knob. "
    "Smaller throat → higher chamber pressure and thrust, but watch the case "
    "limit. Size it so Kn gives Pc ≈ 5–10 MPa for KN-sugar.",
    "expansion_ratio": "Exit/throat area ratio Ae/At. Match to altitude: ~4–8 "
    "at sea level, larger for high-altitude/vacuum. Too large over-expands and "
    "the flow separates (the Summerfield clamp guards against this).",
    "efficiency": "Nozzle/divergence efficiency, 0.93–0.98. Accounts for "
    "non-axial exit flow and losses. 0.97 is typical for a conical nozzle.",
}

# Motor environment / solver ------------------------------------------------ #
MOTOR_ENV = {
    "altitude": "Ambient altitude (m) used for back-pressure on the thrust. 0 = "
    "sea level. Raising it increases thrust (lower ambient pressure).",
    "dt": "Internal-ballistics time step (s). 0.001 is accurate; smaller is "
    "finer but slower. Rarely needs changing.",
    "max_time": "Safety cap on burn duration (s). Just needs to exceed the burn "
    "time; the sim stops at burnout.",
}

# Airframe ------------------------------------------------------------------ #
AIRFRAME = {
    "diameter": "Body reference diameter (m) — sets the frontal area for drag. "
    "Must be ≥ the grain outer diameter. Slimmer bodies have less drag.",
    "cd0": "Zero-lift (subsonic) drag coefficient. 0.2–0.5 for a clean missile; "
    "the model adds a transonic rise automatically. Lower = sleeker.",
    "dry_mass": "Mass without propellant (kg): structure + payload. Heavier → "
    "lower acceleration and apogee; lighter → snappier but less robust.",
}

# Launch -------------------------------------------------------------------- #
LAUNCH = {
    "launch_speed": "Rail-exit speed (m/s). The speed the vehicle leaves the "
    "launcher with. 20–40 m/s is typical so fins have airflow to stabilise.",
    "elevation_deg": "Launch elevation above horizon (°). 90 = straight up "
    "(max altitude); lower trades altitude for downrange. ~80–85 for a sounding "
    "shot; the Auto-aim solver picks this for an intercept.",
    "azimuth_deg": "Launch compass-style azimuth (°): 0 = North, 90 = East. For "
    "an intercept, aim at the target bearing (or let Auto-aim set it).",
}

# Interceptor guidance ------------------------------------------------------ #
GUIDANCE = {
    "launch_position": "Launch site in ENU metres [East, North, Up] relative to "
    "the origin. Usually [0,0,0]; raise Up for a hilltop battery.",
    "guidance_law": "Homing law. PN: classic proportional navigation. APN: "
    "augmented PN, adds a target-acceleration term — better against a "
    "manoeuvring target. PN_GRAVITY: PN plus a gravity-bias so the missile "
    "doesn't sag below the line of sight on long lofted shots.",
    "nav_constant": "Proportional-navigation gain N (3–5 typical). Higher N "
    "pulls lead faster and flattens the trajectory but demands more lateral g; "
    "4 is the classic default.",
    "max_lateral_g": "Airframe lateral acceleration limit (g). Caps the PN "
    "command. 30–60 g for a tactical interceptor; too low and it can't turn "
    "tight enough to hit a manoeuvring target.",
    "seeker_delay": "Time after launch before guidance switches on (s). Lets "
    "the motor boost and the vehicle clear the rail. 0.3–1 s typical.",
    "seeker_range": "Max range (m) at which the seeker can see the target. "
    "Inside this the interceptor homes; outside it flies ballistically.",
    "seeker_angular_noise": "Seeker boresight (line-of-sight) 1-σ error, in "
    "milliradians. 0 = perfect. A few mrad is realistic; large values make the "
    "interceptor chase a jittery track and miss. The solver ignores it (aims at "
    "the nominal track) — only Engage/Monte-Carlo apply it.",
    "seeker_range_noise": "Range-measurement 1-σ error as a fraction of range "
    "(0.05 = 5%). Mostly affects closing-speed estimation; less critical than "
    "angular noise for PN.",
    "seeker_update_rate": "Seeker measurement rate (Hz). The noisy fix is held "
    "between updates; 0 = continuous (refreshed every step). 10–50 Hz is "
    "typical — lower rates let noise persist longer and hurt more.",
}

# Target -------------------------------------------------------------------- #
TARGET = {
    "position": "Target position now, ENU metres [East, North, Up]. This is "
    "where the threat is when you launch.",
    "velocity": "Target velocity, m/s [E, N, Up]. Negative components mean it's "
    "inbound/descending. A fast inbound target is the hard case.",
    "maneuver_accel": "Constant evasive acceleration, m/s² [E, N, Up]. 0 = "
    "ballistic. Add lateral g here to test guidance against a jinking target.",
    "diameter": "Target body diameter (m) — sets its drag area. Larger decays "
    "faster in the atmosphere.",
    "cd0": "Target drag coefficient (0.1–0.5). Higher → more deceleration along "
    "its arc.",
    "mass": "Target mass (kg). Heavier coasts further (more ballistic); lighter "
    "is slowed more by drag.",
}

# Engagement solver --------------------------------------------------------- #
ENGAGEMENT = {
    "dt": "Engagement integration step (s). 0.01 is a good balance; the miss "
    "distance uses an analytic closest-approach so it stays accurate even at "
    "larger steps.",
    "max_time": "Max engagement duration (s). Must be long enough for the "
    "interceptor to reach the target.",
    "lethal_radius": "Miss distance (m) counted as an intercept — the kinematic "
    "closest-approach threshold. Smaller = stricter hit criterion.",
}

# Stage / stack ------------------------------------------------------------- #
STAGE = {
    "ignition_delay": "Coast time (s) after the previous stage burns out before "
    "this one lights. 0 = light immediately; add a few seconds to coast up "
    "before the sustainer fires.",
    "structural_mass": "Inert mass of this stage (case, nozzle, interstage) in "
    "kg, jettisoned at its burnout. Bigger stages weigh more; dropping it is "
    "exactly the staging benefit.",
}

# Stability (Barrowman) ----------------------------------------------------- #
STABILITY = {
    "nose_type": "Nose-cone shape: ogive (most common), cone, parabolic or "
    "haack. Affects where the nose's centre of pressure sits.",
    "fin_root_chord": "Fin chord at the body (m). Bigger fins → CP moves aft → "
    "more stability.",
    "fin_tip_chord": "Fin chord at the tip (m). 0 = a triangular (delta) fin.",
    "fin_span": "Exposed fin semi-span (m), body surface to tip. The strongest "
    "lever on stability — larger span pushes CP aft.",
    "fin_sweep": "Leading-edge sweep distance (m): how far back the tip LE is "
    "from the root LE. Cosmetic for stability, matters for flutter.",
    "dry_cg": "Empty centre of gravity from the nose tip (m). Find it by "
    "balancing the unloaded rocket. Leave blank for an estimate (~0.55·L).",
    "propellant_cg": "Loaded propellant CG from the nose tip (m). Usually well "
    "aft (in the motor). Blank ≈ 0.85·L.",
    "static_margin": "CP-to-CG distance in calibers (body diameters). Aim for "
    "1–2 cal stable across the whole burn: <1 risks instability, >2.5 "
    "weathercocks into wind. CG moves as propellant burns, so check both ends.",
}

# Payload (stack flight) ---------------------------------------------------- #
PAYLOAD = {
    "dry_mass": "Payload/bus mass (kg) carried by the top stage and kept to "
    "apogee. Heavier payload → lower apogee.",
    "diameter": "Payload body diameter (m) for drag after staging.",
    "cd0": "Payload drag coefficient once the stack is gone.",
}

# Salvo / Monte-Carlo ------------------------------------------------------- #
SALVO = {
    "salvo_count": "Number of interceptors fired at the one target (1–8). More "
    "shots raise the layered kill probability.",
    "salvo_stagger": "Seconds between launches. Lets earlier shots be assessed "
    "before later ones commit (shoot-look-shoot).",
    "salvo_spread": "Total spread of launch elevations across the salvo (°), "
    "centred on the auto-aimed solution — widens the covered basket.",
    "mc_trials": "Number of Monte-Carlo runs (10–1000). More trials → smoother "
    "Pk estimate but slower. 150 is a good default.",
    "mc_pos_sigma": "1-σ target-track position error (m). The launcher aims at "
    "the nominal track; bigger error lowers Pk.",
    "mc_vel_sigma": "1-σ target-track velocity error (m/s). Velocity error "
    "grows over flight time, so it hurts long shots most.",
}
