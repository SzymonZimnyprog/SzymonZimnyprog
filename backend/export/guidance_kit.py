"""Guidance & sensors kit: bridge the simulation to real guidance software.

Turns a validated interceptor configuration into the artefacts an engineer
needs to port the *kinematic guidance loop* onto a real flight computer:

* a **sensor specification** — which sensors realise the modelled seeker and
  autopilot (RF/IR seeker, IMU), with the update rates, accuracy budgets and
  ranges read straight from the simulation parameters;
* **porting notes** — the control architecture, coordinate frames, units and a
  parameter map from each simulation field to its software/sensor counterpart;
* a **reference proportional-navigation skeleton** in C, parameterised by the
  same navigation constant ``N`` and acceleration limit the simulation used.

Scope note: this covers only the guidance/navigation/control (GNC) loop — line-
of-sight tracking, the PN steering law and the lateral-acceleration command. It
is the same public, textbook material the Simulink export already produces;
there is no warhead, fuzing, seeker-jamming or terminal-effects content.
"""

from __future__ import annotations

from backend.sim.models import InterceptorModel

G0 = 9.80665

# Seeker technology options able to supply a line-of-sight angle (and rate),
# with the extra observable each provides. Range-capable seekers are needed to
# realise a non-zero range-noise budget; all supply LOS angle.
_SEEKER_OPTIONS = {
    "active_rf": ("Active radar (RF)", "LOS angle + range + range-rate"),
    "semi_active_rf": ("Semi-active radar (RF)", "LOS angle + range-rate"),
    "ir_imaging": ("Imaging infrared (IIR)", "LOS angle only (angle-only)"),
}


def _loop_rate_hz(it: InterceptorModel) -> float:
    """Recommended guidance/seeker loop rate (Hz)."""
    if it.seeker_update_rate > 0:
        return it.seeker_update_rate
    return 100.0  # continuous in the sim -> a sane default digital loop rate


def sensor_spec(it: InterceptorModel) -> dict:
    """Structured (JSON-able) sensor + GNC specification."""
    loop_hz = _loop_rate_hz(it)
    accel_full_scale = round(it.max_lateral_g * 1.5 + 5.0)  # headroom over command
    angular_mrad = it.seeker_angular_noise  # already mrad in the request model
    range_capable = it.seeker_range_noise > 0.0

    seekers = []
    for key, (name, obs) in _SEEKER_OPTIONS.items():
        suitable = True
        if range_capable and key == "ir_imaging":
            suitable = False  # angle-only seeker can't realise a range-noise budget
        seekers.append({"id": key, "name": name, "observables": obs,
                        "suitable": suitable})

    return {
        "guidance_law": it.guidance_law,
        "navigation_constant_N": it.nav_constant,
        "guidance_loop_rate_hz": loop_hz,
        "command_acceleration_limit_g": it.max_lateral_g,
        "seeker": {
            "activation_delay_s": it.seeker_delay,
            "acquisition_range_m": it.seeker_range,
            "los_angular_accuracy_mrad_1sigma": angular_mrad,
            "range_accuracy_fraction_1sigma": it.seeker_range_noise,
            "measurement_rate_hz": loop_hz,
            "tracking_filter": ("alpha-beta" if it.seeker_track_alpha > 0 else "none"),
            "tracking_filter_alpha": it.seeker_track_alpha,
            "candidate_technologies": seekers,
        },
        "imu": {
            "accelerometer_full_scale_g": accel_full_scale,
            "accelerometer_bandwidth_hz": round(loop_hz * 5),
            "gyro_full_scale_dps": 1000,
            "gyro_bandwidth_hz": round(loop_hz * 5),
            "purpose": ("autopilot inner loop; gravity bias compensation"
                        if it.guidance_law == "PN_GRAVITY"
                        else "autopilot inner loop / body-rate stabilisation"),
        },
        "midcourse": {
            "needed": it.seeker_delay > 0.0,
            "duration_s": it.seeker_delay,
            "note": ("INS/GPS (or command uplink) flies the vehicle until the "
                     "seeker acquires at t = activation delay."),
        },
        "frames_and_units": {
            "simulation_frame": "ENU (East, North, Up), metres, m/s, seconds",
            "onboard_frame": "body frame; rotate IMU measurements into a local "
                             "level frame before the PN command",
            "command": "lateral acceleration, m/s^2, perpendicular to LOS",
        },
    }


def _bool(v: bool) -> str:
    return "yes" if v else "no"


