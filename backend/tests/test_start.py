"""Tests for the plain-language Start-page helpers."""

from backend.webui.start_page import _build_request, _compass


def test_compass_cardinals():
    assert _compass(0) == "N"
    assert _compass(90) == "E"
    assert _compass(180) == "S"
    assert _compass(270) == "W"


def test_build_request_places_inbound_target():
    sc = {"distance_km": 10.0, "altitude_km": 5.0, "speed": 300.0,
          "evasive": True, "power": "Large"}
    req = _build_request(sc)
    pos = req.target.position
    vel = req.target.velocity
    assert pos[0] == 10000.0 and pos[2] == 5000.0
    # velocity points back toward the launch site (negative x and z)
    assert vel[0] < 0 and vel[2] < 0
    # evasive -> non-zero manoeuvre; Large -> 7 grain segments
    assert req.target.maneuver_accel[2] != 0.0
    assert req.interceptor.motor.grain.segments == 7
