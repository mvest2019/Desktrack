"""
=============================================================
 activity_tracker.py — Hubstaff-style activity tracking
=============================================================
 How it works:
   1. Listens for mouse clicks/scrolls and keyboard presses
      using pynput (runs in background threads).
      NOTE: mouse *movement* updates the idle timer but is NOT
      counted as a mouse event — only clicks and scrolls are.
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
from config import API_URL

# ── Config ─────────────────────────────────────────────────
# IDLE_THRESHOLD must always be less than WINDOW_SECONDS
# Testing:    WINDOW_SECONDS=60,  IDLE_THRESHOLD=10
# Production: WINDOW_SECONDS=600, IDLE_THRESHOLD=300
IDLE_THRESHOLD  = 180   # Seconds of silence → mark as idle (3 mins)
WINDOW_SECONDS  = 600   # Length of one tracking window (10 mins)

# Mouse move filtering constants
_MOVE_MIN_DISTANCE_PX = 5    # Ignore moves smaller than this (sub-pixel jitter)
_MOVE_RATE_LIMIT_SECS = 0.1  # Max one move activity signal per 100 ms

# Debug log interval (seconds between debug summaries in the log)
_DEBUG_INTERVAL_SECS = 30


class ActivityTracker:
    """
    Start this after login.  Call  start(user_id)  to begin tracking.
    It runs entirely in background threads — never blocks the UI.

    Internal state (updated by pynput callbacks):
      _last_event_time  — timestamp of the last meaningful mouse/keyboard event
      _mouse_events     — count of mouse clicks + scrolls in this window
      _keyboard_events  — count of key presses in this window

    Internal state (updated by the 1-second ticker):
      _active_seconds   — seconds marked ACTIVE in this window
      _idle_seconds     — seconds marked IDLE in this window

    Debug counters (never reset, only used for logging):
      _dbg_move    — raw on_move calls received
      _dbg_click   — raw on_click (pressed=True) calls received
      _dbg_scroll  — raw on_scroll calls received
      _dbg_key     — raw on_key_press calls received
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

        # Timestamp of last meaningful mouse or keyboard event
        self._last_event_time = time.time()

        # Window boundary timestamps
        self._window_start    = datetime.now()

        # pynput listener handles (kept so we can stop them)
        self._mouse_listener    = None
        self._keyboard_listener = None

        # Move-event filtering state (set in _start_listeners)
        self._last_mouse_pos       = None   # (x, y) of last accepted move
        self._last_move_accept_time = 0.0   # epoch seconds of last accepted move

        # Debug counters — cumulative since start, never reset
        self._dbg_move   = 0
        self._dbg_click  = 0
        self._dbg_scroll = 0
        self._dbg_key    = 0
        self._dbg_last_logged = 0.0  # epoch time of last debug summary

        # Lock for counter mutations from pynput threads
        self._lock = threading.Lock()

    # ── Public API ──────────────────────────────────────────

    def start(self, user_id: int):
        """Call this once after login to start all background threads."""
        self._user_id  = user_id
        self._running  = True
        self._window_start = datetime.now()
        self._last_event_time = time.time()
        self._dbg_last_logged = time.time()

        self._start_listeners()

        # Thread 1: 1-second ticker (active/idle bookkeeping + debug logs)
        threading.Thread(target=self._tick_loop, daemon=True).start()

        # Thread 2: window flusher (fires every WINDOW_SECONDS)
        threading.Thread(target=self._window_loop, daemon=True).start()

        self._log(
            f"📊 Activity tracker started "
            f"(window={WINDOW_SECONDS}s, idle_threshold={IDLE_THRESHOLD}s, "
            f"move_min_dist={_MOVE_MIN_DISTANCE_PX}px, "
            f"move_rate_limit={_MOVE_RATE_LIMIT_SECS}s)"
        )

    def flush(self):
        """Force-flush the current window to the backend immediately (call on logout)."""
        if self._user_id and (self._active_seconds + self._idle_seconds) > 0:
            self._flush_window()

    def stop(self):
        """Call this on logout to clean up listeners."""
        self._running = False
        self.flush()
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
        """
        Start mouse and keyboard listeners.

        Mouse event strategy:
          on_move  → updates idle timer only (filtered by distance + rate limit).
                     Does NOT increment _mouse_events — moves are too noisy.
          on_click → increments _mouse_events for button-down events only.
          on_scroll → increments _mouse_events for every scroll tick.
        """

        def on_move(x, y):
            # Always count the raw call for debug purposes (no lock needed — GIL ok for +=1)
            self._dbg_move += 1

            now = time.time()

            # Rate-limit: ignore moves that arrive faster than _MOVE_RATE_LIMIT_SECS
            if now - self._last_move_accept_time < _MOVE_RATE_LIMIT_SECS:
                return

            # Distance filter: ignore sub-pixel OS jitter
            if self._last_mouse_pos is not None:
                dx = x - self._last_mouse_pos[0]
                dy = y - self._last_mouse_pos[1]
                if (dx * dx + dy * dy) < (_MOVE_MIN_DISTANCE_PX ** 2):
                    return

            # Genuine movement detected — update idle timer only, no event count
            self._last_mouse_pos        = (x, y)
            self._last_move_accept_time = now
            self._last_event_time       = now

        def on_click(x, y, button, pressed):
            if not pressed:
                return  # Ignore button-release; only count button-down
            self._dbg_click += 1
            self._on_activity("mouse")

        def on_scroll(x, y, dx, dy):
            self._dbg_scroll += 1
            self._on_activity("mouse")

        def on_key_press(key):
            self._dbg_key += 1
            self._on_activity("keyboard")

        self._mouse_listener = mouse.Listener(
            on_move=on_move, on_click=on_click, on_scroll=on_scroll
        )
        self._keyboard_listener = keyboard.Listener(on_press=on_key_press)

        self._mouse_listener.start()
        self._keyboard_listener.start()

    def _on_activity(self, kind: str):
        """
        Called for clicks, scrolls, and key presses — genuine user actions.
        Updates the idle timer and increments the appropriate event counter.
        Mouse *movement* does NOT go through here (it only updates _last_event_time).
        """
        now = time.time()
        with self._lock:
            self._last_event_time = now
            if kind == "mouse":
                self._mouse_events += 1
            else:
                self._keyboard_events += 1

    # ── 1-second ticker ─────────────────────────────────────

    def _tick_loop(self):
        """
        Runs every second.
        Decides if the current second should count as ACTIVE or IDLE
        and emits a periodic debug summary showing per-handler fire counts.
        """
        while self._running:
            time.sleep(1)
            idle_secs = time.time() - self._last_event_time
            with self._lock:
                if idle_secs < IDLE_THRESHOLD:
                    self._active_seconds += 1
                else:
                    self._idle_seconds += 1

            # Periodic debug summary
            now = time.time()
            if now - self._dbg_last_logged >= _DEBUG_INTERVAL_SECS:
                self._dbg_last_logged = now
                self._log(
                    f"[DEBUG] raw handler calls — "
                    f"on_move={self._dbg_move}, "
                    f"on_click={self._dbg_click}, "
                    f"on_scroll={self._dbg_scroll}, "
                    f"on_key={self._dbg_key} | "
                    f"counted events — mouse={self._mouse_events}, "
                    f"keyboard={self._keyboard_events}"
                )

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
        with self._lock:
            active   = self._active_seconds
            idle     = self._idle_seconds
            m_events = self._mouse_events
            k_events = self._keyboard_events
            w_start  = self._window_start
            w_end    = datetime.now()

        total        = active + idle
        activity_pct = round((active / total) * 100, 1) if total > 0 else 0.0

        payload = {
            "user_id":          self._user_id,
            "window_start":     w_start.isoformat(),
            "window_end":       w_end.isoformat(),
            "active_seconds":   active,
            "idle_seconds":     idle,
            "activity_percent": activity_pct,
            "mouse_events":     m_events,
            "keyboard_events":  k_events,
        }

        self._log(
            f"📊 Window done: active={active}s idle={idle}s pct={activity_pct}% "
            f"mouse_events={m_events} keyboard_events={k_events}"
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
        with self._lock:
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
