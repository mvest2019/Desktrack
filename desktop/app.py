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
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ── Font initialisation ─────────────────────────────────────
# Defaults to Segoe UI; upgraded to Lexend Deca in _init_ui_font()
# once a Tk root window exists and font families can be queried.
_UI_FONT: str = "Segoe UI"


def _init_ui_font(root) -> None:
    """Detect best available UI font once the Tk root window exists."""
    global _UI_FONT
    import tkinter.font as tkfont
    try:
        available = tkfont.families(root)
        for candidate in ("Lexend Deca", "Segoe UI Variable", "Segoe UI", "Calibri"):
            if candidate in available:
                _UI_FONT = candidate
                return
    except Exception:
        pass


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
        _init_ui_font(self)

        self.title("Realisieren Pulse")
        self.geometry("440x620")
        self.resizable(False, False)
        self._center_window(440, 620)
        ctk.set_appearance_mode("light")
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
        row = ctk.CTkFrame(parent, fg_color="#F8FAFC", corner_radius=10,
                           border_color="#E2E8F0", border_width=1, height=50)
        row.pack(fill="x", pady=(4, 0))
        row.pack_propagate(False)
        ctk.CTkLabel(row, text=icon, font=ctk.CTkFont(size=15),
                     text_color="#94A3B8", width=40).pack(side="left", padx=(10, 0))
        entry = ctk.CTkEntry(row, textvariable=var, placeholder_text=placeholder,
                             show=show, font=ctk.CTkFont(size=13),
                             fg_color="transparent", border_width=0,
                             text_color="#0F172A", placeholder_text_color="#94A3B8")
        entry.pack(side="left", fill="both", expand=True, padx=(4, 10))
        return entry

    def _make_dropdown_row(self, parent, icon, var, values):
        row = ctk.CTkFrame(parent, fg_color="#F8FAFC", corner_radius=10,
                           border_color="#E2E8F0", border_width=1, height=50)
        row.pack(fill="x", pady=(4, 0))
        row.pack_propagate(False)
        ctk.CTkLabel(row, text=icon, font=ctk.CTkFont(size=15),
                     text_color="#94A3B8", width=40).pack(side="left", padx=(10, 0))
        menu = ctk.CTkOptionMenu(row, variable=var, values=values,
                                 font=ctk.CTkFont(size=13),
                                 fg_color="#F8FAFC", button_color="#E2E8F0",
                                 button_hover_color="#CBD5E1", text_color="#0F172A",
                                 dropdown_fg_color="#FFFFFF", dropdown_text_color="#0F172A")
        menu.pack(side="left", fill="both", expand=True, padx=(4, 10))
        return menu

    def _build_ui(self):
        """Create both Sign In and Create Account views inside the same window."""
        self.configure(fg_color="#FFFFFF")

        # ── Shared icon header (always visible) ──────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(pady=(36, 0))

        icon_box = ctk.CTkFrame(header, fg_color="#F1F5F9", corner_radius=20,
                                width=96, height=96)
        icon_box.pack()
        icon_box.pack_propagate(False)
        try:
            _img = ctk.CTkImage(Image.open(_ICON_PNG), size=(76, 76))
            ctk.CTkLabel(icon_box, image=_img, text="").place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            ctk.CTkLabel(icon_box, text="R", font=ctk.CTkFont(size=44, weight="bold"),
                         text_color="#4F63D2").place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(header, text="Realisieren Pulse",
                     font=ctk.CTkFont(size=24, weight="bold"),
                     text_color="#0F172A").pack(pady=(12, 0))

        # ── Sign In frame ─────────────────────────────────
        self._login_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._login_frame.pack(fill="both", expand=True, padx=44)

        ctk.CTkLabel(self._login_frame, text="Sign in to your workspace",
                     font=ctk.CTkFont(size=13),
                     text_color="#64748B").pack(pady=(4, 20))

        ctk.CTkLabel(self._login_frame, text="Email Address", anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#475569").pack(fill="x")
        self.email_var = tk.StringVar()
        self.email_entry = self._make_field_row(
            self._login_frame, "✉", self.email_var, "you@example.com")

        ctk.CTkLabel(self._login_frame, text="Password", anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#475569").pack(fill="x", pady=(14, 0))
        self.password_var = tk.StringVar()
        self.password_entry = self._make_field_row(
            self._login_frame, "🔒", self.password_var, "Enter your password", show="•")

        self.error_var = tk.StringVar(value="")
        ctk.CTkLabel(self._login_frame, textvariable=self.error_var,
                     text_color="#DC2626", font=ctk.CTkFont(size=12),
                     wraplength=360).pack(pady=(8, 0))

        self.login_btn = ctk.CTkButton(
            self._login_frame, text="Sign In  →", height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#4F63D2", hover_color="#4050C0",
            corner_radius=12, command=self._on_login_click,
        )
        self.login_btn.pack(fill="x", pady=(12, 0))

        foot1 = ctk.CTkFrame(self._login_frame, fg_color="transparent")
        foot1.pack(pady=(10, 0))
        ctk.CTkLabel(foot1, text="Don't have an account? ",
                     font=ctk.CTkFont(size=12), text_color="#64748B").pack(side="left")
        ctk.CTkButton(foot1, text="Create one",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      text_color="#4F63D2", fg_color="transparent",
                      hover_color="#EEF2FF", border_width=0, height=22,
                      width=70, command=self._show_register).pack(side="left")

        # ── Create Account frame (hidden initially) ───────
        self._reg_frame = ctk.CTkFrame(self, fg_color="transparent")

        ctk.CTkLabel(self._reg_frame, text="Create your account",
                     font=ctk.CTkFont(size=13),
                     text_color="#64748B").pack(pady=(4, 12), padx=44)

        reg_scroll = ctk.CTkScrollableFrame(self._reg_frame, fg_color="transparent",
                                            scrollbar_button_color="#E2E8F0",
                                            scrollbar_button_hover_color="#CBD5E1")
        reg_scroll.pack(fill="both", expand=True, padx=44)

        ctk.CTkLabel(reg_scroll, text="Full Name", anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#475569").pack(fill="x")
        self.reg_name_var = tk.StringVar()
        self._make_field_row(reg_scroll, "👤", self.reg_name_var, "Your name")

        ctk.CTkLabel(reg_scroll, text="Email Address", anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#475569").pack(fill="x", pady=(12, 0))
        self.reg_email_var = tk.StringVar()
        self._make_field_row(reg_scroll, "✉", self.reg_email_var, "you@example.com")

        ctk.CTkLabel(reg_scroll, text="Password", anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#475569").pack(fill="x", pady=(12, 0))
        self.reg_pass_var = tk.StringVar()
        self._make_field_row(reg_scroll, "🔒", self.reg_pass_var, "Min 6 characters", show="•")

        ctk.CTkLabel(reg_scroll, text="You can add Project, Designation and Skills from your Profile after sign-in.",
                     font=ctk.CTkFont(size=11), text_color="#94A3B8",
                     wraplength=320).pack(pady=(10, 0))

        self.reg_error_var = tk.StringVar(value="")
        ctk.CTkLabel(reg_scroll, textvariable=self.reg_error_var,
                     text_color="#DC2626", font=ctk.CTkFont(size=12),
                     wraplength=320).pack(pady=(8, 0))

        self.reg_btn = ctk.CTkButton(
            reg_scroll, text="Create Account  →", height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#4F63D2", hover_color="#4050C0",
            corner_radius=12, command=self._on_register_click,
        )
        self.reg_btn.pack(fill="x", pady=(12, 0))

        foot2 = ctk.CTkFrame(reg_scroll, fg_color="transparent")
        foot2.pack(pady=(10, 0))
        ctk.CTkLabel(foot2, text="Already have an account? ",
                     font=ctk.CTkFont(size=12), text_color="#64748B").pack(side="left")
        ctk.CTkButton(foot2, text="Sign in",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      text_color="#4F63D2", fg_color="transparent",
                      hover_color="#EEF2FF", border_width=0, height=22,
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
        self.reg_btn.configure(text="Create Account  →", state="normal", fg_color="#4F63D2")
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
        TaskEntryDialog(self, user_data).focus()

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
            self.reg_error_var.set("⚠  Please fill in Name, Email and Password.")
            return
        if len(password) < 6:
            self.reg_error_var.set("⚠  Password must be at least 6 characters.")
            return
        self.reg_btn.configure(text="Creating...", state="disabled")
        self.reg_error_var.set("")
        threading.Thread(target=self._do_register,
                         args=(name, email, password),
                         daemon=True).start()

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
        self.reg_btn.configure(text="Create Account  →", state="normal", fg_color="#4F63D2")





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
        self.configure(fg_color="#FFFFFF")
        self.after(200, lambda: _set_window_icon(self))

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self, w, h):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build_ui(self):
        self.configure(fg_color="#EBF0FF")
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=40, pady=0)

        ctk.CTkFrame(inner, fg_color="transparent", height=24).pack()

        # Icon in white rounded box
        icon_box = ctk.CTkFrame(inner, fg_color="#FFFFFF", corner_radius=22,
                                width=100, height=100)
        icon_box.pack()
        icon_box.pack_propagate(False)
        try:
            _img = ctk.CTkImage(Image.open(_ICON_PNG), size=(82, 82))
            ctk.CTkLabel(icon_box, image=_img, text="").place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            ctk.CTkLabel(icon_box, text="R", font=ctk.CTkFont(family=_UI_FONT, size=44, weight="bold"),
                         text_color="#4F63D2").place(relx=0.5, rely=0.5, anchor="center")

        # Greeting
        name = self.user_data.get("username", "there")
        ctk.CTkLabel(inner, text="Welcome back,",
                     font=ctk.CTkFont(family=_UI_FONT, size=14),
                     text_color="#64748B").pack(pady=(20, 0))
        ctk.CTkLabel(inner, text=name,
                     font=ctk.CTkFont(family=_UI_FONT, size=30, weight="bold"),
                     text_color="#0F172A").pack(pady=(2, 0))
        ctk.CTkLabel(inner, text="Let's continue your productive journey.",
                     font=ctk.CTkFont(family=_UI_FONT, size=12),
                     text_color="#94A3B8").pack(pady=(4, 20))

        # Start Monitoring button
        ctk.CTkButton(
            inner, text="▶   Start Monitoring", height=54,
            font=ctk.CTkFont(family=_UI_FONT, size=15, weight="bold"),
            fg_color="#4F63D2", hover_color="#4050C0",
            corner_radius=14, command=self._start,
        ).pack(fill="x", pady=(0, 14))

        # Security info card
        sec_card = ctk.CTkFrame(inner, fg_color="#FFFFFF", corner_radius=14,
                                border_color="#E2E8F0", border_width=1)
        sec_card.pack(fill="x", pady=(0, 14))
        sec_row = ctk.CTkFrame(sec_card, fg_color="transparent")
        sec_row.pack(fill="x", padx=14, pady=14)
        shield_ic = ctk.CTkFrame(sec_row, fg_color="#EEF2FF", corner_radius=10,
                                 width=42, height=42)
        shield_ic.pack(side="left", padx=(0, 12))
        shield_ic.pack_propagate(False)
        ctk.CTkLabel(shield_ic, text="🛡", font=ctk.CTkFont(size=20),
                     text_color="#4F63D2").place(relx=0.5, rely=0.5, anchor="center")
        txt_col = ctk.CTkFrame(sec_row, fg_color="transparent")
        txt_col.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(txt_col, text="Your activity is secure", anchor="w",
                     font=ctk.CTkFont(family=_UI_FONT, size=12, weight="bold"),
                     text_color="#0F172A").pack(anchor="w")
        ctk.CTkLabel(txt_col, text="Realisieren Pulse runs in the background\nand keeps your data safe.",
                     anchor="w", font=ctk.CTkFont(family=_UI_FONT, size=11),
                     text_color="#94A3B8", justify="left").pack(anchor="w", pady=(2, 0))

        # Sign out footer
        foot = ctk.CTkFrame(inner, fg_color="transparent")
        foot.pack(pady=(4, 0))
        ctk.CTkLabel(foot, text="Not you?  ",
                     font=ctk.CTkFont(family=_UI_FONT, size=13),
                     text_color="#64748B").pack(side="left")
        ctk.CTkButton(foot, text="Sign out",
                      font=ctk.CTkFont(family=_UI_FONT, size=13, weight="bold"),
                      text_color="#4F63D2", fg_color="transparent",
                      hover_color="#EEF2FF", border_width=0, height=24, width=70,
                      command=self._sign_out).pack(side="left")

        ctk.CTkFrame(inner, fg_color="transparent", height=8).pack()

    def _start(self):
        self.withdraw()
        TaskEntryDialog(self._login_win, self.user_data, start_win=self).focus()

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
#  TASK ENTRY DIALOG  (shown before monitoring starts)
# ══════════════════════════════════════════════════════════
class TaskEntryDialog(ctk.CTkToplevel):
    """
    Mandatory pre-monitoring popup: "What is your today's task?"
    Single title-only input. On submit → creates task via API, opens DashboardWindow.
    If today's task already exists → skip directly to DashboardWindow.
    """

    def __init__(self, login_win, user_data: dict, start_win=None):
        super().__init__(login_win)
        self._login_win = login_win
        self._start_win = start_win
        self.user_data  = user_data
        self.user_id    = user_data["user_id"]
        self._task_id   = None
        self._task_title = ""
        self._task_status = "pending"

        self.title("Realisieren Pulse — Today's Task")
        self.geometry("460x380")
        self.resizable(False, False)
        self._center_window(460, 380)
        self.configure(fg_color="#FFFFFF")
        self.after(200, lambda: _set_window_icon(self))
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        # Check for existing task in background
        threading.Thread(target=self._check_existing_task, daemon=True).start()

    def _center_window(self, w, h):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build_ui(self):
        self.configure(fg_color="#F0F4FF")
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=36, pady=0)

        ctk.CTkFrame(outer, fg_color="transparent", height=28).pack()

        # Icon
        icon_box = ctk.CTkFrame(outer, fg_color="#FFFFFF", corner_radius=18,
                                width=72, height=72)
        icon_box.pack()
        icon_box.pack_propagate(False)
        try:
            _img = ctk.CTkImage(Image.open(_ICON_PNG), size=(56, 56))
            ctk.CTkLabel(icon_box, image=_img, text="").place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            ctk.CTkLabel(icon_box, text="✓", font=ctk.CTkFont(size=30, weight="bold"),
                         text_color="#4F63D2").place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(outer, text="What is your today's task?",
                     font=ctk.CTkFont(family=_UI_FONT, size=18, weight="bold"),
                     text_color="#0F172A").pack(pady=(16, 4))
        ctk.CTkLabel(outer, text="Enter your main focus for today to start monitoring.",
                     font=ctk.CTkFont(family=_UI_FONT, size=11),
                     text_color="#94A3B8").pack()

        # Input field
        field_frame = ctk.CTkFrame(outer, fg_color="#FFFFFF", corner_radius=12,
                                   border_color="#CBD5E1", border_width=1, height=50)
        field_frame.pack(fill="x", pady=(20, 0))
        field_frame.pack_propagate(False)
        self._task_var = tk.StringVar()
        self._entry = ctk.CTkEntry(
            field_frame, textvariable=self._task_var,
            placeholder_text="e.g. Build login screen, Fix API bug…",
            font=ctk.CTkFont(family=_UI_FONT, size=13),
            fg_color="transparent", border_width=0,
            text_color="#0F172A", placeholder_text_color="#94A3B8",
        )
        self._entry.pack(fill="both", expand=True, padx=14, pady=8)
        self._entry.bind("<Return>", lambda _: self._on_submit())

        self._err_var = tk.StringVar(value="")
        ctk.CTkLabel(outer, textvariable=self._err_var,
                     text_color="#DC2626", font=ctk.CTkFont(size=11),
                     wraplength=380).pack(pady=(6, 0))

        self._btn = ctk.CTkButton(
            outer, text="▶  Start Monitoring", height=50,
            font=ctk.CTkFont(family=_UI_FONT, size=14, weight="bold"),
            fg_color="#4F63D2", hover_color="#4050C0",
            corner_radius=14, command=self._on_submit,
        )
        self._btn.pack(fill="x", pady=(10, 0))

        ctk.CTkFrame(outer, fg_color="transparent", height=8).pack()

    def _check_existing_task(self):
        """Background: if a task already exists for today, skip the prompt."""
        try:
            res = requests.get(f"{API_URL}/api/tasks/{self.user_id}/today", timeout=8)
            if res.status_code == 200:
                data = res.json()
                if data.get("success") and data.get("task"):
                    t = data["task"]
                    self._task_id = t["id"]
                    self._task_title = t["title"]
                    self._task_status = t["status"]
                    self.after(0, self._skip_to_dashboard)
        except Exception:
            pass  # Network error — let user fill in form normally

    def _skip_to_dashboard(self):
        self.withdraw()
        DashboardWindow(
            self._login_win, self.user_data,
            start_win=self._start_win,
            task_id=self._task_id,
            task_title=self._task_title,
            task_status=self._task_status,
        ).focus()
        self.destroy()

    def _on_submit(self):
        title = self._task_var.get().strip()
        if not title:
            self._err_var.set("⚠  Please enter your task for today.")
            return
        self._btn.configure(text="Starting…", state="disabled")
        self._err_var.set("")
        threading.Thread(target=self._do_create_task, args=(title,), daemon=True).start()

    def _do_create_task(self, title: str):
        try:
            res = requests.post(
                f"{API_URL}/api/tasks/quick",
                json={"user_id": self.user_id, "title": title},
                timeout=10,
            )
            if res.status_code == 200:
                data = res.json()
                self._task_id    = data["task_id"]
                self._task_title = data["title"]
                self._task_status = data["status"]
                self.after(0, self._skip_to_dashboard)
            elif res.status_code == 404:
                # User doesn't exist on this server
                _clear_session()
                self.after(0, lambda: self._show_error(
                    f"⚠  Account not found on server ({API_URL}).\n"
                    "Please register or sign in."
                ))
                self.after(2500, self._back_to_login)
            else:
                detail = ""
                try: detail = res.json().get("detail", "")
                except Exception: pass
                msg = f"Server error {res.status_code}"
                if detail: msg += f": {detail}"
                self.after(0, lambda m=msg: self._show_error(f"⚠  {m}. Proceeding offline."))
                self.after(800, lambda: self._open_dashboard_no_task(title))
        except requests.exceptions.ConnectionError:
            self.after(0, lambda: self._show_error("⚠  Cannot reach server. Proceeding offline."))
            self.after(800, lambda: self._open_dashboard_no_task(title))
        except Exception:
            self.after(0, lambda: self._show_error("⚠  Unexpected error. Proceeding offline."))
            self.after(800, lambda: self._open_dashboard_no_task(title))

    def _back_to_login(self):
        self.destroy()
        if self._start_win:
            try: self._start_win.destroy()
            except Exception: pass
        try:
            self._login_win.error_var.set("⚠  Account not found. Please register.")
            self._login_win.email_var.set("")
            self._login_win.password_var.set("")
            self._login_win.login_btn.configure(text="Sign In  →", state="normal")
            self._login_win.deiconify()
        except Exception:
            pass

    def _open_dashboard_no_task(self, title: str):
        self.withdraw()
        DashboardWindow(
            self._login_win, self.user_data,
            start_win=self._start_win,
            task_id=None,
            task_title=title,
            task_status="pending",
        ).focus()
        self.destroy()

    def _show_error(self, msg: str):
        self._err_var.set(msg)
        self._btn.configure(text="▶  Start Monitoring", state="normal")

    def _on_close(self):
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

    def __init__(self, login_win, user_data: dict, start_win=None,
                 task_id=None, task_title="", task_status="pending"):
        super().__init__(login_win)

        self._login_win       = login_win
        self._start_win       = start_win
        self.user_data        = user_data
        self.user_id          = user_data["user_id"]
        self.username         = user_data["username"]
        self.screenshot_count = 0
        self.is_capturing     = True

        # Task state
        self._task_id     = task_id
        self._task_title  = task_title
        self._task_status = task_status

        # Local queue — screenshots saved here when API is unreachable
        import tempfile
        self._queue_dir = Path(tempfile.gettempdir()) / "realisieren_pulse_pending" / str(self.user_id)
        self._queue_dir.mkdir(parents=True, exist_ok=True)

        # Activity tracker — started after UI is built
        self._tracker     = ActivityTracker(log_fn=self._log)
        self._app_tracker = AppTracker(log_fn=self._log)

        self.title(f"Realisieren Pulse — {self.username}")
        self.geometry("560x700")
        self.resizable(False, True)
        self._center_window(560, 700)
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
        self.configure(fg_color="#F5F7FA")

        # ── Header ───────────────────────────────────────
        header = ctk.CTkFrame(self, height=56, corner_radius=0,
                              fg_color="#FFFFFF", border_color="#E2E8F0", border_width=1)
        header.pack(fill="x")
        header.pack_propagate(False)
        try:
            _hdr_img = ctk.CTkImage(Image.open(_ICON_PNG), size=(28, 28))
            ctk.CTkLabel(header, image=_hdr_img, text="  Realisieren Pulse",
                         compound="left", text_color="#0F172A",
                         font=ctk.CTkFont(family=_UI_FONT, size=15, weight="bold")).pack(side="left", padx=16, pady=14)
        except Exception:
            ctk.CTkLabel(header, text="Realisieren Pulse",
                         font=ctk.CTkFont(family=_UI_FONT, size=15, weight="bold"),
                         text_color="#0F172A").pack(side="left", padx=16, pady=14)

        live_pill = ctk.CTkFrame(header, fg_color="#F0FDF4", corner_radius=20)
        live_pill.pack(side="right", padx=14, pady=14)
        ctk.CTkLabel(live_pill, text="●", text_color="#22C55E",
                     font=ctk.CTkFont(size=9)).pack(side="left", padx=(8, 2))
        ctk.CTkLabel(live_pill, text="MONITORING",
                     font=ctk.CTkFont(family=_UI_FONT, size=9, weight="bold"),
                     text_color="#16A34A").pack(side="left", padx=(0, 8))

        # ── Scrollable content ────────────────────────────
        scroll = ctk.CTkScrollableFrame(self, fg_color="#F5F7FA",
                                        scrollbar_button_color="#CBD5E1",
                                        scrollbar_button_hover_color="#94A3B8")
        scroll.pack(fill="both", expand=True)
        inner = ctk.CTkFrame(scroll, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=12)

        # ── KPI strip ─────────────────────────────────────
        self._kpi_tasks_var  = tk.StringVar(value="—")
        self._kpi_done_var   = tk.StringVar(value="—")
        self._kpi_active_var = tk.StringVar(value="—")

        kpi_row = ctk.CTkFrame(inner, fg_color="transparent")
        kpi_row.pack(fill="x", pady=(0, 10))

        def kpi_card(parent, label, var, icon, color, last=False):
            c = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=12,
                             border_color="#E2E8F0", border_width=1)
            c.pack(side="left", expand=True, fill="x",
                   padx=(0, 0 if last else 8))
            body = ctk.CTkFrame(c, fg_color="transparent")
            body.pack(expand=True, fill="both", padx=12, pady=10)
            ic_bg = ctk.CTkFrame(body, fg_color=color, corner_radius=8, width=30, height=30)
            ic_bg.pack(side="left", padx=(0, 10))
            ic_bg.pack_propagate(False)
            ctk.CTkLabel(ic_bg, text=icon,
                         font=ctk.CTkFont(size=13)).place(relx=0.5, rely=0.5, anchor="center")
            txt = ctk.CTkFrame(body, fg_color="transparent")
            txt.pack(side="left", fill="both", expand=True)
            ctk.CTkLabel(txt, textvariable=var,
                         font=ctk.CTkFont(family=_UI_FONT, size=18, weight="bold"),
                         text_color="#0F172A", anchor="w").pack(anchor="w")
            ctk.CTkLabel(txt, text=label,
                         font=ctk.CTkFont(family=_UI_FONT, size=10),
                         text_color="#94A3B8", anchor="w").pack(anchor="w")

        kpi_card(kpi_row, "Today's Tasks",  self._kpi_tasks_var,  "✅", "#EEF2FF")
        kpi_card(kpi_row, "Completed",       self._kpi_done_var,   "🏁", "#F0FDF4")
        kpi_card(kpi_row, "Active Today",    self._kpi_active_var, "⚡", "#FFFBEB", last=True)

        # ══ TASKS CARD ════════════════════════════════════
        task_card = self._card(inner)

        # Card header row
        task_hdr = ctk.CTkFrame(task_card, fg_color="transparent")
        task_hdr.pack(fill="x", padx=14, pady=(12, 0))

        hdr_left = ctk.CTkFrame(task_hdr, fg_color="transparent")
        hdr_left.pack(side="left")
        ic_t = ctk.CTkFrame(hdr_left, fg_color="#EEF2FF", corner_radius=8, width=28, height=28)
        ic_t.pack(side="left", padx=(0, 8))
        ic_t.pack_propagate(False)
        ctk.CTkLabel(ic_t, text="✅", font=ctk.CTkFont(size=12)).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(hdr_left, text="Today's Tasks",
                     font=ctk.CTkFont(family=_UI_FONT, size=13, weight="bold"),
                     text_color="#0F172A").pack(side="left")
        self._task_count_badge = ctk.CTkLabel(
            hdr_left, text="  0  ",
            font=ctk.CTkFont(family=_UI_FONT, size=10, weight="bold"),
            fg_color="#EEF2FF", text_color="#4F63D2", corner_radius=8,
        )
        self._task_count_badge.pack(side="left", padx=(6, 0))

        self._add_btn = ctk.CTkButton(
            task_hdr, text="+ Add", height=26, width=64,
            font=ctk.CTkFont(family=_UI_FONT, size=11, weight="bold"),
            fg_color="#EEF2FF", hover_color="#DBEAFE", text_color="#4F63D2",
            corner_radius=8, command=self._toggle_add_form,
        )
        self._add_btn.pack(side="right")

        # Task list container (packed first so add form can use before=)
        self._tasks_container = ctk.CTkFrame(task_card, fg_color="transparent")
        self._tasks_container.pack(fill="x", padx=12, pady=(8, 12))

        self._tasks_loading_lbl = ctk.CTkLabel(
            self._tasks_container, text="Loading tasks…",
            font=ctk.CTkFont(family=_UI_FONT, size=12), text_color="#94A3B8",
        )
        self._tasks_loading_lbl.pack(pady=14)

        # Inline add form (hidden — shown before _tasks_container via before=)
        self._add_form_visible = False
        self._add_form_frame = ctk.CTkFrame(task_card, fg_color="#F8FAFC",
                                            corner_radius=10, border_color="#E2E8F0", border_width=1)
        self._add_var = tk.StringVar()
        add_inner = ctk.CTkFrame(self._add_form_frame, fg_color="transparent")
        add_inner.pack(fill="x", padx=10, pady=8)
        self._add_entry = ctk.CTkEntry(
            add_inner, textvariable=self._add_var,
            placeholder_text="Task title… (press Enter to add)",
            font=ctk.CTkFont(family=_UI_FONT, size=12),
            fg_color="#FFFFFF", border_color="#CBD5E1", border_width=1,
            text_color="#0F172A", placeholder_text_color="#94A3B8", height=34,
        )
        self._add_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._add_entry.bind("<Return>", lambda _: self._do_add_task())
        self._add_submit_btn = ctk.CTkButton(
            add_inner, text="Add", height=34, width=54,
            font=ctk.CTkFont(family=_UI_FONT, size=11, weight="bold"),
            fg_color="#4F63D2", hover_color="#4050C0", corner_radius=8,
            command=self._do_add_task,
        )
        self._add_submit_btn.pack(side="left")

        # Load all tasks in background
        threading.Thread(target=self._load_all_tasks, daemon=True).start()

        # ══ TRACKING STATUS CARD ═════════════════════════
        track_card = self._card(inner)
        track_hdr = ctk.CTkFrame(track_card, fg_color="transparent")
        track_hdr.pack(fill="x", padx=14, pady=(12, 8))
        ic_tr = ctk.CTkFrame(track_hdr, fg_color="#EEF2FF", corner_radius=8, width=28, height=28)
        ic_tr.pack(side="left", padx=(0, 8))
        ic_tr.pack_propagate(False)
        ctk.CTkLabel(ic_tr, text="📊", font=ctk.CTkFont(size=12)).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(track_hdr, text="Tracking Status",
                     font=ctk.CTkFont(family=_UI_FONT, size=13, weight="bold"),
                     text_color="#0F172A").pack(side="left")

        live_row = ctk.CTkFrame(track_card, fg_color="#F0FDF4", corner_radius=10)
        live_row.pack(fill="x", padx=14, pady=(0, 8))
        self.status_dot = ctk.CTkLabel(live_row, text="●", text_color="#22C55E",
                                       font=ctk.CTkFont(size=11))
        self.status_dot.pack(side="left", padx=(10, 4), pady=10)
        self.status_text = ctk.CTkLabel(
            live_row, text="Tracking started",
            font=ctk.CTkFont(family=_UI_FONT, size=12, weight="bold"),
            text_color="#16A34A",
        )
        self.status_text.pack(side="left")

        self._screenshots_var = tk.StringVar(value="0 screenshots uploaded")
        ctk.CTkLabel(track_card, textvariable=self._screenshots_var,
                     font=ctk.CTkFont(family=_UI_FONT, size=11),
                     text_color="#64748B").pack(padx=14, pady=(0, 12), anchor="w")

        # ══ PROFILE CARD ═════════════════════════════════
        prof_card = self._card(inner)
        prof_hdr = ctk.CTkFrame(prof_card, fg_color="transparent")
        prof_hdr.pack(fill="x", padx=14, pady=(12, 10))
        ic_p = ctk.CTkFrame(prof_hdr, fg_color="#EEF2FF", corner_radius=8, width=28, height=28)
        ic_p.pack(side="left", padx=(0, 8))
        ic_p.pack_propagate(False)
        ctk.CTkLabel(ic_p, text="👤", font=ctk.CTkFont(size=12)).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(prof_hdr, text="My Profile",
                     font=ctk.CTkFont(family=_UI_FONT, size=13, weight="bold"),
                     text_color="#0F172A").pack(side="left")

        # Avatar + identity
        av_row = ctk.CTkFrame(prof_card, fg_color="transparent")
        av_row.pack(fill="x", padx=14, pady=(0, 10))
        initials = "".join(w[0].upper() for w in self.username.split()[:2]) or "U"
        avatar = ctk.CTkFrame(av_row, fg_color="#EEF2FF", corner_radius=22, width=44, height=44)
        avatar.pack(side="left", padx=(0, 12))
        avatar.pack_propagate(False)
        ctk.CTkLabel(avatar, text=initials,
                     font=ctk.CTkFont(family=_UI_FONT, size=15, weight="bold"),
                     text_color="#4F63D2").place(relx=0.5, rely=0.5, anchor="center")
        name_col = ctk.CTkFrame(av_row, fg_color="transparent")
        name_col.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(name_col, text=self.username, anchor="w",
                     font=ctk.CTkFont(family=_UI_FONT, size=13, weight="bold"),
                     text_color="#0F172A").pack(anchor="w")
        ctk.CTkLabel(name_col, text=self.user_data.get("email", ""), anchor="w",
                     font=ctk.CTkFont(family=_UI_FONT, size=11),
                     text_color="#64748B").pack(anchor="w")

        # Stats grid (2-column)
        role_label = self.user_data.get("user_type", "user").replace("user", "Employee").replace("admin", "Admin")
        self._role_var  = tk.StringVar(value=role_label)
        self._proj_var  = tk.StringVar(value=self.user_data.get("project") or "—")
        self._desig_var = tk.StringVar(value=self.user_data.get("designation") or "—")
        self._hours_var = tk.StringVar(value="Loading…")
        self._today_var = tk.StringVar(value="Loading…")

        grid = ctk.CTkFrame(prof_card, fg_color="transparent")
        grid.pack(fill="x", padx=14, pady=(0, 14))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        def stat_cell(parent, label, var, r, c):
            cell = ctk.CTkFrame(parent, fg_color="#F8FAFC", corner_radius=10,
                                border_color="#E2E8F0", border_width=1)
            px = (0, 6) if c == 0 else (0, 0)
            cell.grid(row=r, column=c, sticky="ew", padx=px, pady=(0, 6))
            ctk.CTkLabel(cell, text=label,
                         font=ctk.CTkFont(family=_UI_FONT, size=10),
                         text_color="#94A3B8", anchor="w").pack(anchor="w", padx=10, pady=(7, 1))
            ctk.CTkLabel(cell, textvariable=var,
                         font=ctk.CTkFont(family=_UI_FONT, size=12, weight="bold"),
                         text_color="#0F172A", anchor="w",
                         wraplength=190).pack(anchor="w", padx=10, pady=(0, 7))

        stat_cell(grid, "Role",         self._role_var,  0, 0)
        stat_cell(grid, "Project",       self._proj_var,  0, 1)
        stat_cell(grid, "Designation",   self._desig_var, 1, 0)
        stat_cell(grid, "Total Tracked", self._hours_var, 1, 1)
        stat_cell(grid, "Today Active",  self._today_var, 2, 0)

        threading.Thread(target=self._load_profile_stats, daemon=True).start()

        # ── Open Website button ──────────────────────────
        ctk.CTkButton(
            inner, text="🌐  Open Website", height=40,
            fg_color="#EEF2FF", border_width=1, border_color="#C7D2FE",
            text_color="#4F63D2", hover_color="#E0E7FF",
            font=ctk.CTkFont(family=_UI_FONT, size=13),
            command=self._open_website,
        ).pack(fill="x", pady=(4, 2))

        # ── Logout button ────────────────────────────────
        ctk.CTkButton(
            inner, text="🚪  Logout & Stop Capture", height=44,
            fg_color="#FEF2F2", border_width=1, border_color="#FECACA",
            text_color="#EF4444", hover_color="#FEE2E2",
            font=ctk.CTkFont(family=_UI_FONT, size=13, weight="bold"),
            command=self._logout,
        ).pack(fill="x", pady=(2, 8))

    def _card(self, parent, padx=0, children_fn=None):
        """Helper to create a consistent card frame"""
        card = ctk.CTkFrame(
            parent,
            fg_color="#FFFFFF",
            corner_radius=14,
            border_color="#E2E8F0",
            border_width=1,
        )
        card.pack(fill="x", pady=(0, 12), padx=padx)
        if children_fn:
            children_fn(card)
        return card

    # ── Task list helpers ─────────────────────────────────

    def _toggle_add_form(self):
        if self._add_form_visible:
            self._add_form_frame.pack_forget()
            self._add_form_visible = False
        else:
            self._add_form_frame.pack(fill="x", padx=12, pady=(0, 6),
                                      before=self._tasks_container)
            self._add_form_visible = True
            self._add_var.set("")
            self._add_entry.focus()

    def _do_add_task(self):
        title = self._add_var.get().strip()
        if not title:
            return
        self._add_submit_btn.configure(text="Adding…", state="disabled")
        self._add_var.set("")
        threading.Thread(target=self._create_task_bg, args=(title,), daemon=True).start()

    def _create_task_bg(self, title: str):
        from datetime import date as date_cls
        try:
            res = requests.post(
                f"{API_URL}/api/tasks/quick",
                json={"user_id": self.user_id, "title": title},
                timeout=10,
            )
        except Exception:
            res = None
        self.after(0, lambda: self._add_submit_btn.configure(text="Add", state="normal"))
        self.after(0, self._load_all_tasks)

    def _load_all_tasks(self):
        from datetime import date as date_cls
        try:
            today = date_cls.today().isoformat()
            res = requests.get(
                f"{API_URL}/api/tasks/{self.user_id}",
                params={"date": today},
                timeout=8,
            )
            if res.status_code == 200:
                tasks = res.json().get("tasks", [])
                self.after(0, lambda t=tasks: self._render_task_list(t))
                return
            if res.status_code == 404:
                self.after(0, lambda: self._render_task_list([]))
                return
            self.after(0, lambda c=res.status_code: self._show_tasks_error(c))
        except requests.exceptions.ConnectionError:
            self.after(0, lambda: self._show_tasks_error(None, "Cannot reach server"))
        except Exception:
            self.after(0, self._show_tasks_error)

    def _handle_invalid_session(self):
        _clear_session()
        messagebox.showerror(
            "Account Not Found",
            f"Your account was not found on the server.\n\n"
            f"Please register or sign in with credentials\n"
            f"that match this server:\n{API_URL}",
        )
        self.is_capturing = False
        try:
            self._tracker.stop()
            self._app_tracker.stop()
        except Exception:
            pass
        self.destroy()
        try:
            self._login_win.error_var.set("⚠  Account not found. Please register or sign in.")
            self._login_win.email_var.set("")
            self._login_win.password_var.set("")
            self._login_win.login_btn.configure(text="Sign In  →", state="normal")
            self._login_win.deiconify()
        except Exception:
            pass

    def _show_tasks_error(self, status_code=None, detail=None):
        for w in self._tasks_container.winfo_children():
            w.destroy()
        msg = detail or (f"Server error {status_code}" if status_code else "Could not load tasks")
        ctk.CTkLabel(self._tasks_container, text=f"⚠  {msg}",
                     font=ctk.CTkFont(family=_UI_FONT, size=12),
                     text_color="#EF4444").pack(pady=(12, 4))
        ctk.CTkButton(
            self._tasks_container, text="Retry", height=28, width=70,
            font=ctk.CTkFont(family=_UI_FONT, size=11, weight="bold"),
            fg_color="#EEF2FF", hover_color="#DBEAFE", text_color="#4F63D2",
            corner_radius=8,
            command=lambda: threading.Thread(target=self._load_all_tasks, daemon=True).start(),
        ).pack(pady=(0, 12))

    def _render_task_list(self, tasks: list):
        for w in self._tasks_container.winfo_children():
            w.destroy()

        total     = len(tasks)
        completed = sum(1 for t in tasks if t["status"] == "completed")
        self._kpi_tasks_var.set(str(total))
        self._kpi_done_var.set(str(completed))
        self._task_count_badge.configure(text=f"  {total}  ")

        if not tasks:
            ctk.CTkLabel(self._tasks_container,
                         text="No tasks yet — tap + Add to create one",
                         font=ctk.CTkFont(family=_UI_FONT, size=12),
                         text_color="#94A3B8").pack(pady=16)
            return

        PRI_COLOR = {"high": "#DC2626", "medium": "#D97706", "low": "#16A34A"}
        STA_COLOR = {
            "pending":     ("#FEF3C7", "#D97706", "Pending"),
            "in_progress": ("#EEF2FF", "#4F63D2", "In Progress"),
            "completed":   ("#F0FDF4", "#16A34A", "Done"),
        }

        for t in tasks:
            tid      = t["id"]
            title    = t["title"]
            status   = t["status"]
            pri      = t.get("priority", "medium")
            pc       = PRI_COLOR.get(pri, "#94A3B8")
            s_bg, s_fg, s_lbl = STA_COLOR.get(status, ("#F1F5F9", "#64748B", status.capitalize()))
            is_done  = status == "completed"

            row = ctk.CTkFrame(self._tasks_container, fg_color="#FFFFFF",
                               corner_radius=10, border_color="#E2E8F0", border_width=1)
            row.pack(fill="x", pady=(0, 6))

            stripe = ctk.CTkFrame(row, fg_color=pc, corner_radius=0, width=4)
            stripe.pack(side="left", fill="y")
            stripe.pack_propagate(False)

            body = ctk.CTkFrame(row, fg_color="transparent")
            body.pack(side="left", fill="both", expand=True, padx=(10, 8), pady=8)

            title_row = ctk.CTkFrame(body, fg_color="transparent")
            title_row.pack(fill="x")
            ctk.CTkLabel(title_row, text=title, anchor="w",
                         font=ctk.CTkFont(family=_UI_FONT, size=12, weight="bold"),
                         text_color="#94A3B8" if is_done else "#0F172A",
                         wraplength=320).pack(side="left")
            ctk.CTkLabel(title_row, text=f" {pri.capitalize()} ",
                         font=ctk.CTkFont(family=_UI_FONT, size=9, weight="bold"),
                         fg_color=pc + "25", text_color=pc,
                         corner_radius=6).pack(side="right", padx=(4, 0))

            sts_row = ctk.CTkFrame(body, fg_color="transparent")
            sts_row.pack(fill="x", pady=(4, 0))
            ctk.CTkLabel(sts_row, text=f"  {s_lbl}  ",
                         font=ctk.CTkFont(family=_UI_FONT, size=9, weight="bold"),
                         fg_color=s_bg, text_color=s_fg,
                         corner_radius=6).pack(side="left")

            if not is_done:
                def _mk(lbl, ns, i=tid):
                    return ctk.CTkButton(
                        sts_row, text=lbl, height=22, width=80,
                        font=ctk.CTkFont(family=_UI_FONT, size=9, weight="bold"),
                        fg_color="#F1F5F9", hover_color="#E2E8F0",
                        text_color="#475569", corner_radius=6,
                        command=lambda s=ns, x=i: self._on_task_status_change(x, s),
                    )
                if status != "in_progress":
                    _mk("In Progress", "in_progress").pack(side="right", padx=(4, 0))
                _mk("Done ✓", "completed").pack(side="right", padx=(4, 0))

    def _on_task_status_change(self, task_id: int, new_status: str):
        threading.Thread(
            target=self._do_change_task_status,
            args=(task_id, new_status),
            daemon=True,
        ).start()

    def _do_change_task_status(self, task_id: int, new_status: str):
        try:
            res = requests.patch(
                f"{API_URL}/api/tasks/{task_id}/status",
                json={"user_id": self.user_id, "status": new_status},
                timeout=8,
            )
            if res.status_code == 200 and task_id == self._task_id:
                self._task_status = new_status
        except Exception:
            pass
        self.after(0, self._load_all_tasks)

    def _load_profile_stats(self):
        # ── Profile data (same API as website) ───────────
        try:
            prof = requests.get(f"{API_URL}/api/users/{self.user_id}/profile", timeout=8)
            if prof.status_code == 200:
                d = prof.json()
                self.after(0, lambda: self._proj_var.set(d.get("project") or "—"))
                self.after(0, lambda: self._desig_var.set(d.get("designation") or "—"))
                role = d.get("user_type", "user").replace("user", "Employee").replace("admin", "Admin")
                self.after(0, lambda: self._role_var.set(role))
        except Exception:
            pass

        # ── Activity stats ───────────────────────────────
        try:
            res = requests.get(f"{API_URL}/api/users/{self.user_id}/stats", timeout=8)
            if res.status_code == 200:
                data      = res.json()
                hours     = data.get("total_tracked_hours", 0)
                today_min = data.get("today_active_min", 0)
                today_pct = data.get("today_activity_pct", 0)
                self.after(0, lambda: self._hours_var.set(f"{hours} hrs"))
                self.after(0, lambda: self._today_var.set(f"{today_min} min ({today_pct}% active)"))
                self.after(0, lambda: self._kpi_active_var.set(f"{today_min}m"))
                return
        except Exception:
            pass
        self.after(0, lambda: self._hours_var.set("—"))
        self.after(0, lambda: self._today_var.set("—"))

    # ── Logging ──────────────────────────────────────────
    def _log(self, message: str):
        """Silent — internal logs are not shown to the user"""
        pass

    # ── Progress bar animation ────────────────────────────
    def _animate_progress(self):
        pass

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

    def _update_stats(self, _time_str: str, _size_kb: int):
        try:
            n = self.screenshot_count
            self._screenshots_var.set(
                f"{n} screenshot{'s' if n != 1 else ''} uploaded"
            )
        except Exception:
            pass

    def _poll_activity_status(self):
        """Periodic poll — kept for future use."""
        if not self.is_capturing:
            return
        self.after(5000, self._poll_activity_status)

    # ── Open website in browser ───────────────────────────
    def _open_website(self):
        import webbrowser
        from config import STAGING_WEBSITE_URL
        webbrowser.open(STAGING_WEBSITE_URL)

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
