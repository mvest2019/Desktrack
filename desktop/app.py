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
from PIL import Image                 # Image processing
from datetime import datetime
from activity_tracker import ActivityTracker   # Mouse/keyboard activity tracking
from app_tracker import AppTracker             # Active window + browser URL tracking
from config import API_URL, SCREENSHOT_INTERVAL  # Central config (reads server URL)

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

        self.title("Syntra")
        self.geometry("440x620")
        self.resizable(False, False)
        self._center_window(440, 620)
        ctk.set_appearance_mode("dark")

        self._build_ui()

    def _center_window(self, w, h):
        """Put the window in the middle of the screen"""
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw // 2) - (w // 2)
        y  = (sh // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        """Create all the widgets on the login window"""
        self.configure(fg_color="#161b27")

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=44, pady=0)

        # push content to vertical centre
        ctk.CTkFrame(inner, fg_color="transparent", height=1).pack(expand=True)

        # ── Icon box ──────────────────────────────────────
        icon_box = ctk.CTkFrame(inner, fg_color="#1e2436", corner_radius=16,
                                width=68, height=68)
        icon_box.pack()
        icon_box.pack_propagate(False)
        ctk.CTkLabel(icon_box, text="⚡", font=ctk.CTkFont(size=34),
                     text_color="#e8820c").place(relx=0.5, rely=0.5, anchor="center")

        # ── Title & subtitle ──────────────────────────────
        ctk.CTkLabel(inner, text="Syntra",
                     font=ctk.CTkFont(size=28, weight="bold"),
                     text_color="#ffffff").pack(pady=(14, 2))
        ctk.CTkLabel(inner, text="Real-time work sync & tracking",
                     font=ctk.CTkFont(size=13),
                     text_color="#6b7494").pack(pady=(0, 26))

        # ── Email field ───────────────────────────────────
        ctk.CTkLabel(inner, text="Email Address", anchor="w",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#c8cde0").pack(fill="x")

        email_row = ctk.CTkFrame(inner, fg_color="#1e2130", corner_radius=10,
                                 border_color="#2e3347", border_width=1, height=50)
        email_row.pack(fill="x", pady=(4, 0))
        email_row.pack_propagate(False)
        ctk.CTkLabel(email_row, text="✉", font=ctk.CTkFont(size=15),
                     text_color="#5a6180", width=40).pack(side="left", padx=(10, 0))
        self.email_var = tk.StringVar()
        self.email_entry = ctk.CTkEntry(
            email_row, textvariable=self.email_var,
            placeholder_text="you@example.com",
            font=ctk.CTkFont(size=13), fg_color="transparent", border_width=0,
            text_color="#e0e4f0", placeholder_text_color="#4a5270",
        )
        self.email_entry.pack(side="left", fill="both", expand=True, padx=(4, 10))

        # ── Password field ────────────────────────────────
        ctk.CTkLabel(inner, text="Password", anchor="w",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#c8cde0").pack(fill="x", pady=(16, 0))

        pass_row = ctk.CTkFrame(inner, fg_color="#1e2130", corner_radius=10,
                                border_color="#2e3347", border_width=1, height=50)
        pass_row.pack(fill="x", pady=(4, 0))
        pass_row.pack_propagate(False)
        ctk.CTkLabel(pass_row, text="🔒", font=ctk.CTkFont(size=15),
                     text_color="#5a6180", width=40).pack(side="left", padx=(10, 0))
        self.password_var = tk.StringVar()
        self.password_entry = ctk.CTkEntry(
            pass_row, textvariable=self.password_var,
            placeholder_text="Enter your password", show="•",
            font=ctk.CTkFont(size=13), fg_color="transparent", border_width=0,
            text_color="#e0e4f0", placeholder_text_color="#4a5270",
        )
        self.password_entry.pack(side="left", fill="both", expand=True, padx=(4, 10))

        # ── Error label ───────────────────────────────────
        self.error_var = tk.StringVar(value="")
        self.error_label = ctk.CTkLabel(
            inner, textvariable=self.error_var,
            text_color="#FF6B6B", font=ctk.CTkFont(size=12), wraplength=360,
        )
        self.error_label.pack(pady=(10, 0))

        # ── Sign In button ────────────────────────────────
        self.login_btn = ctk.CTkButton(
            inner, text="Sign In  →", height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#4f8ef7", hover_color="#3a7ae8",
            corner_radius=12, command=self._on_login_click,
        )
        self.login_btn.pack(fill="x", pady=(14, 0))

        # ── Create account link ───────────────────────────
        foot = ctk.CTkFrame(inner, fg_color="transparent")
        foot.pack(pady=(12, 0))
        ctk.CTkLabel(foot, text="Don't have an account? ",
                     font=ctk.CTkFont(size=12), text_color="#6b7494").pack(side="left")
        ctk.CTkButton(foot, text="Create one",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      text_color="#4f8ef7", fg_color="transparent",
                      hover_color="#1a2035", border_width=0, height=22,
                      width=70, command=self._open_register).pack(side="left")

        ctk.CTkFrame(inner, fg_color="transparent", height=1).pack(expand=True)

        # Press Enter to login
        self.bind("<Return>", lambda _: self._on_login_click())
        self.email_entry.focus()

    def _open_register(self):
        """Open the registration window"""
        reg = RegisterWindow(self)
        reg.grab_set()

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
        self.destroy()                        # Close login window
        dashboard = DashboardWindow(user_data)
        dashboard.mainloop()

    def _login_failure(self, message: str):
        """Show error and re-enable the button"""
        self.error_var.set(message)
        self.login_btn.configure(text="Sign In →", state="normal")


# ══════════════════════════════════════════════════════════
#  REGISTER WINDOW
# ══════════════════════════════════════════════════════════
class RegisterWindow(ctk.CTkToplevel):
    """Modal window for creating a new account."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Syntra — Create Account")
        self.geometry("460x660")
        self.resizable(False, False)
        self._center_window(460, 660)
        self.configure(fg_color="#161b27")
        self._build_ui()

    def _center_window(self, w, h):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw // 2) - (w // 2)
        y  = (sh // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _make_field_row(self, parent, icon: str, var: tk.StringVar,
                        placeholder: str, show: str = ""):
        """Create a field row matching the web frontend style (icon + entry)."""
        row = ctk.CTkFrame(parent, fg_color="#1e2130", corner_radius=10,
                           border_color="#2e3347", border_width=1, height=50)
        row.pack(fill="x", pady=(4, 0))
        row.pack_propagate(False)

        ctk.CTkLabel(row, text=icon, font=ctk.CTkFont(size=15),
                     text_color="#5a6180", width=40).pack(side="left", padx=(10, 0))

        entry = ctk.CTkEntry(
            row, textvariable=var, placeholder_text=placeholder,
            show=show, font=ctk.CTkFont(size=13),
            fg_color="transparent", border_width=0, text_color="#e0e4f0",
            placeholder_text_color="#4a5270",
        )
        entry.pack(side="left", fill="both", expand=True, padx=(4, 10))
        return entry

    def _build_ui(self):
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=44, pady=0)

        # push content to vertical centre
        ctk.CTkFrame(inner, fg_color="transparent", height=1).pack(expand=True)

        # ── Icon box ──────────────────────────────────────
        icon_box = ctk.CTkFrame(inner, fg_color="#1e2436", corner_radius=16,
                                width=68, height=68)
        icon_box.pack()
        icon_box.pack_propagate(False)
        ctk.CTkLabel(icon_box, text="⚡", font=ctk.CTkFont(size=34),
                     text_color="#e8820c").place(relx=0.5, rely=0.5, anchor="center")

        # ── Title & subtitle ──────────────────────────────
        ctk.CTkLabel(inner, text="Create Account",
                     font=ctk.CTkFont(size=26, weight="bold"),
                     text_color="#ffffff").pack(pady=(14, 2))
        ctk.CTkLabel(inner, text="Join Syntra today",
                     font=ctk.CTkFont(size=13),
                     text_color="#6b7494").pack(pady=(0, 20))

        # ── Full Name ─────────────────────────────────────
        ctk.CTkLabel(inner, text="Full Name", anchor="w",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#c8cde0").pack(fill="x")
        self.name_var = tk.StringVar()
        self._make_field_row(inner, "👤", self.name_var, "Your name")

        # ── Email ─────────────────────────────────────────
        ctk.CTkLabel(inner, text="Email Address", anchor="w",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#c8cde0").pack(fill="x", pady=(14, 0))
        self.email_var = tk.StringVar()
        self._make_field_row(inner, "✉", self.email_var, "you@example.com")

        # ── Password ──────────────────────────────────────
        ctk.CTkLabel(inner, text="Password", anchor="w",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#c8cde0").pack(fill="x", pady=(14, 0))
        self.pass_var = tk.StringVar()
        self._make_field_row(inner, "🔒", self.pass_var, "Min 6 characters", show="•")

        # ── Error label ───────────────────────────────────
        self.error_var = tk.StringVar(value="")
        ctk.CTkLabel(inner, textvariable=self.error_var,
                     text_color="#FF6B6B", font=ctk.CTkFont(size=12),
                     wraplength=360).pack(pady=(10, 0))

        # ── Create Account button ─────────────────────────
        self.btn = ctk.CTkButton(
            inner, text="Create Account  →", height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#4f8ef7", hover_color="#3a7ae8",
            corner_radius=12, command=self._on_submit,
        )
        self.btn.pack(fill="x", pady=(14, 0))

        # ── Back link ─────────────────────────────────────
        foot = ctk.CTkFrame(inner, fg_color="transparent")
        foot.pack(pady=(12, 0))
        ctk.CTkLabel(foot, text="Already have an account? ",
                     font=ctk.CTkFont(size=12), text_color="#6b7494").pack(side="left")
        ctk.CTkButton(foot, text="Sign in",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      text_color="#4f8ef7", fg_color="transparent",
                      hover_color="#1e2435", border_width=0, height=22,
                      width=50, command=self.destroy).pack(side="left")

        ctk.CTkFrame(inner, fg_color="transparent", height=1).pack(expand=True)

        self.bind("<Return>", lambda _: self._on_submit())

    def _on_submit(self):
        name     = self.name_var.get().strip()
        email    = self.email_var.get().strip()
        password = self.pass_var.get().strip()

        if not name or not email or not password:
            self.error_var.set("⚠  Please fill in all fields.")
            return
        if len(password) < 6:
            self.error_var.set("⚠  Password must be at least 6 characters.")
            return

        self.btn.configure(text="Creating...", state="disabled")
        self.error_var.set("")
        threading.Thread(target=self._do_register,
                         args=(name, email, password), daemon=True).start()

    def _do_register(self, name: str, email: str, password: str):
        try:
            res = requests.post(
                f"{API_URL}/api/register",
                json={"username": name, "email": email, "password": password},
                timeout=10,
            )
            data = res.json()
            if res.ok and data.get("success"):
                self.after(0, self._success)
            else:
                msg = data.get("detail", "Registration failed.")
                self.after(0, lambda: self._failure(msg))
        except requests.exceptions.ConnectionError:
            self.after(0, lambda: self._failure("⚠  Cannot connect to server."))
        except Exception as e:
            self.after(0, lambda: self._failure(f"⚠  Error: {e}"))

    def _success(self):
        self.error_var.set("")
        self.btn.configure(text="✓ Account created! Closing...", state="disabled",
                           fg_color="#2ecc71")
        self.after(1800, self.destroy)

    def _failure(self, msg: str):
        self.error_var.set(msg)
        self.btn.configure(text="Create Account", state="normal")



class DashboardWindow(ctk.CTk):
    """
    Opens after successful login.
    Shows screenshot stats and controls.
    Runs the screenshot loop in a background thread.
    """

    def __init__(self, user_data: dict):
        super().__init__()

        self.user_data        = user_data
        self.user_id          = user_data["user_id"]
        self.username         = user_data["username"]
        self.screenshot_count = 0
        self.is_capturing     = True      # Set to False to stop the loop

        # Activity tracker — started after UI is built
        self._tracker     = ActivityTracker(log_fn=self._log)
        self._app_tracker = AppTracker(log_fn=self._log)

        self.title(f"Syntra — {self.username}")
        self.geometry("540x680")
        self.resizable(False, False)
        self._center_window(540, 680)

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

        ctk.CTkLabel(
            header,
            text="⚡  Syntra",
            font=ctk.CTkFont(size=19, weight="bold"),
        ).pack(side="left", padx=20, pady=18)

        # Live indicator
        live_frame = ctk.CTkFrame(header, fg_color="transparent")
        live_frame.pack(side="right", padx=20)
        ctk.CTkLabel(live_frame, text="●", text_color="#00FF88", font=ctk.CTkFont(size=16)).pack(side="left")
        ctk.CTkLabel(live_frame, text=" MONITORING", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00FF88").pack(side="left")

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

    def _take_and_upload_screenshot(self):
        """Take one screenshot, convert to base64, upload to FastAPI"""

        # ── Step 1: Take screenshot ──────────────────────
        screenshot = pyautogui.screenshot()

        # ── Step 2: Compress and convert to base64 ───────
        # We save to an in-memory buffer instead of a file
        buffer = io.BytesIO()
        screenshot.save(buffer, format="PNG", optimize=True)
        raw_bytes    = buffer.getvalue()
        base64_str   = base64.b64encode(raw_bytes).decode("utf-8")

        # ── Step 3: Build filename ────────────────────────
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{self.user_id}_{ts}.png"

        # ── Step 4: Upload to backend ─────────────────────
        response = requests.post(
            f"{API_URL}/api/screenshots/upload",
            json={
                "user_id":    self.user_id,
                "filename":   filename,
                "image_data": base64_str,
            },
            timeout=30,
        )

        if response.status_code == 200:
            self.screenshot_count += 1
            size_kb = len(raw_bytes) // 1024
            now_str = datetime.now().strftime("%H:%M:%S")

            # Update the UI (must happen on main thread)
            self.after(0, self._update_stats, now_str, size_kb)
            self._log(f"📷 Screenshot #{self.screenshot_count} saved ({size_kb} KB)")
        else:
            self._log(f"⚠  Upload failed: {response.status_code} — {response.text[:80]}")

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
            self.is_capturing = False
            self._tracker.stop()
            self._app_tracker.stop()
            self.destroy()
            # Re-open the login window
            LoginWindow().mainloop()

    def _on_close(self):
        if messagebox.askyesno("Exit", "Stop capturing and exit the app?"):
            self.is_capturing = False
            self._tracker.stop()
            self._app_tracker.stop()
            self.destroy()


# ══════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = LoginWindow()
    app.mainloop()
