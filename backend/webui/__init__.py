"""Pure-Python NiceGUI web UI mounted onto the existing FastAPI app.

Importing the page modules registers their ``@ui.page`` routes. :func:`init`
attaches NiceGUI to a FastAPI application so the REST API (``/api/*``) and the
interactive UI (served at ``/``) run in a single process.
"""

from __future__ import annotations

from fastapi import FastAPI
from nicegui import ui

# Importing the modules registers the @ui.page routes as a side effect.
from . import (  # noqa: F401
    engagement_page,
    items_page,
    missile_page,
    motor_page,
    stack_page,
)


def init(app: FastAPI) -> None:
    """Mount the NiceGUI UI onto ``app`` (keeps all existing /api routes)."""
    ui.run_with(
        app,
        title="Interceptor & Solid-Motor Simulator",
        dark=None,
        storage_secret="szymon-interceptor-sim",
    )
