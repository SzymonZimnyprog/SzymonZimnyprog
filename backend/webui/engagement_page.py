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

from .common import (
    PALETTE,
    bar_fig,
    header,
    line_fig,
    num,
    page_intro,
    stats_row,
    xy_fig,
)
from .motor_page import motor_form

AXES = ["E", "N", "Up"]


def vec_inputs(label: str, vec: list, unit: str) -> None:
    ui.label(f"{label} ({unit})").classes("text-sm font-medium mt-1")
    with ui.grid(columns=3).classes("gap-2 w-full"):
        for i, axis in enumerate(AXES):
            ui.number(label=axis, value=vec[i], step=10).classes("w-full").on(
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

    page_intro(
        "Interception",
        "Proportional-navigation homing against a ballistic target. Run a single "
        "engagement, auto-aim the launch elevation/azimuth, fire a layered salvo, "
        "or estimate kill probability under track uncertainty.",
    )

    with ui.row().classes("w-full gap-4 no-wrap items-start"):
        with ui.column().classes("w-[28rem] gap-2"):
            interceptor = state["interceptor"]
            target = state["target"]

            with ui.card().classes("w-full"):
                ui.label("Interceptor").classes("font-semibold")
                with ui.expansion("Boost motor", icon="rocket").classes("w-full"):
                    motor_form(interceptor["motor"])
                ui.label("Airframe").classes("font-semibold mt-1")
                with ui.grid(columns=3).classes("gap-2 w-full"):
                    num(interceptor["airframe"], "diameter", "Dia", unit="m", step=0.01)
                    num(interceptor["airframe"], "cd0", "Cd0", step=0.01)
                    num(interceptor["airframe"], "dry_mass", "Dry", unit="kg", step=1)
                vec_inputs("Launch position", interceptor["launch_position"], "m")
                ui.label("Launch & guidance").classes("font-semibold mt-1")
                with ui.grid(columns=2).classes("gap-2 w-full"):
                    num(interceptor, "launch_speed", "Rail speed", unit="m/s", step=5)
                    num(interceptor, "elevation_deg", "Elevation", unit="°", step=1,
                        min=0, max=90)
                    num(interceptor, "azimuth_deg", "Azimuth", unit="°", step=5)
                    num(interceptor, "nav_constant", "Nav constant N", step=0.5)
                    num(interceptor, "max_lateral_g", "Max lateral g", step=5)
                    num(interceptor, "seeker_delay", "Seeker delay", unit="s", step=0.1)

            with ui.card().classes("w-full"):
                ui.label("Target").classes("font-semibold")
                vec_inputs("Position", target["position"], "m")
                vec_inputs("Velocity", target["velocity"], "m/s")
                vec_inputs("Maneuver accel", target["maneuver_accel"], "m/s²")
                with ui.grid(columns=3).classes("gap-2 w-full"):
                    num(target, "diameter", "Dia", unit="m", step=0.05)
                    num(target, "cd0", "Cd0", step=0.05)
                    num(target, "mass", "Mass", unit="kg", step=10)

            with ui.card().classes("w-full"):
                ui.label("Engagement").classes("font-semibold")
                with ui.grid(columns=3).classes("gap-2 w-full"):
                    num(state, "dt", "dt", unit="s", step=0.005)
                    num(state, "max_time", "Max t", unit="s", step=10)
                    num(state, "lethal_radius", "Lethal R", unit="m", step=1)

            with ui.row().classes("w-full gap-2 no-wrap"):
                run_btn = ui.button("Engage").classes("flex-grow")
                solve_btn = ui.button("Auto-aim").props("color=violet").classes(
                    "flex-grow"
                )

            with ui.card().classes("w-full"):
                ui.label("Salvo").classes("font-semibold")
                with ui.grid(columns=3).classes("gap-2 w-full"):
                    num(extra, "salvo_count", "Shots", step=1, min=1, max=8)
                    num(extra, "salvo_stagger", "Stagger", unit="s", step=0.5)
                    num(extra, "salvo_spread", "Spread", unit="°", step=1)
                salvo_btn = ui.button("Fire salvo").props("color=amber")
                salvo_btn.classes("w-full")

            with ui.card().classes("w-full"):
                ui.label("Monte-Carlo Pk").classes("font-semibold")
                with ui.grid(columns=3).classes("gap-2 w-full"):
                    num(extra, "mc_trials", "Trials", step=10, min=10, max=1000)
                    num(extra, "mc_pos_sigma", "σ pos", unit="m", step=25)
                    num(extra, "mc_vel_sigma", "σ vel", unit="m/s", step=5)
                mc_btn = ui.button("Run Monte-Carlo").props("color=sky")
                mc_btn.classes("w-full")

        results = ui.column().classes("flex-grow gap-3")

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
    ig = _ground(eng["interceptor_position"], launch)
    tg = _ground(eng["target_position"], launch)
    markers = []
    if hit:
        ip = eng["summary"]["intercept_point"]
        markers = [
            {
                "x": math.hypot(ip[0] - launch[0], ip[1] - launch[1]),
                "y": ip[2],
                "label": "intercept",
            }
        ]
    ui.plotly(
        xy_fig(
            "Ground range (m)",
            "Altitude (m)",
            [
                {"label": "Interceptor", "color": PALETTE["indigo"],
                 "x": ig, "y": [p[2] for p in eng["interceptor_position"]]},
                {"label": "Target", "color": PALETTE["red"],
                 "x": tg, "y": [p[2] for p in eng["target_position"]]},
            ],
            markers=markers,
        )
    ).classes("w-full")
    ui.plotly(
        line_fig(
            "Time (s)",
            "Separation (m)",
            [{"label": "Separation", "color": PALETTE["slate"],
              "x": eng["time"], "y": eng["separation"]}],
        )
    ).classes("w-full")
    ui.plotly(
        line_fig(
            "Time (s)",
            "Speed (m/s)",
            [
                {"label": "Interceptor", "color": PALETTE["indigo"],
                 "x": eng["time"], "y": eng["interceptor_speed"]},
                {"label": "Target", "color": PALETTE["red"],
                 "x": eng["time"], "y": eng["target_speed"]},
            ],
        )
    ).classes("w-full")

    if mode == "solve":
        env = data["envelope"]
        ui.plotly(
            line_fig(
                "Launch elevation (°)",
                "Miss distance (m)",
                [{"label": "Envelope", "color": PALETTE["violet"],
                  "x": [e["elevation"] for e in env],
                  "y": [e["miss"] for e in env]}],
            )
        ).classes("w-full")


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
    ui.table(columns=columns, rows=rows).classes("w-full")


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
    ui.plotly(
        bar_fig("Miss distance (m)", "Trials", centers, counts)
    ).classes("w-full")
