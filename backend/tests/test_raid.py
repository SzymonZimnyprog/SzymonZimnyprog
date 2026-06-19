"""Tests for the many-on-many raid endpoint."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_raid_defends_default_three_threat_raid():
    data = client.post("/api/engagement/raid", json={}).json()
    assert data["threats"] == 3
    assert data["killed"] + data["leakers"] == data["threats"]
    assert data["interceptors_fired"] == 3  # one per threat by default
    assert len(data["targets"]) == 3
    assert len(data["interceptors"]) == 3
    assert data["duration"] > 0.0


def test_raid_assigns_multiple_interceptors_per_threat():
    data = client.post(
        "/api/engagement/raid",
        json={"interceptors_per_threat": 2,
              "threats": [{"position": [16000.0, 0.0, 8000.0],
                           "velocity": [-300.0, 0.0, -30.0]}]},
    ).json()
    assert data["threats"] == 1
    assert data["interceptors_fired"] == 2
    assert all(it["target_index"] == 0 for it in data["interceptors"])


def test_raid_tracks_share_one_absolute_timeline_for_animation():
    data = client.post("/api/engagement/raid", json={}).json()
    for tg in data["targets"]:
        t = tg["track"]["t"]
        assert len(t) >= 2 and t == sorted(t) and t[-1] <= data["duration"] + 1e-6
        if tg["intercepted"]:
            assert tg["intercept_point"] is not None
    for it in data["interceptors"]:
        t = it["track"]["t"]
        assert len(t) >= 2 and t == sorted(t)


def test_raid_reports_leaker_when_threat_unreachable():
    # A hypersonic threat far outside the interceptor envelope should leak.
    data = client.post(
        "/api/engagement/raid",
        json={"threats": [{"position": [120000.0, 0.0, 30000.0],
                           "velocity": [-1500.0, 0.0, 0.0]}],
              "max_time": 40.0},
    ).json()
    assert data["leakers"] == 1
    assert data["killed"] == 0
    assert data["interceptors_per_kill"] is None
