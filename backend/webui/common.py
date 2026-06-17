"""Shared helpers for the NiceGUI web UI.

The UI reuses the FastAPI router functions and the pure-Python simulation core
directly (same process) — there is no duplicated request-handling logic. Heavy
simulations are pushed off the event loop with ``run.io_bound`` so the UI stays
responsive.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import plotly.graph_objects as go
from fastapi import Response
from nicegui import ui

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
    ("/", "Interception"),
    ("/motor", "Motor"),
    ("/stack", "Multi-stage"),
    ("/trajectory", "Trajectory"),
    ("/items", "Items"),
]


def header(active: str) -> None:
    """Shared top navigation bar; ``active`` is the current route path."""
    with ui.header().classes("items-center justify-between bg-slate-800"):
        ui.label("Interceptor & Solid-Motor Simulator").classes(
            "text-lg font-semibold"
        )
        with ui.row().classes("gap-1"):
            for path, label in NAV:
                btn = ui.button(label, on_click=lambda p=path: ui.navigate.to(p))
                flat = "" if path == active else "flat "
                btn.props(f"{flat}dense color=white")


def page_intro(title: str, subtitle: str) -> None:
    ui.label(title).classes("text-2xl font-bold mt-2")
    ui.label(subtitle).classes("text-sm text-slate-500 mb-2 max-w-3xl")


def num(
    target: dict, key: str, label: str, *, unit: str = "", **kwargs: Any
) -> ui.number:
    """A two-way-bound numeric input over a dict entry."""
    text = f"{label} ({unit})" if unit else label
    field = ui.number(label=text, value=target[key], **kwargs).classes("w-full")
    field.bind_value(target, key)
    return field


def stat(label: str, value: str) -> None:
    with ui.card().classes("p-3 items-center min-w-28"):
        ui.label(value).classes("text-lg font-semibold")
        ui.label(label).classes("text-xs text-slate-500")


def stats_row(items: Sequence[tuple[str, str]]) -> None:
    with ui.row().classes("flex-wrap gap-2"):
        for label, value in items:
            stat(label, value)


def line_fig(
    xlabel: str,
    ylabel: str,
    series: list[dict],
    *,
    height: int = 340,
) -> go.Figure:
    """Build a Plotly line figure from ``{label, color, x, y}`` series."""
    fig = go.Figure()
    for s in series:
        fig.add_trace(
            go.Scatter(
                x=s["x"],
                y=s["y"],
                mode="lines",
                name=s["label"],
                line=dict(color=s.get("color", PALETTE["indigo"]), width=2),
            )
        )
    fig.update_layout(
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        template="plotly_white",
        height=height,
        margin=dict(l=60, r=20, t=20, b=45),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
    )
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
                x=s["x"],
                y=s["y"],
                mode="lines",
                name=s["label"],
                line=dict(color=s.get("color", PALETTE["indigo"]), width=2),
            )
        )
    for m in markers or []:
        fig.add_trace(
            go.Scatter(
                x=[m["x"]],
                y=[m["y"]],
                mode="markers+text",
                text=[m["label"]],
                textposition="top center",
                marker=dict(color=m.get("color", PALETTE["red"]), size=10, symbol="x"),
                showlegend=False,
            )
        )
    fig.update_layout(
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        template="plotly_white",
        height=height,
        margin=dict(l=60, r=20, t=20, b=45),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
    )
    if equal_aspect:
        fig.update_yaxes(scaleanchor="x", scaleratio=1)
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
    )
    return fig


def offer_download(response: Response, filename: str) -> None:
    """Trigger a browser download from a FastAPI export ``Response``."""
    ui.download.content(response.body, filename)
    ui.notify(f"Downloaded {filename}", type="positive")


def warnings_panel(warnings: list[str]) -> None:
    if not warnings:
        return
    with ui.card().classes("bg-amber-50 border border-amber-300 w-full"):
        ui.label("Design warnings").classes("font-semibold text-amber-700")
        for w in warnings:
            ui.label(f"• {w}").classes("text-sm text-amber-800")
