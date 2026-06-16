# Start the FastAPI backend with hot reload (http://localhost:8000).
# Run from the repository root:  .\dev-backend.ps1
$ErrorActionPreference = "Stop"
.\.venv\Scripts\python -m uvicorn backend.main:app --reload
