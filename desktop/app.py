"""
=============================================================
 WorkPulse — Windows Desktop App
=============================================================
 This is the main Windows application.

 What it does:
   1. Shows a modern login window
   2. Sends email + password to the FastAPI backend
   3. If login works → opens the monitoring dashboard
   4. Starts taking a screenshot every 15 seconds
   5. Uploads each screenshot to the backend (stored in PostgreSQL)
   6. User can logout to stop capturing

 How to run:
   python app.py

 Requirements:
   pip install -r requirements.txt
=============================================================
"""

import customtkinter as ctk          # Modern-looking UI widgets
import tkinter as tk
from tkinter import messagebox
import requests                       # HTTP calls to FastAPI
import threading                      # Run screenshot loop in background
import time
import pyautogui                      # Take screenshots
import base64                         # Convert image → text for API
import io                             # In-memory file operations
import json
import sys
from PIL import Image                 # Image processing
from datetime import datetime
from activity_tracker import ActivityTracker   # Mouse/keyboard activity tracking
from app_tracker import AppTracker             # Active window + browser URL tracking
from config import API_URL, SCREENSHOT_INTERVAL  # Central config (reads server URL)
from pathlib import Path

# ── App icon paths ─────────────────────────────────────────
_HERE     = Path(__file__).parent
_ICON_ICO = str(_HERE / "app_icon.ico")
# When frozen (EXE), PNG is bundled next to the exe; in dev mode use ../imgs/
_ICON_PNG = str(
    _HERE / "app_icon.png"
    if (_HERE / "app_icon.png").exists()
    else Path(__file__).parent.parent / "imgs" / "app_icon.png"
)

# ── Persistent icon photo (must stay alive — GC kills it otherwise) ─
_ICON_PHOTO = None

def _set_window_icon(win):
    """Set title-bar icon on any tk/CTk window reliably."""
    global _ICON_PHOTO
    try:
        if _ICON_PHOTO is None:
            from PIL import ImageTk
            _ICON_PHOTO = ImageTk.PhotoImage(
                Image.open(_ICON_PNG).resize((32, 32), Image.LANCZOS)
            )
        win.wm_iconphoto(True, _ICON_PHOTO)
    except Exception:
        try:
            win.iconbitmap(_ICON_ICO)
        except Exception:
            pass

# ── Session persistence ─────────────────────────────────────
if getattr(sys, "frozen", False):
    _APP_DIR = Path(sys.executable).parent   # next to the .exe
else:
    _APP_DIR = Path(__file__).parent

_SESSION_FILE = _APP_DIR / "session.json"


def _save_session(user_data: dict):
    try:
        _SESSION_FILE.write_text(json.dumps(user_data), encoding="utf-8")
    except Exception:
        pass


