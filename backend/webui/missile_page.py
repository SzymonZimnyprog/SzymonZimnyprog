"""Trajectory tab: single un-guided missile flight + airframe CAD export."""

from __future__ import annotations

import math

from nicegui import run, ui

from backend.routers import export as export_router
from backend.routers.export import AirframeCadRequest
from backend.routers.missile import simulate as missile_simulate
from backend.sim.models import MissileRequest

from .common import (
    PALETTE,
    header,
    line_fig,
    num,
    offer_download,
    page_intro,
    stats_row,
    xy_fig,
)
from .motor_page import motor_form


@ui.page("/trajectory")
def trajectory_page() -> None:
    header("/trajectory")
    state = MissileRequest().model_dump(mode="json")
    cad = AirframeCadRequest().model_dump(mode="json")
    result: dict = {}

    page_intro(
        "Missile trajectory",
        "3-DOF point-mass flight (RK4) in an ENU frame: boosted ascent on the "
        "motor, ISA atmosphere, Mach-dependent drag and mass depletion.",
    )

    with ui.row().classes("w-full gap-4 no-wrap items-start"):
        with ui.card().classes("w-96"):
            with ui.expansion("Motor", icon="rocket", value=True).classes("w-full"):
                motor_form(state["motor"])
            ui.label("Airframe").classes("font-semibold mt-2")
            with ui.grid(columns=2).classes("gap-2 w-full"):
                num(state["airframe"], "diameter", "Body dia", unit="m", step=0.01)
                num(state["airframe"], "cd0", "Cd0 (subsonic)", step=0.01)
                num(state["airframe"], "dry_mass", "Dry mass", unit="kg", step=1)
            ui.label("Launch").classes("font-semibold mt-2")
            with ui.grid(columns=2).classes("gap-2 w-full"):
                num(state, "launch_speed", "Rail speed", unit="m/s", step=5)
                num(state, "elevation_deg", "Elevation", unit="°", step=1,
                    min=0, max=90)
                num(state, "azimuth_deg", "Azimuth", unit="°", step=5)
                num(state, "dt", "Time step", unit="s", step=0.01)
            with ui.expansion("Airframe CAD", icon="view_in_ar").classes("w-full"):
                with ui.grid(columns=2).classes("gap-2 w-full"):
                    num(cad, "body_length", "Body length", unit="m", step=0.1)
                    num(cad, "nose_length", "Nose length", unit="m", step=0.1)
                    num(cad, "fin_count", "Fin count", step=1, min=0, max=8)
                    num(cad, "fin_span", "Fin span", unit="m", step=0.01)
                    num(cad, "fin_root", "Fin root chord", unit="m", step=0.01)
            run_btn = ui.button("Fly missile").classes("w-full mt-2")

        results = ui.column().classes("flex-grow gap-3")

    async def run_flight() -> None:
        run_btn.props("loading")
        try:
            req = MissileRequest.model_validate(state)
            result.clear()
            result.update(await run.io_bound(missile_simulate, req))
        except Exception as exc:  # noqa: BLE001
            ui.notify(str(exc), type="negative", multi_line=True)
            return
        finally:
            run_btn.props(remove="loading")
        render()

    def render() -> None:
        results.clear()
        s = result["summary"]
        ground = [
            math.hypot(p[0], p[1]) for p in result["position"]
        ]
        with results:
            stats_row(
                [
                    ("Apogee", f"{s['apogee'] / 1000:.2f} km"),
                    ("Max speed", f"{s['max_speed']:.0f} m/s"),
                    ("Max Mach", f"{s['max_mach']:.2f}"),
                    ("Range", f"{s['range'] / 1000:.2f} km"),
                    ("Flight time", f"{s['flight_time']:.1f} s"),
                ]
            )
            ui.plotly(
                xy_fig(
                    "Ground range (m)",
                    "Altitude (m)",
                    [{"label": "Trajectory", "color": PALETTE["green"],
                      "x": ground, "y": result["altitude"]}],
                )
            ).classes("w-full")
            ui.plotly(
                line_fig(
                    "Time (s)",
                    "Speed (m/s)",
                    [{"label": "Speed", "color": PALETTE["green"],
                      "x": result["time"], "y": result["speed"]}],
                )
            ).classes("w-full")

            ui.label("Export").classes("font-semibold mt-2")
            mreq = MissileRequest.model_validate(state)
            areq = AirframeCadRequest.model_validate(
                {**cad, "airframe": state["airframe"]}
            )
            with ui.row().classes("flex-wrap gap-2"):
                _btn("trajectory.csv",
                     lambda: export_router.trajectory_csv_export(mreq),
                     "trajectory.csv")
                _btn("airframe.stl", lambda: export_router.airframe_stl_export(areq),
                     "airframe.stl")
                _btn("airframe.scad", lambda: export_router.airframe_scad_export(areq),
                     "airframe.scad")

    run_btn.on_click(run_flight)


def _btn(label: str, fn, filename: str) -> None:
    def handler() -> None:
        try:
            offer_download(fn(), filename)
        except Exception as exc:  # noqa: BLE001
            ui.notify(str(exc), type="negative")

    ui.button(label, on_click=handler).props("dense outline")
