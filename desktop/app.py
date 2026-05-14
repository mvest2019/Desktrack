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
                     font=ctk.CTkFont(family="Lexend Deca", size=18, weight="bold"),
                     text_color="#0F172A").pack(pady=(16, 4))
        ctk.CTkLabel(outer, text="Enter your main focus for today to start monitoring.",
                     font=ctk.CTkFont(family="Lexend Deca", size=11),
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
            font=ctk.CTkFont(family="Lexend Deca", size=13),
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
            font=ctk.CTkFont(family="Lexend Deca", size=14, weight="bold"),
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
                self._task_id = data["task_id"]
                self._task_title = data["title"]
                self._task_status = data["status"]
                self.after(0, self._skip_to_dashboard)
            else:
                self.after(0, lambda: self._show_error("Could not save task. Proceeding anyway."))
                self.after(500, lambda: self._open_dashboard_no_task(title))
        except Exception:
            self.after(0, lambda: self._show_error("No server connection. Proceeding offline."))
            self.after(800, lambda: self._open_dashboard_no_task(title))

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
        """Build the dashboard layout"""

        # ── Top header bar ───────────────────────────────
        header = ctk.CTkFrame(self, height=62, corner_radius=0, fg_color="#FFFFFF",
                              border_color="#E2E8F0", border_width=1)
        header.pack(fill="x")
        header.pack_propagate(False)

        try:
            _hdr_img = ctk.CTkImage(Image.open(_ICON_PNG), size=(32, 32))
            ctk.CTkLabel(header, image=_hdr_img, text="  Realisieren Pulse",
                         compound="left", text_color="#0F172A",
                         font=ctk.CTkFont(family="Lexend Deca", size=16, weight="bold")).pack(side="left", padx=18, pady=15)
        except Exception:
            ctk.CTkLabel(header, text="R  Realisieren Pulse",
                         font=ctk.CTkFont(family="Lexend Deca", size=16, weight="bold"),
                         text_color="#0F172A").pack(side="left", padx=18, pady=15)

        live_frame = ctk.CTkFrame(header, fg_color="#F0FDF4", corner_radius=20)
        live_frame.pack(side="right", padx=16, pady=16)
        ctk.CTkLabel(live_frame, text="●", text_color="#22C55E",
                     font=ctk.CTkFont(size=10)).pack(side="left", padx=(10, 2))
        ctk.CTkLabel(live_frame, text="MONITORING",
                     font=ctk.CTkFont(family="Lexend Deca", size=9, weight="bold"),
                     text_color="#16A34A").pack(side="left", padx=(0, 10))

        # ── Scrollable content ────────────────────────────
        scroll = ctk.CTkScrollableFrame(self, fg_color="#F5F7FA",
                                        scrollbar_button_color="#CBD5E1",
                                        scrollbar_button_hover_color="#94A3B8")
        scroll.pack(fill="both", expand=True)
        inner = ctk.CTkFrame(scroll, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=18, pady=14)

        # ─ Section helper ─────────────────────────────────
        def section_label(parent, icon, text):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", pady=(0, 6))
            ic = ctk.CTkFrame(row, fg_color="#EEF2FF", corner_radius=8, width=30, height=30)
            ic.pack(side="left", padx=(0, 8))
            ic.pack_propagate(False)
            ctk.CTkLabel(ic, text=icon, font=ctk.CTkFont(size=14)).place(relx=0.5, rely=0.5, anchor="center")
            ctk.CTkLabel(row, text=text, font=ctk.CTkFont(family="Lexend Deca", size=13, weight="bold"),
                         text_color="#0F172A").pack(side="left")

        # ══ TODAY'S TASK CARD ════════════════════════════
        task_card = self._card(inner)
        task_hdr = ctk.CTkFrame(task_card, fg_color="transparent")
        task_hdr.pack(fill="x", padx=16, pady=(14, 10))
        section_label(task_hdr, "✅", "Today's Task")

        # Task title display
        title_text = self._task_title if self._task_title else "No task set"
        self._task_title_lbl = ctk.CTkLabel(
            task_card,
            text=title_text,
            font=ctk.CTkFont(family="Lexend Deca", size=14, weight="bold"),
            text_color="#0F172A", anchor="w", wraplength=460,
        )
        self._task_title_lbl.pack(fill="x", padx=16, pady=(0, 10))

        # Status badge
        STATUS_COLORS = {
            "pending":     ("#FEF3C7", "#D97706", "Pending"),
            "in_progress": ("#EEF2FF", "#4F63D2", "In Progress"),
            "completed":   ("#F0FDF4", "#16A34A", "Completed"),
        }
        self._status_badge_frame = ctk.CTkFrame(task_card, fg_color="transparent")
        self._status_badge_frame.pack(fill="x", padx=16, pady=(0, 10))
        self._status_badge = ctk.CTkLabel(self._status_badge_frame, text="",
                                          font=ctk.CTkFont(family="Lexend Deca", size=11, weight="bold"),
                                          corner_radius=8, padx=10, pady=4)
        self._status_badge.pack(side="left")
        self._refresh_status_badge(STATUS_COLORS)

        # Status update buttons
        btn_row = ctk.CTkFrame(task_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 14))

        def make_status_btn(label, status, color, hover):
            return ctk.CTkButton(
                btn_row, text=label, height=34,
                font=ctk.CTkFont(family="Lexend Deca", size=11, weight="bold"),
                fg_color=color, hover_color=hover, text_color="#FFFFFF",
                corner_radius=8, width=110,
                command=lambda s=status: self._update_task_status(s, STATUS_COLORS),
            )

        make_status_btn("Pending", "pending", "#F59E0B", "#D97706").pack(side="left", padx=(0, 6))
        make_status_btn("In Progress", "in_progress", "#4F63D2", "#4050C0").pack(side="left", padx=(0, 6))
        make_status_btn("Completed", "completed", "#22C55E", "#16A34A").pack(side="left")

        self._task_msg_var = tk.StringVar(value="")
        ctk.CTkLabel(task_card, textvariable=self._task_msg_var,
                     font=ctk.CTkFont(family="Lexend Deca", size=11),
                     text_color="#64748B").pack(padx=16, pady=(0, 8))

        # ══ TRACKING STATUS CARD ═════════════════════════
        status_card = self._card(inner)
        status_hdr = ctk.CTkFrame(status_card, fg_color="transparent")
        status_hdr.pack(fill="x", padx=16, pady=(14, 8))
        section_label(status_hdr, "📊", "Tracking Status")

        status_row = ctk.CTkFrame(status_card, fg_color="transparent")
        status_row.pack(fill="x", padx=16, pady=(0, 14))
        self.status_dot = ctk.CTkLabel(status_row, text="●", text_color="#22C55E",
                                       font=ctk.CTkFont(size=18))
        self.status_dot.pack(side="left")
        self.status_text = ctk.CTkLabel(
            status_row, text="  Tracking started",
            font=ctk.CTkFont(family="Lexend Deca", size=12), text_color="#64748B",
        )
        self.status_text.pack(side="left")

        # ══ PROFILE CARD ═════════════════════════════════
        prof_card = self._card(inner)
        prof_hdr = ctk.CTkFrame(prof_card, fg_color="transparent")
        prof_hdr.pack(fill="x", padx=16, pady=(14, 10))
        section_label(prof_hdr, "👤", "My Profile")

        prof_body = ctk.CTkFrame(prof_card, fg_color="transparent")
        prof_body.pack(fill="x", padx=16, pady=(0, 14))

        # Avatar + name row
        av_row = ctk.CTkFrame(prof_body, fg_color="transparent")
        av_row.pack(fill="x", pady=(0, 10))
        initials = "".join(w[0].upper() for w in self.username.split()[:2]) or "U"
        avatar = ctk.CTkFrame(av_row, fg_color="#EEF2FF", corner_radius=20,
                              width=40, height=40)
        avatar.pack(side="left", padx=(0, 10))
        avatar.pack_propagate(False)
        ctk.CTkLabel(avatar, text=initials,
                     font=ctk.CTkFont(family="Lexend Deca", size=14, weight="bold"),
                     text_color="#4F63D2").place(relx=0.5, rely=0.5, anchor="center")
        name_col = ctk.CTkFrame(av_row, fg_color="transparent")
        name_col.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(name_col, text=self.username, anchor="w",
                     font=ctk.CTkFont(family="Lexend Deca", size=13, weight="bold"),
                     text_color="#0F172A").pack(anchor="w")
        ctk.CTkLabel(name_col, text=self.user_data.get("email", ""),
                     anchor="w", font=ctk.CTkFont(family="Lexend Deca", size=11),
                     text_color="#64748B").pack(anchor="w")

        # Info grid
        def info_row(parent, label, value_var):
            row = ctk.CTkFrame(parent, fg_color="#F8FAFC", corner_radius=8,
                               border_color="#E2E8F0", border_width=1)
            row.pack(fill="x", pady=(0, 4))
            ctk.CTkLabel(row, text=label, width=130, anchor="w",
                         font=ctk.CTkFont(family="Lexend Deca", size=11),
                         text_color="#64748B").pack(side="left", padx=(12, 0), pady=8)
            ctk.CTkLabel(row, textvariable=value_var, anchor="w",
                         font=ctk.CTkFont(family="Lexend Deca", size=11, weight="bold"),
                         text_color="#0F172A").pack(side="left", padx=(4, 12), pady=8)

        role_label = self.user_data.get("user_type", "user").replace("user", "Employee").replace("admin", "Admin")
        self._role_var   = tk.StringVar(value=role_label)
        self._proj_var   = tk.StringVar(value=self.user_data.get("project") or "—")
        self._desig_var  = tk.StringVar(value=self.user_data.get("designation") or "—")
        self._hours_var  = tk.StringVar(value="Loading…")
        self._today_var  = tk.StringVar(value="Loading…")

        info_row(prof_body, "Role", self._role_var)
        info_row(prof_body, "Project", self._proj_var)
        info_row(prof_body, "Designation", self._desig_var)
        info_row(prof_body, "Total Tracked", self._hours_var)
        info_row(prof_body, "Today Active", self._today_var)

        # Load live stats in background
        threading.Thread(target=self._load_profile_stats, daemon=True).start()

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

    def _refresh_status_badge(self, STATUS_COLORS):
        s = self._task_status
        bg, fg, label = STATUS_COLORS.get(s, ("#F1F5F9", "#64748B", s.capitalize()))
        self._status_badge.configure(text=f"  {label}  ", fg_color=bg, text_color=fg)

    def _update_task_status(self, new_status: str, STATUS_COLORS: dict):
        if not self._task_id:
            self._task_msg_var.set("⚠  No task linked to this session.")
            return
        if self._task_status == new_status:
            return
        self._task_msg_var.set("Updating…")
        threading.Thread(
            target=self._do_update_status,
            args=(new_status, STATUS_COLORS),
            daemon=True,
        ).start()

    def _do_update_status(self, new_status: str, STATUS_COLORS: dict):
        try:
            res = requests.patch(
                f"{API_URL}/api/tasks/{self._task_id}/status",
                json={"user_id": self.user_id, "status": new_status},
                timeout=8,
            )
            if res.status_code == 200:
                self._task_status = new_status
                self.after(0, lambda: self._refresh_status_badge(STATUS_COLORS))
                self.after(0, lambda: self._task_msg_var.set("✓  Status updated"))
                self.after(2500, lambda: self._task_msg_var.set(""))
            else:
                self.after(0, lambda: self._task_msg_var.set("⚠  Update failed. Try again."))
        except Exception:
            self.after(0, lambda: self._task_msg_var.set("⚠  No connection."))

    def _load_profile_stats(self):
        try:
            res = requests.get(f"{API_URL}/api/users/{self.user_id}/stats", timeout=8)
            if res.status_code == 200:
                data = res.json()
                hours = data.get("total_tracked_hours", 0)
                today_min = data.get("today_active_min", 0)
                today_pct = data.get("today_activity_pct", 0)
                self.after(0, lambda: self._hours_var.set(f"{hours} hrs total"))
                self.after(0, lambda: self._today_var.set(f"{today_min} min  ({today_pct}% active)"))
        except Exception:
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
