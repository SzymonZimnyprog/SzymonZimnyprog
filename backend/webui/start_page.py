"""Start tab: a plain-language, no-jargon front door for non-experts.

Pick a ready-made scenario or move three everyday sliders; the computer aims the
interceptor for you (fire-control solver) and explains, in plain words, what
happened — with a 3D replay. Everything technical stays on the other tabs.
"""

from __future__ import annotations

import math

from nicegui import run, ui

from backend.routers.engagement import solve as eng_solve
from backend.sim.models import EngagementRequest

from .common import (
    PALETTE,
    animated_path3d_fig,
    card,
    header,
    page_body,
    plot,
    stats_row,
)

POWER_SEGMENTS = {"Small": 3, "Medium": 5, "Large": 7}

SCENARIOS = {
    "🟢 Easy: slow & close": dict(distance_km=6, altitude_km=3, speed=180,
                                  evasive=False, power="Medium"),
    "🔴 Hard: fast & high": dict(distance_km=22, altitude_km=11, speed=600,
                                 evasive=False, power="Large"),
    "🟠 Tricky: dodging": dict(distance_km=12, altitude_km=7, speed=350,
                               evasive=True, power="Large"),
}


@ui.page("/start")
def start_page() -> None:
    header("/start")
    sc = {"distance_km": 12.0, "altitude_km": 7.0, "speed": 300.0,
          "evasive": False, "power": "Medium"}
    refreshers: list = []

    with page_body():
        ui.label("Interceptor simulator — start here").classes("text-3xl font-bold")
        with ui.row().classes("items-start gap-2 max-w-3xl"):
            ui.icon("waving_hand").classes("text-primary text-2xl mt-1")
            ui.label(
                "No rocket science needed. Pick a scenario or move the sliders to "
                "describe an incoming threat. We'll launch an interceptor at it — "
                "the computer does the aiming — and tell you, in plain words, what "
                "happens."
            ).classes("text-base text-slate-600")

        with ui.row().classes("w-full gap-4 items-start"):
            with ui.column().classes("w-[30rem] gap-3"):
                with card("Try a ready-made scenario", "auto_awesome").classes(
                    "w-full"
                ):
                    ui.label("One click — we fill in everything for you.").classes(
                        "text-xs text-slate-500"
                    )
                    with ui.row().classes("flex-wrap gap-2"):
                        for label, preset in SCENARIOS.items():
                            ui.button(
                                label,
                                on_click=lambda _e, p=preset: _scenario(p),
                            ).props("outline no-caps")

                with card("…or describe it yourself", "tune").classes("w-full"):
                    _slider(sc, refreshers, "distance_km",
                            "How far away is the threat?", 2, 35, "km")
                    _slider(sc, refreshers, "altitude_km",
                            "How high is it flying?", 1, 15, "km")
                    _slider(sc, refreshers, "speed",
                            "How fast is it coming at us?", 100, 800, "m/s")
                    ui.switch("It tries to dodge").bind_value(sc, "evasive").tooltip(
                        "The threat jinks to evade — makes the catch harder."
                    )
                    with ui.row().classes("items-center gap-2"):
                        ui.label("Interceptor size:").classes("text-sm")
                        ui.toggle(list(POWER_SEGMENTS), value=sc["power"]).bind_value(
                            sc, "power"
                        ).props("no-caps").tooltip(
                            "Bigger = more motor, reaches farther/faster."
                        )

                launch_btn = ui.button("🚀  Launch the interceptor!").props(
                    "size=lg no-caps"
                ).classes("w-full text-lg")

            results = ui.column().classes("flex-grow gap-3 min-w-[420px]")
            with results:
                ui.label("Press Launch to see what happens.").classes("text-slate-500")

    async def launch() -> None:
        launch_btn.props("loading")
        try:
            req = _build_request(sc)
            sol = await run.io_bound(eng_solve, req)
        except Exception as exc:  # noqa: BLE001
            ui.notify(str(exc), type="negative", multi_line=True)
            return
        finally:
            launch_btn.props(remove="loading")
        _render(results, sol, sc)

    async def _scenario(preset: dict) -> None:
        sc.update(preset)
        for r in refreshers:
            r()
        await launch()

    launch_btn.on_click(launch)


def _slider(target, refreshers, key, label, lo, hi, unit):
    with ui.column().classes("w-full gap-0"):
        lab = ui.label().classes("text-sm font-medium")
        s = ui.slider(min=lo, max=hi, value=target[key]).props("label-always")
        s.bind_value(target, key)

        def _txt() -> None:
            lab.text = f"{label}  —  {target[key]:.0f} {unit}"

        s.on_value_change(lambda _e: _txt())
        refreshers.append(_txt)
        _txt()


