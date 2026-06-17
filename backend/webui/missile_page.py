"""Trajectory tab: single un-guided missile flight + airframe CAD export."""

from __future__ import annotations

import math

from nicegui import run, ui

from backend.routers import export as export_router
from backend.routers.export import AirframeCadRequest
from backend.routers.missile import simulate as missile_simulate
from backend.sim.models import MissileRequest

from . import help_text as H
from .common import (
    PALETTE,
    card,
    header,
    line_fig,
    num,
    offer_download,
    page_body,
    page_intro,
    path3d_fig,
    plot,
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

    with page_body():
        page_intro(
            "Missile trajectory",
            "3-DOF point-mass flight (RK4) in an ENU frame: boosted ascent on the "
            "motor, ISA atmosphere, Mach-dependent drag and mass depletion.",
        )

        with ui.row().classes("w-full gap-4 items-start"):
            with card().classes("w-96"):
                with ui.expansion("Motor", icon="rocket", value=True).classes("w-full"):
                    motor_form(state["motor"])
                ui.label("Airframe").classes("font-semibold mt-2")
                with ui.grid(columns=2).classes("gap-2 w-full"):
                    num(state["airframe"], "diameter", "Body dia", unit="m", step=0.01,
                        help=H.AIRFRAME["diameter"])
                    num(state["airframe"], "cd0", "Cd0 (subsonic)", step=0.01,
                        help=H.AIRFRAME["cd0"])
                    num(state["airframe"], "dry_mass", "Dry mass", unit="kg", step=1,
                        help=H.AIRFRAME["dry_mass"])
                ui.label("Launch").classes("font-semibold mt-2")
                with ui.grid(columns=2).classes("gap-2 w-full"):
                    num(state, "launch_speed", "Rail speed", unit="m/s", step=5,
                        help=H.LAUNCH["launch_speed"])
                    num(state, "elevation_deg", "Elevation", unit="°", step=1,
                        min=0, max=90, help=H.LAUNCH["elevation_deg"])
                    num(state, "azimuth_deg", "Azimuth", unit="°", step=5,
                        help=H.LAUNCH["azimuth_deg"])
                    num(state, "dt", "Time step", unit="s", step=0.01,
                        help=H.ENGAGEMENT["dt"])
                with ui.expansion("Airframe CAD", icon="view_in_ar").classes("w-full"):
                    with ui.grid(columns=2).classes("gap-2 w-full"):
                        num(cad, "body_length", "Body length", unit="m", step=0.1)
                        num(cad, "nose_length", "Nose length", unit="m", step=0.1)
                        num(cad, "fin_count", "Fin count", step=1, min=0, max=8)
                        num(cad, "fin_span", "Fin span", unit="m", step=0.01)
                        num(cad, "fin_root", "Fin root chord", unit="m", step=0.01)
                run_btn = ui.button("Fly missile", icon="rocket_launch").classes(
                    "w-full mt-2"
                )

            results = ui.column().classes("flex-grow gap-3 min-w-[420px]")

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
        pos = result["position"]
        ground = [math.hypot(p[0], p[1]) for p in pos]
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
            with ui.tabs().classes("w-full") as tabs:
                ui.tab("3D", icon="3d_rotation")
                ui.tab("Profile", icon="show_chart")
                ui.tab("Speed", icon="speed")
            with ui.tab_panels(tabs, value="3D").classes("w-full"):
                with ui.tab_panel("3D"):
                    plot(
                        path3d_fig(
                            [{"label": "Trajectory", "color": PALETTE["green"],
                              "x": [p[0] for p in pos], "y": [p[1] for p in pos],
                              "z": [p[2] for p in pos]}]
                        )
                    )
                with ui.tab_panel("Profile"):
                    plot(
                        xy_fig(
                            "Ground range (m)", "Altitude (m)",
                            [{"label": "Trajectory", "color": PALETTE["green"],
                              "x": ground, "y": result["altitude"]}],
                        )
                    )
                with ui.tab_panel("Speed"):
                    plot(
                        line_fig(
                            "Time (s)", "Speed (m/s)",
                            [{"label": "Speed", "color": PALETTE["green"],
                              "x": result["time"], "y": result["speed"]}],
                        )
                    )

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

    ui.button(label, icon="download", on_click=handler).props("dense outline no-caps")
