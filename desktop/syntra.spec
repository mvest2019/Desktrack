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

# ── Icon: only include if the file exists (build still works without it) ──
import os as _os
_icon_path  = 'assets/icon.ico'
_icon       = _icon_path if _os.path.exists(_icon_path) else None
_icon_datas = [(_icon_path, 'assets')] if _icon else []

a = Analysis(
    # ── Entry point ─────────────────────────────────────────
    # This is the first Python file that runs when the EXE starts.
    ['app.py'],

    pathex=['.'],           # extra Python search paths
    binaries=[],            # extra .dll / .so files (none needed here)

    # ── Extra non-Python files to bundle ──────────────────
    # Format: ('source_path', 'dest_folder_inside_bundle')
    # If you add an icon file, list it here so it's included.
    datas=_icon_datas,

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
    name='Syntra',              # ← name of the output .exe file
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                   # compress the EXE (reduces file size ~30%)
    upx_exclude=[],
    runtime_tmpdir=None,

    # console=False  →  no black terminal window appears when user runs it
    console=False,

    icon=_icon,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
