# ============================================================
# main.py — FastAPI Backend
# ============================================================
# TWO databases (as per SRS §4.1):
#
#   PostgreSQL  →  users table (authentication, structured data)
#   MongoDB     →  raw_samples collection (screenshots / telemetry)
#
# Run with:  uvicorn main:app --reload --port 8000
# API docs:  http://localhost:8000/docs

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import bcrypt
from datetime import datetime
import logging
import os
import base64
import shutil
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("ai_assistant")

# PostgreSQL
from database import get_db, engine
from models import Base, User, ActivityLog, AppLog, Task, TaskNote

# MongoDB
from mongo import get_raw_samples

# Schemas
from schemas import (
    LoginRequest, LoginResponse,
    RegisterRequest, RegisterResponse,
    ScreenshotUploadRequest, ScreenshotUploadResponse,
    ActivityLogRequest, ActivityLogResponse, ActivitySummaryResponse, ActivitySummaryItem,
    AppLogBatchRequest, AppLogBatchResponse, AppLogsResponse, AppLogRecord,
    AppSummaryResponse, AppSummaryEntry,
    AdminUserItem, AdminUsersResponse,
    UserProfileResponse, UserProfileUpdateRequest,
    TaskCreateRequest, TaskEditRequest, TaskStatusUpdateRequest,
    TaskNoteCreateRequest, TaskNoteItem, TaskItem,
    TaskListResponse, TaskSummaryResponse,
    AdminTaskItem, AdminTaskListResponse, AdminTaskStatsResponse, AdminTaskUserStat,
)

# Auto-create PostgreSQL tables on startup
Base.metadata.create_all(bind=engine)

# ── Screenshot storage folder ────────────────────────────────
# Stores screenshots inside the project: backend/screenshots/{user_id}/

SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Syntra API",
    description=(
        "**PostgreSQL** → Users (auth)\n\n"
        "**MongoDB** → Screenshots / raw_samples (telemetry)"
    ),
    version="1.0.0",
)

# ── CORS: read allowed origins from environment variable ────
# In .env.staging set: ALLOWED_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000
# Falls back to localhost + LAN IPs if env var not set.
_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://192.168.1.77:3000,http://0.0.0.0:3000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════
@app.get("/api/health", tags=["General"])
def health_check():
    try:
        col   = get_raw_samples()
        count = col.estimated_document_count()  # number of user documents
        mongo_status = f"connected ({count} user docs)"
    except Exception as e:
        mongo_status = f"error: {e}"

    return {
        "api":      "running",
        "mongodb":  mongo_status,
        "postgres": "connected",
    }


# ══════════════════════════════════════════════════════════
# AUTH — PostgreSQL (users table)
# ══════════════════════════════════════════════════════════

