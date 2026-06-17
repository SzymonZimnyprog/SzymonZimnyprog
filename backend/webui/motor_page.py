"""Motor tab: internal ballistics, thrust/pressure curves, CAD & Simulink export."""

from __future__ import annotations

from nicegui import run, ui

from backend.routers import export as export_router
from backend.routers.motor import simulate as motor_simulate
from backend.sim.geometry import nozzle_profile
from backend.sim.models import MotorRequest, PropellantModel
from backend.sim.propellant import PRESETS

from . import help_text as H
from .common import (
    PALETTE,
    card,
    header,
    line_fig,
    nozzle_section_fig,
    num,
    offer_download,
    page_body,
    page_intro,
    plot,
    select_field,
    stats_row,
    warnings_panel,
)

GRAIN_TYPES = ["BATES", "TUBULAR", "ROD", "END_BURNER"]


def motor_form(state: dict) -> None:
    """Render the propellant / grain / nozzle form bound to ``state`` in place."""
    prop = state["propellant"]
    grain = state["grain"]
    nozzle = state["nozzle"]

    with ui.row().classes("gap-1 flex-wrap items-center"):
        ui.label("Propellant preset:").classes("self-center text-sm")
        for key in PRESETS:
            ui.button(
                key,
                on_click=lambda k=key: state["propellant"].update(
                    PropellantModel.from_preset(k).model_dump(mode="json")
                ),
            ).props("dense outline no-caps").tooltip(
                f"Load standard parameters for {key}"
            )

    with ui.expansion("Propellant parameters", icon="science").classes("w-full"):
        with ui.grid(columns=2).classes("gap-2 w-full"):
            num(prop, "a", "Burn-rate a", unit="mm/s@1MPa", step=0.1,
                help=H.PROPELLANT["a"])
            num(prop, "n", "Burn exponent n", step=0.01, help=H.PROPELLANT["n"])
            num(prop, "density", "Density", unit="kg/m³", step=10,
                help=H.PROPELLANT["density"])
            num(prop, "gamma", "γ (cp/cv)", step=0.01, help=H.PROPELLANT["gamma"])
            num(prop, "t_flame", "Flame temp", unit="K", step=50,
                help=H.PROPELLANT["t_flame"])
            num(prop, "molar_mass", "Molar mass", unit="kg/mol", step=0.001,
                help=H.PROPELLANT["molar_mass"])
            num(prop, "c_star_eff", "c* efficiency", step=0.01,
                help=H.PROPELLANT["c_star_eff"])

    ui.label("Grain").classes("font-semibold mt-2")
    select_field(grain, "grain_type", "Grain type", GRAIN_TYPES,
                 help=H.GRAIN["grain_type"])
    with ui.grid(columns=2).classes("gap-2 w-full"):
        num(grain, "outer_diameter", "Outer dia", unit="m", step=0.005,
            help=H.GRAIN["outer_diameter"])
        num(grain, "core_diameter", "Core dia", unit="m", step=0.005,
            help=H.GRAIN["core_diameter"])
        num(grain, "segment_length", "Segment len", unit="m", step=0.01,
            help=H.GRAIN["segment_length"])
        num(grain, "segments", "Segments", step=1, min=1, help=H.GRAIN["segments"])

    ui.label("Nozzle").classes("font-semibold mt-2")
    with ui.grid(columns=2).classes("gap-2 w-full"):
        num(nozzle, "throat_diameter", "Throat dia", unit="m", step=0.002,
            help=H.NOZZLE["throat_diameter"])
        num(nozzle, "expansion_ratio", "Expansion ratio Ae/At", step=0.5,
            help=H.NOZZLE["expansion_ratio"])
        num(nozzle, "efficiency", "Nozzle efficiency", step=0.01,
            help=H.NOZZLE["efficiency"])

    with ui.expansion("Environment & solver", icon="tune").classes("w-full"):
        with ui.grid(columns=2).classes("gap-2 w-full"):
            num(state, "altitude", "Altitude", unit="m", step=100,
                help=H.MOTOR_ENV["altitude"])
            num(state, "dt", "Time step", unit="s", step=0.001,
                help=H.MOTOR_ENV["dt"])
            num(state, "max_time", "Max time", unit="s", step=5,
                help=H.MOTOR_ENV["max_time"])


