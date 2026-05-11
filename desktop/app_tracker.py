"""
=============================================================
 app_tracker.py — Active window + browser URL tracker
=============================================================
 How it works:
   Every POLL_INTERVAL seconds (3s):
     1. win32gui.GetForegroundWindow() → get the HWND of the active window
     2. win32gui.GetWindowText(hwnd)   → window title
     3. win32process.GetWindowThreadProcessId(hwnd) → process ID
     4. psutil.Process(pid).name()    → e.g. "chrome.exe"
     5. If browser → try to read the address bar text via uiautomation
     6. If SAME app+title as before → accumulate time, update URL if found
     7. If DIFFERENT → save old session to buffer, start new session

   Every FLUSH_INTERVAL seconds (60s):
     → POST all buffered records to POST /api/applogs/batch
     → Clear the buffer

 Why pywin32?
   Windows exposes every GUI window via a Win32 API.
   GetForegroundWindow returns a handle to whatever window has keyboard focus.
   GetWindowThreadProcessId converts that handle to a process ID.
   psutil then turns the PID into a readable process name.

 Why uiautomation for browser URLs?
   Windows UI Automation (UIA) lets you inspect any UI element tree —
   buttons, text fields, etc. — in any running application.
   Browser address bars are EditControl elements with known names.
   We ask UIA for that element and read its current text value.
=============================================================
"""

import threading
import time
import requests
from datetime import datetime

from config import API_URL   # ✅ reads from config.ini / env var (was hardcoded localhost)

# ── pywin32 + psutil (Windows-only) ────────────────────────
try:
    import win32gui
    import win32process
    import psutil
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    print("⚠  pywin32/psutil not installed — app tracking disabled. Run: pip install pywin32 psutil")

# ── uiautomation (Windows UI Automation) ───────────────────
try:
    import uiautomation as auto
    UI_AUTO_AVAILABLE = True
except Exception:
    UI_AUTO_AVAILABLE = False
    print("⚠  uiautomation not installed — browser URL detection disabled. Run: pip install uiautomation")

# ── Config ──────────────────────────────────────────────────
POLL_INTERVAL  = 3    # seconds between active-window polls
FLUSH_INTERVAL = 60   # seconds between batch sends to backend

# Process names that are browsers
BROWSER_PROCESSES = {"chrome.exe", "msedge.exe", "brave.exe", "firefox.exe"}

# Human-friendly names for common apps
FRIENDLY_NAMES = {
    "chrome.exe":      "Google Chrome",
    "msedge.exe":      "Microsoft Edge",
    "brave.exe":       "Brave Browser",
    "firefox.exe":     "Firefox",
    "code.exe":        "VS Code",
    "explorer.exe":    "Windows Explorer",
    "notepad.exe":     "Notepad",
    "notepad++.exe":   "Notepad++",
    "python.exe":      "Python",
    "python3.exe":     "Python",
    "python3.11.exe":  "Python",
    "pythonw.exe":     "Python",
    "excel.exe":       "Microsoft Excel",
    "winword.exe":     "Microsoft Word",
    "powerpnt.exe":    "PowerPoint",
    "outlook.exe":     "Outlook",
    "teams.exe":       "Microsoft Teams",
    "slack.exe":       "Slack",
    "discord.exe":     "Discord",
    "zoom.exe":        "Zoom",
    "postman.exe":     "Postman",
    "dbeaver.exe":     "DBeaver",
    "cmd.exe":         "Command Prompt",
    "powershell.exe":  "PowerShell",
    "windowsterminal.exe": "Windows Terminal",
}


def _get_active_window() -> tuple:
    """
    Returns (friendly_app_name, raw_process_name, window_title, hwnd).
    Returns (None, None, None, None) if detection fails or pywin32 is missing.
    """
    if not WIN32_AVAILABLE:
        return None, None, None, None
    try:
        hwnd   = win32gui.GetForegroundWindow()
        title  = win32gui.GetWindowText(hwnd)
        if not title:
            return None, None, None, None
        _, pid     = win32process.GetWindowThreadProcessId(hwnd)
        proc_name  = psutil.Process(pid).name().lower()
        friendly   = FRIENDLY_NAMES.get(proc_name, proc_name.replace(".exe", "").title())
        return friendly, proc_name, title, hwnd
    except Exception:
        return None, None, None, None


