; =============================================================
; installer.iss — Inno Setup script
; =============================================================
; Inno Setup is a FREE tool that turns your .exe into an
; installable "setup wizard" (like any professional software).
;
; DOWNLOAD Inno Setup from: https://jrsoftware.org/isdl.php
;
; HOW TO USE:
;   1. Build the EXE first:  .\build_exe.ps1
;   2. Open Inno Setup Compiler
;   3. File → Open → select this installer.iss file
;   4. Build → Compile
;   5. Output:  desktop/installer_output/SyntraSetup.exe
;
; What this installer does for the user:
;   - Shows a professional "Next → Next → Install" wizard
;   - Copies Syntra.exe to:  C:\Program Files\Syntra\
;   - Adds a Start Menu shortcut
;   - Adds a Desktop shortcut
;   - Adds entry to "Add or Remove Programs" (so they can uninstall)
;   - Optionally starts Syntra after install
; =============================================================

#define MyAppName      "Syntra"
#define MyAppVersion   "1.0.0"
#define MyAppPublisher "Your Company Name"
#define MyAppURL       "http://108.181.168.43"
#define MyAppExeName   "Syntra.exe"
#define MyAppDescription "Real-time work sync and activity tracker"

[Setup]
; ── Basic info ───────────────────────────────────────────────
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}    ; unique ID (don't change once released)
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; ── Installation folder ──────────────────────────────────────
; {autopf} = C:\Program Files  (or x86 on 32-bit systems)
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

; ── Output ───────────────────────────────────────────────────
OutputDir=installer_output
OutputBaseFilename=SyntraSetup
SetupIconFile=assets\icon.ico   ; comment out if you don't have an icon yet

; ── Compression ──────────────────────────────────────────────
Compression=lzma
SolidCompression=yes

; ── Wizard appearance ────────────────────────────────────────
WizardStyle=modern

; ── Require admin rights (needed to write to Program Files) ──
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; ── These are checkboxes shown to the user during install ────
Name: "desktopicon"; Description: "Create a &Desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; ── Copy the built EXE into the install folder ───────────────
; Source is relative to this .iss file (both are in desktop/)
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; ── If the user can override the server URL, include a default config.ini ──
; Uncomment these lines if you want to ship a config.ini:
; Source: "dist_config\config.ini"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

[Icons]
; ── Start Menu shortcut ──────────────────────────────────────
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; ── Desktop shortcut (only if user checked the checkbox above) ──
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; ── After install, offer to launch the app immediately ───────
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Launch {#MyAppName} now"; \
    Flags: nowait postinstall skipifsilent
