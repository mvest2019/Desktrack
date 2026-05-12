@echo off
cd /d "%~dp0"

:: Read API_URL from api.env
set API_URL=http://localhost:8000
for /f "tokens=1,* delims==" %%A in ('findstr /i "API_URL" api.env') do (
    if /i "%%A"=="API_URL" set API_URL=%%B
)
echo API_URL = %API_URL%

set PYTHONIOENCODING=utf-8

start "Backend"  cmd /k "set PYTHONIOENCODING=utf-8 && set API_URL=%API_URL% && cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000"
start "Frontend" cmd /k "set BACKEND_URL=%API_URL% && cd frontend && npm run dev"
start "Desktop"  cmd /k "set PYTHONIOENCODING=utf-8 && set API_URL=%API_URL% && cd desktop && python app.py"

echo All 3 services started!
