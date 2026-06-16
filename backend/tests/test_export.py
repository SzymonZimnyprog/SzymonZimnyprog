"""Tests for the CAD (STL/OpenSCAD) and Simulink/MATLAB export endpoints."""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_grain_stl_is_valid_ascii_stl():
    resp = client.post("/api/export/cad/grain.stl", json={})
    assert resp.status_code == 200
    body = resp.text
    assert body.startswith("solid")
    assert "endsolid" in body
    assert "facet normal" in body
    assert "attachment" in resp.headers["content-disposition"]


def test_nozzle_and_airframe_stl():
    assert client.post("/api/export/cad/nozzle.stl", json={}).text.startswith("solid")
    assert client.post("/api/export/cad/airframe.stl", json={}).text.startswith("solid")


def test_openscad_is_parametric():
    resp = client.post("/api/export/cad/grain.scad", json={})
    assert resp.status_code == 200
    assert "outer_diameter" in resp.text
    assert "module grain_segment" in resp.text


def test_thrust_curve_csv_header():
    resp = client.post("/api/export/simulink/thrust_curve.csv", json={})
    assert resp.status_code == 200
    lines = resp.text.strip().splitlines()
    assert lines[0] == "time_s,thrust_N,chamber_pressure_Pa,mass_flow_kgps"
    assert len(lines) > 2


def test_rasp_eng_format():
    resp = client.post("/api/export/simulink/motor.eng", json={})
    assert resp.status_code == 200
    assert "SZ-MOTOR" in resp.text
    assert resp.text.lstrip().startswith(";")


def test_engagement_csv():
    resp = client.post("/api/export/simulink/engagement.csv", json={})
    assert resp.status_code == 200
    assert resp.text.startswith("time_s,int_x")


def test_matlab_driver():
    resp = client.get("/api/export/simulink/driver.m")
    assert resp.status_code == 200
    assert "szymon_sim_driver" in resp.text
    assert "webwrite" in resp.text
