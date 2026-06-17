"""Interception tab: PN engagement, fire-control solver, salvo and Monte-Carlo."""

from __future__ import annotations

import math

from nicegui import run, ui

from backend.routers.engagement import (
    MonteCarloRequest,
    SalvoRequest,
)
from backend.routers.engagement import (
    montecarlo as eng_montecarlo,
)
from backend.routers.engagement import (
    salvo as eng_salvo,
)
from backend.routers.engagement import (
    simulate as eng_simulate,
)
from backend.routers.engagement import (
    solve as eng_solve,
)
from backend.sim.models import EngagementRequest

from . import help_text as H
from .common import (
    PALETTE,
    animated_path3d_fig,
    bar_fig,
    card,
    header,
    line_fig,
    num,
    page_body,
    page_intro,
    plot,
    stats_row,
    xy_fig,
)
from .motor_page import motor_form

AXES = ["E", "N", "Up"]


def vec_inputs(label: str, vec: list, unit: str, help: str = "") -> None:
    with ui.row().classes("items-center gap-1 mt-1"):
        ui.label(f"{label} ({unit})").classes("text-sm font-medium")
        if help:
            ui.icon("info").classes("text-primary text-sm").tooltip(help)
    with ui.grid(columns=3).classes("gap-2 w-full"):
        for i, axis in enumerate(AXES):
            field = ui.number(label=axis, value=vec[i], step=10)
            field.props("outlined dense").classes("w-full")
            field.on(
                "update:model-value",
                lambda e, idx=i: vec.__setitem__(idx, float(e.args or 0.0)),
            )


