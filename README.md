# Interceptor & Solid-Motor Simulator

A parametric aerospace-engineering simulation suite built as a full-stack web
app, with **CAD** and **Simulink/MATLAB** export. It models:

- **Solid rocket motor internal ballistics** — parametric grain geometry
  (BATES / TUBULAR / ROD / end-burner), Saint-Robert burn-rate law, equilibrium
  chamber pressure, nozzle thrust coefficient → thrust curve, total impulse,
  Isp, NAR/Tripoli impulse class, and design diagnostics (Kn, port/throat,
  warnings).
- **Missile flight dynamics** — 3-DOF point-mass (RK4), ISA-1976 atmosphere,
  Mach-dependent drag, mass depletion from the motor.
- **Interception** — proportional-navigation homing against a ballistic target,
  plus a **fire-control solver** that computes the launch elevation/azimuth for
  an intercept and returns the launch envelope.

> Physics/kinematics simulator on standard public models (Sutton; Zarchan).
> No warhead, lethality, fuzing or propellant-manufacturing content — intercept
> is a purely kinematic closest-approach criterion.

## Quick start

There are **two ways to run the app**, both backed by the identical Python
simulation core.

### A. Pure Python — one process, no Node (simplest)

The whole app — REST API **and** an interactive web UI — runs from a single
Python process, with the UI built in [NiceGUI](https://nicegui.io). No Node, no
second terminal.

```bash
make install          # python venv (installs the UI too)
make ui               # http://localhost:8080  (UI + /api + Swagger /docs)
```

```powershell
# Windows (PowerShell, no make)
.\setup.ps1           # create .venv + install deps
.\dev-ui.ps1          # http://localhost:8080
```

If you only want the Python app, you can skip Node entirely:
`pip install -r backend/requirements-dev.txt` then `python -m backend.app`.

### B. React frontend + FastAPI backend (two processes)

```bash
make install          # python venv + npm install
make dev-backend      # FastAPI at http://localhost:8000  (Swagger: /docs)
make dev-frontend     # Vite UI  at http://localhost:5173
make test             # backend pytest + frontend vitest
make lint             # ruff + eslint
```

```powershell
# Windows (PowerShell, no make)
.\setup.ps1           # create .venv + install backend & frontend deps
.\dev-backend.ps1     # terminal A — FastAPI at http://localhost:8000
.\dev-frontend.ps1    # terminal B — Vite UI  at http://localhost:5173
```

Run the scripts from the repository root. Prerequisites: Python 3.11+ (use
`py -3` if `python` is not on PATH); Node 18+ only for option **B**. If scripts
are blocked, allow them for the session with
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, or run the
commands inside them directly.

## Web app

The Python UI (`:8080`) opens on a plain-language **Start** tab made for
non-experts: pick a ready-made scenario or move three everyday sliders, hit
**Launch**, and get a plain-words verdict ("✓ Caught it!"), a 3D replay and a
"what just happened?" explainer — the computer does the aiming. The full set of
engineering tabs (shared with the React UI at `:5173`):

- **Interception** — configure interceptor + target, run the engagement, or hit
  **Auto-aim** to compute the firing solution; see an **animated 3D replay** of
  the target flying and the interceptor running it down, plus separation, the
  launch envelope, INTERCEPT/MISS verdict, **Fire salvo** and **Monte-Carlo Pk**.
  (Animated 3D playback is in the Python UI.)
- **Motor** — propellant / grain / nozzle parameters, thrust & pressure curves,
  design diagnostics & warnings, and CAD/Simulink export.
- **Multi-stage** — a stage stack: **Run stack** for the combined thrust
  profile, **Fly stack** to fly the staged flight and jettison spent-stage mass
  at each burnout.
- **Trajectory** — single un-guided missile flight + airframe CAD export.
- **Items** — original demo CRUD resource.

## API

| Endpoint | Purpose |
| --- | --- |
| `POST /api/motor/simulate` | thrust curve + summary |
| `POST /api/motor/sweep` | re-run across one parameter |
| `POST /api/motor/multistage` | combined thrust of a stage stack |
| `GET  /api/motor/presets` | propellant presets |
| `POST /api/missile/simulate` | un-guided trajectory |
| `POST /api/engagement/simulate` | PN interception run |
| `POST /api/engagement/solve` | fire-control firing solution |
| `POST /api/engagement/salvo` | layered salvo, Pk = hits/count |
| `POST /api/engagement/montecarlo` | Pk under track uncertainty |
| `POST /api/export/cad/*.{stl,scad}` | CAD geometry |
| `POST /api/export/simulink/*` | CSV, RASP `.eng`, MATLAB driver |

See [`docs/SIMULATION.md`](docs/SIMULATION.md) for the physics, formulae and the
CAD / Simulink workflows.