def sensor_spec_markdown(it: InterceptorModel) -> str:
    """Human-readable sensor spec + porting notes (Markdown)."""
    s = sensor_spec(it)
    sk, imu = s["seeker"], s["imu"]
    lines: list[str] = []
    a = lines.append

    a("# Guidance & Sensors Kit")
    a("")
    a("Generated from the interceptor configuration. Covers the kinematic "
      "guidance/navigation/control (GNC) loop only — no warhead, fuzing or "
      "terminal-effects content.")
    a("")
    a("## 1. Guidance law")
    a("")
    a(f"- **Law:** {s['guidance_law']} (proportional navigation family)")
    a(f"- **Navigation constant N:** {s['navigation_constant_N']}")
    a(f"- **Guidance loop rate:** {s['guidance_loop_rate_hz']:.0f} Hz")
    a(f"- **Command acceleration limit:** {s['command_acceleration_limit_g']:.0f} g "
      f"({s['command_acceleration_limit_g'] * G0:.0f} m/s^2)")
    if s["guidance_law"] == "APN":
        a("- APN adds a target-acceleration term; the seeker/estimator must "
          "supply an estimate of target lateral acceleration.")
    if s["guidance_law"] == "PN_GRAVITY":
        a("- Gravity-compensated PN: add +g to the command's vertical channel, "
          "so the IMU/level reference must observe the gravity vector.")
    a("")
    a("## 2. Seeker")
    a("")
    a(f"- **Activation delay:** {sk['activation_delay_s']:.2f} s after launch")
    a(f"- **Acquisition range:** {sk['acquisition_range_m']:.0f} m")
    a(f"- **LOS angular accuracy:** {sk['los_angular_accuracy_mrad_1sigma']:.2f} "
      "mrad (1σ)")
    a(f"- **Range accuracy:** {sk['range_accuracy_fraction_1sigma'] * 100:.1f}% "
      "of range (1σ)" if sk["range_accuracy_fraction_1sigma"] > 0
      else "- **Range accuracy:** not required (angle-only PN is sufficient)")
    a(f"- **Measurement rate:** {sk['measurement_rate_hz']:.0f} Hz")
    a(f"- **Tracking filter:** {sk['tracking_filter']}"
      + (f" (α = {sk['tracking_filter_alpha']:.2f})"
         if sk["tracking_filter"] != "none" else ""))
    a("")
    a("Candidate seeker technologies:")
    a("")
    a("| Technology | Observables | Suitable here |")
    a("| --- | --- | --- |")
    for c in sk["candidate_technologies"]:
        a(f"| {c['name']} | {c['observables']} | {_bool(c['suitable'])} |")
    a("")
    a("## 3. Inertial measurement unit (IMU)")
    a("")
    a(f"- **Accelerometer full scale:** ±{imu['accelerometer_full_scale_g']} g "
      "(command limit + headroom)")
    a(f"- **Gyro full scale:** ±{imu['gyro_full_scale_dps']} °/s")
    a(f"- **Bandwidth:** ≥ {imu['accelerometer_bandwidth_hz']:.0f} Hz "
      "(≈ 5× the loop rate)")
    a(f"- **Purpose:** {imu['purpose']}")
    a("")
    a("## 4. Midcourse")
    a("")
    if s["midcourse"]["needed"]:
        a(f"- Needed for the first {s['midcourse']['duration_s']:.2f} s. "
          f"{s['midcourse']['note']}")
    else:
        a("- Not needed; the seeker is active from launch.")
    a("")
    a("## 5. Frames, units & control architecture")
    a("")
    a(f"- **Simulation frame:** {s['frames_and_units']['simulation_frame']}")
    a(f"- **Onboard frame:** {s['frames_and_units']['onboard_frame']}")
    a(f"- **Command:** {s['frames_and_units']['command']}")
    a("")
    a("```")
    a("seeker LOS angle ──▶ LOS-rate estimate ──▶ PN law (×N·Vc) ──▶ a_cmd")
    a("                                                     │")
    a("           IMU (accel + gyro) ──▶ autopilot inner loop ──▶ fin/TVC actuation")
    a("```")
    a("")
    a("## 6. Parameter map (simulation → software)")
    a("")
    a("| Simulation field | Software / sensor counterpart |")
    a("| --- | --- |")
    a(f"| `nav_constant` = {it.nav_constant} | PN gain `N` in the steering law |")
    a(f"| `max_lateral_g` = {it.max_lateral_g:.0f} | command saturation + "
      "accelerometer full scale |")
    a(f"| `seeker_delay` = {it.seeker_delay:.2f} s | midcourse→terminal handover |")
    a(f"| `seeker_range` = {it.seeker_range:.0f} m | seeker acquisition range / "
      "link budget |")
    a(f"| `seeker_angular_noise` = {it.seeker_angular_noise:.2f} mrad | seeker "
      "boresight accuracy (1σ) |")
    a(f"| `seeker_update_rate` = {it.seeker_update_rate:.0f} Hz | seeker / guidance "
      "loop rate |")
    a(f"| `seeker_track_alpha` = {it.seeker_track_alpha:.2f} | onboard tracking "
      "filter gain |")
    a("")
    a("## 7. Validation")
    a("")
    a("Drive the ported guidance loop with the recorded engagement time history "
      "(`/api/export/simulink/engagement.csv`) as a software-in-the-loop "
      "reference: feed the true relative geometry in, and check the commanded "
      "acceleration matches the simulation's `interceptor_accel_cmd` channel.")
    a("")
    return "\n".join(lines)