@ui.page("/")
def engagement_page() -> None:
    header("/")
    state = EngagementRequest().model_dump(mode="json")
    extra = {
        "salvo_count": 3,
        "salvo_stagger": 1.0,
        "salvo_spread": 6.0,
        "mc_trials": 150,
        "mc_pos_sigma": 200.0,
        "mc_vel_sigma": 20.0,
    }
    result: dict = {"mode": None, "data": None}

    with page_body():
        page_intro(
            "Interception",
            "Proportional-navigation homing against a ballistic target. Run a single "
            "engagement, auto-aim the launch elevation/azimuth, fire a layered salvo, "
            "or estimate kill probability under track uncertainty.",
        )

        with ui.row().classes("w-full gap-4 items-start"):
            with ui.column().classes("w-[30rem] gap-2"):
                interceptor = state["interceptor"]
                target = state["target"]

                with card("Interceptor", "rocket_launch").classes("w-full"):
                    with ui.expansion("Boost motor", icon="local_fire_department"
                                      ).classes("w-full"):
                        motor_form(interceptor["motor"])
                    ui.label("Airframe").classes("font-semibold mt-1")
                    with ui.grid(columns=3).classes("gap-2 w-full"):
                        num(interceptor["airframe"], "diameter", "Dia", unit="m",
                            step=0.01, help=H.AIRFRAME["diameter"])
                        num(interceptor["airframe"], "cd0", "Cd0", step=0.01,
                            help=H.AIRFRAME["cd0"])
                        num(interceptor["airframe"], "dry_mass", "Dry", unit="kg",
                            step=1, help=H.AIRFRAME["dry_mass"])
                    vec_inputs("Launch position", interceptor["launch_position"], "m",
                               help=H.GUIDANCE["launch_position"])
                    ui.label("Launch & guidance").classes("font-semibold mt-1")
                    with ui.grid(columns=2).classes("gap-2 w-full"):
                        num(interceptor, "launch_speed", "Rail speed", unit="m/s",
                            step=5, help=H.LAUNCH["launch_speed"])
                        num(interceptor, "elevation_deg", "Elevation", unit="°", step=1,
                            min=0, max=90, help=H.LAUNCH["elevation_deg"])
                        num(interceptor, "azimuth_deg", "Azimuth", unit="°", step=5,
                            help=H.LAUNCH["azimuth_deg"])
                        num(interceptor, "nav_constant", "Nav constant N", step=0.5,
                            help=H.GUIDANCE["nav_constant"])
                        num(interceptor, "max_lateral_g", "Max lateral g", step=5,
                            help=H.GUIDANCE["max_lateral_g"])
                        num(interceptor, "seeker_delay", "Seeker delay", unit="s",
                            step=0.1, help=H.GUIDANCE["seeker_delay"])

                with card("Target", "adjust").classes("w-full"):
                    vec_inputs("Position", target["position"], "m",
                               help=H.TARGET["position"])
                    vec_inputs("Velocity", target["velocity"], "m/s",
                               help=H.TARGET["velocity"])
                    vec_inputs("Maneuver accel", target["maneuver_accel"], "m/s²",
                               help=H.TARGET["maneuver_accel"])
                    with ui.grid(columns=3).classes("gap-2 w-full"):
                        num(target, "diameter", "Dia", unit="m", step=0.05,
                            help=H.TARGET["diameter"])
                        num(target, "cd0", "Cd0", step=0.05, help=H.TARGET["cd0"])
                        num(target, "mass", "Mass", unit="kg", step=10,
                            help=H.TARGET["mass"])

                with card("Engagement", "tune").classes("w-full"):
                    with ui.grid(columns=3).classes("gap-2 w-full"):
                        num(state, "dt", "dt", unit="s", step=0.005,
                            help=H.ENGAGEMENT["dt"])
                        num(state, "max_time", "Max t", unit="s", step=10,
                            help=H.ENGAGEMENT["max_time"])
                        num(state, "lethal_radius", "Lethal R", unit="m", step=1,
                            help=H.ENGAGEMENT["lethal_radius"])

                with ui.row().classes("w-full gap-2 no-wrap"):
                    run_btn = ui.button("Engage", icon="play_arrow")
                    run_btn.classes("flex-grow")
                    solve_btn = ui.button("Auto-aim", icon="my_location")
                    solve_btn.props("color=accent").classes("flex-grow")

                with card("Salvo", "grain").classes("w-full"):
                    with ui.grid(columns=3).classes("gap-2 w-full"):
                        num(extra, "salvo_count", "Shots", step=1, min=1, max=8,
                            help=H.SALVO["salvo_count"])
                        num(extra, "salvo_stagger", "Stagger", unit="s", step=0.5,
                            help=H.SALVO["salvo_stagger"])
                        num(extra, "salvo_spread", "Spread", unit="°", step=1,
                            help=H.SALVO["salvo_spread"])
                    salvo_btn = ui.button("Fire salvo", icon="whatshot")
                    salvo_btn.props("color=warning").classes("w-full")

                with card("Monte-Carlo Pk", "casino").classes("w-full"):
                    with ui.grid(columns=3).classes("gap-2 w-full"):
                        num(extra, "mc_trials", "Trials", step=10, min=10, max=1000,
                            help=H.SALVO["mc_trials"])
                        num(extra, "mc_pos_sigma", "σ pos", unit="m", step=25,
                            help=H.SALVO["mc_pos_sigma"])
                        num(extra, "mc_vel_sigma", "σ vel", unit="m/s", step=5,
                            help=H.SALVO["mc_vel_sigma"])
                    mc_btn = ui.button("Run Monte-Carlo", icon="analytics")
                    mc_btn.props("color=secondary").classes("w-full")

            results = ui.column().classes("flex-grow gap-3 min-w-[420px]")

    # ---- actions -------------------------------------------------------- #
    async def _run(btn, mode, fn, req):
        btn.props("loading")
        try:
            data = await run.io_bound(fn, req)
            result.update(mode=mode, data=data)
        except Exception as exc:  # noqa: BLE001
            ui.notify(str(exc), type="negative", multi_line=True)
            return
        finally:
            btn.props(remove="loading")
        render()

    async def engage():
        await _run(run_btn, "engage", eng_simulate,
                   EngagementRequest.model_validate(state))

    async def autoaim():
        await _run(solve_btn, "solve", eng_solve,
                   EngagementRequest.model_validate(state))

    async def fire_salvo():
        req = SalvoRequest.model_validate(
            {
                "engagement": state,
                "count": int(extra["salvo_count"]),
                "stagger": extra["salvo_stagger"],
                "elevation_spread": extra["salvo_spread"],
                "auto_aim": True,
            }
        )
        await _run(salvo_btn, "salvo", eng_salvo, req)

    async def run_mc():
        req = MonteCarloRequest.model_validate(
            {
                "engagement": state,
                "trials": int(extra["mc_trials"]),
                "position_sigma": extra["mc_pos_sigma"],
                "velocity_sigma": extra["mc_vel_sigma"],
                "seed": 0,
            }
        )
        await _run(mc_btn, "montecarlo", eng_montecarlo, req)

    # ---- rendering ------------------------------------------------------ #
    def render():
        results.clear()
        mode, data = result["mode"], result["data"]
        with results:
            if mode in ("engage", "solve"):
                _render_engagement(mode, data, state)
            elif mode == "salvo":
                _render_salvo(data)
            elif mode == "montecarlo":
                _render_montecarlo(data)

    run_btn.on_click(engage)
    solve_btn.on_click(autoaim)
    salvo_btn.on_click(fire_salvo)
    mc_btn.on_click(run_mc)


