"""Trajectory tab: single un-guided missile flight + airframe CAD export."""

from __future__ import annotations

import math

from nicegui import run, ui

from backend.routers import export as export_router
from backend.routers.export import AirframeCadRequest
from backend.routers.missile import StabilityRequest
from backend.routers.missile import simulate as missile_simulate
from backend.routers.missile import stability as stability_endpoint
from backend.sim.models import MissileRequest

from . import help_text as H
from .common import (
    PALETTE,
    animated_path3d_fig,
    card,
    header,
    line_fig,
    num,
    offer_download,
    page_body,
    page_intro,
    plot,
    select_field,
    stability_fig,
    stats_row,
    warnings_panel,
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

                _stability_section(state, cad)

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
                    ui.label(
                        "▶ Press Play to watch the missile fly its arc, or drag "
                        "the slider to scrub through the flight."
                    ).classes("text-sm text-slate-500")
                    plot(
                        animated_path3d_fig(
                            [{"label": "Trajectory", "color": PALETTE["green"],
                              "x": [p[0] for p in pos], "y": [p[1] for p in pos],
                              "z": [p[2] for p in pos]}],
                            times=result["time"],
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


def _stability_section(state: dict, cad: dict) -> None:
    total = cad["nose_length"] + cad["body_length"]
    stab = {
        "diameter": state["airframe"]["diameter"],
        "nose_length": cad["nose_length"],
        "body_length": cad["body_length"],
        "nose_type": "ogive",
        "fin_count": cad["fin_count"],
        "fin_root_chord": cad["fin_root"],
        "fin_tip_chord": round(cad["fin_root"] * 0.5, 3),
        "fin_span": cad["fin_span"],
        "fin_sweep": round(cad["fin_root"] * 0.4, 3),
        "fin_root_position": None,
        "dry_mass": state["airframe"]["dry_mass"],
        "dry_cg": round(0.55 * total, 3),
        "propellant_mass": 8.0,
        "propellant_cg": round(0.85 * total, 3),
    }

    with ui.expansion("Stability (Barrowman)", icon="balance").classes("w-full"):
        ui.label(
            "Centre of pressure vs centre of gravity → static margin. "
            "Aim for 1–2 calibers across the whole burn."
        ).classes("text-xs text-slate-500")
        select_field(stab, "nose_type", "Nose type",
                     ["ogive", "cone", "parabolic", "haack"],
                     help=H.STABILITY["nose_type"])
        with ui.grid(columns=2).classes("gap-2 w-full"):
            num(stab, "fin_root_chord", "Fin root chord", unit="m", step=0.01,
                help=H.STABILITY["fin_root_chord"])
            num(stab, "fin_tip_chord", "Fin tip chord", unit="m", step=0.01,
                help=H.STABILITY["fin_tip_chord"])
            num(stab, "fin_span", "Fin span", unit="m", step=0.01,
                help=H.STABILITY["fin_span"])
            num(stab, "fin_sweep", "Fin sweep", unit="m", step=0.01,
                help=H.STABILITY["fin_sweep"])
            num(stab, "dry_cg", "Empty CG", unit="m", step=0.05,
                help=H.STABILITY["dry_cg"])
            num(stab, "propellant_mass", "Prop mass", unit="kg", step=1)
            num(stab, "propellant_cg", "Prop CG", unit="m", step=0.05,
                help=H.STABILITY["propellant_cg"])
        out = ui.column().classes("w-full gap-2")

        def analyse() -> None:
            out.clear()
            try:
                res = stability_endpoint(StabilityRequest.model_validate(stab))
            except Exception as exc:  # noqa: BLE001
                ui.notify(str(exc), type="negative")
                return
            with out:
                ml, me = res["static_margin_loaded"], res["static_margin_empty"]
                stats_row(
                    [
                        ("Margin loaded", f"{ml:.2f} cal"),
                        ("Margin empty", f"{me:.2f} cal"),
                        ("CP", f"{res['x_cp']:.2f} m"),
                        ("CG loaded", f"{res['x_cg_loaded']:.2f} m"),
                        ("CNα", f"{res['cn_alpha']:.1f}/rad"),
                    ]
                )
                plot(stability_fig(res))
                warnings_panel(res["warnings"])

        ui.button("Analyse stability", icon="balance", on_click=analyse).props(
            "outline no-caps"
        ).classes("w-full")


def _btn(label: str, fn, filename: str) -> None:
    def handler() -> None:
        try:
            offer_download(fn(), filename)
        except Exception as exc:  # noqa: BLE001
            ui.notify(str(exc), type="negative")

    ui.button(label, icon="download", on_click=handler).props("dense outline no-caps")
