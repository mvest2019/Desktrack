# =============================================================
# start_server.ps1 — Start backend + frontend (LAN accessible)
# =============================================================
# Run from the Desktrack root folder:
#   .\start_server.ps1
#
# Others on LAN can open: http://<your-ip>:3000
# Desktop app config.ini: api_url = http://<your-ip>:8000
# =============================================================

$root = $PSScriptRoot

# ── Detect LAN IP ────────────────────────────────────────────
$lanIp = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
    Select-Object -First 1).IPAddress

# ── Kill any existing python/node ────────────────────────────
Get-Process python, node -ErrorAction SilentlyContinue | Stop-Process -Force

# ── Start FastAPI backend (port 8000) ────────────────────────
Start-Process powershell -ArgumentList `
    "-NoExit", "-Command", `
    "cd '$root\backend'; pip install -r requirements.txt; python -m uvicorn main:app --host 0.0.0.0 --port 8000" `
    -WindowStyle Normal

# ── Start Next.js frontend (port 3000) ───────────────────────
Start-Process powershell -ArgumentList `
    "-NoExit", "-Command", `
    "cd '$root\frontend'; npm install; npm run dev -- -H 0.0.0.0" `
    -WindowStyle Normal

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Syntra LAN Server started!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Your LAN IP : $lanIp" -ForegroundColor Yellow
Write-Host "  Frontend    : http://${lanIp}:3000" -ForegroundColor Green
Write-Host "  Backend     : http://${lanIp}:8000" -ForegroundColor Green
Write-Host ""
Write-Host "  Desktop app config.ini on client PCs:" -ForegroundColor Gray
Write-Host "    api_url = http://${lanIp}:8000" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Keep both PowerShell windows open." -ForegroundColor Yellow
Write-Host "Closing them stops the services." -ForegroundColor Yellow
