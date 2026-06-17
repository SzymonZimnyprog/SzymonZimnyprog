"""Tests for the nozzle/grain cross-section geometry."""

import math

from backend.sim.geometry import nozzle_profile


def test_exit_radius_follows_area_ratio():
    geo = nozzle_profile(throat_diameter=0.02, expansion_ratio=9.0,
                         chamber_diameter=0.14, grain_length=1.0, core_diameter=0.05)
    # Re = Rt * sqrt(ER); ER=9 -> exit dia = 3x throat dia
    assert math.isclose(geo["exit_diameter"], 0.02 * 3.0, rel_tol=1e-6)
    assert math.isclose(geo["throat_diameter"], 0.02, rel_tol=1e-6)


def test_profile_is_monotonic_along_axis():
    geo = nozzle_profile(0.02, 6.0, 0.14, 0.8, 0.04)
    xs = geo["profile_x"]
    assert xs == sorted(xs)
    assert xs[0] == 0.0
    assert geo["x_exit"] == geo["total_length"]
    # radii: chamber == chamber, then throat (min), then exit (> throat)
    rs = geo["profile_r"]
    assert rs[0] == rs[1] == geo["chamber_radius"]
    assert rs[2] == geo["throat_radius"] <= rs[3]


def test_core_radius_clamped_nonneg():
    geo = nozzle_profile(0.02, 6.0, 0.14, 0.8, 0.0)
    assert geo["core_radius"] == 0.0