@app.post("/api/register", response_model=RegisterResponse, tags=["Auth — PostgreSQL"])
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Create a new user.
    Stored in PostgreSQL 'users' table.
    Password hashed with bcrypt before saving.
    """
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = bcrypt.hashpw(
        request.password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    user = User(
        username=request.username,
        email=request.email,
        password=hashed,
        user_type=request.user_type if request.user_type in ("admin", "user") else "user",
        project=request.project if request.project in ("Bold", "MView") else None,
        designation=request.designation,
        isactive=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return RegisterResponse(
        success=True,
        user_id=user.id,
        message=f"Account created! Welcome, {user.username}.",
    )


@app.post("/api/login", response_model=LoginResponse, tags=["Auth — PostgreSQL"])
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Validate email + password against PostgreSQL users table.
    """
    log.info("─── LOGIN ATTEMPT ───")
    log.info("  email received : %s", request.email)
    log.info("  password length: %d chars", len(request.password))

    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        log.warning("  STEP 1 FAIL: no user found for email '%s'", request.email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    log.info("  STEP 1 OK : user found — id=%s username=%s", user.id, user.username)
    log.info("  STEP 2    : isactive=%s", user.isactive)

    if not user.isactive:
        log.warning("  STEP 2 FAIL: account is disabled")
        raise HTTPException(status_code=403, detail="Account disabled. Contact admin.")

    log.info("  STEP 2 OK : account is active")
    log.info("  STEP 3    : checking password against stored hash")

    stored = user.password
    # Support both bcrypt-hashed and legacy plain-text passwords
    try:
        if stored.startswith("$2b$") or stored.startswith("$2a$"):
            match = bcrypt.checkpw(request.password.encode("utf-8"), stored.encode("utf-8"))
        else:
            match = (request.password == stored)
    except Exception:
        match = False

    if not match:
        log.warning("  STEP 3 FAIL: password mismatch")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    log.info("  STEP 3 OK : password matches — login successful!")
    return LoginResponse(
        success=True,
        user_id=user.id,
        username=user.username,
        email=user.email,
        user_type=user.user_type,
        project=user.project,
        designation=user.designation,
        message="Login successful",
    )


# ══════════════════════════════════════════════════════════
# SCREENSHOTS — files on disk + metadata in MongoDB
# ══════════════════════════════════════════════════════════

@app.post("/api/screenshots/upload", response_model=ScreenshotUploadResponse, tags=["Screenshots"])
def upload_screenshot(request: ScreenshotUploadRequest, db: Session = Depends(get_db)):
    """
    Receive a screenshot from the desktop app.
    - Saves the PNG file to  backend/screenshots/{user_id}/{filename}
    - Stores metadata (path, size, timestamp) in MongoDB
    - Does NOT store base64 in DB
    """
    log.info("📷 Upload: user_id=%s file=%s data_len=%d",
             request.user_id, request.filename, len(request.image_data))

    # Step 1: Confirm user exists
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Step 2: Decode base64 → raw PNG bytes
    try:
        img_bytes = base64.b64decode(request.image_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {e}")

    # Step 3: Save to disk   backend/screenshots/{user_id}/filename.png
    user_dir = SCREENSHOT_DIR / str(request.user_id)
    user_dir.mkdir(exist_ok=True)
    file_path = user_dir / request.filename
    file_path.write_bytes(img_bytes)
    file_size = len(img_bytes)

    log.info("💾 Saved to disk: %s (%d KB)", file_path, file_size // 1024)

    # Step 4: Push metadata into user's paths array (one doc per user)
    entry = {
        "name":      request.filename,
        "file_path": str(file_path),
        "file_size": file_size,
        "taken_at":  datetime.now(),
    }
    try:
        col = get_raw_samples()
        col.update_one(
            {"user_id": request.user_id},
            {"$push": {"paths": entry}},
            upsert=True,
        )
        log.info("✅ Metadata pushed to MongoDB paths: user=%s file=%s",
                 request.user_id, request.filename)
    except Exception as e:
        log.error("❌ MongoDB metadata push failed: %s", e)
        raise HTTPException(status_code=500, detail=f"MongoDB error: {e}")

    return ScreenshotUploadResponse(
        success=True,
        screenshot_id=request.filename,
        message=f"Saved to disk ({file_size // 1024} KB)",
    )


@app.get("/api/screenshots/{user_id}", tags=["Screenshots"])
def get_screenshots(user_id: int, limit: int = 50):
    """List recent screenshots for a user (metadata only, no image data)."""
    col = get_raw_samples()
    doc = col.find_one({"user_id": user_id})
    if not doc:
        return {"success": True, "user_id": user_id, "count": 0, "screenshots": []}

    paths = doc.get("paths", [])
    # Sort newest first, then apply limit
    paths_sorted = sorted(paths, key=lambda x: x.get("taken_at", datetime.min), reverse=True)[:limit]

    screenshots = [
        {
            "id":           entry["name"],
            "filename":     entry["name"],
            "taken_at":     entry["taken_at"].isoformat(),
            "file_size_kb": entry.get("file_size", 0) // 1024,
        }
        for entry in paths_sorted
    ]
    return {"success": True, "user_id": user_id, "count": len(screenshots), "screenshots": screenshots}


@app.get("/api/screenshots/{user_id}/{screenshot_id}/image", tags=["Screenshots"])
def get_screenshot_image(user_id: int, screenshot_id: str):
    """
    Return the PNG file directly from disk.
    screenshot_id is the filename (e.g. screenshot_1_20260507_174421.png).
    """
    col = get_raw_samples()
    doc = col.find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    entry = next((p for p in doc.get("paths", []) if p.get("name") == screenshot_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    file_path = Path(entry.get("file_path", ""))
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found on disk")

    return FileResponse(
        path=str(file_path),
        media_type="image/png",
        filename=screenshot_id,
    )


@app.get("/api/stats/{user_id}", tags=["Screenshots"])
def get_stats(user_id: int):
    """Total screenshot count + last capture time."""
    col = get_raw_samples()
    doc = col.find_one({"user_id": user_id})
    if not doc:
        return {"total_screenshots": 0, "last_capture": None}

    paths  = doc.get("paths", [])
    total  = len(paths)
    latest = max((p["taken_at"] for p in paths), default=None) if paths else None
    return {
        "total_screenshots": total,
        "last_capture": latest.isoformat() if latest else None,
    }


@app.delete("/api/screenshots/{user_id}/{screenshot_id}", tags=["Screenshots"])
def delete_screenshot(user_id: int, screenshot_id: str):
    """Delete screenshot file from disk and remove entry from user's paths array."""
    col = get_raw_samples()
    doc = col.find_one({"user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    entry = next((p for p in doc.get("paths", []) if p.get("name") == screenshot_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    # Delete file from disk
    file_path = Path(entry.get("file_path", ""))
    if file_path.exists():
        file_path.unlink()
        log.info("🗑 Deleted file: %s", file_path)

    # Remove the entry from the paths array
    col.update_one(
        {"user_id": user_id},
        {"$pull": {"paths": {"name": screenshot_id}}},
    )

    return {"success": True, "message": "Screenshot deleted"}


# ══════════════════════════════════════════════════════════
# ACTIVITY TRACKING — PostgreSQL (activity_logs table)
# ══════════════════════════════════════════════════════════

@app.post("/api/activity/log", response_model=ActivityLogResponse, tags=["Activity"])
def log_activity(request: ActivityLogRequest, db: Session = Depends(get_db)):
    """
    Receive one completed 10-minute activity window from the desktop app.
    Saves active_seconds, idle_seconds, activity_percent, and event counts.
    """
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    entry = ActivityLog(
        user_id=request.user_id,
        window_start=datetime.fromisoformat(request.window_start),
        window_end=datetime.fromisoformat(request.window_end),
        active_seconds=request.active_seconds,
        idle_seconds=request.idle_seconds,
        activity_percent=round(request.activity_percent, 1),
        mouse_events=request.mouse_events,
        keyboard_events=request.keyboard_events,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    log.info("📊 Activity log saved: user=%s active=%ds idle=%ds pct=%.1f%%",
             request.user_id, request.active_seconds, request.idle_seconds, request.activity_percent)

    return ActivityLogResponse(success=True, log_id=entry.id, message="Activity logged")


@app.get("/api/activity/{user_id}", response_model=ActivitySummaryResponse, tags=["Activity"])
def get_activity(user_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """
    Return today's aggregated activity stats + last N windows for the timeline chart.
    """
    from datetime import date
    today_start = datetime.combine(date.today(), datetime.min.time())

    # All windows today for aggregation
    today_logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.user_id == user_id, ActivityLog.window_start >= today_start)
        .all()
    )

    today_active = sum(r.active_seconds for r in today_logs)
    today_idle   = sum(r.idle_seconds   for r in today_logs)
    total_today  = today_active + today_idle
    today_pct    = round((today_active / total_today) * 100, 1) if total_today > 0 else 0.0

    # Recent windows for the bar chart (newest first → frontend reverses)
    recent = (
        db.query(ActivityLog)
        .filter(ActivityLog.user_id == user_id)
        .order_by(ActivityLog.window_start.desc())
        .limit(limit)
        .all()
    )

    logs = [
        ActivitySummaryItem(
            window_start=r.window_start.isoformat(),
            window_end=r.window_end.isoformat(),
            active_seconds=r.active_seconds,
            idle_seconds=r.idle_seconds,
            activity_percent=r.activity_percent,
            mouse_events=r.mouse_events,
            keyboard_events=r.keyboard_events,
        )
        for r in recent
    ]

    return ActivitySummaryResponse(
        user_id=user_id,
        today_active_sec=today_active,
        today_idle_sec=today_idle,
        today_percent=today_pct,
        logs=logs,
    )


# ══════════════════════════════════════════════════════════
# APP / WINDOW TRACKING — PostgreSQL (app_logs table)
# ══════════════════════════════════════════════════════════

@app.post("/api/applogs/batch", response_model=AppLogBatchResponse, tags=["App Tracking"])
def save_app_logs(request: AppLogBatchRequest, db: Session = Depends(get_db)):
    """
    Receive a batch of app window sessions from the desktop app.
    Each record = one continuous session on one application window.
    Desktop sends these every 60 seconds.
    """
    saved = 0
    for item in request.logs:
        # Skip junk entries (< 3 seconds)
        if item.duration_sec < 3:
            continue
        entry = AppLog(
            user_id=item.user_id,
            app_name=item.app_name,
            window_title=item.window_title,
            url=item.url,
            start_time=datetime.fromisoformat(item.start_time),
            end_time=datetime.fromisoformat(item.end_time),
            duration_sec=item.duration_sec,
        )
        db.add(entry)
        saved += 1

    db.commit()
    log.info("📋 App logs saved: %d records", saved)
    return AppLogBatchResponse(success=True, saved=saved, message=f"Saved {saved} records")


@app.get("/api/applogs/{user_id}", response_model=AppLogsResponse, tags=["App Tracking"])
def get_app_logs(user_id: int, limit: int = 200, date: str = None, db: Session = Depends(get_db)):
    """
    Return app window sessions for a user.
    Optional ?date=YYYY-MM-DD filters to that day only.
    """
    from datetime import date as date_cls
    q = db.query(AppLog).filter(AppLog.user_id == user_id)
    if date:
        try:
            d = date_cls.fromisoformat(date)
            day_start = datetime.combine(d, datetime.min.time())
            day_end   = datetime.combine(d, datetime.max.time())
            q = q.filter(AppLog.start_time >= day_start, AppLog.start_time <= day_end)
        except ValueError:
            pass
    rows = q.order_by(AppLog.start_time.desc()).limit(limit).all()
    records = [
        AppLogRecord(
            id=r.id,
            app_name=r.app_name or "",
            window_title=r.window_title or "",
            url=r.url or "",
            start_time=r.start_time.isoformat(),
            end_time=r.end_time.isoformat(),
            duration_sec=r.duration_sec,
        )
        for r in rows
    ]
    return AppLogsResponse(user_id=user_id, count=len(records), logs=records)


@app.get("/api/applogs/{user_id}/summary", response_model=AppSummaryResponse, tags=["App Tracking"])
def get_app_summary(user_id: int, date: str = None, db: Session = Depends(get_db)):
    """
    Return total time per application for a given date (?date=YYYY-MM-DD).
    Defaults to today.
    """
    from datetime import date as date_cls
    from sqlalchemy import func

    if date:
        try:
            d = date_cls.fromisoformat(date)
        except ValueError:
            d = date_cls.today()
    else:
        d = date_cls.today()

    today_start = datetime.combine(d, datetime.min.time())
    today_end   = datetime.combine(d, datetime.max.time())

    rows = (
        db.query(
            AppLog.app_name,
            func.sum(AppLog.duration_sec).label("total_sec"),
            func.count(AppLog.id).label("session_count"),
        )
        .filter(AppLog.user_id == user_id, AppLog.start_time >= today_start, AppLog.start_time <= today_end)
        .group_by(AppLog.app_name)
        .order_by(func.sum(AppLog.duration_sec).desc())
        .all()
    )

    entries = [
        AppSummaryEntry(
            app_name=r.app_name or "Unknown",
            total_sec=r.total_sec or 0,
            session_count=r.session_count,
        )
        for r in rows
    ]
    return AppSummaryResponse(user_id=user_id, entries=entries)


# ══════════════════════════════════════════════════════════
# USER PROFILE
# ══════════════════════════════════════════════════════════

@app.get("/api/users/{user_id}/profile", response_model=UserProfileResponse, tags=["Profile"])
def get_profile(user_id: int, db: Session = Depends(get_db)):
    """Return profile details for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserProfileResponse(
        user_id=user.id,
        username=user.username,
        email=user.email,
        user_type=user.user_type,
        project=user.project,
        designation=user.designation,
        isactive=user.isactive,
        created_at=user.created_at.isoformat(),
    )


@app.patch("/api/users/{user_id}/profile", response_model=UserProfileResponse, tags=["Profile"])
def update_profile(user_id: int, request: UserProfileUpdateRequest, db: Session = Depends(get_db)):
    """Update username, designation, or project for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.username is not None:
        user.username = request.username
    if request.designation is not None:
        user.designation = request.designation
    if request.project is not None:
        if request.project not in ("Bold", "MView"):
            raise HTTPException(status_code=400, detail="project must be 'Bold' or 'MView'")
        user.project = request.project

    db.commit()
    db.refresh(user)

    return UserProfileResponse(
        user_id=user.id,
        username=user.username,
        email=user.email,
        user_type=user.user_type,
        project=user.project,
        designation=user.designation,
        isactive=user.isactive,
        created_at=user.created_at.isoformat(),
    )


# ══════════════════════════════════════════════════════════
# ADMIN — list all users (admin only)
# ══════════════════════════════════════════════════════════

@app.get("/api/admin/users", response_model=AdminUsersResponse, tags=["Admin"])
def admin_list_users(admin_id: int, db: Session = Depends(get_db)):
    """
    Return every user in the system.
    Requires caller to be an admin (admin_id must exist and have user_type='admin').
    """
    caller = db.query(User).filter(User.id == admin_id).first()
    if not caller or caller.user_type != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    users = db.query(User).order_by(User.created_at.asc()).all()
    return AdminUsersResponse(
        count=len(users),
        users=[
            AdminUserItem(
                user_id=u.id,
                username=u.username,
                email=u.email,
                user_type=u.user_type,
                project=u.project,
                designation=u.designation,
                isactive=u.isactive,
                created_at=u.created_at.isoformat(),
            )
            for u in users
        ],
    )


@app.patch("/api/admin/users/{user_id}/type", tags=["Admin"])
def admin_change_user_type(user_id: int, admin_id: int, new_type: str, db: Session = Depends(get_db)):
    """
    Change a user's type between 'admin' and 'user'.
    Only an admin can call this.
    """
    caller = db.query(User).filter(User.id == admin_id).first()
    if not caller or caller.user_type != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    if new_type not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="new_type must be 'admin' or 'user'")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.user_type = new_type
    db.commit()
    return {"success": True, "message": f"User {target.username} is now '{new_type}'"}


# ══════════════════════════════════════════════════════════
# TASKS — Daily task submission system (PostgreSQL)
# ══════════════════════════════════════════════════════════

def _task_to_item(t: Task) -> TaskItem:
    """Convert a Task ORM object to the TaskItem schema."""
    return TaskItem(
        id=t.id,
        user_id=t.user_id,
        title=t.title,
        description=t.description,
        priority=t.priority,
        status=t.status,
        expected_completion_time=t.expected_completion_time,
        task_date=t.task_date.isoformat(),
        completed_at=t.completed_at.isoformat() if t.completed_at else None,
        created_at=t.created_at.isoformat(),
        updated_at=t.updated_at.isoformat(),
        notes=[
            TaskNoteItem(id=n.id, note=n.note, created_at=n.created_at.isoformat())
            for n in sorted(t.notes, key=lambda n: n.created_at)
        ],
    )


@app.post("/api/tasks", tags=["Tasks"])
def create_task(request: TaskCreateRequest, db: Session = Depends(get_db)):
    """Create a new task for today. Optionally includes a first progress note."""
    from datetime import date as date_cls
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    task = Task(
        user_id=request.user_id,
        title=request.title.strip(),
        description=request.description,
        priority=request.priority or "medium",
        status="pending",
        expected_completion_time=request.expected_completion_time,
        task_date=date_cls.today(),
    )
    db.add(task)
    db.flush()   # get task.id before commit

    if request.notes and request.notes.strip():
        note = TaskNote(task_id=task.id, user_id=request.user_id, note=request.notes.strip())
        db.add(note)

    db.commit()
    db.refresh(task)
    log.info("✅ Task created: user=%s title=%r", request.user_id, request.title)
    return {"success": True, "task_id": task.id, "message": "Task created"}


@app.get("/api/tasks/{user_id}", response_model=TaskListResponse, tags=["Tasks"])
def get_tasks(user_id: int, date: str = None, status: str = None, db: Session = Depends(get_db)):
    """Return tasks for a user, optionally filtered by date and/or status."""
    from datetime import date as date_cls
    try:
        d = date_cls.fromisoformat(date) if date else date_cls.today()
    except ValueError:
        d = date_cls.today()

    q = db.query(Task).filter(Task.user_id == user_id, Task.task_date == d)
    if status:
        q = q.filter(Task.status == status)
    tasks = q.order_by(Task.created_at.asc()).all()

    return TaskListResponse(
        success=True,
        user_id=user_id,
        date=d.isoformat(),
        count=len(tasks),
        tasks=[_task_to_item(t) for t in tasks],
    )


@app.get("/api/tasks/{user_id}/summary", response_model=TaskSummaryResponse, tags=["Tasks"])
def get_task_summary(user_id: int, date: str = None, db: Session = Depends(get_db)):
    """Return task counts and completion % for the dashboard widget."""
    from datetime import date as date_cls
    try:
        d = date_cls.fromisoformat(date) if date else date_cls.today()
    except ValueError:
        d = date_cls.today()

    tasks = db.query(Task).filter(Task.user_id == user_id, Task.task_date == d).all()
    total       = len(tasks)
    pending     = sum(1 for t in tasks if t.status == "pending")
    in_progress = sum(1 for t in tasks if t.status == "in_progress")
    completed   = sum(1 for t in tasks if t.status == "completed")
    pct         = round((completed / total) * 100, 1) if total > 0 else 0.0

    return TaskSummaryResponse(
        success=True, user_id=user_id, date=d.isoformat(),
        total=total, pending=pending, in_progress=in_progress,
        completed=completed, completion_pct=pct,
    )


@app.patch("/api/tasks/{task_id}", tags=["Tasks"])
def edit_task(task_id: int, request: TaskEditRequest, db: Session = Depends(get_db)):
    """Edit task title, description, priority, or expected_completion_time."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != request.user_id:
        raise HTTPException(status_code=403, detail="Not your task")

    if request.title is not None:
        task.title = request.title.strip()
    if request.description is not None:
        task.description = request.description
    if request.priority is not None:
        if request.priority not in ("low", "medium", "high"):
            raise HTTPException(status_code=400, detail="priority must be low/medium/high")
        task.priority = request.priority
    if request.expected_completion_time is not None:
        task.expected_completion_time = request.expected_completion_time

    task.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True, "message": "Task updated"}


@app.patch("/api/tasks/{task_id}/status", tags=["Tasks"])
def update_task_status(task_id: int, request: TaskStatusUpdateRequest, db: Session = Depends(get_db)):
    """Update task status. Sets completed_at when status becomes 'completed'."""
    valid = ("pending", "in_progress", "completed")
    if request.status not in valid:
        raise HTTPException(status_code=400, detail=f"status must be one of {valid}")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != request.user_id:
        raise HTTPException(status_code=403, detail="Not your task")

    task.status = request.status
    task.updated_at = datetime.utcnow()
    if request.status == "completed" and not task.completed_at:
        task.completed_at = datetime.utcnow()
    elif request.status != "completed":
        task.completed_at = None   # re-open clears the timestamp

    db.commit()
    return {"success": True, "task_id": task_id, "status": request.status, "message": "Status updated"}


@app.delete("/api/tasks/{task_id}", tags=["Tasks"])
def delete_task(task_id: int, user_id: int, db: Session = Depends(get_db)):
    """Delete a task and all its notes (cascade)."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not your task")

    db.delete(task)
    db.commit()
    return {"success": True, "message": "Task deleted"}


@app.post("/api/tasks/{task_id}/notes", tags=["Tasks"])
def add_task_note(task_id: int, request: TaskNoteCreateRequest, db: Session = Depends(get_db)):
    """Add a progress note to a task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not request.note.strip():
        raise HTTPException(status_code=400, detail="Note cannot be empty")

    note = TaskNote(task_id=task_id, user_id=request.user_id, note=request.note.strip())
    db.add(note)
    db.commit()
    db.refresh(note)
    return {"success": True, "note_id": note.id, "message": "Note added"}


@app.get("/api/admin/tasks", response_model=AdminTaskListResponse, tags=["Admin Tasks"])
def admin_get_tasks(admin_id: int, date: str = None, user_id: int = None,
                    status: str = None, project: str = None, db: Session = Depends(get_db)):
    """Return all tasks across employees with optional filters."""
    from datetime import date as date_cls
    caller = db.query(User).filter(User.id == admin_id).first()
    if not caller or caller.user_type != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        d = date_cls.fromisoformat(date) if date else date_cls.today()
    except ValueError:
        d = date_cls.today()

    q = db.query(Task, User).join(User, Task.user_id == User.id).filter(Task.task_date == d)
    if user_id:
        q = q.filter(Task.user_id == user_id)
    if status:
        q = q.filter(Task.status == status)
    if project:
        q = q.filter(User.project == project)

    rows = q.order_by(Task.created_at.asc()).all()

    items = [
        AdminTaskItem(
            task_id=t.id,
            user_id=t.user_id,
            username=u.username,
            project=u.project,
            title=t.title,
            priority=t.priority,
            status=t.status,
            expected_completion_time=t.expected_completion_time,
            task_date=t.task_date.isoformat(),
            completed_at=t.completed_at.isoformat() if t.completed_at else None,
            created_at=t.created_at.isoformat(),
            note_count=len(t.notes),
        )
        for t, u in rows
    ]

    return AdminTaskListResponse(success=True, date=d.isoformat(), count=len(items), tasks=items)


@app.get("/api/admin/tasks/stats", response_model=AdminTaskStatsResponse, tags=["Admin Tasks"])
def admin_task_stats(admin_id: int, date: str = None, project: str = None, db: Session = Depends(get_db)):
    """Team-level task productivity stats, broken down by employee."""
    from datetime import date as date_cls
    caller = db.query(User).filter(User.id == admin_id).first()
    if not caller or caller.user_type != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        d = date_cls.fromisoformat(date) if date else date_cls.today()
    except ValueError:
        d = date_cls.today()

    q = db.query(Task, User).join(User, Task.user_id == User.id).filter(Task.task_date == d)
    if project:
        q = q.filter(User.project == project)
    rows = q.all()

    # Group by user
    from collections import defaultdict
    by_user: dict = defaultdict(lambda: {"user": None, "tasks": []})
    for t, u in rows:
        by_user[u.id]["user"] = u
        by_user[u.id]["tasks"].append(t)

    by_employee = []
    for uid, data in by_user.items():
        u = data["user"]
        tasks = data["tasks"]
        total       = len(tasks)
        completed   = sum(1 for t in tasks if t.status == "completed")
        in_progress = sum(1 for t in tasks if t.status == "in_progress")
        pending     = sum(1 for t in tasks if t.status == "pending")
        pct         = round((completed / total) * 100, 1) if total > 0 else 0.0
        by_employee.append(AdminTaskUserStat(
            user_id=u.id, username=u.username, project=u.project,
            total=total, completed=completed, in_progress=in_progress,
            pending=pending, completion_pct=pct,
        ))

    total_all     = len(rows)
    completed_all = sum(1 for t, _ in rows if t.status == "completed")
    in_prog_all   = sum(1 for t, _ in rows if t.status == "in_progress")
    pending_all   = sum(1 for t, _ in rows if t.status == "pending")
    pct_all       = round((completed_all / total_all) * 100, 1) if total_all > 0 else 0.0

    return AdminTaskStatsResponse(
        success=True, date=d.isoformat(),
        total_tasks=total_all, completed=completed_all,
        in_progress=in_prog_all, pending=pending_all,
        completion_pct=pct_all,
        by_employee=sorted(by_employee, key=lambda x: x.completion_pct, reverse=True),
    )

