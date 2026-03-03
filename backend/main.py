from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.routers import items


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="SzymonZimnyprog API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(items.router, prefix="/api/items", tags=["items"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
