from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import engagement, export, items, missile, motor


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="SzymonZimnyprog Interceptor & Motor Simulator API",
    version="0.2.0",
    description=(
        "Parametric solid-rocket-motor internal ballistics, missile flight "
        "dynamics and proportional-navigation interception simulation, with "
        "CAD (STL/OpenSCAD) and Simulink/MATLAB export."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items.router, prefix="/api/items", tags=["items"])
app.include_router(motor.router, prefix="/api/motor", tags=["motor"])
app.include_router(missile.router, prefix="/api/missile", tags=["missile"])
app.include_router(engagement.router, prefix="/api/engagement", tags=["engagement"])
app.include_router(export.router, prefix="/api/export", tags=["export"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
