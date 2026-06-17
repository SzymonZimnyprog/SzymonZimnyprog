"""Multi-stage tab: combined thrust profile and full staged flight."""

from __future__ import annotations

import math

from nicegui import run, ui

from backend.routers.missile import MultiStageFlightRequest, multistage_flight
from backend.routers.motor import MultiStageRequest
from backend.routers.motor import multistage as motor_multistage
from backend.sim.models import AirframeModel, GrainModel, MotorRequest, PropellantModel

from . import help_text as H
from .common import (
    PALETTE,
    card,
    header,
    line_fig,
    num,
    page_body,
    page_intro,
    path3d_fig,
    plot,
    select_field,
    stats_row,
    xy_fig,
)

GRAIN_TYPES = ["BATES", "TUBULAR", "ROD", "END_BURNER"]


def _stage(grain_type, od, core, seglen, segs, throat, exp_ratio, delay):
    motor = MotorRequest(
        propellant=PropellantModel.from_preset("APCP"),
        grain=GrainModel(
            grain_type=grain_type,
            outer_diameter=od,
            core_diameter=core,
            segment_length=seglen,
            segments=segs,
        ),
    )
    motor.nozzle.throat_diameter = throat
    motor.nozzle.expansion_ratio = exp_ratio
    return {
        "motor": motor.model_dump(mode="json"),
        "ignition_delay": delay,
        "structural_mass": 5.0,
    }


def _default_stages() -> list[dict]:
    return [
        _stage("TUBULAR", 0.14, 0.05, 0.30, 3, 0.030, 8.0, 0.0),
        _stage("BATES", 0.12, 0.06, 0.40, 2, 0.018, 10.0, 1.5),
    ]