def _ground(positions: list[list[float]], origin: list[float]) -> list[float]:
    return [math.hypot(p[0] - origin[0], p[1] - origin[1]) for p in positions]


def _render_engagement(mode: str, data: dict, state: dict) -> None:
    eng = data["engagement"] if mode == "solve" else data
    s = eng["summary"]
    hit = s["intercepted"]
    verdict = "✓ INTERCEPT" if hit else "✗ MISS"
    ui.label(verdict).classes(
        "text-2xl font-bold " + ("text-green-600" if hit else "text-red-600")
    )
    if mode == "solve":
        stats_row(
            [
                ("Elevation", f"{data['elevation_deg']:.1f}°"),
                ("Azimuth", f"{data['azimuth_deg']:.1f}°"),
                ("Miss", f"{data['miss_distance']:.1f} m"),
                ("Intercept t", f"{data['intercept_time']:.2f} s"),
            ]
        )
    stats_row(
        [
            ("Miss distance", f"{s['miss_distance']:.2f} m"),
            ("Intercept time", f"{s['intercept_time']:.2f} s"),
            ("Closing speed", f"{s['closing_speed_at_intercept']:.0f} m/s"),
        ]
    )

    launch = state["interceptor"]["launch_position"]
    ipos = eng["interceptor_position"]
    tpos = eng["target_position"]
    ig = _ground(ipos, launch)
    tg = _ground(tpos, launch)
    marker2d, marker3d = [], []
    if hit:
        ip = s["intercept_point"]
        marker2d = [{"x": math.hypot(ip[0] - launch[0], ip[1] - launch[1]),
                     "y": ip[2], "label": "intercept"}]
        marker3d = [{"x": ip[0], "y": ip[1], "z": ip[2], "label": "intercept"}]

    with ui.tabs().classes("w-full") as tabs:
        ui.tab("3D", icon="3d_rotation")
        ui.tab("Profile", icon="show_chart")
        ui.tab("Separation", icon="straighten")
        ui.tab("Speed", icon="speed")
        if mode == "solve":
            ui.tab("Envelope", icon="radar")
    with ui.tab_panels(tabs, value="3D").classes("w-full"):
        with ui.tab_panel("3D"):
            ui.label(
                "▶ Press Play to watch the target fly and the interceptor run "
                "it down, or drag the slider to scrub through the engagement."
            ).classes("text-sm text-slate-500")
            plot(
                animated_path3d_fig(
                    [
                        {"label": "Interceptor", "color": PALETTE["indigo"],
                         "x": [p[0] for p in ipos], "y": [p[1] for p in ipos],
                         "z": [p[2] for p in ipos]},
                        {"label": "Target", "color": PALETTE["red"],
                         "x": [p[0] for p in tpos], "y": [p[1] for p in tpos],
                         "z": [p[2] for p in tpos]},
                    ],
                    times=eng["time"],
                    markers=marker3d,
                )
            )
        with ui.tab_panel("Profile"):
            plot(
                xy_fig(
                    "Ground range (m)", "Altitude (m)",
                    [
                        {"label": "Interceptor", "color": PALETTE["indigo"],
                         "x": ig, "y": [p[2] for p in ipos]},
                        {"label": "Target", "color": PALETTE["red"],
                         "x": tg, "y": [p[2] for p in tpos]},
                    ],
                    markers=marker2d,
                )
            )
        with ui.tab_panel("Separation"):
            plot(
                line_fig(
                    "Time (s)", "Separation (m)",
                    [{"label": "Separation", "color": PALETTE["slate"],
                      "x": eng["time"], "y": eng["separation"]}],
                )
            )
        with ui.tab_panel("Speed"):
            plot(
                line_fig(
                    "Time (s)", "Speed (m/s)",
                    [
                        {"label": "Interceptor", "color": PALETTE["indigo"],
                         "x": eng["time"], "y": eng["interceptor_speed"]},
                        {"label": "Target", "color": PALETTE["red"],
                         "x": eng["time"], "y": eng["target_speed"]},
                    ],
                )
            )
        if mode == "solve":
            with ui.tab_panel("Envelope"):
                env = data["envelope"]
                plot(
                    line_fig(
                        "Launch elevation (°)", "Miss distance (m)",
                        [{"label": "Envelope", "color": PALETTE["violet"],
                          "x": [e["elevation"] for e in env],
                          "y": [e["miss"] for e in env]}],
                    )
                )


