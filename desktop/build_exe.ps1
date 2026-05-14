# =============================================================
# build_exe.ps1  — One-click EXE builder for Realisieren Pulse desktop app
# =============================================================
# Run this from the desktop\ folder:
#   cd desktop
#   .\build_exe.ps1
#
# What it does:
#   1. Checks that PyInstaller is installed
#   2. Cleans old build artifacts
#   3. Runs PyInstaller with our realisieren-pulse.spec
#   4. Tells you where the EXE is
#
# The resulting EXE is:  desktop\dist\RealisierenPulse.exe
# =============================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Realisieren Pulse EXE Builder" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Make sure we are in the desktop\ folder ─────────
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
Write-Host "[1/4] Working directory: $scriptDir" -ForegroundColor Green

# ── Step 2: Install ALL dependencies first ───────────────────
Write-Host "[2/4] Installing all required packages..." -ForegroundColor Green
pip install `
    "Pillow>=11.0.0" `
    customtkinter `
    pyautogui `
    requests `
    pynput `
    pywin32 `
    psutil `
    uiautomation `
    pyinstaller
Write-Host "      All packages installed." -ForegroundColor Green

# ── Step 3: Convert PNG icon → ICO (realisieren-pulse.spec and installer.iss need .ico) ─
Write-Host "[3/5] Converting PNG icon to ICO format..." -ForegroundColor Green
if (-not (Test-Path "assets")) { New-Item -ItemType Directory -Path "assets" | Out-Null }
$pngSource = "..\imgs\app_icon.png"
$icoTarget = "assets\icon.ico"
if (Test-Path $pngSource) {
    # Temporarily allow errors so we can check $LASTEXITCODE ourselves
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    python -c "from PIL import Image; img = Image.open(r'$pngSource').convert('RGBA'); img.save(r'$icoTarget', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]); print('Icon converted.')"
    $ErrorActionPreference = $prev
    if ($LASTEXITCODE -eq 0 -and (Test-Path $icoTarget)) {
        Write-Host "      Icon created: $icoTarget" -ForegroundColor Green
    } else {
        Write-Host "      WARNING: Icon conversion failed (Pillow not installed?)." -ForegroundColor Yellow
        Write-Host "      Run: pip install 'Pillow>=11.0.0'  then re-run this script." -ForegroundColor Yellow
        Write-Host "      Continuing without icon..." -ForegroundColor Yellow
    }
} else {
    Write-Host "      WARNING: $pngSource not found. EXE will have no custom icon." -ForegroundColor Yellow
}

# ── Step 4: Clean previous build output ─────────────────────
Write-Host "[4/5] Cleaning old build artifacts..." -ForegroundColor Green
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist")  { Remove-Item "dist"  -Recurse -Force }
Write-Host "      Cleaned." -ForegroundColor Green

# ── Step 5: Run PyInstaller ──────────────────────────────────
Write-Host "[5/5] Building EXE with PyInstaller..." -ForegroundColor Green
Write-Host ""

python -m PyInstaller realisieren-pulse.spec

Write-Host ""
if (-not (Test-Path "dist\RealisierenPulse.exe")) {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  BUILD FAILED! Check errors above." -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    exit 1
}

# Copy config.ini next to the EXE so interval/URL overrides are always present
Copy-Item "config.ini" "dist\config.ini" -Force
Write-Host "      config.ini copied to dist\" -ForegroundColor Green

$exePath = Resolve-Path "dist\RealisierenPulse.exe"
$exeSize = [math]::Round((Get-Item $exePath).Length / 1MB, 1)
Write-Host "========================================" -ForegroundColor Green
Write-Host "  EXE BUILD SUCCESSFUL! ($exeSize MB)" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# ── Step 6: Compile installer with Inno Setup (automatic) ────
Write-Host "[6/6] Compiling installer with Inno Setup..." -ForegroundColor Green

$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    $iscc = "C:\Program Files\Inno Setup 6\ISCC.exe"
}

if (Test-Path $iscc) {
    if (Test-Path "installer_output") { Remove-Item "installer_output" -Recurse -Force }
    & $iscc "installer.iss"
    if (Test-Path "installer_output\RealisierenPulseSetup.exe") {
        $setupPath = Resolve-Path "installer_output\RealisierenPulseSetup.exe"
        $setupSize = [math]::Round((Get-Item $setupPath).Length / 1MB, 1)
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  ALL DONE!" -ForegroundColor Green
        Write-Host "  Installer: $setupPath" -ForegroundColor Green
        Write-Host "  Size: ${setupSize} MB" -ForegroundColor Green
        Write-Host "  Share this file with your users." -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
    } else {
        Write-Host "  Installer compile failed. Check Inno Setup output above." -ForegroundColor Red
    }
} else {
    Write-Host "  Inno Setup not found. Run manually:" -ForegroundColor Yellow
    Write-Host "  Open Inno Setup → installer.iss → press F9" -ForegroundColor Yellow
}