@ui.page("/stack")
def stack_page() -> None:
    header("/stack")
    stages: list[dict] = _default_stages()
    flight = {
        "payload": AirframeModel(diameter=0.14, cd0=0.35, dry_mass=30.0).model_dump(),
        "launch_speed": 30.0,
        "elevation_deg": 80.0,
        "azimuth_deg": 0.0,
        "drop_last_stage": False,
    }
    thrust_result: dict = {}
    flight_result: dict = {}

    with page_body():
        page_intro(
            "Multi-stage stack",
            "Sequential stages (boost → sustain): each ignites after the previous "
            "burns out plus its coast delay. Run the combined thrust, or fly the "
            "staged stack and jettison spent-stage mass at each burnout.",
        )

        with ui.row().classes("w-full gap-4 items-start"):
            with ui.column().classes("w-[30rem] gap-2"):

                @ui.refreshable
                def stage_cards() -> None:
                    for i, stage in enumerate(stages):
                        g = stage["motor"]["grain"]
                        n = stage["motor"]["nozzle"]
                        with card().classes("w-full"):
                            head_cls = "items-center justify-between w-full"
                            with ui.row().classes(head_cls):
                                ui.label(f"Stage {i + 1}").classes("font-semibold")
                                with ui.row().classes("gap-1"):
                                    for key in ("KNSB", "APCP"):
                                        ui.button(
                                            key,
                                            on_click=lambda s=stage, k=key: (
                                                s["motor"]["propellant"].update(
                                                    PropellantModel.from_preset(
                                                        k
                                                    ).model_dump(mode="json")
                                                )
                                            ),
                                        ).props("dense outline no-caps")
                                    if len(stages) > 1:
                                        ui.button(
                                            icon="close",
                                            on_click=lambda idx=i: _remove(idx),
                                        ).props("dense flat color=red")
                            select_field(g, "grain_type", "Grain type", GRAIN_TYPES,
                                         help=H.GRAIN["grain_type"])
                            with ui.grid(columns=2).classes("gap-2 w-full"):
                                num(g, "outer_diameter", "Outer dia", unit="m",
                                    step=0.005, help=H.GRAIN["outer_diameter"])
                                num(g, "core_diameter", "Core dia", unit="m",
                                    step=0.005, help=H.GRAIN["core_diameter"])
                                num(g, "segment_length", "Segment len", unit="m",
                                    step=0.01, help=H.GRAIN["segment_length"])
                                num(g, "segments", "Segments", step=1, min=1,
                                    help=H.GRAIN["segments"])
                                num(n, "throat_diameter", "Throat dia", unit="m",
                                    step=0.002, help=H.NOZZLE["throat_diameter"])
                                num(stage, "ignition_delay", "Ignite delay", unit="s",
                                    step=0.5, min=0, help=H.STAGE["ignition_delay"])
                                num(stage, "structural_mass", "Struct. mass", unit="kg",
                                    step=0.5, min=0, help=H.STAGE["structural_mass"])

                def _remove(idx: int) -> None:
                    stages.pop(idx)
                    stage_cards.refresh()

                def _add() -> None:
                    if len(stages) >= 5:
                        ui.notify("Maximum 5 stages", type="warning")
                        return
                    stages.append(
                        _stage("BATES", 0.12, 0.06, 0.40, 2, 0.018, 10.0, 1.5)
                    )
                    stage_cards.refresh()

                stage_cards()
                ui.button("Add stage", icon="add", on_click=_add).props(
                    "outline no-caps"
                ).classes("w-full")

                with card("Flight parameters", "flight_takeoff").classes("w-full"):
                    pay = flight["payload"]
                    with ui.grid(columns=2).classes("gap-2 w-full"):
                        num(pay, "dry_mass", "Payload mass", unit="kg", step=1,
                            help=H.PAYLOAD["dry_mass"])
                        num(pay, "diameter", "Payload dia", unit="m", step=0.01,
                            help=H.PAYLOAD["diameter"])
                        num(pay, "cd0", "Payload Cd0", step=0.01, help=H.PAYLOAD["cd0"])
                        num(flight, "launch_speed", "Launch speed", unit="m/s", step=5,
                            help=H.LAUNCH["launch_speed"])
                        num(flight, "elevation_deg", "Elevation", unit="°", step=1,
                            min=0, max=90, help=H.LAUNCH["elevation_deg"])
                        num(flight, "azimuth_deg", "Azimuth", unit="°", step=5,
                            help=H.LAUNCH["azimuth_deg"])
                    ui.switch("Drop last stage at burnout").bind_value(
                        flight, "drop_last_stage"
                    ).tooltip(
                        "Jettison the top stage too (e.g. release a free-flying "
                        "payload); otherwise the last stage is kept."
                    )

                with ui.row().classes("w-full gap-2 no-wrap"):
                    run_btn = ui.button("Run stack", icon="bolt").classes("flex-grow")
                    fly_btn = ui.button("Fly stack", icon="rocket_launch")
                    fly_btn.props("color=positive").classes("flex-grow")

            results = ui.column().classes("flex-grow gap-3 min-w-[420px]")

    def _stage_payload() -> list[dict]:
        return [
            {"motor": s["motor"], "ignition_delay": s["ignition_delay"]}
            for s in stages
        ]

    async def run_stack() -> None:
        run_btn.props("loading")
        try:
            req = MultiStageRequest.model_validate({"stages": _stage_payload()})
            thrust_result.clear()
            thrust_result.update(await run.io_bound(motor_multistage, req))
        except Exception as exc:  # noqa: BLE001
            ui.notify(str(exc), type="negative", multi_line=True)
            return
        finally:
            run_btn.props(remove="loading")
        render()

    async def fly_stack() -> None:
        fly_btn.props("loading")
        try:
            req = MultiStageFlightRequest.model_validate(
                {
                    "stages": stages,
                    "payload": flight["payload"],
                    "launch_speed": flight["launch_speed"],
                    "elevation_deg": flight["elevation_deg"],
                    "azimuth_deg": flight["azimuth_deg"],
                    "drop_last_stage": flight["drop_last_stage"],
                    "dt": 0.02,
                    "max_time": 600.0,
                }
            )
            flight_result.clear()
            flight_result.update(await run.io_bound(multistage_flight, req))
        except Exception as exc:  # noqa: BLE001
            ui.notify(str(exc), type="negative", multi_line=True)
            return
        finally:
            fly_btn.props(remove="loading")
        render()

    def render() -> None:
        results.clear()
        with results:
            if thrust_result:
                _render_thrust(thrust_result)
            if flight_result:
                _render_flight(flight_result)
            if not thrust_result and not flight_result:
                ui.label("Define the stages, then Run or Fly the stack.").classes(
                    "text-slate-500"
                )

    run_btn.on_click(run_stack)
    fly_btn.on_click(fly_stack)


def _render_thrust(res: dict) -> None:
    s = res["summary"]
    ui.label("Combined thrust").classes("text-lg font-semibold")
    stats_row(
        [
            ("Total impulse", f"{s['total_impulse']:.0f} N·s"),
            ("Class", s["impulse_class"]),
            ("Peak thrust", f"{s['peak_thrust']:.0f} N"),
            ("Stack burn", f"{s['burn_time']:.1f} s"),
            ("Stages", str(s["stage_count"])),
            ("Prop mass", f"{s['propellant_mass_total']:.1f} kg"),
        ]
    )
    plot(
        line_fig(
            "Time (s)", "Thrust (N)",
            [{"label": "Stack thrust", "color": PALETTE["indigo"],
              "x": res["time"], "y": res["thrust"]}],
        )
    )
    _stage_table(res["stages"])


