# start.ps1 — Launch all 3 services in separate PowerShell windows

$root = $PSScriptRoot

# ── Read API_URL from api.env ────────────────────────────────
$apiUrl = "http://localhost:8000"  # fallback default
$envFile = "$root\api.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*API_URL\s*=\s*(.+)$') {
            $apiUrl = $matches[1].Trim()
        }
    }
}
Write-Host "API_URL = $apiUrl" -ForegroundColor Cyan

# ── Backend ──────────────────────────────────────────────────
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "`$env:PYTHONIOENCODING='utf-8'; `$env:API_URL='$apiUrl'; cd '$root\backend'; python -m uvicorn main:app --host 0.0.0.0 --port 8000" `
    -WindowStyle Normal

# ── Frontend ─────────────────────────────────────────────────
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "`$env:BACKEND_URL='$apiUrl'; cd '$root\frontend'; npm run dev" `
    -WindowStyle Normal

# ── Desktop ──────────────────────────────────────────────────
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "`$env:PYTHONIOENCODING='utf-8'; `$env:API_URL='$apiUrl'; cd '$root\desktop'; python app.py" `
    -WindowStyle Normal

Write-Host "All 3 services started (API_URL=$apiUrl)" -ForegroundColor Green
