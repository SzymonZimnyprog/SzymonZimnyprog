# Interceptor & Solid-Motor Simulator

A parametric aerospace-engineering simulation suite: solid rocket motor
internal ballistics, missile flight dynamics, and proportional-navigation
interception — driveable from the **web app**, exportable to **CAD**
(STL / OpenSCAD), and to **Simulink / MATLAB** (CSV, RASP `.eng`, REST driver).

> **Scope.** This is a physics/kinematics simulator built on standard,
> publicly documented engineering models (Sutton, *Rocket Propulsion
> Elements*; Zarchan, *Tactical and Strategic Missile Guidance*). It models
> propulsion, atmospheric flight and guidance *control laws*. It contains no
> warhead, lethality, fuzing or propellant-manufacturing content — intercept
> is a purely kinematic closest-approach criterion.

## Architecture

```
backend/sim/        physics core (pure Python + numpy)
  atmosphere.py     ISA 1976 standard atmosphere
  propellant.py     propellant thermochemistry + burn-rate law, presets
  grain.py          parametric grain geometry + surface regression
  motor.py          internal ballistics -> thrust curve, Isp, total impulse
  aerodynamics.py   Mach-dependent drag model
  dynamics.py       3-DOF point-mass flight integrator (RK4)
  guidance.py       proportional-navigation guidance law
  engagement.py     interceptor-vs-target engagement
  models.py         Pydantic request/response schemas + builders

backend/export/     stl.py (mesh), openscad.py (parametric), simulink.py
backend/routers/    motor, missile, engagement, export
frontend/src/       React UI (tabs: Interception / Motor / Trajectory / Items)
```

## Physics models

### Solid rocket motor (`/api/motor/simulate`)

Quasi-steady lumped-parameter internal ballistics:

| Quantity | Relation |
| --- | --- |
| Burn rate | `r = a · Pc^n` (Saint-Robert) |
| Equilibrium chamber pressure | `Pc = (ρ_p · A_b · a · c* / A_t)^(1/(1−n))` |
| Choked mass flow | `ṁ = Pc · A_t / c*` |
| Characteristic velocity | `c* = √(R·T0) / Γ(γ) · η_c*` |
| Thrust | `F = C_f · A_t · Pc` |

`C_f` includes the ideal-expansion momentum term plus an ambient-pressure
correction; the nozzle exit Mach number is solved from the area-ratio relation.
Outputs: thrust / pressure / mass-flow / Kn vs time, total impulse, NAR/Tripoli
impulse class, specific impulse, peak thrust and pressure.

Grain types (all with exact regression geometry):

| Type | Burning surfaces | Thrust character |
| --- | --- | --- |
| `BATES` | central bore + end faces | mildly progressive→neutral |
| `TUBULAR` | inner + outer + ends | progressive, short/high-Pc |
| `ROD` | outer surface + ends | regressive |
| `END_BURNER` | one face only | long, low, near-constant |

A **Summerfield separation** clamp prevents the unphysical negative thrust a
lumped model would otherwise predict for a grossly over-expanded nozzle.

### Multi-stage stack (`POST /api/motor/multistage`)

Builds the combined thrust profile of a sequential stage stack (e.g. a boosted
sustainer): stage *i* ignites after stage *i−1* burns out plus its coast
`ignition_delay`. Returns the combined (downsampled) thrust curve, per-stage
timing/impulse, and the stack totals. In the web app: the **Multi-stage** tab.

### Staged flight (`POST /api/missile/multistage`)

Flies the staged stack with the flight integrator, jettisoning each spent
stage's `structural_mass` at its burnout (the last stage is kept unless
`drop_last_stage`). Returns the trajectory plus the separation events
(time / altitude / mass after jettison) — showing the apogee/velocity gain that
staging buys over a single grain of the same propellant.

### Design sweep (`POST /api/motor/sweep`)

Re-runs the motor across a list of values for one parameter
(`nozzle.throat_diameter`, `nozzle.expansion_ratio`, `grain.core_diameter`,
`grain.outer_diameter`, `grain.segment_length`, `grain.segments`,
`propellant.n`, `altitude`) and returns the summary metrics for each — e.g. the
classic peak-pressure-vs-throat-area trade. Exposed in the web app as the
**Design sweep** panel on the Motor tab.

### Missile trajectory (`/api/missile/simulate`)

