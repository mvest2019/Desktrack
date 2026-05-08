# start.ps1 — Launch all 3 services in separate PowerShell windows

$root = $PSScriptRoot

# Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; python -m uvicorn main:app --port 8000" -WindowStyle Normal

# Frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev" -WindowStyle Normal

# Desktop
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\desktop'; python app.py" -WindowStyle Normal

Write-Host "All 3 services started in separate windows."