def pn_reference_c(it: InterceptorModel) -> str:
    """A self-contained C reference of the PN steering law for this config."""
    n = it.nav_constant
    a_max = it.max_lateral_g * G0
    gravity_line = (
        "    /* PN_GRAVITY: compensate the gravity bias on the vertical channel */\n"
        "    a_cmd[2] += 9.80665f;\n"
        if it.guidance_law == "PN_GRAVITY" else ""
    )
    apn_note = (
        "/* APN: add (N/2) * a_target_perp to a_cmd using the estimated target\n"
        "   acceleration from the seeker/estimator (not shown). */\n"
        if it.guidance_law == "APN" else ""
    )
    return f"""/* pn_guidance.c -- reference proportional-navigation steering law.
 *
 * Generated from the interceptor configuration (guidance law: {it.guidance_law}).
 * Kinematic GNC only: maps the seeker line-of-sight geometry to a lateral
 * acceleration command. Port into your flight-software guidance task running
 * at {_loop_rate_hz(it):.0f} Hz. Frame: local level (East, North, Up), SI units.
 */
#include <math.h>

#define NAV_CONSTANT      {n:.3f}f   /* PN gain N (sim: nav_constant)        */
#define ACCEL_LIMIT_MPS2  {a_max:.3f}f /* command saturation (sim: max_lateral_g) */

static void cross3(const float a[3], const float b[3], float out[3]) {{
    out[0] = a[1]*b[2] - a[2]*b[1];
    out[1] = a[2]*b[0] - a[0]*b[2];
    out[2] = a[0]*b[1] - a[1]*b[0];
}}
static float dot3(const float a[3], const float b[3]) {{
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
}}

{apn_note}/* Inputs (from the seeker + own navigation state):
 *   r_rel[3]  relative position  target - interceptor   [m]
 *   v_rel[3]  relative velocity  target - interceptor   [m/s]
 * Output:
 *   a_cmd[3]  commanded lateral acceleration            [m/s^2]
 */
void pn_command(const float r_rel[3], const float v_rel[3], float a_cmd[3]) {{
    float r2 = dot3(r_rel, r_rel);
    if (r2 < 1e-6f) {{ a_cmd[0]=a_cmd[1]=a_cmd[2]=0.0f; return; }}

    /* LOS rotation rate: omega = (r x v) / (r . r) */
    float omega[3];
    cross3(r_rel, v_rel, omega);
    omega[0] /= r2; omega[1] /= r2; omega[2] /= r2;

    /* Closing speed Vc = -(r . v)/|r| */
    float r_norm = sqrtf(r2);
    float Vc = -dot3(r_rel, v_rel) / r_norm;

    /* PN: a_cmd = N * Vc * (omega x los_hat) */
    float los_hat[3] = {{ r_rel[0]/r_norm, r_rel[1]/r_norm, r_rel[2]/r_norm }};
    float perp[3];
    cross3(omega, los_hat, perp);
    a_cmd[0] = NAV_CONSTANT * Vc * perp[0];
    a_cmd[1] = NAV_CONSTANT * Vc * perp[1];
    a_cmd[2] = NAV_CONSTANT * Vc * perp[2];
{gravity_line}
    /* Saturate to the airframe's lateral-acceleration limit */
    float mag = sqrtf(dot3(a_cmd, a_cmd));
    if (mag > ACCEL_LIMIT_MPS2 && mag > 0.0f) {{
        float k = ACCEL_LIMIT_MPS2 / mag;
        a_cmd[0] *= k; a_cmd[1] *= k; a_cmd[2] *= k;
    }}
}}
"""
