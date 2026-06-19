"""Tests for the atmospheric wind model and its effect on flight."""

import numpy as np
from fastapi.testclient import TestClient

from backend.main import app
from backend.sim.wind import WindField

client = TestClient(app)


def test_wind_from_bearing_points_opposite():
    # A westerly (from 270°) wind blows toward the east (+E).
    assert np.allclose(WindField(speed=10, from_deg=270).at(100), [10, 0, 0],
                       atol=1e-6)
    # A northerly (from 0°) wind blows toward the south (-N).
    assert np.allclose(WindField(speed=10, from_deg=0).at(100), [0, -10, 0],
                       atol=1e-6)


def test_zero_wind_is_a_noop_at_any_altitude():
    w = WindField()
    assert np.allclose(w.at(0), 0) and np.allclose(w.at(20000), 0)
    assert not w.is_active()


def test_shear_strengthens_wind_with_altitude():
    w = WindField(speed=10, from_deg=270, reference_alt=10, shear=0.143)
    assert np.linalg.norm(w.at(10)) < np.linalg.norm(w.at(1000))
    # clamped so it never runs away at extreme altitude
    assert np.linalg.norm(w.at(1e9)) <= 10 * 10 + 1e-6


def test_crosswind_drifts_a_ballistic_trajectory():
    calm = client.post("/api/missile/simulate", json={}).json()
    windy = client.post(
        "/api/missile/simulate",
        json={"wind": {"speed": 30, "from_deg": 270}},
    ).json()
    # west wind pushes the impact point east (+E) relative to the calm shot
    assert windy["position"][-1][0] > calm["position"][-1][0] + 10.0


def test_no_wind_engagement_matches_default():
    a = client.post("/api/engagement/simulate", json={}).json()
    b = client.post("/api/engagement/simulate",
                    json={"wind": {"speed": 0}}).json()
    assert a["summary"]["miss_distance"] == b["summary"]["miss_distance"]
