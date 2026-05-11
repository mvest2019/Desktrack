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
    user_type: str           # "admin" or "user"
    project: Optional[str]   # "Bold" or "MView"
    designation: Optional[str]
    message: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    user_type: Optional[str] = "user"    # "admin" or "user"
    project: Optional[str] = None        # "Bold" or "MView"
    designation: Optional[str] = None    # e.g. "Frontend Dev", "Marketing"

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


# ── User Profile schemas ─────────────────────────────────────

class UserProfileResponse(BaseModel):
    user_id:     int
    username:    str
    email:       str
    user_type:   str
    project:     Optional[str]
    designation: Optional[str]
    isactive:    bool
    created_at:  str

class UserProfileUpdateRequest(BaseModel):
    username:    Optional[str] = None
    designation: Optional[str] = None
    project:     Optional[str] = None  # "Bold" or "MView"


# ── Admin schemas ────────────────────────────────────────────

class AdminUserItem(BaseModel):
    user_id:     int
    username:    str
    email:       str
    user_type:   str
    project:     Optional[str]
    designation: Optional[str]
    isactive:    bool
    created_at:  str

class AdminUsersResponse(BaseModel):
    count: int
    users: List[AdminUserItem]


# ── Task schemas ─────────────────────────────────────────────

class TaskCreateRequest(BaseModel):
    user_id:                  int
    title:                    str
    description:              Optional[str] = None
    priority:                 Optional[str] = "medium"   # low / medium / high
    expected_completion_time: Optional[str] = None       # free text: "by 3pm", "2h"
    notes:                    Optional[str] = None       # optional first note on creation

class TaskEditRequest(BaseModel):
    user_id:                  int
    title:                    Optional[str] = None
    description:              Optional[str] = None
    priority:                 Optional[str] = None
    expected_completion_time: Optional[str] = None

class TaskStatusUpdateRequest(BaseModel):
    user_id: int
    status:  str   # pending / in_progress / completed

class TaskNoteCreateRequest(BaseModel):
    user_id: int
    note:    str

class TaskNoteItem(BaseModel):
    id:         int
    note:       str
    created_at: str

class TaskItem(BaseModel):
    id:                       int
    user_id:                  int
    title:                    str
    description:              Optional[str]
    priority:                 str
    status:                   str
    expected_completion_time: Optional[str]
    task_date:                str
    completed_at:             Optional[str]
    created_at:               str
    updated_at:               str
    notes:                    List[TaskNoteItem]

class TaskSummary(BaseModel):
    total:          int
    pending:        int
    in_progress:    int
    completed:      int
    completion_pct: float

class TaskListResponse(BaseModel):
    success:  bool
    user_id:  int
    date:     str
    count:    int
    tasks:    List[TaskItem]

class TaskSummaryResponse(BaseModel):
    success:        bool
    user_id:        int
    date:           str
    total:          int
    pending:        int
    in_progress:    int
    completed:      int
    completion_pct: float

class AdminTaskItem(BaseModel):
    task_id:                  int
    user_id:                  int
    username:                 str
    project:                  Optional[str]
    title:                    str
    priority:                 str
    status:                   str
    expected_completion_time: Optional[str]
    task_date:                str
    completed_at:             Optional[str]
    created_at:               str
    note_count:               int

class AdminTaskListResponse(BaseModel):
    success: bool
    date:    str
    count:   int
    tasks:   List[AdminTaskItem]

class AdminTaskUserStat(BaseModel):
    user_id:        int
    username:       str
    project:        Optional[str]
    total:          int
    completed:      int
    in_progress:    int
    pending:        int
    completion_pct: float

class AdminTaskStatsResponse(BaseModel):
    success:        bool
    date:           str
    total_tasks:    int
    completed:      int
    in_progress:    int
    pending:        int
    completion_pct: float
    by_employee:    List[AdminTaskUserStat]
