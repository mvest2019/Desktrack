# =============================================================
# build_exe.ps1  — One-click EXE builder for Syntra desktop app
# =============================================================
# Run this from the desktop\ folder:
#   cd desktop
#   .\build_exe.ps1
#
# What it does:
#   1. Checks that PyInstaller is installed
#   2. Cleans old build artifacts
#   3. Runs PyInstaller with our syntra.spec
#   4. Tells you where the EXE is
#
# The resulting EXE is:  desktop\dist\Syntra.exe
# =============================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Syntra EXE Builder" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Make sure we are in the desktop\ folder ─────────
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
Write-Host "[1/4] Working directory: $scriptDir" -ForegroundColor Green

# ── Step 2: Install / verify PyInstaller ────────────────────
Write-Host "[2/4] Checking PyInstaller..." -ForegroundColor Green
$pyinstaller = Get-Command pyinstaller -ErrorAction SilentlyContinue
if (-not $pyinstaller) {
    Write-Host "      PyInstaller not found. Installing..." -ForegroundColor Yellow
    pip install pyinstaller
    Write-Host "      PyInstaller installed." -ForegroundColor Green
} else {
    Write-Host "      PyInstaller is ready." -ForegroundColor Green
}

# ── Step 3: Clean previous build output ─────────────────────
Write-Host "[3/4] Cleaning old build artifacts..." -ForegroundColor Green
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist")  { Remove-Item "dist"  -Recurse -Force }
Write-Host "      Cleaned." -ForegroundColor Green

# ── Step 4: Run PyInstaller ──────────────────────────────────
Write-Host "[4/4] Building EXE with PyInstaller..." -ForegroundColor Green
Write-Host ""

pyinstaller syntra.spec

Write-Host ""
if (Test-Path "dist\Syntra.exe") {
    $exePath = Resolve-Path "dist\Syntra.exe"
    $exeSize = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  BUILD SUCCESSFUL!" -ForegroundColor Green
    Write-Host "  EXE: $exePath" -ForegroundColor Green
    Write-Host "  Size: ${exeSize} MB" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next step:" -ForegroundColor Yellow
    Write-Host "  Open Inno Setup Compiler → File → Open → installer.iss" -ForegroundColor Yellow
    Write-Host "  Then: Build → Compile" -ForegroundColor Yellow
    Write-Host "  Output: installer_output\SyntraSetup.exe" -ForegroundColor Yellow
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  BUILD FAILED! Check errors above." -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    exit 1
}
