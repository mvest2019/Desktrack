# =============================================================
# syntra.spec — PyInstaller build specification
# =============================================================
# PyInstaller reads this file to know:
#   - Which Python files to bundle
#   - Which extra data files to include (icons, etc.)
#   - Whether to produce one .exe or a folder
#   - Whether to show a console window
#
# HOW TO USE:
#   cd desktop
#   pyinstaller syntra.spec
#
# Output: desktop/dist/Syntra.exe
# =============================================================

block_cipher = None

import os as _os

# ── assets/icon.ico — used as the EXE file icon (built by build_exe.ps1) ──
_icon_path  = 'assets/icon.ico'
_icon       = _icon_path if _os.path.exists(_icon_path) else None
_icon_datas = [(_icon_path, 'assets')] if _icon else []

# ── app_icon.ico — used at runtime for the window titlebar (app.py line ~41) ──
# Must be bundled so Path(__file__).parent resolves it correctly inside the EXE.
_app_icon_path  = 'app_icon.ico'
_app_icon_datas = [(_app_icon_path, '.')] if _os.path.exists(_app_icon_path) else []

a = Analysis(
    # ── Entry point ─────────────────────────────────────────
    ['app.py'],

    pathex=['.'],
    binaries=[],

    # ── Extra non-Python files to bundle ──────────────────
    # assets/icon.ico  → EXE file icon (shown in Explorer / taskbar)
    # app_icon.ico     → runtime window titlebar icon (loaded by app.py)
    datas=_icon_datas + _app_icon_datas,

    hiddenimports=[
        # PyInstaller sometimes misses these — list them explicitly
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        'uiautomation',
        'win32api',
        'win32con',
        'win32gui',
        'win32process',
        'psutil',
        'requests',
    ],

    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Syntra',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,

    # console=False → no black terminal window appears when user runs it
    console=False,

    icon=_icon,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
