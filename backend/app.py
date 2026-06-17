"""Single-process entry point: FastAPI REST API + NiceGUI web UI.

Run it with::

    python -m backend.app          # http://localhost:8080  (UI + /api + /docs)

or via uvicorn (the ASGI app already has the UI mounted)::

    uvicorn backend.app:app --host 0.0.0.0 --port 8080

The pure-Python UI is served at ``/``; the REST API stays at ``/api/*`` (so the
Simulink/MATLAB ``webwrite`` driver and any other API client keep working), and
the interactive OpenAPI docs remain at ``/docs``.
"""

from __future__ import annotations

from backend import webui
from backend.main import app

# Attach the NiceGUI UI to the existing FastAPI app (registers UI routes).
webui.init(app)


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
