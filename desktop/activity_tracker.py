"""
=============================================================
 activity_tracker.py — Hubstaff-style activity tracking
=============================================================
 How it works:
   1. Listens for mouse movement/clicks and keyboard presses
      using pynput (runs in background threads).
   2. Every second, checks if the user is active or idle:
        idle  = no event for more than IDLE_THRESHOLD seconds
        active = at least one event in the last IDLE_THRESHOLD seconds
   3. Every WINDOW_SECONDS (10 min), calculates stats for
      that window and POSTs them to /api/activity/log.

 Activity % = (active_seconds / window_seconds) × 100
=============================================================
"""

import threading
import time
import requests
from datetime import datetime

from pynput import mouse, keyboard
from config import API_URL   # ✅ reads from config.ini / env var (was hardcoded localhost)

# ── Config ─────────────────────────────────────────────────
# IDLE_THRESHOLD must always be less than WINDOW_SECONDS
# Testing:    WINDOW_SECONDS=60,  IDLE_THRESHOLD=10
# Production: WINDOW_SECONDS=600, IDLE_THRESHOLD=300
IDLE_THRESHOLD  = 180   # Seconds of silence → mark as idle (3 mins)
WINDOW_SECONDS  = 600   # Length of one tracking window (10 mins)


class ActivityTracker:
    """
    Start this after login.  Call  start(user_id)  to begin tracking.
    It runs entirely in background threads — never blocks the UI.

    Internal state (updated by pynput callbacks):
      _last_event_time  — timestamp of the last mouse/keyboard event
      _mouse_events     — count of mouse moves + clicks in this window
      _keyboard_events  — count of key presses in this window

    Internal state (updated by the 1-second ticker):
      _active_seconds   — seconds marked ACTIVE in this window
      _idle_seconds     — seconds marked IDLE in this window
    """

    def __init__(self, log_fn=None):
        """
        log_fn: optional callable(str) that writes to the desktop app's
                activity log box.  If None, falls back to print().
        """
        self._log_fn          = log_fn or print
        self._user_id         = None
        self._running         = False

        # Event counters (reset each window)
        self._mouse_events    = 0
        self._keyboard_events = 0

        # Activity seconds (reset each window)
        self._active_seconds  = 0
        self._idle_seconds    = 0

        # Timestamp of last mouse or keyboard event
        self._last_event_time = time.time()

        # Window boundary timestamps
        self._window_start    = datetime.now()

        # pynput listener handles (kept so we can stop them)
        self._mouse_listener    = None
        self._keyboard_listener = None

    # ── Public API ──────────────────────────────────────────

    def start(self, user_id: int):
        """Call this once after login to start all background threads."""
        self._user_id  = user_id
        self._running  = True
        self._window_start = datetime.now()
        self._last_event_time = time.time()

        self._start_listeners()

        # Thread 1: 1-second ticker (active/idle bookkeeping)
        threading.Thread(target=self._tick_loop, daemon=True).start()

        # Thread 2: window flusher (fires every WINDOW_SECONDS)
        threading.Thread(target=self._window_loop, daemon=True).start()

        self._log(f"📊 Activity tracker started (window={WINDOW_SECONDS}s, idle threshold={IDLE_THRESHOLD}s)")

    def stop(self):
        """Call this on logout to clean up listeners."""
        self._running = False
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._keyboard_listener:
            self._keyboard_listener.stop()
        self._log("📊 Activity tracker stopped")

    def current_status(self) -> dict:
        """
        Returns a snapshot of the current tracking state.
        Used by the desktop UI to show live status.
        """
        idle_secs = time.time() - self._last_event_time
        status    = "IDLE" if idle_secs >= IDLE_THRESHOLD else "ACTIVE"
        return {
            "status":           status,
            "active_seconds":   self._active_seconds,
            "idle_seconds":     self._idle_seconds,
            "mouse_events":     self._mouse_events,
            "keyboard_events":  self._keyboard_events,
            "idle_for":         int(idle_secs),
        }

    # ── pynput listeners ────────────────────────────────────

    def _start_listeners(self):
        """Start mouse and keyboard listeners in their own threads."""

        def on_move(x, y):
            self._on_activity("mouse")

        def on_click(x, y, button, pressed):
            if pressed:
                self._on_activity("mouse")

        def on_scroll(x, y, dx, dy):
            self._on_activity("mouse")

        def on_key_press(key):
            self._on_activity("keyboard")

        self._mouse_listener = mouse.Listener(
            on_move=on_move, on_click=on_click, on_scroll=on_scroll
        )
        self._keyboard_listener = keyboard.Listener(on_press=on_key_press)

        self._mouse_listener.start()
        self._keyboard_listener.start()

    def _on_activity(self, kind: str):
        """Called by pynput on any mouse or keyboard event."""
        self._last_event_time = time.time()
        if kind == "mouse":
            self._mouse_events += 1
        else:
            self._keyboard_events += 1

    # ── 1-second ticker ─────────────────────────────────────

    def _tick_loop(self):
        """
        Runs every second.
        Decides if the current second should count as ACTIVE or IDLE
        and increments the appropriate counter.
        """
        while self._running:
            time.sleep(1)
            idle_secs = time.time() - self._last_event_time
            if idle_secs < IDLE_THRESHOLD:
                self._active_seconds += 1
            else:
                self._idle_seconds += 1

    # ── 10-minute window flusher ─────────────────────────────

    def _window_loop(self):
        """
        Waits WINDOW_SECONDS, then sends the window summary to the backend.
        Resets all counters for the next window.
        """
        while self._running:
            time.sleep(WINDOW_SECONDS)
            if not self._running:
                break
            self._flush_window()

    def _flush_window(self):
        """Calculate activity % for this window and POST to backend."""
        window_end   = datetime.now()
        total        = self._active_seconds + self._idle_seconds
        activity_pct = round((self._active_seconds / total) * 100, 1) if total > 0 else 0.0

        payload = {
            "user_id":          self._user_id,
            "window_start":     self._window_start.isoformat(),
            "window_end":       window_end.isoformat(),
            "active_seconds":   self._active_seconds,
            "idle_seconds":     self._idle_seconds,
            "activity_percent": activity_pct,
            "mouse_events":     self._mouse_events,
            "keyboard_events":  self._keyboard_events,
        }

        self._log(
            f"📊 Window done: active={self._active_seconds}s "
            f"idle={self._idle_seconds}s pct={activity_pct}%"
        )

        try:
            resp = requests.post(f"{API_URL}/api/activity/log", json=payload, timeout=10)
            if resp.status_code == 200:
                self._log("✅ Activity log sent to backend")
            else:
                self._log(f"⚠  Activity log upload failed: {resp.status_code}")
        except Exception as e:
            self._log(f"⚠  Activity log error: {e}")

        # Reset for next window
        self._window_start    = datetime.now()
        self._active_seconds  = 0
        self._idle_seconds    = 0
        self._mouse_events    = 0
        self._keyboard_events = 0

    # ── Internal logging ─────────────────────────────────────

    def _log(self, msg: str):
        try:
            self._log_fn(msg)
        except Exception:
            print(msg)