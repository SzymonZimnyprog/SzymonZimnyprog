# First-time setup for Windows / PowerShell.
# Run from the repository root:  .\setup.ps1
$ErrorActionPreference = "Stop"

Write-Host "Creating Python virtual environment (.venv)..."
python -m venv .venv

Write-Host "Installing backend dependencies..."
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r backend\requirements-dev.txt

Write-Host "Installing frontend dependencies..."
Push-Location frontend
npm install
Pop-Location

Write-Host ""
Write-Host "Setup complete. Open two terminals and run:"
Write-Host "  .\dev-backend.ps1     (http://localhost:8000)"
Write-Host "  .\dev-frontend.ps1    (http://localhost:5173)"
