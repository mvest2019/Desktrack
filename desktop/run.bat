@echo off
title Realisieren Pulse — Desktop App
cd /d "%~dp0"

echo.
echo  ==========================================
echo   Realisieren Pulse Desktop App  [Dev Mode]
echo  ==========================================
echo.

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found. Install Python and add it to PATH.
    pause
    exit /b 1
)

:: Install / update dependencies silently if anything is missing
echo  Checking dependencies...
pip install -r requirements.txt -q --disable-pip-version-check
echo  Dependencies OK.
echo.

:: Run the app
echo  Launching app...
echo.
python app.py

:: If the app crashes, keep the window open so you can read the error
if errorlevel 1 (
    echo.
    echo  ==========================================
    echo   APP CRASHED - see error above
    echo  ==========================================
    pause
)
