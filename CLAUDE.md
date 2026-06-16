# CLAUDE.md

This file provides guidance to AI assistants (Claude, etc.) working in this repository.

## Project Overview

Full-stack web application — a **parametric interceptor-missile & solid-rocket-motor
simulator**:
- **Backend**: Python 3.12 + FastAPI — REST API served at `http://localhost:8000`
- **Frontend**: React 18 + TypeScript + Vite — dev server at `http://localhost:5173`

The frontend proxies all `/api/*` requests to the backend (configured in `vite.config.ts`).

The simulation core (`backend/sim/`) models solid rocket motor internal
ballistics, 3-DOF flight dynamics and proportional-navigation interception, and
exports geometry to **CAD** (STL / OpenSCAD) and time histories to
**Simulink / MATLAB** (CSV, RASP `.eng`, REST driver). See
[`docs/SIMULATION.md`](docs/SIMULATION.md) for the full physics and workflows.
It is an engineering/physics simulator built on standard public models — no
warhead, lethality, fuzing or propellant-manufacturing content; intercept is a
purely kinematic closest-approach criterion.

## Repository Structure

```
/
├── CLAUDE.md                  # This file
├── Makefile                   # Developer shortcuts
├── docker-compose.yml         # Runs backend + frontend together
├── pyproject.toml             # Python tool config (pytest, ruff)
├── .gitignore
│
├── docs/
│   └── SIMULATION.md          # Physics models, CAD & Simulink workflows
│
├── backend/
│   ├── main.py                # FastAPI app entry point (registers routers)
│   ├── requirements.txt       # Production dependencies (incl. numpy)
│   ├── requirements-dev.txt   # Dev/test dependencies
│   ├── .env.example           # Env var template — copy to .env
│   ├── Dockerfile
│   ├── sim/                   # Simulation core (pure Python + numpy)
│   │   ├── atmosphere.py      #   ISA 1976 standard atmosphere
│   │   ├── propellant.py      #   thermochemistry, burn-rate law, presets
│   │   ├── grain.py           #   parametric grain geometry + regression
│   │   ├── motor.py           #   internal ballistics -> thrust curve
│   │   ├── aerodynamics.py    #   Mach-dependent drag model
│   │   ├── dynamics.py        #   3-DOF point-mass flight integrator (RK4)
│   │   ├── guidance.py        #   proportional-navigation guidance law
│   │   ├── engagement.py      #   interceptor-vs-target engagement
│   │   └── models.py          #   Pydantic schemas + builders
│   ├── export/                # CAD + Simulink exporters
│   │   ├── stl.py             #   surface-of-revolution STL meshes
│   │   ├── openscad.py        #   parametric OpenSCAD source
│   │   └── simulink.py        #   CSV, RASP .eng, MATLAB driver
│   ├── routers/
│   │   ├── items.py           # Example CRUD router
│   │   ├── motor.py           # /api/motor
│   │   ├── missile.py         # /api/missile
│   │   ├── engagement.py      # /api/engagement
│   │   └── export.py          # /api/export (CAD + Simulink)
│   └── tests/
│       ├── test_items.py
│       ├── test_motor.py
│       ├── test_missile.py
│       ├── test_engagement.py
│       └── test_export.py
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── eslint.config.js       # ESLint flat config (TS + browser globals)
    ├── Dockerfile
    └── src/
        ├── main.tsx           # React entry point
        ├── App.tsx            # Root component (tabbed shell)
        ├── App.test.tsx       # Component tests (Vitest)
        ├── api.ts             # Typed API client (fetch wrapper)
        ├── defaults.ts        # Default parameter sets
        ├── components/        # NumberField, LineChart, TrajectoryPlot
        ├── pages/             # Motor / Missile / Engagement / Items pages
        ├── index.css
        └── App.css
```

## Development Setup

### First-time setup

```bash
# Create Python virtual env and install all deps
make install
```

### Running locally (two terminals)

```bash
# Terminal 1 — backend (hot reload)
make dev-backend

# Terminal 2 — frontend (HMR)
make dev-frontend
```

### Running with Docker Compose

```bash
make dev
# or
docker compose up --build
```

### Environment variables

```bash
cp backend/.env.example backend/.env
# Edit backend/.env as needed
```

## Testing

```bash
make test          # run all tests
make test-backend  # pytest (backend/tests/)
make test-frontend # vitest (frontend/src/*.test.tsx)
```

Backend tests use FastAPI's `TestClient` (synchronous, no server needed).
Frontend tests use Vitest + React Testing Library.

## Linting & Formatting

```bash
make lint          # ruff check + eslint
make format        # ruff format (Python only)
```

Python: `ruff` (lint + format). Config in `pyproject.toml`.
TypeScript: ESLint. Config in `frontend/.eslintrc` (add as needed).

## Key Conventions

### Backend (Python / FastAPI)

- All routes live in `backend/routers/`. Each file = one logical resource.
- Register routers in `backend/main.py` with a path prefix and tag.
- Use Pydantic models for request/response validation — never raw dicts.
- Use `HTTPException` for error responses with appropriate status codes.
- In-memory store is a placeholder — replace with a real DB (SQLAlchemy + Alembic recommended).

### Frontend (React / TypeScript)

- All API calls go through `src/api.ts` — never call `fetch` directly in components.
- Components live in `src/components/` (create as needed).
- Pages live in `src/pages/` (create as needed when adding routing).
- Use functional components and hooks only — no class components.
- Keep components small and focused; extract logic into custom hooks when reused.

### General

- **No secrets in git** — use `.env` files (covered by `.gitignore`).
- Validate input at boundaries (API and form level); trust internal data.
- Do not add dependencies without a clear reason.

## Git Conventions

### Branch Naming

- `main` — stable production branch
- `feature/<description>` — new features
- `fix/<description>` — bug fixes
- `claude/<session-id>` — AI-assisted branches (auto-generated)

### Commit Messages (Conventional Commits)

```
<type>(<scope>): <summary>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`

```
feat(items): add pagination to list endpoint
fix(frontend): handle 404 gracefully in App
docs: update CLAUDE.md with docker instructions
```

## AI Assistant Guidelines

### Do

- Read a file before editing it.
- Keep changes minimal and focused on what was asked.
- Add new routers under `backend/routers/` and register them in `main.py`.
- Add new React components under `frontend/src/components/`.
- Update this file when making significant architectural decisions.
- Push to the `claude/<session-id>` branch specified in the task.

### Do Not

- Push to `main` without explicit permission.
- Commit `.env` files or secrets.
- Add unnecessary abstractions, helpers, or future-proofing.
- Skip writing tests for new backend routes.
- Use class components on the frontend.
