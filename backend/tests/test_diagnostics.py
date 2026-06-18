"""Tests for the plain-language engagement diagnosis."""

from backend.sim.diagnostics import diagnose_engagement


def _eng(intercepted, miss, vc=300.0, acmd=None, spd=None):
    return {
        "summary": {"intercepted": intercepted, "miss_distance": miss,
                    "closing_speed_at_intercept": vc},
        "interceptor_accel_cmd": acmd if acmd is not None else [10.0, 20.0],
        "interceptor_speed": spd if spd is not None else [400.0, 500.0],
    }


def test_hit_verdict_explains_success():
    d = diagnose_engagement(_eng(True, 2.0), max_lateral_g=60, lethal_radius=5)
    assert d["verdict"] == "hit"
    assert any("spare" in r for r in d["reasons"])


def test_miss_g_limited_when_command_saturates():
    # commanded accel pinned at the g-limit for the whole run
    a_max = 60 * 9.80665
    d = diagnose_engagement(
        _eng(False, 40.0, acmd=[a_max] * 10), max_lateral_g=60, lethal_radius=5)
    assert d["verdict"] == "miss"
    assert any("turn limit" in r for r in d["reasons"])
    assert d["tips"]


def test_miss_outrun_when_not_closing():
    d = diagnose_engagement(_eng(False, 80.0, vc=-50.0),
                            max_lateral_g=60, lethal_radius=5)
    assert any("pulling away" in r or "catch up" in r for r in d["reasons"])


def test_miss_flags_maneuver_and_noise():
    d = diagnose_engagement(_eng(False, 30.0), max_lateral_g=60, lethal_radius=5,
                            target_maneuvering=True, seeker_noisy=True)
    text = " ".join(d["reasons"] + d["tips"])
    assert "dodging" in text and ("noisy" in text or "noise" in text)
