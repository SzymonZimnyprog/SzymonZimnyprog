"""Tests for the design-studio optimisation helpers and endpoints."""

import math

from fastapi.testclient import TestClient

from backend.main import app
from backend.sim.optimize import (
    golden_section_maximize,
    golden_section_minimize,
    solve_to_target,
)

client = TestClient(app)


# --- pure numeric helpers ------------------------------------------------- #
def test_golden_section_minimises_parabola():
    x = golden_section_minimize(lambda v: (v - 3.0) ** 2, 0.0, 10.0)
    assert abs(x - 3.0) < 1e-3


def test_golden_section_maximises():
    x = golden_section_maximize(lambda v: -((v + 1.0) ** 2) + 5.0, -5.0, 5.0)
    assert abs(x + 1.0) < 1e-3


def test_solve_to_target_hits_monotonic_root():
    # f(x) = x^2 over [0, 5], target 9 -> x = 3
    x = solve_to_target(lambda v: v * v, 9.0, 0.0, 5.0)
    assert abs(x - 3.0) < 1e-2


def test_solve_to_target_out_of_reach_returns_closest():
    # target below the whole range -> returns the end nearest in value
    x = solve_to_target(lambda v: v + 10.0, 0.0, 0.0, 5.0)
    assert abs(x - 0.0) < 1e-6


def test_solve_to_target_trig_root():
    x = solve_to_target(math.sin, 0.0, 2.0, 4.0)  # root at pi
    assert abs(x - math.pi) < 1e-2


# --- motor design optimiser ----------------------------------------------- #
def test_optimize_throat_for_peak_pressure():
    payload = {
        "parameter": "nozzle.throat_diameter",
        "metric": "peak_pressure",
        "target": 6.0e6,
        "lower": 0.01,
        "upper": 0.04,
    }
    data = client.post("/api/motor/optimize", json=payload).json()
    # achieved peak pressure should be close to the 6 MPa target
    assert abs(data["achieved"] - 6.0e6) / 6.0e6 < 0.1
    assert 0.01 <= data["value"] <= 0.04


def test_optimize_rejects_bad_bounds():
    payload = {"parameter": "nozzle.throat_diameter", "metric": "peak_pressure",
               "target": 6.0e6, "lower": 0.04, "upper": 0.01}
    assert client.post("/api/motor/optimize", json=payload).status_code == 400


# --- 2-D sweep / heatmap --------------------------------------------------- #
def test_sweep2d_grid_shape():
    payload = {
        "param_x": "nozzle.throat_diameter",
        "param_y": "grain.core_diameter",
        "values_x": [0.015, 0.02, 0.025],
        "values_y": [0.02, 0.03],
        "metric": "total_impulse",
    }
    data = client.post("/api/motor/sweep2d", json=payload).json()
    assert len(data["z"]) == 2          # rows = values_y
    assert len(data["z"][0]) == 3       # cols = values_x
    assert all(v > 0 for row in data["z"] for v in row)


# --- sensitivity / tornado ------------------------------------------------- #
def test_sensitivity_sorted_by_swing():
    resp = client.post("/api/motor/sensitivity", json={"metric": "total_impulse"})
    data = resp.json()
    swings = [r["swing"] for r in data["rows"]]
    assert swings == sorted(swings, reverse=True)
    assert data["baseline"] > 0


# --- trajectory launch optimiser ------------------------------------------ #
def test_optimize_launch_apogee_prefers_steep():
    data = client.post("/api/missile/optimize_launch",
                       json={"objective": "apogee"}).json()
    # max-altitude launch should be fairly steep
    assert data["elevation_deg"] > 70.0
    assert data["objective_value"] > 0.0


def test_optimize_launch_range_is_flatter_than_apogee():
    apo = client.post("/api/missile/optimize_launch",
                      json={"objective": "apogee"}).json()
    rng = client.post("/api/missile/optimize_launch",
                      json={"objective": "range"}).json()
    assert rng["elevation_deg"] < apo["elevation_deg"]