def _load_session():
    try:
        if _SESSION_FILE.exists():
            return json.loads(_SESSION_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def _clear_session():
    try:
        if _SESSION_FILE.exists():
            _SESSION_FILE.unlink()
    except Exception:
        pass

# ── Configuration ──────────────────────────────────────────
# API_URL and SCREENSHOT_INTERVAL now come from config.py.
# To point to a different server, edit config.py or set
# the API_URL environment variable before launching.


# ── Global theme settings ──────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ══════════════════════════════════════════════════════════
#  LOGIN WINDOW
# ══════════════════════════════════════════════════════════
class LoginWindow(ctk.CTk):
    """
    The first window users see.
    Has email + password fields and a Sign In button.
    """

    def __init__(self):
        super().__init__()

        self.title("Realisieren Pulse")
        self.geometry("440x620")
        self.resizable(False, False)
        self._center_window(440, 620)
        ctk.set_appearance_mode("dark")
        _set_window_icon(self)
        self._build_ui()

        # If a session is saved, skip login and show the Start screen
        saved = _load_session()
        if saved:
            self.after(150, lambda: self._show_start_screen(saved))

    def _center_window(self, w, h):
        """Put the window in the middle of the screen"""
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw // 2) - (w // 2)
        y  = (sh // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _make_field_row(self, parent, icon, var, placeholder, show=""):
        row = ctk.CTkFrame(parent, fg_color="#1e2130", corner_radius=10,
                           border_color="#2e3347", border_width=1, height=50)
        row.pack(fill="x", pady=(4, 0))
        row.pack_propagate(False)
        ctk.CTkLabel(row, text=icon, font=ctk.CTkFont(size=15),
                     text_color="#5a6180", width=40).pack(side="left", padx=(10, 0))
        entry = ctk.CTkEntry(row, textvariable=var, placeholder_text=placeholder,
                             show=show, font=ctk.CTkFont(size=13),
                             fg_color="transparent", border_width=0,
                             text_color="#e0e4f0", placeholder_text_color="#4a5270")
        entry.pack(side="left", fill="both", expand=True, padx=(4, 10))
        return entry

    def _build_ui(self):
        """Create both Sign In and Create Account views inside the same window."""
        self.configure(fg_color="#161b27")

        # ── Shared icon header (always visible) ──────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(pady=(36, 0))

        icon_box = ctk.CTkFrame(header, fg_color="#1e2436", corner_radius=20,
                                width=96, height=96)
        icon_box.pack()
        icon_box.pack_propagate(False)
        try:
            _img = ctk.CTkImage(Image.open(_ICON_PNG), size=(76, 76))
            ctk.CTkLabel(icon_box, image=_img, text="").place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            ctk.CTkLabel(icon_box, text="R", font=ctk.CTkFont(size=44, weight="bold"),
                         text_color="#4f8ef7").place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(header, text="Realisieren Pulse",
                     font=ctk.CTkFont(size=26, weight="bold"),
                     text_color="#ffffff").pack(pady=(12, 0))

        # ── Sign In frame ─────────────────────────────────
        self._login_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._login_frame.pack(fill="both", expand=True, padx=44)

        ctk.CTkLabel(self._login_frame, text="Real-time work sync & tracking",
                     font=ctk.CTkFont(size=13),
                     text_color="#6b7494").pack(pady=(4, 20))

        ctk.CTkLabel(self._login_frame, text="Email Address", anchor="w",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#c8cde0").pack(fill="x")
        self.email_var = tk.StringVar()
        self.email_entry = self._make_field_row(
            self._login_frame, "✉", self.email_var, "you@example.com")

        ctk.CTkLabel(self._login_frame, text="Password", anchor="w",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#c8cde0").pack(fill="x", pady=(14, 0))
        self.password_var = tk.StringVar()
        self.password_entry = self._make_field_row(
            self._login_frame, "🔒", self.password_var, "Enter your password", show="•")

        self.error_var = tk.StringVar(value="")
        ctk.CTkLabel(self._login_frame, textvariable=self.error_var,
                     text_color="#FF6B6B", font=ctk.CTkFont(size=12),
                     wraplength=360).pack(pady=(8, 0))

        self.login_btn = ctk.CTkButton(
            self._login_frame, text="Sign In  →", height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#4f8ef7", hover_color="#3a7ae8",
            corner_radius=12, command=self._on_login_click,
        )
        self.login_btn.pack(fill="x", pady=(12, 0))

        foot1 = ctk.CTkFrame(self._login_frame, fg_color="transparent")
        foot1.pack(pady=(10, 0))
        ctk.CTkLabel(foot1, text="Don't have an account? ",
                     font=ctk.CTkFont(size=12), text_color="#6b7494").pack(side="left")
        ctk.CTkButton(foot1, text="Create one",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      text_color="#4f8ef7", fg_color="transparent",
                      hover_color="#1a2035", border_width=0, height=22,
                      width=70, command=self._show_register).pack(side="left")

        # ── Create Account frame (hidden initially) ───────
        self._reg_frame = ctk.CTkFrame(self, fg_color="transparent")

        ctk.CTkLabel(self._reg_frame, text="Create your account",
                     font=ctk.CTkFont(size=13),
                     text_color="#6b7494").pack(pady=(4, 20), padx=44)

        reg_inner = ctk.CTkFrame(self._reg_frame, fg_color="transparent")
        reg_inner.pack(fill="both", expand=True, padx=44)

        ctk.CTkLabel(reg_inner, text="Full Name", anchor="w",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#c8cde0").pack(fill="x")
        self.reg_name_var = tk.StringVar()
        self._make_field_row(reg_inner, "👤", self.reg_name_var, "Your name")

        ctk.CTkLabel(reg_inner, text="Email Address", anchor="w",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#c8cde0").pack(fill="x", pady=(12, 0))
        self.reg_email_var = tk.StringVar()
        self._make_field_row(reg_inner, "✉", self.reg_email_var, "you@example.com")

        ctk.CTkLabel(reg_inner, text="Password", anchor="w",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#c8cde0").pack(fill="x", pady=(12, 0))
        self.reg_pass_var = tk.StringVar()
        self._make_field_row(reg_inner, "🔒", self.reg_pass_var, "Min 6 characters", show="•")

        self.reg_error_var = tk.StringVar(value="")
        ctk.CTkLabel(reg_inner, textvariable=self.reg_error_var,
                     text_color="#FF6B6B", font=ctk.CTkFont(size=12),
                     wraplength=360).pack(pady=(8, 0))

        self.reg_btn = ctk.CTkButton(
            reg_inner, text="Create Account  →", height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#4f8ef7", hover_color="#3a7ae8",
            corner_radius=12, command=self._on_register_click,
        )
        self.reg_btn.pack(fill="x", pady=(12, 0))

        foot2 = ctk.CTkFrame(reg_inner, fg_color="transparent")
        foot2.pack(pady=(10, 0))
        ctk.CTkLabel(foot2, text="Already have an account? ",
                     font=ctk.CTkFont(size=12), text_color="#6b7494").pack(side="left")
        ctk.CTkButton(foot2, text="Sign in",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      text_color="#4f8ef7", fg_color="transparent",
                      hover_color="#1a2035", border_width=0, height=22,
                      width=50, command=self._show_login).pack(side="left")

        self.bind("<Return>", lambda _: self._on_login_click())
        self.email_entry.focus()

    def _show_register(self):
        self._login_frame.pack_forget()
        self._reg_frame.pack(fill="both", expand=True)
        self.reg_name_var.set("")
        self.reg_email_var.set("")
        self.reg_pass_var.set("")
        self.reg_error_var.set("")
        self.reg_btn.configure(text="Create Account  →", state="normal", fg_color="#4f8ef7")
        self.unbind("<Return>")
        self.bind("<Return>", lambda _: self._on_register_click())

    def _show_login(self):
        self._reg_frame.pack_forget()
        self._login_frame.pack(fill="both", expand=True, padx=44)
        self.error_var.set("")
        self.login_btn.configure(text="Sign In  →", state="normal")
        self.unbind("<Return>")
        self.bind("<Return>", lambda _: self._on_login_click())
        self.email_entry.focus()

    def _on_login_click(self):
        """Called when user clicks Sign In"""
        email    = self.email_var.get().strip()
        password = self.password_var.get().strip()

        # Simple validation
        if not email or not password:
            self.error_var.set("⚠  Please fill in both fields.")
            return

        # Show loading state
        self.login_btn.configure(text="Signing in...", state="disabled")
        self.error_var.set("")

        # Do the actual login in a background thread
        # (so the UI doesn't freeze while waiting for the server)
        threading.Thread(
            target=self._do_login,
            args=(email, password),
            daemon=True,
        ).start()

    def _do_login(self, email: str, password: str):
        """Background thread: call the API, then update UI on result"""
        try:
            response = requests.post(
                f"{API_URL}/api/login",
                json={"email": email, "password": password},
                timeout=10,
            )

            if response.status_code == 200:
                user_data = response.json()
                # Schedule UI update on the main thread (tkinter requirement)
                self.after(0, self._login_success, user_data)
            else:
                error_msg = response.json().get("detail", "Login failed.")
                self.after(0, self._login_failure, error_msg)

        except requests.exceptions.ConnectionError:
            self.after(0, self._login_failure,
                       "⚠  Cannot connect to server.\nMake sure the backend is running.")
        except requests.exceptions.Timeout:
            self.after(0, self._login_failure, "⚠  Server took too long to respond.")
        except Exception as e:
            self.after(0, self._login_failure, f"⚠  Unexpected error: {e}")

    def _login_success(self, user_data: dict):
        """Called on main thread after successful login"""
        _save_session(user_data)              # Persist so next launch skips login
        self.withdraw()
        DashboardWindow(self, user_data).focus()

    def _show_start_screen(self, user_data: dict):
        """Hide login and show the one-click Start screen"""
        self.withdraw()
        StartWindow(self, user_data)

    def _login_failure(self, message: str):
        """Show error and re-enable the button"""
        self.error_var.set(message)
        self.login_btn.configure(text="Sign In →", state="normal")

    # ── Registration (inline) ─────────────────────────────
    def _on_register_click(self):
        name     = self.reg_name_var.get().strip()
        email    = self.reg_email_var.get().strip()
        password = self.reg_pass_var.get().strip()
        if not name or not email or not password:
            self.reg_error_var.set("⚠  Please fill in all fields.")
            return
        if len(password) < 6:
            self.reg_error_var.set("⚠  Password must be at least 6 characters.")
            return
        self.reg_btn.configure(text="Creating...", state="disabled")
        self.reg_error_var.set("")
        threading.Thread(target=self._do_register,
                         args=(name, email, password), daemon=True).start()

    def _do_register(self, name, email, password):
        try:
            res = requests.post(f"{API_URL}/api/register",
                                json={"username": name, "email": email, "password": password},
                                timeout=10)
            data = res.json()
            if res.ok and data.get("success"):
                self.after(0, lambda: self.reg_btn.configure(
                    text="✓ Signing in...", state="disabled", fg_color="#2ecc71"))
                login_res = requests.post(f"{API_URL}/api/login",
                                          json={"email": email, "password": password},
                                          timeout=10)
                if login_res.status_code == 200:
                    user_data = login_res.json()
                    self.after(0, lambda: self._login_success(user_data))
                else:
                    self.after(0, self._show_login)
            else:
                msg = data.get("detail", "Registration failed.")
                self.after(0, lambda: self._reg_failure(msg))
        except requests.exceptions.ConnectionError:
            self.after(0, lambda: self._reg_failure("⚠  Cannot connect to server."))
        except Exception as e:
            self.after(0, lambda: self._reg_failure(f"⚠  Error: {e}"))

    def _reg_failure(self, msg):
        self.reg_error_var.set(msg)
        self.reg_btn.configure(text="Create Account  →", state="normal", fg_color="#4f8ef7")





# ══════════════════════════════════════════════════════════
#  START WINDOW  (shown on every open after first login)
# ══════════════════════════════════════════════════════════
class StartWindow(ctk.CTkToplevel):
    """
    One-click start screen shown when a saved session exists.
    No password needed — just press Start to begin monitoring.
    """

    def __init__(self, login_win, user_data: dict):
        super().__init__(login_win)
        self._login_win = login_win
        self.user_data  = user_data

        self.title("Realisieren Pulse")
        self.geometry("440x500")
        self.resizable(False, False)
        self._center_window(440, 500)
        self.configure(fg_color="#161b27")
        self.after(200, lambda: _set_window_icon(self))

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self, w, h):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build_ui(self):
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=44, pady=0)

        ctk.CTkFrame(inner, fg_color="transparent", height=1).pack(expand=True)

        # Icon
        icon_box = ctk.CTkFrame(inner, fg_color="#1e2436", corner_radius=20,
                                width=96, height=96)
        icon_box.pack()
        icon_box.pack_propagate(False)
        try:
            _img = ctk.CTkImage(Image.open(_ICON_PNG), size=(76, 76))
            ctk.CTkLabel(icon_box, image=_img, text="").place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            ctk.CTkLabel(icon_box, text="R", font=ctk.CTkFont(size=44, weight="bold"),
                         text_color="#4f8ef7").place(relx=0.5, rely=0.5, anchor="center")

        # Greeting
        name = self.user_data.get("username", "there")
        ctk.CTkLabel(inner, text="Welcome back,",
                     font=ctk.CTkFont(size=14), text_color="#6b7494").pack(pady=(18, 0))
        ctk.CTkLabel(inner, text=name,
                     font=ctk.CTkFont(size=30, weight="bold"),
                     text_color="#ffffff").pack(pady=(2, 6))

        # Project / designation badge
        project     = self.user_data.get("project", "")
        designation = self.user_data.get("designation", "")
        badge_text  = "  ·  ".join(filter(None, [designation, project]))
        if badge_text:
            badge_frame = ctk.CTkFrame(inner, fg_color="#1a2840", corner_radius=20)
            badge_frame.pack(pady=(0, 26))
            ctk.CTkLabel(badge_frame, text=badge_text,
                         font=ctk.CTkFont(size=12), text_color="#4a9eff",
                         padx=14, pady=6).pack()
        else:
            ctk.CTkFrame(inner, fg_color="transparent", height=26).pack()

        # Start button
        ctk.CTkButton(
            inner, text="▶   Start Monitoring", height=56,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#4f8ef7", hover_color="#3a7ae8",
            corner_radius=14, command=self._start,
        ).pack(fill="x")

        # Sign out link
        foot = ctk.CTkFrame(inner, fg_color="transparent")
        foot.pack(pady=(16, 0))
        ctk.CTkLabel(foot, text="Not you?  ",
                     font=ctk.CTkFont(size=12), text_color="#6b7494").pack(side="left")
        ctk.CTkButton(foot, text="Sign out",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      text_color="#f87171", fg_color="transparent",
                      hover_color="#1a2035", border_width=0, height=22, width=60,
                      command=self._sign_out).pack(side="left")

        ctk.CTkFrame(inner, fg_color="transparent", height=1).pack(expand=True)

    def _start(self):
        self.withdraw()
        DashboardWindow(self._login_win, self.user_data, start_win=self).focus()

    def _sign_out(self):
        _clear_session()
        self.destroy()
        self._login_win.email_var.set("")
        self._login_win.password_var.set("")
        self._login_win.error_var.set("")
        self._login_win.login_btn.configure(text="Sign In  →", state="normal")
        self._login_win.deiconify()

    def _on_close(self):
        # Closing the window exits the app but keeps session for next time
        self._login_win.destroy()


# ══════════════════════════════════════════════════════════
#  DASHBOARD WINDOW
# ══════════════════════════════════════════════════════════
class DashboardWindow(ctk.CTkToplevel):
    """
    Opens after successful login.
    Shows screenshot stats and controls.
    Runs the screenshot loop in a background thread.
    """

    def __init__(self, login_win, user_data: dict, start_win=None):
        super().__init__(login_win)

        self._login_win       = login_win
        self._start_win       = start_win
        self.user_data        = user_data
        self.user_id          = user_data["user_id"]
        self.username         = user_data["username"]
        self.screenshot_count = 0
        self.is_capturing     = True      # Set to False to stop the loop

        # Local queue — screenshots saved here when API is unreachable
        import tempfile
        self._queue_dir = Path(tempfile.gettempdir()) / "realisieren_pulse_pending" / str(self.user_id)
        self._queue_dir.mkdir(parents=True, exist_ok=True)

        # Activity tracker — started after UI is built
        self._tracker     = ActivityTracker(log_fn=self._log)
        self._app_tracker = AppTracker(log_fn=self._log)

        self.title(f"Realisieren Pulse — {self.username}")
        self.geometry("540x680")
        self.resizable(False, False)
        self._center_window(540, 680)
        self.after(200, lambda: _set_window_icon(self))

        self._build_ui()
        self._animate_progress()  # Start after all widgets are built

        # Start screenshot capture in background
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,   # Daemon threads die when the app closes
        )
        self._capture_thread.start()

        # Start activity tracker (mouse + keyboard listener + window flusher)
        self._tracker.start(self.user_id)
        # Start app tracker (active window + browser URL)
        self._app_tracker.start(self.user_id)

        # Start retry thread — uploads any queued screenshots when API is back
        self._retry_thread = threading.Thread(
            target=self._retry_pending_uploads,
            daemon=True,
        )
        self._retry_thread.start()

        # Poll live activity status every 5 seconds for desktop status updates
        self.after(5000, self._poll_activity_status)

        # Ask user to confirm before closing
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self, w, h):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build_ui(self):
        """Build the dashboard layout"""

        # ── Top header bar ───────────────────────────────
        header = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color=("#1a1a2e", "#1a1a2e"))
        header.pack(fill="x")
        header.pack_propagate(False)

        try:
            _hdr_img = ctk.CTkImage(Image.open(_ICON_PNG), size=(40, 40))
            ctk.CTkLabel(header, image=_hdr_img, text="  Realisieren Pulse",
                         compound="left",
                         font=ctk.CTkFont(size=19, weight="bold")).pack(side="left", padx=20, pady=15)
        except Exception:
            ctk.CTkLabel(
                header,
                text="R  Realisieren Pulse",
                font=ctk.CTkFont(size=19, weight="bold"),
            ).pack(side="left", padx=20, pady=15)

        # Live indicator
        live_frame = ctk.CTkFrame(header, fg_color="transparent")
        live_frame.pack(side="right", padx=20)
        ctk.CTkLabel(live_frame, text="●", text_color="#00FF88", font=ctk.CTkFont(size=16)).pack(side="left")
        ctk.CTkLabel(live_frame, text=" MONITORING", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00FF88").pack(side="left")

        # ── Welcome banner (auto-hides after 4 s) ────────
        self._welcome_bar = ctk.CTkFrame(self, height=42, corner_radius=0,
                                         fg_color=("#0d1a30", "#0d1a30"))
        self._welcome_bar.pack(fill="x")
        self._welcome_bar.pack_propagate(False)
        ctk.CTkLabel(
            self._welcome_bar,
            text=f"👋  Welcome back, {self.username}!   Realisieren Pulse is monitoring your activity.",
            font=ctk.CTkFont(size=12),
            text_color="#5da8ff",
        ).pack(expand=True)
        self.after(4000, lambda: self._welcome_bar.pack_forget())

        # ── Content area ─────────────────────────────────
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=16)

        # ── Welcome card ─────────────────────────────────
        self._card(
            content,
            children_fn=lambda f: [
                ctk.CTkLabel(f, text=f"👋  Welcome, {self.username}!", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=16, pady=(14, 4)),
                ctk.CTkLabel(f, text=self.user_data["email"], font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="w", padx=16, pady=(0, 14)),
            ]
        )

        # ── Status card ──────────────────────────────────
        status_card = self._card(content)

        ctk.CTkLabel(
            status_card, text="Capture Status",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(14, 8))

        status_row = ctk.CTkFrame(status_card, fg_color="transparent")
        status_row.pack(fill="x", padx=16, pady=(0, 14))

        self.status_dot = ctk.CTkLabel(status_row, text="●", text_color="#00FF88", font=ctk.CTkFont(size=18))
        self.status_dot.pack(side="left")

        self.status_text = ctk.CTkLabel(
            status_row,
            text=f"  Active — screenshot every {SCREENSHOT_INTERVAL}s",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        )
        self.status_text.pack(side="left")

        # Progress bar (just visual — fills up between each screenshot)
        self.progress = ctk.CTkProgressBar(status_card, height=4)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=16, pady=(0, 16))

        # ── Stat counters ────────────────────────────────
        stats_frame = ctk.CTkFrame(content, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 12))
        stats_frame.columnconfigure([0, 1], weight=1)

        # Screenshots taken
        count_card = ctk.CTkFrame(stats_frame, fg_color=("#1e1e30", "#1e1e30"), corner_radius=14)
        count_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.count_num = ctk.CTkLabel(count_card, text="0", font=ctk.CTkFont(size=32, weight="bold"), text_color="#4A9EFF")
        self.count_num.pack(pady=(16, 2))
        ctk.CTkLabel(count_card, text="Screenshots Taken", font=ctk.CTkFont(size=11), text_color="gray").pack(pady=(0, 16))

        # Last capture time
        time_card = ctk.CTkFrame(stats_frame, fg_color=("#1e1e30", "#1e1e30"), corner_radius=14)
        time_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self.last_time_label = ctk.CTkLabel(time_card, text="--:--:--", font=ctk.CTkFont(size=24, weight="bold"), text_color="#A78BFA")
        self.last_time_label.pack(pady=(16, 2))
        ctk.CTkLabel(time_card, text="Last Capture", font=ctk.CTkFont(size=11), text_color="gray").pack(pady=(0, 16))

        # Next capture countdown
        next_card = self._card(content)
        next_card_row = ctk.CTkFrame(next_card, fg_color="transparent")
        next_card_row.pack(fill="x", padx=16, pady=12)
        ctk.CTkLabel(next_card_row, text="⏱  Next screenshot in:", font=ctk.CTkFont(size=13), text_color="gray").pack(side="left")
        self.countdown_label = ctk.CTkLabel(next_card_row, text="15s", font=ctk.CTkFont(size=13, weight="bold"), text_color="#34D399")
        self.countdown_label.pack(side="left", padx=6)

        # ── Logout button ────────────────────────────────
        ctk.CTkButton(
            content,
            text="🚪  Logout & Stop Capture",
            height=46,
            fg_color="transparent",
            border_width=1,
            border_color=("#444", "#444"),
            text_color=("gray40", "gray60"),
            hover_color=("#2a2a2a", "#2a2a2a"),
            font=ctk.CTkFont(size=13),
            command=self._logout,
        ).pack(fill="x", pady=(4, 8))

    def _card(self, parent, padx=0, children_fn=None):
        """Helper to create a consistent card frame"""
        card = ctk.CTkFrame(
            parent,
            fg_color=("#1e1e30", "#1e1e30"),
            corner_radius=14,
        )
        card.pack(fill="x", pady=(0, 12), padx=padx)
        if children_fn:
            children_fn(card)
        return card

    # ── Logging ──────────────────────────────────────────
    def _log(self, message: str):
        """Silent — internal logs are not shown to the user"""
        pass

    # ── Progress bar animation ────────────────────────────
    def _animate_progress(self):
        """Animate the progress bar to show time until next screenshot"""
        if not self.is_capturing:
            return
        now = time.time()
        # _last_capture is set after each screenshot
        elapsed = now - getattr(self, "_last_capture_time", now)
        fraction = min(elapsed / SCREENSHOT_INTERVAL, 1.0)
        self.progress.set(fraction)
        remaining = max(0, SCREENSHOT_INTERVAL - elapsed)
        self.countdown_label.configure(text=f"{remaining:.0f}s")
        # Update every 0.5 seconds
        self.after(500, self._animate_progress)

    # ── Screenshot capture loop ───────────────────────────
    def _capture_loop(self):
        """
        Runs in a background thread.
        Takes a screenshot every SCREENSHOT_INTERVAL seconds.
        """
        self._log("✅ Screenshot capture started")

        while self.is_capturing:
            self._last_capture_time = time.time()
            try:
                self._take_and_upload_screenshot()
            except Exception as e:
                self._log(f"❌ Error: {e}")

            # Wait for the interval (in small chunks so we can stop quickly)
            elapsed = 0
            while elapsed < SCREENSHOT_INTERVAL and self.is_capturing:
                time.sleep(0.5)
                elapsed += 0.5

        self._log("🛑 Capture stopped.")

    def _upload_screenshot_bytes(self, raw_bytes: bytes, filename: str) -> bool:
        """Try to upload raw PNG bytes to the API. Returns True on success."""
        base64_str = base64.b64encode(raw_bytes).decode("utf-8")
        try:
            response = requests.post(
                f"{API_URL}/api/screenshots/upload",
                json={"user_id": self.user_id, "filename": filename, "image_data": base64_str},
                timeout=30,
            )
            return response.status_code == 200
        except Exception:
            return False

    def _take_and_upload_screenshot(self):
        """Take one screenshot, try to upload; save locally if API is down."""

        # ── Step 1: Take screenshot ──────────────────────
        screenshot = pyautogui.screenshot()

        # ── Step 2: Compress to PNG bytes ────────────────
        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG", optimize=True)
        raw_bytes = buffer.getvalue()

        # ── Step 3: Build filename ────────────────────────
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{self.user_id}_{ts}.png"

        # ── Step 4: Upload or queue locally ──────────────
        if self._upload_screenshot_bytes(raw_bytes, filename):
            self.screenshot_count += 1
            now_str = datetime.now().strftime("%H:%M:%S")
            self.after(0, self._update_stats, now_str, len(raw_bytes) // 1024)
            self._log(f"📷 Screenshot #{self.screenshot_count} uploaded")
        else:
            # API down — save to local queue, retry thread will upload later
            local_path = self._queue_dir / filename
            local_path.write_bytes(raw_bytes)
            self._log(f"💾 API unavailable — queued locally: {local_path.name}")

    def _retry_pending_uploads(self):
        """Background thread: retry uploading queued screenshots when API is back."""
        while self.is_capturing:
            pending = sorted(self._queue_dir.glob("*.png"))
            for f in pending:
                if not self.is_capturing:
                    break
                try:
                    raw_bytes = f.read_bytes()
                    if self._upload_screenshot_bytes(raw_bytes, f.name):
                        f.unlink()  # Delete after successful upload
                        self.screenshot_count += 1
                        now_str = datetime.now().strftime("%H:%M:%S")
                        self.after(0, self._update_stats, now_str, len(raw_bytes) // 1024)
                        self._log(f"✅ Queued screenshot uploaded: {f.name}")
                except Exception:
                    pass  # Will retry next cycle
            # Wait 60 seconds before next retry attempt
            for _ in range(120):
                if not self.is_capturing:
                    break
                time.sleep(0.5)

    def _update_stats(self, time_str: str, size_kb: int):
        """Update the count and last-capture labels"""
        self.count_num.configure(text=str(self.screenshot_count))
        self.last_time_label.configure(text=time_str)

    def _poll_activity_status(self):
        """Periodic poll — kept for future use."""
        if not self.is_capturing:
            return
        self.after(5000, self._poll_activity_status)

    # ── Logout & close ────────────────────────────────────
    def _logout(self):
        if messagebox.askyesno("Logout", "Stop capturing and logout?"):
            _clear_session()
            self.is_capturing = False
            self._tracker.stop()
            self._app_tracker.stop()
            self.destroy()
            # Destroy start window if it was the entry point
            if self._start_win:
                try:
                    self._start_win.destroy()
                except Exception:
                    pass
            # Show fresh login window
            self._login_win.email_var.set("")
            self._login_win.password_var.set("")
            self._login_win.error_var.set("")
            self._login_win.login_btn.configure(text="Sign In  →", state="normal")
            self._login_win.deiconify()

    def _on_close(self):
        if messagebox.askyesno("Exit", "Stop capturing and exit the app?"):
            self.is_capturing = False
            self._tracker.stop()
            self._app_tracker.stop()
            self.destroy()
            self._login_win.destroy()   # session is kept — next open shows Start screen


# ══════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = LoginWindow()
    app.mainloop()
