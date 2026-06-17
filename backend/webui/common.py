"""Shared helpers, theming and Plotly figure builders for the NiceGUI web UI.

The UI reuses the FastAPI router functions and the pure-Python simulation core
directly (same process) — there is no duplicated request-handling logic. Heavy
simulations are pushed off the event loop with ``run.io_bound`` so the UI stays
responsive. Every input carries a hover tooltip explaining how to choose it
(see :mod:`backend.webui.help_text`).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import plotly.graph_objects as go
from fastapi import Response
from nicegui import ui

# Brand palette (indigo-forward, colour-blind-friendly accents).
PALETTE = {
    "indigo": "#6366f1",
    "green": "#10b981",
    "amber": "#f59e0b",
    "red": "#ef4444",
    "sky": "#0ea5e9",
    "violet": "#8b5cf6",
    "slate": "#64748b",
}

NAV = [
    ("/", "Interception", "gps_fixed"),
    ("/motor", "Motor", "local_fire_department"),
    ("/stack", "Multi-stage", "layers"),
    ("/trajectory", "Trajectory", "show_chart"),
    ("/studio", "Studio", "tune"),
    ("/items", "Items", "list"),
]

_PLOT_CONFIG = {"displaylogo": False, "responsive": True}


def apply_theme() -> None:
    """Set brand colours, fonts and a little global CSS. Call once per page."""
    ui.colors(
        primary=PALETTE["indigo"],
        secondary=PALETTE["sky"],
        accent=PALETTE["violet"],
        positive=PALETTE["green"],
        negative=PALETTE["red"],
        warning=PALETTE["amber"],
    )
    font = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Inter:wght@400;500;600;700&display=swap">'
    )
    ui.add_head_html(
        font
        + """
        <style>
          body { font-family: 'Inter', system-ui, sans-serif; }
          .sim-card { border: 1px solid rgba(99,102,241,.12);
                      box-shadow: 0 1px 3px rgba(15,23,42,.06); border-radius: 14px; }
          .sim-stat { transition: transform .12s ease; }
          .sim-stat:hover { transform: translateY(-2px); }
          .q-field--outlined .q-field__control { border-radius: 10px; }
          .nicegui-content { padding: 0; }
        </style>
        """
    )


def header(active: str) -> None:
    """Shared top navigation bar; ``active`` is the current route path."""
    apply_theme()
    dark = ui.dark_mode()
    with ui.header(elevated=True).classes(
        "items-center justify-between px-4 py-2"
    ).style("background: linear-gradient(90deg,#312e81,#4f46e5);"):
        with ui.row().classes("items-center gap-2 no-wrap"):
            ui.icon("rocket_launch").classes("text-2xl")
            ui.label("Interceptor & Solid-Motor Simulator").classes(
                "text-lg font-semibold"
            )
        with ui.row().classes("items-center gap-1 no-wrap"):
            for path, label, icon in NAV:
                is_active = path == active
                btn = ui.button(
                    label, icon=icon, on_click=lambda p=path: ui.navigate.to(p)
                )
                # Active = outlined (visible white text + border on the gradient);
                # inactive = flat. Both keep white text.
                style = "outline" if is_active else "flat"
                btn.props(f"{style} no-caps dense color=white").classes("rounded-lg")
                if is_active:
                    btn.classes("font-bold bg-white/10")
            ui.button(icon="dark_mode", on_click=dark.toggle).props(
                "flat round dense color=white"
            ).tooltip("Toggle dark mode")


def page_body():
    """A centred, max-width column that holds a page's content."""
    return ui.column().classes("w-full max-w-[1500px] mx-auto p-4 gap-3")


def page_intro(title: str, subtitle: str) -> None:
    ui.label(title).classes("text-2xl font-bold")
    with ui.row().classes("items-start gap-2 max-w-4xl"):
        ui.icon("info").classes("text-primary mt-1")
        ui.label(
            subtitle + "  Hover any field for guidance on how to choose it."
        ).classes("text-sm text-slate-500")


def card(title: str = "", icon: str = ""):
    """A styled card; optionally with a titled header row."""
    c = ui.card().classes("sim-card w-full p-4 gap-2")
    if title:
        with c:
            with ui.row().classes("items-center gap-2"):
                if icon:
                    ui.icon(icon).classes("text-primary")
                ui.label(title).classes("font-semibold text-base")
    return c


def num(
    target: dict,
    key: str,
    label: str,
    *,
    unit: str = "",
    help: str = "",
    **kwargs: Any,
) -> ui.number:
    """A two-way-bound numeric input over a dict entry, with a guidance tooltip."""
    text = f"{label} ({unit})" if unit else label
    field = ui.number(label=text, value=target[key], **kwargs)
    field.props("outlined dense").classes("w-full")
    field.bind_value(target, key)
    if help:
        field.tooltip(help)
    return field