@ui.page("/motor")
def motor_page() -> None:
    header("/motor")
    state = MotorRequest().model_dump(mode="json")
    result: dict = {}

    with page_body():
        page_intro(
            "Solid rocket motor",
            "Quasi-steady internal ballistics: equilibrium chamber pressure, nozzle "
            "thrust coefficient and the resulting thrust curve, with design "
            "diagnostics and CAD / Simulink export.",
        )

        with ui.row().classes("w-full gap-4 items-start"):
            with card().classes("w-96"):
                motor_form(state)
                run_btn = ui.button("Run motor", icon="play_arrow")
                run_btn.classes("w-full mt-2")

            results = ui.column().classes("flex-grow gap-3 min-w-[420px]")

    async def run_motor() -> None:
        run_btn.props("loading")
        try:
            req = MotorRequest.model_validate(state)
            result.clear()
            result.update(await run.io_bound(motor_simulate, req))
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            ui.notify(str(exc), type="negative", multi_line=True)
            return
        finally:
            run_btn.props(remove="loading")
        render()

    def render() -> None:
        results.clear()
        s = result["summary"]
        with results:
            stats_row(
                [
                    ("Total impulse", f"{s['total_impulse']:.0f} N·s"),
                    ("Class", s["impulse_class"]),
                    ("Peak thrust", f"{s['peak_thrust']:.0f} N"),
                    ("Avg thrust", f"{s['average_thrust']:.0f} N"),
                    ("Burn time", f"{s['burn_time']:.2f} s"),
                    ("Isp", f"{s['specific_impulse']:.0f} s"),
                    ("Peak Pc", f"{s['peak_pressure'] / 1e6:.2f} MPa"),
                    ("Kn (init/max)", f"{s['kn_initial']:.0f}/{s['kn_max']:.0f}"),
                    ("Port/throat", f"{s['port_to_throat']:.2f}"),
                    ("Prop mass", f"{s['propellant_mass_initial']:.2f} kg"),
                ]
            )
            warnings_panel(s["warnings"])
            plot(
                line_fig(
                    "Time (s)",
                    "Thrust (N)",
                    [{"label": "Thrust", "color": PALETTE["indigo"],
                      "x": result["time"], "y": result["thrust"]}],
                )
            )
            plot(
                line_fig(
                    "Time (s)",
                    "Chamber pressure (MPa)",
                    [{"label": "Pc", "color": PALETTE["red"], "x": result["time"],
                      "y": [p / 1e6 for p in result["chamber_pressure"]]}],
                )
            )

            # Geometric cross-section reflecting the nozzle/grain sizing.
            ui.label("Nozzle & grain geometry").classes("font-semibold mt-2")
            g = state["grain"]
            geo = nozzle_profile(
                throat_diameter=state["nozzle"]["throat_diameter"],
                expansion_ratio=state["nozzle"]["expansion_ratio"],
                chamber_diameter=g["outer_diameter"],
                grain_length=g["segment_length"] * g["segments"],
                core_diameter=g["core_diameter"],
            )
            plot(nozzle_section_fig(geo))
            noz_len = (geo["converging_length"] + geo["diverging_length"]) * 1000
            ui.label(
                f"Throat Ø{geo['throat_diameter'] * 1000:.1f} mm · "
                f"exit Ø{geo['exit_diameter'] * 1000:.1f} mm · "
                f"ε={geo['expansion_ratio']:.1f} · "
                f"nozzle length {noz_len:.0f} mm (15° divergent). "
                "Export the exact solid via the buttons below."
            ).classes("text-xs text-slate-500")

            _intercept_workflow()

            ui.label("Export").classes("font-semibold mt-2")
            req = MotorRequest.model_validate(state)
            with ui.row().classes("flex-wrap gap-2"):
                _export_btn("grain.stl", export_router.grain_stl_export, req)
                _export_btn("nozzle.stl", export_router.nozzle_stl_export, req)
                _export_btn("grain.scad", export_router.grain_scad_export, req)
                _export_btn("nozzle.scad", export_router.nozzle_scad_export, req)
                _export_btn(
                    "thrust_curve.csv", export_router.thrust_curve_csv_export, req
                )
                _export_btn("motor.eng", export_router.motor_eng_export, req)

    run_btn.on_click(run_motor)


def _intercept_workflow() -> None:
    """Explain how a sized motor becomes an actual aimed interception."""
    with ui.expansion(
        "From this design to an actual intercept", icon="route"
    ).classes("w-full mt-2"):
        steps = [
            ("Size & check", "Tune the motor here until thrust, chamber "
             "pressure and impulse are healthy (no warnings). Export the STL/"
             "OpenSCAD if you're building it."),
            ("Confirm stability", "On the Trajectory tab, open Stability "
             "(Barrowman) and keep the static margin at 1–2 calibers across the "
             "whole burn — an unstable airframe can't be guided."),
            ("Load it as the interceptor", "On the Interception tab this same "
             "motor is the interceptor's Boost motor; set the target's position "
             "and velocity."),
            ("Auto-aim = the firing solution", "Press Auto-aim: the solver "
             "searches the launch elevation and azimuth that intercept, and "
             "returns that firing solution plus the launch envelope. Those two "
             "angles ARE how you physically point the launcher."),
            ("Guidance flies the rest", "After launch the seeker acquires the "
             "target and proportional navigation (PN/APN) steers the missile to "
             "closest approach — you aim the launcher, the guidance law does the "
             "in-flight homing."),
        ]
        for i, (title, body) in enumerate(steps, 1):
            with ui.row().classes("items-start gap-2 no-wrap"):
                ui.label(f"{i}").classes(
                    "text-white bg-primary rounded-full w-6 h-6 "
                    "flex items-center justify-center text-sm shrink-0")
                with ui.column().classes("gap-0"):
                    ui.label(title).classes("font-semibold text-sm")
                    ui.label(body).classes("text-xs text-slate-500")


def _export_btn(filename: str, fn, req) -> None:
    def handler() -> None:
        try:
            offer_download(fn(req), filename)
        except Exception as exc:  # noqa: BLE001
            ui.notify(str(exc), type="negative")

    ui.button(filename, icon="download", on_click=handler).props(
        "dense outline no-caps"
    )
