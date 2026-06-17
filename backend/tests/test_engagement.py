"""Tests for proportional navigation guidance and the engagement endpoint."""

import numpy as np
from fastapi.testclient import TestClient

from backend.main import app
from backend.sim.guidance import pn_acceleration, seeker_measurement

client = TestClient(app)


def test_pn_zero_on_collision_course():
    # Interceptor heading straight at a stationary target: no LOS rotation,
    # so the PN command is ~zero.
    r_m = np.array([0.0, 0.0, 0.0])
    v_m = np.array([100.0, 0.0, 0.0])
    r_t = np.array([1000.0, 0.0, 0.0])
    v_t = np.array([0.0, 0.0, 0.0])
    a = pn_acceleration(r_m, v_m, r_t, v_t)
    assert np.linalg.norm(a) < 1e-6


def test_pn_commands_turn_when_offset():
    # Target offset laterally => non-zero LOS rate => non-zero command.
    r_m = np.array([0.0, 0.0, 0.0])
    v_m = np.array([100.0, 0.0, 0.0])
    r_t = np.array([1000.0, 200.0, 0.0])
    v_t = np.array([0.0, 0.0, 0.0])
    a = pn_acceleration(r_m, v_m, r_t, v_t)
    assert np.linalg.norm(a) > 0.0


def test_pn_respects_g_limit():
    r_m = np.array([0.0, 0.0, 0.0])
    v_m = np.array([1000.0, 0.0, 0.0])
    r_t = np.array([500.0, 500.0, 0.0])
    v_t = np.array([-300.0, 300.0, 0.0])
    a = pn_acceleration(r_m, v_m, r_t, v_t, nav_constant=6.0, max_lateral_g=20.0)
    assert np.linalg.norm(a) <= 20.0 * 9.80665 + 1e-6


def test_engagement_default_intercepts():
    resp = client.post("/api/engagement/simulate", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["intercepted"] is True
    assert data["summary"]["miss_distance"] < 5.0
    assert len(data["time"]) == len(data["separation"])


def test_engagement_miss_when_target_receding():
    # Target already overhead and accelerating away faster than the
    # interceptor can ever close: no intercept possible.
    payload = {
        "target": {
            "position": [2000.0, 0.0, 25000.0],
            "velocity": [2500.0, 0.0, 1500.0],
        }
    }
    data = client.post("/api/engagement/simulate", json=payload).json()
    assert data["summary"]["intercepted"] is False
    assert data["summary"]["miss_distance"] > 5.0


# --- seeker measurement noise --------------------------------------------- #
def test_seeker_measurement_no_noise_is_exact():
    rng = np.random.default_rng(0)
    r_m = np.array([0.0, 0.0, 0.0])
    r_t = np.array([1000.0, 0.0, 500.0])
    meas = seeker_measurement(r_m, r_t, rng, 0.0, 0.0)
    assert np.allclose(meas, r_t)


def test_seeker_angular_noise_offsets_perpendicular_to_los():
    rng = np.random.default_rng(1)
    r_m = np.array([0.0, 0.0, 0.0])
    r_t = np.array([1000.0, 0.0, 0.0])
    # large boresight noise -> measurement wanders off-axis, range ~preserved
    offsets = []
    for _ in range(200):
        m = seeker_measurement(r_m, r_t, rng, angular_sigma_rad=0.05)
        offsets.append(m)
    offsets = np.array(offsets)
    # range to target roughly preserved (angular noise only)
    ranges = np.linalg.norm(offsets, axis=1)
    assert abs(ranges.mean() - 1000.0) < 5.0
    # lateral spread (y/z) is non-trivial
    assert offsets[:, 1].std() > 10.0 or offsets[:, 2].std() > 10.0


def test_engagement_target_measured_equals_truth_without_noise():
    data = client.post("/api/engagement/simulate", json={}).json()
    assert data["target_measured"] == data["target_position"]


def test_seeker_noise_degrades_miss_distance():
    # A clean intercept becomes worse (on average) under heavy seeker noise.
    clean = client.post("/api/engagement/simulate", json={}).json()
    assert clean["summary"]["miss_distance"] < 5.0

    misses = []
    for seed in range(6):
        payload = {
            "interceptor": {
                "seeker_angular_noise": 30.0,  # mrad, very noisy
                "seeker_range_noise": 0.1,
                "seeker_update_rate": 20.0,
            },
            "seed": seed,
        }
        d = client.post("/api/engagement/simulate", json=payload).json()
        misses.append(d["summary"]["miss_distance"])
        # the measured track should differ from the true track under noise
        assert d["target_measured"] != d["target_position"]
    assert max(misses) > clean["summary"]["miss_distance"]