3-DOF point-mass flight in an ENU flat-earth frame, RK4-integrated. Thrust acts
along the velocity vector (along the launch direction before lift-off), with
ISA atmosphere, Mach-dependent drag and mass depletion from the motor mass-flow.

### Interception (`/api/engagement/simulate`)

Interceptor and target are propagated together. The interceptor boosts on its
solid motor, then homes using **true proportional navigation**:

```
Ω      = (R × V) / (R · R)        # line-of-sight rate
V_c    = −(R · V) / |R|           # closing speed
a_cmd  = N · V_c · (Ω × R̂)        # perpendicular to LOS, |a| ≤ g_max
```

The target flies a ballistic arc (gravity + drag) with an optional constant
manoeuvre acceleration. The run stops at closest approach; if that distance is
inside `lethal_radius` the engagement is reported as an intercept.

### Fire-control solver (`POST /api/engagement/solve`)

Closes the loop into an interception *system*: given the target state, it
computes the launch **azimuth** (from the target bearing) and searches the
launch **elevation** that minimises miss distance. The motor thrust curve is
built once and reused — only the launch direction is varied per evaluation
(coarse elevation scan → golden-section refinement → small azimuth refinement).
Returns the firing solution, the launch **envelope** (miss vs elevation) and
the full engagement at the solution for plotting. In the web app this is the
**Auto-aim** button on the Interception tab.

### Salvo / layered defence (`POST /api/engagement/salvo`)

Fires `count` interceptors from one site, `stagger` seconds apart, with launch
elevations spread symmetrically about the (auto-aimed) nominal solution. Each
later shot engages the target where it has moved to by its launch time
(`advance_target`). Reports per-shot outcome, number of hits and a kill
probability `Pk = hits / count`. In the web app: **Fire salvo** on the
Interception tab.

### Monte-Carlo Pk (`POST /api/engagement/montecarlo`)

The launcher aims once at the estimated (nominal) track; the true target is
then drawn `trials` times by adding Gaussian noise (`position_sigma`,
`velocity_sigma`) and flown against the fixed firing solution. Returns the kill
probability, miss-distance statistics (mean / median / p90) and a histogram.
The closest approach is computed analytically per step (closest point of
approach), so the miss distance — and therefore Pk — is accurate regardless of
the integration step. In the web app: **Run Monte-Carlo** on the Interception
tab.

## CAD workflow

Every motor/airframe parameter set can be exported as geometry:

* **STL** (`/api/export/cad/{grain,nozzle,airframe}.stl`) — watertight meshes by
  surface-of-revolution; import into any CAD/slicer.
* **OpenSCAD** (`/api/export/cad/{grain,nozzle,airframe}.scad`) — *parametric*,
  editable source with every dimension as a named variable at the top of the
  file. Open in OpenSCAD or import into FreeCAD to keep iterating.

In the web app, run a motor/trajectory simulation and use the **Export**
buttons. Programmatically:

```bash
curl -X POST localhost:8000/api/export/cad/nozzle.scad \
  -H 'Content-Type: application/json' -d @motor.json -o nozzle.scad
openscad nozzle.scad
```

## Simulink / MATLAB workflow

Three integration paths:

1. **RASP `.eng`** (`/api/export/simulink/motor.eng`) — the standard motor file
   read by OpenRocket / ThrustCurve.org and importable into Simulink with
   `readmatrix`.
2. **CSV** (`thrust_curve.csv`, `engagement.csv`) — load with
   `readtimetable` / `readmatrix` and feed `From Workspace` blocks.
3. **Live REST driver** (`/api/export/simulink/driver.m`) — `szymon_sim_driver.m`
   calls the running API with `webwrite` and lands the results in the MATLAB
   workspace as `timeseries` objects:

```matlab
% start the backend first (make dev-backend)
out = szymon_sim_driver('motor');              % default motor
plot(out.thrust_ts);                            % thrust curve
out = szymon_sim_driver('engagement', req);    % req: scenario struct
% interceptor_ts / target_ts / separation_ts are now in the base workspace,
% ready for Simulink "From Workspace" blocks.
```

## Running

```bash
make install
make dev-backend     # http://localhost:8000  (Swagger at /docs)
make dev-frontend    # http://localhost:5173
make test            # backend pytest + frontend vitest
make lint            # ruff + eslint
```
