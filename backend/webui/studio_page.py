"""Design Studio: motor optimiser, 2-D heatmaps, sensitivity, launch optimiser."""

from __future__ import annotations

import math

from nicegui import run, ui

from backend.routers.missile import LaunchOptimizeRequest
from backend.routers.missile import optimize_launch as launch_opt
from backend.routers.motor import (
    MotorOptimizeRequest,
    MotorSweep2DRequest,
    SensitivityRequest,
)
from backend.routers.motor import (
    optimize as motor_optimize,
)
from backend.routers.motor import (
    sensitivity as motor_sensitivity,
)
from backend.routers.motor import (
    sweep2d as motor_sweep2d,
)

from .common import (
    PALETTE,
    card,
    header,
    heatmap_fig,
    line_fig,
    num,
    page_body,
    page_intro,
    plot,
    select_field,
    stats_row,
    tornado_fig,
    xy_fig,
)

PARAMS = [
    "nozzle.throat_diameter",
    "nozzle.expansion_ratio",
    "grain.outer_diameter",
    "grain.core_diameter",
    "grain.segment_length",
    "grain.segments",
    "propellant.n",
    "altitude",
]
METRICS = [
    "total_impulse",
    "peak_pressure",
    "average_thrust",
    "peak_thrust",
    "burn_time",
    "specific_impulse",
]


@ui.page("/studio")
def studio_page() -> None:
    header("/studio")
    with page_body():
        page_intro(
            "Design studio",
            "Close the loop: size a motor to hit a target, map a metric over two "
            "parameters, rank what matters, and find the best launch angle.",
        )
        with ui.row().classes("w-full gap-4 items-start flex-wrap"):
            _optimizer_panel()
            _heatmap_panel()
        with ui.row().classes("w-full gap-4 items-start flex-wrap"):
            _sensitivity_panel()
            _launch_panel()


def _optimizer_panel() -> None:
    st = {"parameter": "nozzle.throat_diameter", "metric": "peak_pressure",
          "target": 6.0e6, "lower": 0.01, "upper": 0.04}
    with card("Motor optimiser", "track_changes").classes("w-[460px]"):
        ui.label(
            "Solve one design variable so a metric meets a target "
            "(e.g. throat → peak chamber pressure)."
        ).classes("text-xs text-slate-500")
        select_field(st, "parameter", "Design variable", PARAMS)
        select_field(st, "metric", "Target metric", METRICS)
        with ui.grid(columns=3).classes("gap-2 w-full"):
            num(st, "target", "Target value", step=1)
            num(st, "lower", "Lower bound", step=0.005)
            num(st, "upper", "Upper bound", step=0.005)
        out = ui.column().classes("w-full gap-2")
        btn = ui.button("Optimise", icon="track_changes").classes("w-full")

        async def runit() -> None:
            btn.props("loading")
            try:
                req = MotorOptimizeRequest.model_validate(st)
                res = await run.io_bound(motor_optimize, req)
            except Exception as exc:  # noqa: BLE001
                ui.notify(str(exc), type="negative", multi_line=True)
                return
            finally:
                btn.props(remove="loading")
            s = res["summary"]
            out.clear()
            with out:
                stats_row([
                    ("Solved value", f"{res['value']:.4g}"),
                    ("Achieved", f"{res['achieved']:.4g}"),
                    ("Target", f"{res['target']:.4g}"),
                    ("Impulse", f"{s['total_impulse']:.0f} N·s"),
                    ("Class", s["impulse_class"]),
                    ("Peak Pc", f"{s['peak_pressure'] / 1e6:.2f} MPa"),
                ])
        btn.on_click(runit)


