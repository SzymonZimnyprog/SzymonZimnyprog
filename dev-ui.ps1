# Run the pure-Python app: REST API + NiceGUI web UI together (http://localhost:8080).
# No Node and no second terminal needed.
# Run from the repository root:  .\dev-ui.ps1
$ErrorActionPreference = "Stop"
.\.venv\Scripts\python -m backend.app
