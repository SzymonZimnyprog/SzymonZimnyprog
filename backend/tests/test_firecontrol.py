"""Tests for the fire-control (firing-solution) solver and endpoint."""

import numpy as np
from fastapi.testclient import TestClient

from backend.main import app
from backend.sim.firecontrol import bearing_to_target

client = TestClient(app)


def test_bearing_points_east_and_north():
    launch = np.array([0.0, 0.0, 0.0])
    east = bearing_to_target(launch, np.array([1000.0, 0.0, 0.0]))
    north = bearing_to_target(launch, np.array([0.0, 1000.0, 0.0]))
    assert abs(east - 90.0) < 1e-6
    assert abs(north - 0.0) < 1e-6


def test_solver_finds_intercept_from_bad_initial_guess():
    payload = {
        "interceptor": {"elevation_deg": 10.0, "azimuth_deg": 0.0},
        "target": {
            "position": [18000.0, 0.0, 9000.0],
            "velocity": [-280.0, 0.0, -25.0],
        },
    }
    data = client.post("/api/engagement/solve", json=payload).json()
    assert data["intercepted"] is True
    assert data["miss_distance"] < 5.0
    # azimuth should swing toward the target's easterly bearing (~90 deg)
    assert 80.0 < data["azimuth_deg"] < 100.0
    assert len(data["envelope"]) >= 8
    # the returned engagement carries plottable time histories
    assert len(data["engagement"]["time"]) == len(data["engagement"]["separation"])


def test_solver_reports_miss_for_unreachable_target():
    payload = {
        "interceptor": {"max_lateral_g": 40.0},
        "target": {
            "position": [3000.0, 0.0, 30000.0],
            "velocity": [3000.0, 0.0, 1500.0],
        },
    }
    data = client.post("/api/engagement/solve", json=payload).json()
    assert data["intercepted"] is False
