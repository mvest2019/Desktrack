# schemas.py — screenshot_id is now the filename string (e.g. screenshot_1_20260507_174421.png)
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    user_id: int
    username: str
    email: str
    user_type: str  # "admin" or "user"
    message: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    user_type: Optional[str] = "user"  # "admin" or "user"

class RegisterResponse(BaseModel):
    success: bool
    user_id: int
    message: str

class ScreenshotUploadRequest(BaseModel):
    user_id: int        # links to PostgreSQL users.id
    filename: str
    image_data: str     # base64 PNG

class ScreenshotUploadResponse(BaseModel):
    success: bool
    screenshot_id: str  # MongoDB ObjectId as string
    message: str

# ── Activity tracking ────────────────────────────────────────

class ActivityLogRequest(BaseModel):
    """Sent by desktop app at the end of each 10-minute window."""
    user_id:          int
    window_start:     str   # ISO datetime string
    window_end:       str   # ISO datetime string
    active_seconds:   int
    idle_seconds:     int
    activity_percent: float
    mouse_events:     int
    keyboard_events:  int

class ActivityLogResponse(BaseModel):
    success: bool
    log_id:  int
    message: str

class ActivitySummaryItem(BaseModel):
    window_start:     str
    window_end:       str
    active_seconds:   int
    idle_seconds:     int
    activity_percent: float
    mouse_events:     int
    keyboard_events:  int

class ActivitySummaryResponse(BaseModel):
    user_id:          int
    today_active_sec: int
    today_idle_sec:   int
    today_percent:    float
    logs:             List[ActivitySummaryItem]


# ── App / window tracking ────────────────────────────────────

class AppLogItem(BaseModel):
    """One app window session sent from the desktop app."""
    user_id:      int
    app_name:     str
    window_title: str
    url:          str
    start_time:   str   # ISO datetime
    end_time:     str   # ISO datetime
    duration_sec: int

class AppLogBatchRequest(BaseModel):
    """Desktop sends a batch of sessions every 60 seconds."""
    logs: List[AppLogItem]

class AppLogBatchResponse(BaseModel):
    success:  bool
    saved:    int
    message:  str

class AppLogRecord(BaseModel):
    """One row returned to the frontend."""
    id:           int
    app_name:     str
    window_title: str
    url:          str
    start_time:   str
    end_time:     str
    duration_sec: int

class AppLogsResponse(BaseModel):
    user_id: int
    count:   int
    logs:    List[AppLogRecord]

class AppSummaryEntry(BaseModel):
    app_name:     str
    total_sec:    int
    session_count: int

class AppSummaryResponse(BaseModel):
    user_id: int
    entries: List[AppSummaryEntry]


# ── Admin schemas ────────────────────────────────────────────

class AdminUserItem(BaseModel):
    user_id:    int
    username:   str
    email:      str
    user_type:  str
    isactive:   bool
    created_at: str

class AdminUsersResponse(BaseModel):
    count: int
    users: List[AdminUserItem]