def select_field(
    target: dict, key: str, label: str, options: list[str], *, help: str = ""
) -> ui.select:
    sel = ui.select(options, value=target[key], label=label)
    sel.props("outlined dense").classes("w-full")
    sel.bind_value(target, key)
    if help:
        sel.tooltip(help)
    return sel


def stat(label: str, value: str, *, color: str = "") -> None:
    with ui.card().classes("sim-stat sim-card p-3 items-center min-w-28"):
        cls = "text-xl font-bold" + (f" text-[{color}]" if color else "")
        ui.label(value).classes(cls)
        ui.label(label).classes("text-xs text-slate-500 text-center")


def stats_row(items: Sequence[tuple[str, str]]) -> None:
    with ui.row().classes("flex-wrap gap-2"):
        for label, value in items:
            stat(label, value)


def _layout(fig: go.Figure, xlabel: str, ylabel: str, height: int) -> None:
    fig.update_layout(
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        template="plotly_white",
        height=height,
        margin=dict(l=60, r=20, t=20, b=45),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
        hovermode="x unified",
        font=dict(family="Inter, sans-serif"),
    )


def line_fig(
    xlabel: str, ylabel: str, series: list[dict], *, height: int = 320
) -> go.Figure:
    """Build a Plotly line figure from ``{label, color, x, y}`` series."""
    fig = go.Figure()
    for s in series:
        fig.add_trace(
            go.Scatter(
                x=s["x"], y=s["y"], mode="lines", name=s["label"],
                line=dict(color=s.get("color", PALETTE["indigo"]), width=2.5),
            )
        )
    _layout(fig, xlabel, ylabel, height)
    return fig


def xy_fig(
    xlabel: str,
    ylabel: str,
    series: list[dict],
    markers: list[dict] | None = None,
    *,
    height: int = 380,
    equal_aspect: bool = False,
) -> go.Figure:
    """Plot one or more X/Y paths with optional annotated markers."""
    fig = go.Figure()
    for s in series:
        fig.add_trace(
            go.Scatter(
                x=s["x"], y=s["y"], mode="lines", name=s["label"],
                line=dict(color=s.get("color", PALETTE["indigo"]), width=2.5),
            )
        )
    for m in markers or []:
        fig.add_trace(
            go.Scatter(
                x=[m["x"]], y=[m["y"]], mode="markers+text", text=[m["label"]],
                textposition="top center",
                marker=dict(color=m.get("color", PALETTE["red"]), size=11, symbol="x"),
                showlegend=False,
            )
        )
    _layout(fig, xlabel, ylabel, height)
    fig.update_layout(hovermode="closest")
    if equal_aspect:
        fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def path3d_fig(
    series: list[dict],
    markers: list[dict] | None = None,
    *,
    height: int = 480,
) -> go.Figure:
    """Interactive 3D trajectory plot. Series carry x (E), y (N), z (Up)."""
    fig = go.Figure()
    for s in series:
        fig.add_trace(
            go.Scatter3d(
                x=s["x"], y=s["y"], z=s["z"], mode="lines", name=s["label"],
                line=dict(color=s.get("color", PALETTE["indigo"]), width=5),
            )
        )
        # mark the start point of each path
        if s["x"]:
            fig.add_trace(
                go.Scatter3d(
                    x=[s["x"][0]], y=[s["y"][0]], z=[s["z"][0]], mode="markers",
                    marker=dict(size=4, color=s.get("color", PALETTE["indigo"])),
                    showlegend=False,
                )
            )
    for m in markers or []:
        fig.add_trace(
            go.Scatter3d(
                x=[m["x"]], y=[m["y"]], z=[m["z"]], mode="markers+text",
                text=[m["label"]], textposition="top center",
                marker=dict(size=6, color=m.get("color", PALETTE["red"]), symbol="x"),
                showlegend=False,
            )
        )
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
        scene=dict(
            xaxis_title="East (m)",
            yaxis_title="North (m)",
            zaxis_title="Up (m)",
            aspectmode="data",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
        font=dict(family="Inter, sans-serif"),
    )
    return fig


