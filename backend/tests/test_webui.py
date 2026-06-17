"""Tests for the pure-Python (NiceGUI) web-UI helpers and data transforms.

These cover the custom logic the UI adds on top of the API: figure builders and
the geometry transforms used to plot trajectories and place separation markers.
The simulation/export endpoints the UI calls are covered by the other test
modules; here we check the glue is correct.
"""

from __future__ import annotations

import plotly.graph_objects as go

from backend.webui import common
from backend.webui.engagement_page import _ground
from backend.webui.stack_page import _ground_at


def test_line_fig_has_one_trace_per_series():
    fig = common.line_fig(
        "t",
        "F",
        [
            {"label": "a", "x": [0, 1, 2], "y": [0, 1, 0]},
            {"label": "b", "x": [0, 1, 2], "y": [1, 2, 3]},
        ],
    )
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2
    assert fig.layout.xaxis.title.text == "t"
    assert fig.layout.yaxis.title.text == "F"


def test_xy_fig_markers_add_extra_traces():
    fig = common.xy_fig(
        "x",
        "y",
        [{"label": "path", "x": [0, 1], "y": [0, 1]}],
        markers=[{"x": 0.5, "y": 0.5, "label": "hit"}],
    )
    # one line trace + one marker trace
    assert len(fig.data) == 2
    assert fig.data[1].mode == "markers+text"
    assert fig.data[1].text == ("hit",)


def test_xy_fig_equal_aspect_locks_axes():
    fig = common.xy_fig(
        "x", "y", [{"label": "p", "x": [0, 1], "y": [0, 1]}], equal_aspect=True
    )
    assert fig.layout.yaxis.scaleanchor == "x"


def test_bar_fig_single_bar_trace():
    fig = common.bar_fig("bin", "count", ["0", "1", "2"], [3, 5, 1])
    assert len(fig.data) == 1
    assert tuple(fig.data[0].y) == (3, 5, 1)


def test_ground_at_picks_nearest_sample_time():
    times = [0.0, 1.0, 2.0, 3.0]
    ground = [0.0, 100.0, 250.0, 400.0]
    # closest to t=1.9 is index 2 (t=2.0)
    assert _ground_at(times, ground, 1.9) == 250.0
    # exact endpoints
    assert _ground_at(times, ground, 0.0) == 0.0
    assert _ground_at(times, ground, 3.0) == 400.0


def test_ground_at_empty_is_zero():
    assert _ground_at([], [], 1.0) == 0.0


def test_ground_projection_is_horizontal_distance_from_origin():
    positions = [[0.0, 0.0, 10.0], [3.0, 4.0, 20.0], [6.0, 8.0, 5.0]]
    origin = [0.0, 0.0, 0.0]
    out = _ground(positions, origin)
    assert out == [0.0, 5.0, 10.0]  # hypot(3,4)=5, hypot(6,8)=10


def test_ground_projection_respects_launch_origin_offset():
    positions = [[100.0, 0.0, 0.0], [103.0, 4.0, 0.0]]
    origin = [100.0, 0.0, 0.0]
    out = _ground(positions, origin)
    assert out == [0.0, 5.0]
