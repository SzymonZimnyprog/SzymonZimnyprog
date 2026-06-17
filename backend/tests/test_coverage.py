"""Tests for the defended-area / engagement-envelope map."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_defended_area_grid_shape_and_some_hits():
    payload = {
        "target_speed": 300.0,
        "downrange_min": 4000.0, "downrange_max": 18000.0, "downrange_steps": 4,
        "altitude_min": 2000.0, "altitude_max": 9000.0, "altitude_steps": 3,
    }
    data = client.post("/api/engagement/defended_area", json=payload).json()
    assert len(data["values_x"]) == 4
    assert len(data["values_y"]) == 3
    assert len(data["miss"]) == 3 and len(data["miss"][0]) == 4
    assert len(data["hit"]) == 3 and len(data["hit"][0]) == 4
    # near-in targets should be reachable -> at least one hit somewhere
    assert data["hit_fraction"] > 0.0
    # miss is capped
    assert all(v <= data["miss_cap"] for row in data["miss"] for v in row)
