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

```bash
make install          # python venv + npm install
make dev-backend      # FastAPI at http://localhost:8000  (Swagger: /docs)
make dev-frontend     # Vite UI  at http://localhost:5173
make test             # backend pytest + frontend vitest
make lint             # ruff + eslint
```

## Web app

Four tabs:

- **Interception** — configure interceptor + target, run the engagement, or hit
  **Auto-aim** to compute the firing solution; see trajectories, separation,
  the launch envelope, and INTERCEPT/MISS verdict. Export engagement CSV and a
  MATLAB driver.
- **Motor** — propellant / grain / nozzle parameters, thrust & pressure curves,
  design diagnostics & warnings, a **Design sweep** panel, and CAD/Simulink
  export.
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
