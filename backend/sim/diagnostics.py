"""Plain-language diagnosis of an engagement outcome.

Looks at the recorded engagement (commanded acceleration, speed, closing speed,
miss distance) and the interceptor's limits, and explains in everyday words why
it hit or missed, with actionable tips. Heuristic and purely kinematic — it
reads the same time histories the plots show.
"""

from __future__ import annotations

G0 = 9.80665


def diagnose_engagement(
    eng: dict,
    *,
    max_lateral_g: float,
    lethal_radius: float,
    target_maneuvering: bool = False,
    seeker_noisy: bool = False,
) -> dict:
    """Return ``{verdict, miss_distance, reasons, tips}`` in plain language."""
    s = eng.get("summary", {})
    hit = bool(s.get("intercepted"))
    miss = float(s.get("miss_distance", float("inf")))
    vc = float(s.get("closing_speed_at_intercept", 0.0))

    acmd = eng.get("interceptor_accel_cmd") or [0.0]
    spd = eng.get("interceptor_speed") or [0.0]
    a_max = max_lateral_g * G0
    sat_frac = (sum(1 for a in acmd if a >= 0.9 * a_max) / len(acmd)) if acmd else 0.0
    end_speed = spd[-1] if spd else 0.0

    reasons: list[str] = []
    tips: list[str] = []

    if hit:
        reasons.append(
            f"Reached the threat with {miss:.1f} m to spare "
            f"(anything within {lethal_radius:.0f} m counts as a catch)."
        )
        if vc > 0:
            reasons.append(f"Still closing fast — about {vc:.0f} m/s — at the "
                           "meeting point.")
        if sat_frac > 0.2:
            reasons.append("It spent a lot of the flight turning near its "
                           "limit, so there wasn't much margin to spare.")
        return {"verdict": "hit", "miss_distance": miss,
                "reasons": reasons, "tips": tips}

    # ---- miss: rank the likely causes -------------------------------------
    if sat_frac > 0.25:
        reasons.append(
            f"It hit its turn limit (~{max_lateral_g:.0f} g) and couldn't bend "
            "its path onto the threat fast enough."
        )
        tips.append("Give the interceptor more turn (raise max lateral g), or "
                    "launch sooner for a straighter, head-on intercept.")
    if vc <= 0.0:
        reasons.append("By the closest point the threat was pulling away — the "
                       "interceptor simply couldn't catch up.")
        tips.append("Use a bigger/faster interceptor, or engage while the "
                    "threat is still approaching.")
    elif end_speed < 150.0:
        reasons.append(
            f"The interceptor had slowed to ~{end_speed:.0f} m/s (drag and "
            "gravity bleed off speed) before it arrived."
        )
        tips.append("More motor (a bigger grain) keeps speed up; or engage at "
                    "shorter range.")
    if target_maneuvering:
        reasons.append("The threat was dodging, which keeps breaking the "
                       "collision course.")
        tips.append("Try APN guidance — it allows for the target's "
                    "acceleration.")
    if seeker_noisy:
        reasons.append("A noisy seeker scattered the aim point during homing.")
        tips.append("Turn on the tracking filter (Tracker α) or raise the "
                    "seeker update rate.")
    if not reasons:
        reasons.append(
            f"Closest pass was {miss:.0f} m — just outside the "
            f"{lethal_radius:.0f} m catch distance."
        )
        tips.append("Engage a little closer, or use a bigger interceptor.")

    return {"verdict": "miss", "miss_distance": miss,
            "reasons": reasons, "tips": tips}
