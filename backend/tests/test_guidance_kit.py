"""Tests for the guidance & sensors kit exporter (sim -> guidance software)."""

from fastapi.testclient import TestClient

from backend.export.guidance_kit import pn_reference_c, sensor_spec
from backend.main import app
from backend.sim.models import InterceptorModel

client = TestClient(app)


def test_spec_reads_guidance_and_imu_from_config():
    spec = sensor_spec(InterceptorModel(nav_constant=4.5, max_lateral_g=50))
    assert spec["navigation_constant_N"] == 4.5
    assert spec["command_acceleration_limit_g"] == 50
    # accelerometer must have headroom over the command limit
    assert spec["imu"]["accelerometer_full_scale_g"] > 50


def test_continuous_seeker_gets_a_sane_default_loop_rate():
    spec = sensor_spec(InterceptorModel(seeker_update_rate=0))
    assert spec["guidance_loop_rate_hz"] == 100.0
    spec2 = sensor_spec(InterceptorModel(seeker_update_rate=40))
    assert spec2["guidance_loop_rate_hz"] == 40


def test_range_noise_budget_rules_out_angle_only_seeker():
    spec = sensor_spec(InterceptorModel(seeker_range_noise=0.05))
    ir = next(c for c in spec["seeker"]["candidate_technologies"]
              if c["id"] == "ir_imaging")
    assert ir["suitable"] is False
    rf = next(c for c in spec["seeker"]["candidate_technologies"]
              if c["id"] == "active_rf")
    assert rf["suitable"] is True


def test_c_reference_embeds_nav_constant_and_limit():
    c = pn_reference_c(InterceptorModel(nav_constant=3.5, max_lateral_g=40))
    assert "void pn_command" in c
    assert "3.500f" in c  # NAV_CONSTANT
    assert "392" in c     # 40 g * 9.80665 ~ 392 m/s^2 accel limit
    # plain PN has no gravity-compensation line
    assert "a_cmd[2] += 9.80665f" not in c


def test_c_reference_adds_gravity_term_for_pn_gravity():
    c = pn_reference_c(InterceptorModel(guidance_law="PN_GRAVITY"))
    assert "a_cmd[2] += 9.80665f" in c


def test_export_endpoints_serve_downloads():
    r = client.post("/api/export/guidance/sensors.md", json={})
    assert r.status_code == 200
    assert "guidance_sensors.md" in r.headers["content-disposition"]
    assert "Guidance & Sensors Kit" in r.text

    r = client.post("/api/export/guidance/pn_reference.c", json={})
    assert r.status_code == 200
    assert "pn_guidance.c" in r.headers["content-disposition"]

    r = client.post("/api/export/guidance/spec.json", json={})
    assert r.json()["navigation_constant_N"] == 4.0
