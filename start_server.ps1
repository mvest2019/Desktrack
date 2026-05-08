# =============================================================
# start_server.ps1 — Start backend + frontend on Windows Server
# =============================================================
# Run this ONCE to start both services.
# They run in separate PowerShell windows that stay open.
#
# FIRST TIME ONLY — run these before this script:
#   pip install -r backend\requirements.txt
#   cd frontend ; npm install ; npm run build ; cd ..
#
# EVERY TIME after reboot or to restart:
#   .\start_server.ps1
# =============================================================

$root = $PSScriptRoot

# ── Check .env exists ────────────────────────────────────────
if (-not (Test-Path "$root\backend\.env")) {
    Write-Host "ERROR: backend\.env not found!" -ForegroundColor Red
    Write-Host "Copy backend\.env.staging to backend\.env and fill in values." -ForegroundColor Yellow
    exit 1
}

# ── Start FastAPI backend (port 8000) ────────────────────────
Write-Host "Starting backend on port 8000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList `
    "-NoExit", "-Command", `
    "cd '$root\backend'; `$env:PYTHONUNBUFFERED=1; python -m uvicorn main:app --host 0.0.0.0 --port 8000" `
    -WindowStyle Normal

Start-Sleep -Seconds 3

# ── Start Next.js frontend (port 3000) ───────────────────────
# Uses `npm start` (production) not `npm run dev`
Write-Host "Starting frontend on port 3000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList `
    "-NoExit", "-Command", `
    "cd '$root\frontend'; npm start" `
    -WindowStyle Normal

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  SERVICES STARTED" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor Green
Write-Host "" -ForegroundColor Green
Write-Host "  From other machines:" -ForegroundColor Green
Write-Host "  Backend:  http://108.181.168.43:8000" -ForegroundColor Green
Write-Host "  Frontend: http://108.181.168.43:3000" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Keep both PowerShell windows open." -ForegroundColor Yellow
Write-Host "Closing them stops the services." -ForegroundColor Yellow
