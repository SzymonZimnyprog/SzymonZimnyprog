"""Tests for the salvo (layered-defence) engagement endpoint."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_salvo_runs_each_shot_with_stagger_and_spread():
    payload = {
        "count": 4,
        "stagger": 1.5,
        "elevation_spread": 8.0,
        "auto_aim": False,
        "engagement": {
            "target": {
                "position": [22000.0, 0.0, 11000.0],
                "velocity": [-320.0, 0.0, -30.0],
            }
        },
    }
    data = client.post("/api/engagement/salvo", json=payload).json()
    assert data["count"] == 4
    assert len(data["shots"]) == 4
    # launch times are staggered
    times = [s["launch_time"] for s in data["shots"]]
    assert times == sorted(times)
    assert times[1] - times[0] == 1.5
    # elevations are spread (not all identical)
    elevations = {round(s["elevation_deg"], 3) for s in data["shots"]}
    assert len(elevations) == 4
    assert 0.0 <= data["success_fraction"] <= 1.0


def test_salvo_intercepts_reachable_target():
    # Default target/elevation already intercept; no need for the auto-aim
    # search here (keeps the test fast).
    data = client.post(
        "/api/engagement/salvo", json={"count": 3, "auto_aim": False}
    ).json()
    assert data["intercepted"] is True
    assert data["hits"] >= 1
    assert data["best_miss"] < 5.0


def test_single_shot_salvo_has_no_spread():
    data = client.post(
        "/api/engagement/salvo", json={"count": 1, "auto_aim": False}
    ).json()
    assert data["count"] == 1
    assert len(data["shots"]) == 1
    assert data["shots"][0]["launch_time"] == 0.0