def _axis_range(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    pad = (hi - lo) * 0.05 or 1.0
    return [lo - pad, hi + pad]


def _resample(seq: list[float], idxs: list[int]) -> list[float]:
    return [seq[i] for i in idxs]


def animated_path3d_fig(
    series: list[dict],
    times: list[float] | None = None,
    *,
    markers: list[dict] | None = None,
    frames: int = 90,
    max_samples: int = 200,
    height: int = 560,
) -> go.Figure:
    """An animated, replayable 3D trajectory.

    Each series (``{label, color, x, y, z}``) is drawn as a growing trail with a
    moving head marker; a Play/Pause control and a time slider scrub through the
    flight. ``markers`` (e.g. the intercept point or stage separations) are shown
    statically throughout. Axis ranges are fixed so the scene doesn't jump.
    """
    n_full = max((len(s["x"]) for s in series), default=0)
    if n_full < 2:
        return path3d_fig(series, markers=markers, height=height)

    # Downsample each path to keep the animation light, preserving endpoints.
    def ds_indices(n: int) -> list[int]:
        if n <= max_samples:
            return list(range(n))
        return sorted(
            {round(i * (n - 1) / (max_samples - 1)) for i in range(max_samples)}
        )

    ds = []
    for s in series:
        idxs = ds_indices(len(s["x"]))
        ds.append(
            {
                "label": s["label"],
                "color": s.get("color", PALETTE["indigo"]),
                "x": _resample(s["x"], idxs),
                "y": _resample(s["y"], idxs),
                "z": _resample(s["z"], idxs),
            }
        )

    n_anim = max(len(s["x"]) for s in ds)
    n_frames = min(frames, n_anim)
    fracs = [k / (n_frames - 1) for k in range(n_frames)]

    def head(s: dict, f: float) -> int:
        return int(round(f * (len(s["x"]) - 1)))

    def traces_at(f: float) -> list[go.Scatter3d]:
        # The animated traces: a bold growing trail + a large moving head per path.
        data = []
        for s in ds:
            j = head(s, f)
            data.append(
                go.Scatter3d(
                    x=s["x"][: j + 1], y=s["y"][: j + 1], z=s["z"][: j + 1],
                    mode="lines", name=s["label"],
                    line=dict(color=s["color"], width=7),
                )
            )
            data.append(
                go.Scatter3d(
                    x=[s["x"][j]], y=[s["y"][j]], z=[s["z"][j]],
                    mode="markers", showlegend=False,
                    marker=dict(size=9, color=s["color"],
                                line=dict(color="white", width=1)),
                )
            )
        return data

    fig = go.Figure(
        data=traces_at(0.0),
        frames=[
            go.Frame(data=traces_at(f), name=str(k)) for k, f in enumerate(fracs)
        ],
    )

    # Static traces drawn AFTER the animated ones (frames only update indices
    # 0..2N-1, so these stay put): a faint full-path reference per series, then
    # the annotation markers (intercept point, stage separations).
    for s in ds:
        fig.add_trace(
            go.Scatter3d(
                x=s["x"], y=s["y"], z=s["z"], mode="lines", opacity=0.2,
                line=dict(color=s["color"], width=2), showlegend=False,
                hoverinfo="skip",
            )
        )
    for m in markers or []:
        fig.add_trace(
            go.Scatter3d(
                x=[m["x"]], y=[m["y"]], z=[m["z"]], mode="markers+text",
                text=[m["label"]], textposition="top center", showlegend=False,
                marker=dict(size=8, color=m.get("color", PALETTE["red"]), symbol="x"),
            )
        )

    # Slider labels in real seconds when a time base is supplied.
    if times:
        labels = [f"{times[int(round(f * (len(times) - 1)))]:.1f}" for f in fracs]
    else:
        labels = [str(k) for k in range(n_frames)]

    allx = [v for s in ds for v in s["x"]]
    ally = [v for s in ds for v in s["y"]]
    allz = [v for s in ds for v in s["z"]]

    play_args = [None, {"frame": {"duration": 60, "redraw": True},
                        "fromcurrent": True, "transition": {"duration": 0}}]
    pause_args = [[None], {"frame": {"duration": 0, "redraw": False},
                           "mode": "immediate", "transition": {"duration": 0}}]

    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Inter, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
        scene=dict(
            xaxis=dict(title="East (m)", range=_axis_range(allx)),
            yaxis=dict(title="North (m)", range=_axis_range(ally)),
            zaxis=dict(title="Up (m)", range=_axis_range(allz)),
            # A filled cube (not "data") so a near-planar engagement still spreads
            # across the box instead of collapsing to an edge-on sliver.
            aspectmode="cube",
            camera=dict(eye=dict(x=1.6, y=1.5, z=0.9)),
        ),
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                showactive=False,
                x=0.0,
                y=0.0,
                xanchor="left",
                yanchor="top",
                pad=dict(t=2, r=8),
                buttons=[
                    dict(label="▶ Play", method="animate", args=play_args),
                    dict(label="⏸ Pause", method="animate", args=pause_args),
                ],
            )
        ],
        sliders=[
            dict(
                active=0,
                x=0.12,
                len=0.88,
                y=0.0,
                yanchor="top",
                pad=dict(t=2),
                currentvalue=dict(prefix="t = ", suffix=" s", visible=True),
                steps=[
                    dict(
                        method="animate",
                        label=labels[k],
                        args=[[str(k)], {"frame": {"duration": 0, "redraw": True},
                                         "mode": "immediate",
                                         "transition": {"duration": 0}}],
                    )
                    for k in range(n_frames)
                ],
            )
        ],
    )
    return fig


