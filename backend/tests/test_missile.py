"""Tests for atmosphere, flight dynamics and the missile trajectory endpoint."""

from fastapi.testclient import TestClient

from backend.main import app
from backend.sim.aerodynamics import drag_coefficient
from backend.sim.atmosphere import atmosphere

client = TestClient(app)


def test_atmosphere_decreases_with_altitude():
    sea = atmosphere(0.0)
    high = atmosphere(20000.0)
    assert sea.density > high.density > 0
    assert sea.pressure > high.pressure > 0
    assert sea.speed_of_sound > 0


def test_transonic_drag_rise():
    # drag coefficient peaks transonically, above the subsonic baseline
    assert drag_coefficient(1.1, 0.4) > drag_coefficient(0.5, 0.4)
    assert drag_coefficient(1.1, 0.4) > drag_coefficient(3.0, 0.4)


def test_missile_trajectory_endpoint():
    resp = client.post("/api/missile/simulate", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["apogee"] > 0
    assert data["summary"]["max_speed"] > 0
    assert len(data["time"]) == len(data["altitude"])
    # vehicle should come back down (altitude history starts and ends low)
    assert data["altitude"][0] < data["summary"]["apogee"]


def test_steeper_launch_reaches_higher():
    base = {"launch_speed": 30.0, "elevation_deg": 85.0}
    flat = {"launch_speed": 30.0, "elevation_deg": 30.0}
    high = client.post("/api/missile/simulate", json=base).json()
    low = client.post("/api/missile/simulate", json=flat).json()
    assert high["summary"]["apogee"] > low["summary"]["apogee"]


def test_multistage_flight_stages_and_drops_mass():
    payload = {
        "stages": [
            {"motor": {}, "structural_mass": 8.0, "ignition_delay": 0.0},
            {"motor": {}, "structural_mass": 4.0, "ignition_delay": 1.0},
        ],
        "payload": {"diameter": 0.16, "cd0": 0.3, "dry_mass": 15.0},
        "elevation_deg": 85.0,
    }
    data = client.post("/api/missile/multistage", json=payload).json()
    assert data["summary"]["apogee"] > 0
    assert len(data["stage_starts"]) == 2
    # second stage ignites after the first burnout + coast
    assert data["stage_starts"][1] > data["stage_starts"][0]
    # the spent first stage is jettisoned (last stage kept by default)
    assert len(data["separations"]) == 1
    sep = data["separations"][0]
    assert sep["mass_after"] < data["initial_mass"]



# --- aerodynamic stability (Barrowman) ------------------------------------ #
def test_stability_typical_finned_rocket_is_stable():
    from backend.sim.stability import barrowman_stability

    res = barrowman_stability(
        diameter=0.16, nose_length=0.6, body_length=2.5,
        fin_count=4, fin_root_chord=0.30, fin_tip_chord=0.15,
        fin_span=0.18, fin_sweep=0.12,
        dry_mass=40.0, dry_cg=1.6, propellant_mass=8.0, propellant_cg=2.7,
    )
    # CP must sit behind both CGs for positive static margin
    assert res.x_cp > res.x_cg_loaded
    assert res.static_margin_loaded > 0.0
    assert res.cn_fins > 0.0


def test_stability_cone_cp_is_aft_of_ogive():
    from backend.sim.stability import barrowman_stability

    common = dict(diameter=0.16, nose_length=0.6, body_length=2.5, fin_count=0)
    ogive = barrowman_stability(nose_type="ogive", **common)
    cone = barrowman_stability(nose_type="cone", **common)
    assert cone.x_cp_nose > ogive.x_cp_nose


def test_stability_no_fins_warns():
    from backend.sim.stability import barrowman_stability

    res = barrowman_stability(
        diameter=0.16, nose_length=0.6, body_length=2.5, fin_count=0,
        dry_mass=40.0,
    )
    assert any("unstable" in w.lower() for w in res.warnings)


def test_stability_endpoint():
    payload = {
        "diameter": 0.16, "nose_length": 0.6, "body_length": 2.5,
        "fin_count": 4, "fin_span": 0.18, "dry_cg": 1.6,
        "propellant_mass": 8.0, "propellant_cg": 2.7,
    }
    data = client.post("/api/missile/stability", json=payload).json()
    assert "static_margin_loaded" in data
    assert data["x_cp"] > 0
    assert data["cn_alpha"] > 2.0  # nose (2) + fins