def _build_request(sc: dict) -> EngagementRequest:
    d = EngagementRequest().model_dump()
    x = sc["distance_km"] * 1000.0
    z = sc["altitude_km"] * 1000.0
    n = math.hypot(x, z) or 1.0
    speed = sc["speed"]
    d["target"]["position"] = [x, 0.0, z]
    d["target"]["velocity"] = [-x / n * speed, 0.0, -z / n * speed]
    d["target"]["maneuver_accel"] = (
        [0.0, 0.0, 40.0] if sc["evasive"] else [0.0, 0.0, 0.0]
    )
    d["interceptor"]["motor"]["grain"]["segments"] = POWER_SEGMENTS[sc["power"]]
    return EngagementRequest.model_validate(d)


def _render(results, sol: dict, sc: dict) -> None:
    results.clear()
    eng = sol["engagement"]
    s = eng["summary"]
    hit = s["intercepted"]
    miss = s["miss_distance"]
    t = sol["intercept_time"]
    elev = sol["elevation_deg"]
    az = sol["azimuth_deg"]
    ip = s.get("intercept_point", [0, 0, 0])
    rng_km = math.hypot(ip[0], ip[1]) / 1000.0

    with results:
        if hit:
            ui.label("✓ Caught it!").classes("text-3xl font-bold text-green-600")
            ui.label(
                f"The computer aimed the launcher {elev:.0f}° above the horizon "
                f"(pointing {_compass(az)}), fired, and the interceptor met the "
                f"threat about {t:.0f} seconds later, ~{rng_km:.1f} km away. "
                f"Closest approach: {miss:.1f} m — close enough to count as a hit."
            ).classes("text-base text-slate-600 max-w-3xl")
        else:
            ui.label("✗ It got away").classes("text-3xl font-bold text-red-600")
            ui.label(
                f"Even aiming its best ({elev:.0f}° above the horizon), the "
                f"interceptor could only get within {miss:.0f} m of the threat — "
                "not close enough to stop it. Try a closer/slower threat or a "
                "bigger interceptor."
            ).classes("text-base text-slate-600 max-w-3xl")

        stats_row([
            ("Aim (up)", f"{elev:.0f}°"),
            ("Aim (compass)", _compass(az)),
            ("Time to reach", f"{t:.0f} s" if t else "—"),
            ("Closest pass", f"{miss:.0f} m"),
        ])

        ipos = eng["interceptor_position"]
        tpos = eng["target_position"]
        marker = []
        if hit:
            marker = [{"x": ip[0], "y": ip[1], "z": ip[2], "label": "caught here"}]
        ui.label("▶ Press Play to watch it happen in 3D:").classes(
            "text-sm text-slate-500 mt-1"
        )
        plot(
            animated_path3d_fig(
                [
                    {"label": "Our interceptor", "color": PALETTE["indigo"],
                     "x": [p[0] for p in ipos], "y": [p[1] for p in ipos],
                     "z": [p[2] for p in ipos]},
                    {"label": "Incoming threat", "color": PALETTE["red"],
                     "x": [p[0] for p in tpos], "y": [p[1] for p in tpos],
                     "z": [p[2] for p in tpos]},
                ],
                times=eng["time"],
                markers=marker,
            )
        )

        with ui.expansion("What just happened? (in plain words)",
                          icon="help_outline").classes("w-full"):
            for line in _explain(sc, hit):
                ui.label("• " + line).classes("text-sm text-slate-600")


def _compass(az: float) -> str:
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"]
    return dirs[round((az % 360) / 45)]


def _explain(sc: dict, hit: bool) -> list[str]:
    out = [
        "An interceptor is a small rocket that chases another flying object and "
        "tries to pass as close to it as possible.",
        f"You said the threat is {sc['distance_km']:.0f} km away, "
        f"{sc['altitude_km']:.0f} km high, coming in at {sc['speed']:.0f} m/s "
        f"(~{sc['speed'] * 3.6:.0f} km/h).",
        "The computer worked out which direction and angle to fire so the paths "
        "cross — that's the 'aiming' shown in the result.",
        "After launch a 'seeker' watches the threat and steering keeps nudging "
        "the interceptor onto a collision course (this is called proportional "
        "navigation).",
    ]
    if sc["evasive"]:
        out.append("Because the threat was dodging, the interceptor had to keep "
                   "correcting — harder, and it needs energy to spare.")
    out.append(
        "It worked: the two paths met within the catch distance."
        if hit else
        "It fell short — usually too far, too fast, or not enough time to climb "
        "and turn. A bigger interceptor or a closer threat helps."
    )
    return out