def _render_flight(res: dict) -> None:
    s = res["summary"]
    ui.label("Staged flight").classes("text-lg font-semibold mt-2")
    stats_row(
        [
            ("Apogee", f"{s['apogee'] / 1000:.2f} km"),
            ("Max speed", f"{s['max_speed']:.0f} m/s"),
            ("Max Mach", f"{s['max_mach']:.2f}"),
            ("Range", f"{s['range'] / 1000:.2f} km"),
            ("Flight time", f"{s['flight_time']:.1f} s"),
            ("Initial mass", f"{res['initial_mass']:.1f} kg"),
        ]
    )
    pos = res["position"]
    ground = [math.hypot(p[0], p[1]) for p in pos]
    markers2d, markers3d = [], []
    for j, ev in enumerate(res["separations"]):
        idx = _nearest_index(res["time"], ev["time"])
        markers2d.append(
            {"x": ground[idx], "y": ev["altitude"], "label": f"S{j + 1} drop"}
        )
        markers3d.append(
            {"x": pos[idx][0], "y": pos[idx][1], "z": pos[idx][2],
             "label": f"S{j + 1} drop"}
        )
    with ui.tabs().classes("w-full") as tabs:
        ui.tab("3D", icon="3d_rotation")
        ui.tab("Profile", icon="show_chart")
        ui.tab("Mass", icon="scale")
    with ui.tab_panels(tabs, value="3D").classes("w-full"):
        with ui.tab_panel("3D"):
            plot(
                path3d_fig(
                    [{"label": "Staged flight", "color": PALETTE["green"],
                      "x": [p[0] for p in pos], "y": [p[1] for p in pos],
                      "z": [p[2] for p in pos]}],
                    markers=markers3d,
                )
            )
        with ui.tab_panel("Profile"):
            plot(
                xy_fig(
                    "Ground range (m)", "Altitude (m)",
                    [{"label": "Staged flight", "color": PALETTE["green"],
                      "x": ground, "y": res["altitude"]}],
                    markers=markers2d,
                )
            )
        with ui.tab_panel("Mass"):
            plot(
                line_fig(
                    "Time (s)", "Mass (kg)",
                    [{"label": "Total mass", "color": PALETTE["amber"],
                      "x": res["time"], "y": res["mass"]}],
                )
            )
    _separation_table(res["separations"])


def _nearest_index(times: list[float], t: float) -> int:
    best, best_d = 0, float("inf")
    for i, ti in enumerate(times):
        d = abs(ti - t)
        if d < best_d:
            best_d, best = d, i
    return best


def _ground_at(times: list[float], ground: list[float], t: float) -> float:
    if not ground:
        return 0.0
    return ground[_nearest_index(times, t)]


def _stage_table(rows: list[dict]) -> None:
    columns = [
        {"name": "stage", "label": "Stage", "field": "stage"},
        {"name": "ignite", "label": "Ignite (s)", "field": "ignite"},
        {"name": "burn", "label": "Burn (s)", "field": "burn"},
        {"name": "impulse", "label": "Impulse (N·s)", "field": "impulse"},
        {"name": "cls", "label": "Class", "field": "cls"},
    ]
    data = [
        {
            "stage": r["index"] + 1,
            "ignite": f"{r['start_time']:.2f}",
            "burn": f"{r['burn_time']:.2f}",
            "impulse": f"{r['total_impulse']:.0f}",
            "cls": r["impulse_class"],
        }
        for r in rows
    ]
    ui.table(columns=columns, rows=data).classes("w-full sim-card")


def _separation_table(events: list[dict]) -> None:
    if not events:
        return
    ui.label("Stage separations").classes("font-semibold mt-2")
    columns = [
        {"name": "event", "label": "Event", "field": "event"},
        {"name": "time", "label": "Time (s)", "field": "time"},
        {"name": "alt", "label": "Altitude (km)", "field": "alt"},
        {"name": "mass", "label": "Mass after (kg)", "field": "mass"},
    ]
    data = [
        {
            "event": f"Stage {i + 1} jettison",
            "time": f"{ev['time']:.2f}",
            "alt": f"{ev['altitude'] / 1000:.2f}",
            "mass": f"{ev['mass_after']:.1f}",
        }
        for i, ev in enumerate(events)
    ]
    ui.table(columns=columns, rows=data).classes("w-full sim-card")