def _get_browser_url(proc_name: str, hwnd: int) -> str | None:
    """
    Read the current URL from the browser address bar.
    Scoped to the specific active window via ControlFromHandle so we never
    accidentally read from a background window.

    Chrome / Edge / Brave: EditControl(Name="Address and search bar")
    Firefox:               EditControl(ClassName="urlbar-input")
    """
    if not UI_AUTO_AVAILABLE or not hwnd:
        return None
    try:
        window = auto.ControlFromHandle(hwnd)
        if proc_name in {"chrome.exe", "msedge.exe", "brave.exe"}:
            ctrl = window.EditControl(Name="Address and search bar")
            if ctrl.Exists(0.5, 0.1):
                val = ctrl.GetValuePattern().Value
                if val and ("." in val or val.startswith("http")):
                    return val if val.startswith("http") else f"https://{val}"
        elif proc_name == "firefox.exe":
            ctrl = window.EditControl(ClassName="urlbar-input")
            if ctrl.Exists(0.5, 0.1):
                val = ctrl.GetValuePattern().Value
                if val:
                    return val if val.startswith("http") else f"https://{val}"
    except Exception:
        pass
    return None


class AppTracker:
    """
    Tracks which application windows the user focuses on and for how long.
    Also captures browser URLs when a browser is in focus.

    Usage:
        tracker = AppTracker(log_fn=print)
        tracker.start(user_id=1)
        ...
        tracker.stop()
    """

    def __init__(self, log_fn=None):
        self._log_fn   = log_fn or print
        self._user_id  = None
        self._running  = False

        # Currently active session
        self._current_app   : str | None = None
        self._current_title : str | None = None
        self._current_url   : str | None = None
        self._current_proc  : str | None = None
        self._session_start : datetime | None = None

        # Completed sessions waiting to be sent
        self._buffer: list[dict] = []
        self._lock = threading.Lock()

    # ── Public API ──────────────────────────────────────────

    def start(self, user_id: int):
        """Start polling the active window and flushing records."""
        self._user_id  = user_id
        self._running  = True
        self._session_start = datetime.now()
        threading.Thread(target=self._poll_loop,  daemon=True).start()
        threading.Thread(target=self._flush_loop, daemon=True).start()
        self._log("🖥  App tracker started (polls every 3s, flushes every 60s)")

    def stop(self):
        """Stop tracking and flush any remaining records."""
        self._running = False
        self._close_current_session()
        self._flush_buffer()
        self._log("🖥  App tracker stopped")

    def current_app(self) -> dict:
        """Return a snapshot of the currently active app (for UI display)."""
        return {
            "app":   self._current_app or "—",
            "title": self._current_title or "—",
            "url":   self._current_url or "",
        }

    # ── Internal polling ────────────────────────────────────

    def _poll_loop(self):
        """Every POLL_INTERVAL seconds: check the foreground window."""
        while self._running:
            time.sleep(POLL_INTERVAL)
            app, proc, title, hwnd = _get_active_window()
            if not app:
                continue

            # Grab URL if this is a browser window
            url = None
            if proc in BROWSER_PROCESSES:
                url = _get_browser_url(proc, hwnd)

            # Same window as before → just update URL if we got a better one
            if app == self._current_app and title == self._current_title:
                if url:
                    self._current_url = url
                continue

            # Window changed → save the old session, start a new one
            self._close_current_session()
            self._current_app   = app
            self._current_title = title
            self._current_url   = url
            self._current_proc  = proc
            self._session_start = datetime.now()

    def _close_current_session(self):
        """Save the current session to the buffer (if it lasted ≥ 3 seconds)."""
        if not self._current_app or not self._session_start:
            return
        end = datetime.now()
        dur = int((end - self._session_start).total_seconds())
        if dur < 3:
            return   # too short — probably just alt-tabbing

        record = {
            "user_id":      self._user_id,
            "app_name":     self._current_app,
            "window_title": self._current_title or "",
            "url":          self._current_url   or "",
            "start_time":   self._session_start.isoformat(),
            "end_time":     end.isoformat(),
            "duration_sec": dur,
        }
        with self._lock:
            self._buffer.append(record)

    # ── Internal flushing ───────────────────────────────────

    def _flush_loop(self):
        """Every FLUSH_INTERVAL seconds: send buffered records to the backend."""
        while self._running:
            time.sleep(FLUSH_INTERVAL)
            self._flush_buffer()

    def _flush_buffer(self):
        """POST all buffered records to /api/applogs/batch and clear the buffer."""
        with self._lock:
            if not self._buffer:
                return
            batch = list(self._buffer)
            self._buffer.clear()

        try:
            resp = requests.post(
                f"{API_URL}/api/applogs/batch",
                json={"logs": batch},
                timeout=10,
            )
            if resp.status_code == 200:
                self._log(f"✅ App logs sent: {len(batch)} sessions")
            else:
                self._log(f"⚠  App logs upload failed: {resp.status_code}")
        except Exception as e:
            self._log(f"⚠  App logs error: {e}")

    # ── Internal logging ─────────────────────────────────────

    def _log(self, msg: str):
        try:
            self._log_fn(msg)
        except Exception:
            print(msg)