"""Tests for the Monte-Carlo kill-probability endpoint."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_zero_uncertainty_gives_certain_kill():
    data = client.post("/api/engagement/montecarlo", json={
        "trials": 20, "position_sigma": 0.0, "velocity_sigma": 0.0,
    }).json()
    assert data["trials"] == 20
    assert data["pk"] == 1.0
    assert data["mean_miss"] < 5.0  # default lethal radius


def test_histogram_counts_sum_to_trials():
    data = client.post("/api/engagement/montecarlo", json={
        "trials": 40, "position_sigma": 400.0, "velocity_sigma": 30.0, "seed": 3,
    }).json()
    assert sum(data["histogram_counts"]) == 40
    assert len(data["histogram_edges"]) == len(data["histogram_counts"]) + 1
    assert 0.0 <= data["pk"] <= 1.0
    assert data["p90_miss"] >= data["median_miss"]


def test_large_uncertainty_reduces_pk():
    tight = client.post("/api/engagement/montecarlo", json={
        "trials": 40, "position_sigma": 100.0, "velocity_sigma": 10.0, "seed": 5,
    }).json()
    loose = client.post("/api/engagement/montecarlo", json={
        "trials": 40, "position_sigma": 4000.0, "velocity_sigma": 500.0, "seed": 5,
    }).json()
    assert loose["pk"] <= tight["pk"]