def stability_fig(res: dict, *, height: int = 220) -> go.Figure:
    """Horizontal schematic of the airframe with CP and CG marked."""
    total = res["body_length_total"]
    d = res["diameter"]
    fig = go.Figure()
    # body as a rounded bar centred on y=0
    fig.add_shape(type="rect", x0=0, x1=total, y0=-d / 2, y1=d / 2,
                  fillcolor="rgba(99,102,241,0.10)", line=dict(color=PALETTE["indigo"]))
    pts = [
        ("CP", res["x_cp"], PALETTE["indigo"], "triangle-down", "top center"),
        ("CG loaded", res["x_cg_loaded"], PALETTE["green"], "circle", "top center"),
        ("CG empty", res["x_cg_empty"], PALETTE["amber"], "circle-open",
         "bottom center"),
    ]
    for label, x, color, symbol, textpos in pts:
        fig.add_trace(
            go.Scatter(
                x=[x], y=[0], mode="markers+text", name=label, text=[label],
                textposition=textpos,
                marker=dict(size=14, color=color, symbol=symbol,
                            line=dict(color="white", width=1)),
            )
        )
    fig.update_layout(
        template="plotly_white", height=height,
        margin=dict(l=10, r=10, t=10, b=30), showlegend=False,
        xaxis_title="Position from nose tip (m)",
        yaxis=dict(visible=False, range=[-total * 0.12, total * 0.18]),
        font=dict(family="Inter, sans-serif"),
    )
    return fig


def bar_fig(
    xlabel: str, ylabel: str, x: list, y: list, *, height: int = 320
) -> go.Figure:
    fig = go.Figure(go.Bar(x=x, y=y, marker_color=PALETTE["sky"]))
    fig.update_layout(
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        template="plotly_white",
        height=height,
        margin=dict(l=60, r=20, t=20, b=45),
        font=dict(family="Inter, sans-serif"),
    )
    return fig


def heatmap_fig(
    values_x: list,
    values_y: list,
    z: list[list[float]],
    xlabel: str,
    ylabel: str,
    metric: str,
    *,
    height: int = 420,
    colorscale: str = "Viridis",
    reversescale: bool = False,
) -> go.Figure:
    fig = go.Figure(
        go.Heatmap(
            x=values_x, y=values_y, z=z, colorscale=colorscale,
            reversescale=reversescale, colorbar=dict(title=metric),
        )
    )
    fig.update_layout(
        xaxis_title=xlabel, yaxis_title=ylabel, template="plotly_white",
        height=height, margin=dict(l=70, r=20, t=20, b=50),
        font=dict(family="Inter, sans-serif"),
    )
    return fig


def tornado_fig(
    rows: list[dict], baseline: float, metric: str, *, height: int = 320
) -> go.Figure:
    """Horizontal tornado: each parameter's metric swing about the baseline."""
    rows = list(reversed(rows))  # largest swing on top
    params = [r["parameter"] for r in rows]
    lows = [r["low"] - baseline for r in rows]
    highs = [r["high"] - baseline for r in rows]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=params, x=lows, orientation="h", name="−Δ param",
                         marker_color=PALETTE["sky"]))
    fig.add_trace(go.Bar(y=params, x=highs, orientation="h", name="+Δ param",
                         marker_color=PALETTE["amber"]))
    fig.update_layout(
        barmode="overlay", template="plotly_white", height=height,
        xaxis_title=f"Δ {metric} from baseline", margin=dict(l=160, r=20, t=20, b=45),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
        font=dict(family="Inter, sans-serif"),
    )
    return fig


def plot(fig: go.Figure) -> ui.plotly:
    """Render a Plotly figure full-width with a clean toolbar."""
    fig.update_layout(modebar=dict(orientation="v"))
    element = ui.plotly(fig).classes("w-full sim-card")
    return element


def offer_download(response: Response, filename: str) -> None:
    """Trigger a browser download from a FastAPI export ``Response``."""
    ui.download.content(response.body, filename)
    ui.notify(f"Downloaded {filename}", type="positive")


def warnings_panel(warnings: list[str]) -> None:
    if not warnings:
        return
    with ui.card().classes("bg-amber-50 border border-amber-300 w-full rounded-xl"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("warning").classes("text-amber-600")
            ui.label("Design warnings").classes("font-semibold text-amber-700")
        for w in warnings:
            ui.label(f"• {w}").classes("text-sm text-amber-800")
