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


def _ramp(n):
    return {"label": "p", "x": list(range(n)), "y": list(range(n)),
            "z": list(range(n))}


def test_animated_path3d_has_frames_and_controls():
    series = [_ramp(50)]
    fig = common.animated_path3d_fig(series, times=[i * 0.1 for i in range(50)],
                                     frames=30)
    j = fig.to_plotly_json()
    assert len(j["frames"]) == 30
    # play/pause buttons present
    labels = [b["label"] for b in j["layout"]["updatemenus"][0]["buttons"]]
    assert any("Play" in lbl for lbl in labels)
    assert any("Pause" in lbl for lbl in labels)
    # time slider present, labelled in seconds
    steps = j["layout"]["sliders"][0]["steps"]
    assert len(steps) == 30
    assert steps[0]["label"] == "0.0"


def test_animated_path3d_first_frame_is_short_last_is_full():
    series = [_ramp(40)]
    fig = common.animated_path3d_fig(series, frames=20)
    frames = fig.to_plotly_json()["frames"]
    # trail trace (index 0) grows from ~1 point to the full path
    first_trail = frames[0]["data"][0]["x"]
    last_trail = frames[-1]["data"][0]["x"]
    assert len(first_trail) == 1
    assert len(last_trail) == 40


def test_animated_path3d_degenerate_falls_back_to_static():
    # a single sample can't animate; should return a static figure (no frames)
    fig = common.animated_path3d_fig([_ramp(1)])
    assert not fig.to_plotly_json().get("frames")


def _salvo_track(t0, t1, n=10):
    ts = [t0 + (t1 - t0) * k / (n - 1) for k in range(n)]
    return {"t": ts, "x": list(ts), "y": [0.0] * n, "z": list(ts)}


def test_animated_salvo_fig_animates_shots_on_a_common_timeline():
    data = {
        "duration": 8.0,
        "target_track": _salvo_track(0.0, 8.0, 20),
        "shots": [
            {"index": 0, "intercepted": False, "miss_distance": 40.0,
             "intercept_point": None, "track": _salvo_track(0.0, 7.0)},
            {"index": 1, "intercepted": True, "miss_distance": 2.0,
             "intercept_point": [5.0, 0.0, 5.0], "track": _salvo_track(2.0, 8.0)},
        ],
    }
    fig = common.animated_salvo_fig(data, frames=20)
    j = fig.to_plotly_json()
    assert j["frames"]
    # one animated trail+head pair per series (target + 2 shots = 3 series)
    assert len(j["frames"][0]["data"]) == 6
    # the staggered second shot sits on the pad until t=2 (interp clamps),
    # so its first samples don't move
    head_x = [fr["data"][5]["x"][0] for fr in j["frames"]]
    assert head_x[0] == head_x[1]  # still on the pad early on
    assert head_x[-1] > head_x[0]  # has flown by the end
    # the intercept point is marked
    assert any(t.get("text") for t in j["data"])


def test_animated_salvo_fig_empty_without_tracks():
    assert not common.animated_salvo_fig({}).to_plotly_json().get("frames")


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
