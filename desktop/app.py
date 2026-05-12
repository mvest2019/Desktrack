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

        ctk.CTkLabel(reg_scroll, text="Account Type", anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#475569").pack(fill="x", pady=(12, 0))
        self.reg_user_type_var = tk.StringVar(value="Employee (User)")
        self._make_dropdown_row(reg_scroll, "🛡", self.reg_user_type_var,
                                ["Employee (User)", "Admin"])

        ctk.CTkLabel(reg_scroll, text="Project", anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#475569").pack(fill="x", pady=(12, 0))
        self.reg_project_var = tk.StringVar(value="Select project...")
        self._make_dropdown_row(reg_scroll, "🌐", self.reg_project_var,
                                ["Select project...", "Bold", "MView"])

        ctk.CTkLabel(reg_scroll, text="Designation", anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#475569").pack(fill="x", pady=(12, 0))
        self.reg_designation_var = tk.StringVar()
        self._make_field_row(reg_scroll, "💼", self.reg_designation_var,
                             "e.g. Frontend Dev, Marketing")

        ctk.CTkLabel(reg_scroll, text="Skills", anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#475569").pack(fill="x", pady=(12, 0))
        self.reg_skills_var = tk.StringVar()
        self._make_field_row(reg_scroll, "⚡", self.reg_skills_var,
                             "e.g. Python, React, UI/UX")

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
        self.reg_user_type_var.set("Employee (User)")
        self.reg_project_var.set("Select project...")
        self.reg_designation_var.set("")
        self.reg_skills_var.set("")
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
        name        = self.reg_name_var.get().strip()
        email       = self.reg_email_var.get().strip()
        password    = self.reg_pass_var.get().strip()
        user_type   = "admin" if self.reg_user_type_var.get() == "Admin" else "user"
        project_sel = self.reg_project_var.get()
        project     = project_sel if project_sel in ("Bold", "MView") else None
        designation = self.reg_designation_var.get().strip()
        skills      = self.reg_skills_var.get().strip()

        if not name or not email or not password:
            self.reg_error_var.set("⚠  Please fill in Name, Email and Password.")
            return
        if not project:
            self.reg_error_var.set("⚠  Please select a project.")
            return
        if len(password) < 6:
            self.reg_error_var.set("⚠  Password must be at least 6 characters.")
            return
        self.reg_btn.configure(text="Creating...", state="disabled")
        self.reg_error_var.set("")
        threading.Thread(target=self._do_register,
                         args=(name, email, password, user_type, project, designation, skills),
                         daemon=True).start()

    def _do_register(self, name, email, password, user_type, project, designation, skills):
        try:
            res = requests.post(f"{API_URL}/api/register",
                                json={"username": name, "email": email, "password": password,
                                      "user_type": user_type, "project": project,
                                      "designation": designation, "skills": skills},
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
            ctk.CTkLabel(icon_box, text="R", font=ctk.CTkFont(family="Lexend Deca", size=44, weight="bold"),
                         text_color="#4F63D2").place(relx=0.5, rely=0.5, anchor="center")

        # Greeting
        name = self.user_data.get("username", "there")
        ctk.CTkLabel(inner, text="Welcome back,",
                     font=ctk.CTkFont(family="Lexend Deca", size=14),
                     text_color="#64748B").pack(pady=(20, 0))
        ctk.CTkLabel(inner, text=name,
                     font=ctk.CTkFont(family="Lexend Deca", size=30, weight="bold"),
                     text_color="#0F172A").pack(pady=(2, 0))
        ctk.CTkLabel(inner, text="Let's continue your productive journey.",
                     font=ctk.CTkFont(family="Lexend Deca", size=12),
                     text_color="#94A3B8").pack(pady=(4, 20))

        # Start Monitoring button
        ctk.CTkButton(
            inner, text="▶   Start Monitoring", height=54,
            font=ctk.CTkFont(family="Lexend Deca", size=15, weight="bold"),
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
                     font=ctk.CTkFont(family="Lexend Deca", size=12, weight="bold"),
                     text_color="#0F172A").pack(anchor="w")
        ctk.CTkLabel(txt_col, text="Realisieren Pulse runs in the background\nand keeps your data safe.",
                     anchor="w", font=ctk.CTkFont(family="Lexend Deca", size=11),
                     text_color="#94A3B8", justify="left").pack(anchor="w", pady=(2, 0))

        # Sign out footer
        foot = ctk.CTkFrame(inner, fg_color="transparent")
        foot.pack(pady=(4, 0))
        ctk.CTkLabel(foot, text="Not you?  ",
                     font=ctk.CTkFont(family="Lexend Deca", size=13),
                     text_color="#64748B").pack(side="left")
        ctk.CTkButton(foot, text="Sign out",
                      font=ctk.CTkFont(family="Lexend Deca", size=13, weight="bold"),
                      text_color="#4F63D2", fg_color="transparent",
                      hover_color="#EEF2FF", border_width=0, height=24, width=70,
                      command=self._sign_out).pack(side="left")

        ctk.CTkFrame(inner, fg_color="transparent", height=8).pack()

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
        self.geometry("540x420")
        self.resizable(False, False)
        self._center_window(540, 420)
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
        header = ctk.CTkFrame(self, height=70, corner_radius=0, fg_color="#FFFFFF",
                              border_color="#E2E8F0", border_width=1)
        header.pack(fill="x")
        header.pack_propagate(False)

        try:
            _hdr_img = ctk.CTkImage(Image.open(_ICON_PNG), size=(36, 36))
            ctk.CTkLabel(header, image=_hdr_img, text="  Realisieren Pulse",
                         compound="left", text_color="#0F172A",
                         font=ctk.CTkFont(family="Lexend Deca", size=17, weight="bold")).pack(side="left", padx=20, pady=17)
        except Exception:
            ctk.CTkLabel(header, text="R  Realisieren Pulse",
                         font=ctk.CTkFont(family="Lexend Deca", size=17, weight="bold"),
                         text_color="#0F172A").pack(side="left", padx=20, pady=17)

        # MONITORING pill
        live_frame = ctk.CTkFrame(header, fg_color="#F0FDF4", corner_radius=20)
        live_frame.pack(side="right", padx=20, pady=20)
        ctk.CTkLabel(live_frame, text="●", text_color="#22C55E",
                     font=ctk.CTkFont(size=11), padx=4).pack(side="left", padx=(10, 2))
        ctk.CTkLabel(live_frame, text="MONITORING",
                     font=ctk.CTkFont(family="Lexend Deca", size=10, weight="bold"),
                     text_color="#16A34A").pack(side="left", padx=(0, 10))

        # ── Welcome banner (auto-hides after 4 s) ────────
        self._welcome_bar = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color="#EEF2FF")
        self._welcome_bar.pack(fill="x")
        self._welcome_bar.pack_propagate(False)
        ctk.CTkLabel(
            self._welcome_bar,
            text=f"👋  Welcome back, {self.username}!   Realisieren Pulse is monitoring your activity.",
            font=ctk.CTkFont(family="Lexend Deca", size=12), text_color="#4F63D2",
        ).pack(expand=True)
        self.after(4000, lambda: self._welcome_bar.pack_forget())

        # ── Content area ─────────────────────────────────
        content = ctk.CTkFrame(self, fg_color="#F5F7FA")
        content.pack(fill="both", expand=True, padx=0, pady=0)

        inner = ctk.CTkFrame(content, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=16)

        # ── User card with avatar ─────────────────────────
        user_card = self._card(inner)
        user_row = ctk.CTkFrame(user_card, fg_color="transparent")
        user_row.pack(fill="x", padx=16, pady=14)

        initials = "".join(w[0].upper() for w in self.username.split()[:2]) or "U"
        avatar = ctk.CTkFrame(user_row, fg_color="#EEF2FF", corner_radius=22,
                              width=44, height=44)
        avatar.pack(side="left", padx=(0, 12))
        avatar.pack_propagate(False)
        ctk.CTkLabel(avatar, text=initials,
                     font=ctk.CTkFont(family="Lexend Deca", size=16, weight="bold"),
                     text_color="#4F63D2").place(relx=0.5, rely=0.5, anchor="center")

        info_col = ctk.CTkFrame(user_row, fg_color="transparent")
        info_col.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(info_col, text=self.username, anchor="w",
                     font=ctk.CTkFont(family="Lexend Deca", size=15, weight="bold"),
                     text_color="#0F172A").pack(anchor="w")
        ctk.CTkLabel(info_col, text=self.user_data["email"], anchor="w",
                     font=ctk.CTkFont(family="Lexend Deca", size=11),
                     text_color="#64748B").pack(anchor="w", pady=(2, 0))

        # ── Status card ──────────────────────────────────
        status_card = self._card(inner)

        status_hdr = ctk.CTkFrame(status_card, fg_color="transparent")
        status_hdr.pack(fill="x", padx=16, pady=(14, 8))

        trk_ic = ctk.CTkFrame(status_hdr, fg_color="#EEF2FF", corner_radius=10,
                              width=36, height=36)
        trk_ic.pack(side="left", padx=(0, 10))
        trk_ic.pack_propagate(False)
        ctk.CTkLabel(trk_ic, text="📊", font=ctk.CTkFont(size=16)).place(
            relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(status_hdr, text="Tracking Status",
                     font=ctk.CTkFont(family="Lexend Deca", size=13, weight="bold"),
                     text_color="#0F172A").pack(side="left")

        status_row = ctk.CTkFrame(status_card, fg_color="transparent")
        status_row.pack(fill="x", padx=16, pady=(0, 14))

        self.status_dot = ctk.CTkLabel(status_row, text="●", text_color="#22C55E",
                                       font=ctk.CTkFont(size=18))
        self.status_dot.pack(side="left")

        self.status_text = ctk.CTkLabel(
            status_row,
            text="  Tracking started",
            font=ctk.CTkFont(family="Lexend Deca", size=12), text_color="#64748B",
        )
        self.status_text.pack(side="left")



        # ── Logout button ────────────────────────────────
        ctk.CTkButton(
            inner,
            text="🚪  Logout & Stop Capture",
            height=46,
            fg_color="#FEF2F2",
            border_width=1,
            border_color="#FECACA",
            text_color="#EF4444",
            hover_color="#FEE2E2",
            font=ctk.CTkFont(family="Lexend Deca", size=13, weight="bold"),
            command=self._logout,
        ).pack(fill="x", pady=(4, 8))

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
        pass

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
