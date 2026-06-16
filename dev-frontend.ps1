# Start the Vite dev server with HMR (http://localhost:5173).
# Run from the repository root:  .\dev-frontend.ps1
$ErrorActionPreference = "Stop"
Push-Location frontend
try {
    npm run dev
}
finally {
    Pop-Location
}