def _render_salvo(data: dict) -> None:
    hit = data["intercepted"]
    ui.label("✓ TARGET KILLED" if hit else "✗ LEAKER").classes(
        "text-2xl font-bold " + ("text-green-600" if hit else "text-red-600")
    )
    stats_row(
        [
            ("Shots", str(data["count"])),
            ("Hits", str(data["hits"])),
            ("Pk", f"{data['success_fraction'] * 100:.0f}%"),
            ("Best miss", f"{data['best_miss']:.2f} m"),
            ("Azimuth", f"{data['azimuth_deg']:.1f}°"),
        ]
    )
    columns = [
        {"name": "shot", "label": "Shot", "field": "shot"},
        {"name": "launch", "label": "Launch (s)", "field": "launch"},
        {"name": "elev", "label": "Elevation (°)", "field": "elev"},
        {"name": "miss", "label": "Miss (m)", "field": "miss"},
        {"name": "result", "label": "Result", "field": "result"},
    ]
    rows = [
        {
            "shot": sh["index"] + 1,
            "launch": f"{sh['launch_time']:.1f}",
            "elev": f"{sh['elevation_deg']:.1f}",
            "miss": f"{sh['miss_distance']:.2f}",
            "result": "HIT" if sh["intercepted"] else "miss",
        }
        for sh in data["shots"]
    ]
    ui.table(columns=columns, rows=rows).classes("w-full sim-card")


def _render_montecarlo(data: dict) -> None:
    pk = data["pk"]
    ui.label(f"Pk = {pk * 100:.1f}%").classes(
        "text-2xl font-bold "
        + ("text-green-600" if pk >= 0.5 else "text-amber-600")
    )
    stats_row(
        [
            ("Trials", str(data["trials"])),
            ("Hits", str(data["hits"])),
            ("Mean miss", f"{data['mean_miss']:.1f} m"),
            ("Median miss", f"{data['median_miss']:.1f} m"),
            ("P90 miss", f"{data['p90_miss']:.1f} m"),
            ("Elevation", f"{data['elevation_deg']:.1f}°"),
        ]
    )
    edges = data["histogram_edges"]
    counts = data["histogram_counts"]
    centers = [
        f"{(edges[i] + edges[i + 1]) / 2:.0f}" for i in range(len(counts))
    ]
    plot(bar_fig("Miss distance (m)", "Trials", centers, counts))