def _heatmap_panel() -> None:
    st = {"param_x": "nozzle.throat_diameter", "param_y": "grain.core_diameter",
          "metric": "total_impulse",
          "x_min": 0.015, "x_max": 0.03, "x_n": 10,
          "y_min": 0.02, "y_max": 0.05, "y_n": 8}
    with card("2-D sweep heatmap", "grid_on").classes("flex-grow min-w-[460px]"):
        ui.label("Map a metric over a grid of two design parameters.").classes(
            "text-xs text-slate-500"
        )
        select_field(st, "param_x", "X parameter", PARAMS)
        select_field(st, "param_y", "Y parameter", PARAMS)
        select_field(st, "metric", "Metric", METRICS)
        with ui.grid(columns=3).classes("gap-2 w-full"):
            num(st, "x_min", "X min", step=0.005)
            num(st, "x_max", "X max", step=0.005)
            num(st, "x_n", "X steps", step=1, min=2, max=30)
            num(st, "y_min", "Y min", step=0.005)
            num(st, "y_max", "Y max", step=0.005)
            num(st, "y_n", "Y steps", step=1, min=2, max=30)
        out = ui.column().classes("w-full")
        btn = ui.button("Compute heatmap", icon="grid_on").classes("w-full")

        async def runit() -> None:
            btn.props("loading")
            try:
                vx = _linspace(st["x_min"], st["x_max"], int(st["x_n"]))
                vy = _linspace(st["y_min"], st["y_max"], int(st["y_n"]))
                req = MotorSweep2DRequest.model_validate({
                    "param_x": st["param_x"], "param_y": st["param_y"],
                    "metric": st["metric"], "values_x": vx, "values_y": vy,
                })
                res = await run.io_bound(motor_sweep2d, req)
            except Exception as exc:  # noqa: BLE001
                ui.notify(str(exc), type="negative", multi_line=True)
                return
            finally:
                btn.props(remove="loading")
            out.clear()
            with out:
                plot(heatmap_fig(res["values_x"], res["values_y"], res["z"],
                                 res["param_x"], res["param_y"], res["metric"]))
        btn.on_click(runit)


def _sensitivity_panel() -> None:
    st = {"metric": "total_impulse", "delta": 0.1}
    with card("Sensitivity (tornado)", "sort").classes("w-[460px]"):
        ui.label(
            "Which parameters move the metric most, ±delta about the base."
        ).classes("text-xs text-slate-500")
        select_field(st, "metric", "Metric", METRICS)
        num(st, "delta", "Delta (fraction)", step=0.05, min=0.01, max=0.9)
        out = ui.column().classes("w-full")
        btn = ui.button("Rank parameters", icon="sort").classes("w-full")

        async def runit() -> None:
            btn.props("loading")
            try:
                req = SensitivityRequest.model_validate(
                    {"metric": st["metric"], "delta": st["delta"]}
                )
                res = await run.io_bound(motor_sensitivity, req)
            except Exception as exc:  # noqa: BLE001
                ui.notify(str(exc), type="negative", multi_line=True)
                return
            finally:
                btn.props(remove="loading")
            out.clear()
            with out:
                plot(tornado_fig(res["rows"], res["baseline"], res["metric"]))
        btn.on_click(runit)


def _launch_panel() -> None:
    st = {"objective": "apogee"}
    with card("Launch optimiser", "trending_up").classes("flex-grow min-w-[460px]"):
        ui.label(
            "Find the launch elevation that maximises apogee or downrange range "
            "for the default missile."
        ).classes("text-xs text-slate-500")
        select_field(st, "objective", "Objective", ["apogee", "range"])
        out = ui.column().classes("w-full")
        btn = ui.button("Optimise launch", icon="trending_up").classes("w-full")

        async def runit() -> None:
            btn.props("loading")
            try:
                req = LaunchOptimizeRequest(objective=st["objective"])
                res = await run.io_bound(launch_opt, req)
            except Exception as exc:  # noqa: BLE001
                ui.notify(str(exc), type="negative", multi_line=True)
                return
            finally:
                btn.props(remove="loading")
            s = res["summary"]
            pos = res["position"]
            ground = [math.hypot(p[0], p[1]) for p in pos]
            out.clear()
            with out:
                stats_row([
                    ("Best elevation", f"{res['elevation_deg']:.1f}°"),
                    ("Apogee", f"{s['apogee'] / 1000:.2f} km"),
                    ("Range", f"{s['range'] / 1000:.2f} km"),
                    ("Max speed", f"{s['max_speed']:.0f} m/s"),
                ])
                plot(xy_fig("Ground range (m)", "Altitude (m)",
                            [{"label": "Optimal", "color": PALETTE["green"],
                              "x": ground, "y": res["altitude"]}]))
                plot(line_fig("Time (s)", "Speed (m/s)",
                              [{"label": "Speed", "color": PALETTE["green"],
                                "x": res["time"], "y": res["speed"]}]))
        btn.on_click(runit)


def _linspace(lo: float, hi: float, n: int) -> list[float]:
    n = max(2, n)
    return [lo + (hi - lo) * i / (n - 1) for i in range(n)]
