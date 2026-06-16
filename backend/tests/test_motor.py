"""Tests for the solid rocket motor internal-ballistics model and endpoint."""

from fastapi.testclient import TestClient

from backend.main import app
from backend.sim.grain import Grain, GrainType
from backend.sim.motor import Nozzle, exit_mach, simulate_motor
from backend.sim.propellant import PRESETS

client = TestClient(app)


def test_exit_mach_supersonic():
    # Larger area ratio => higher supersonic exit Mach.
    assert exit_mach(4.0, 1.2) > exit_mach(2.0, 1.2) > 1.0


def test_c_star_positive():
    for prop in PRESETS.values():
        assert prop.c_star > 0


def test_motor_simulation_is_physical():
    prop = PRESETS["KNSB"]
    grain = Grain(GrainType.BATES, outer_diameter=0.075, core_diameter=0.025,
                  segment_length=0.12, segments=4, density=prop.density)
    nozzle = Nozzle(throat_diameter=0.018, expansion_ratio=6.0)
    res = simulate_motor(prop, grain, nozzle, dt=0.001)

    assert res.burn_time > 0
    assert res.total_impulse > 0
    assert res.peak_thrust > 0
    assert res.peak_pressure > 0
    assert 50 < res.specific_impulse < 350          # plausible for KNSB
    assert res.propellant_mass_initial > 0
    assert res.impulse_class != ""
    # thrust curve ends at zero (tail-off sample appended)
    assert res.thrust[-1] == 0.0


def test_grain_burns_out():
    prop = PRESETS["KNSB"]
    grain = Grain(GrainType.BATES, outer_diameter=0.05, core_diameter=0.02,
                  segment_length=0.08, segments=1, density=prop.density)
    assert grain.burn_area(grain.web_thickness) <= 1e-9
    assert grain.volume(grain.web_thickness) < grain.volume(0.0)


def test_higher_throat_lowers_pressure():
    prop = PRESETS["KNSB"]
    grain = Grain(GrainType.BATES, outer_diameter=0.075, core_diameter=0.025,
                  segment_length=0.12, segments=4, density=prop.density)
    small = simulate_motor(prop, grain, Nozzle(0.015, 6.0), dt=0.002)
    large = simulate_motor(prop, grain, Nozzle(0.025, 6.0), dt=0.002)
    assert small.peak_pressure > large.peak_pressure


def test_motor_endpoint():
    resp = client.post("/api/motor/simulate", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total_impulse"] > 0
    assert len(data["time"]) == len(data["thrust"])


def test_motor_presets_endpoint():
    resp = client.get("/api/motor/presets")
    assert resp.status_code == 200
    assert "KNSB" in resp.json()


def test_all_grain_types_produce_positive_impulse():
    prop = PRESETS["KNSB"]
    nozzle = Nozzle(throat_diameter=0.018, expansion_ratio=6.0)
    for gt in (GrainType.BATES, GrainType.TUBULAR, GrainType.ROD):
        grain = Grain(gt, outer_diameter=0.075, core_diameter=0.025,
                      segment_length=0.12, segments=2, density=prop.density)
        res = simulate_motor(prop, grain, nozzle, dt=0.002)
        assert res.total_impulse > 0, gt
        assert res.peak_thrust > 0, gt


def test_no_negative_thrust_when_over_expanded():
    # Oversized throat + large expansion ratio => over-expansion; thrust must
    # never go negative (Summerfield separation clamp).
    prop = PRESETS["KNSB"]
    grain = Grain(GrainType.END_BURNER, outer_diameter=0.075, core_diameter=0.0,
                  segment_length=0.12, segments=1, density=prop.density)
    res = simulate_motor(prop, grain, Nozzle(0.018, 6.0), dt=0.002)
    assert all(t >= 0.0 for t in res.thrust)
    assert res.total_impulse >= 0.0


def test_smaller_throat_raises_pressure():
    base = {"nozzle": {"throat_diameter": 0.018, "expansion_ratio": 6.0,
                       "efficiency": 0.97}}
    resp = client.post("/api/motor/sweep", json={
        "base": base,
        "parameter": "nozzle.throat_diameter",
        "values": [0.014, 0.018, 0.022],
    })
    assert resp.status_code == 200
    pts = resp.json()["points"]
    pressures = [p["summary"]["peak_pressure"] for p in pts]
    # peak pressure strictly decreases as the throat opens up
    assert pressures[0] > pressures[1] > pressures[2]
