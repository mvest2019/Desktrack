# ============================================================
# models.py — Database table definitions
# ============================================================
# Each class here = one table in your PostgreSQL database.
# SQLAlchemy will auto-create these tables when you start the app.

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    """
    This maps to the 'users' table in PostgreSQL.
    Each User object = one row in the table.
    """
    __tablename__ = "users"

    id          = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username    = Column(String(100), nullable=False)
    email       = Column(String(255), nullable=False, unique=True, index=True)
    password    = Column(String(255), nullable=False)
    user_type   = Column(String(20), nullable=False, default="user")  # "admin" or "user"
    project     = Column(String(50), nullable=True)   # "Bold" or "MView"
    designation = Column(String(100), nullable=True)  # e.g. "Frontend Dev", "Marketing"
    skills      = Column(String(500), nullable=True)  # comma-separated, e.g. "Python, React"
    isactive    = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    # One user → many screenshots (one-to-many relationship)
    screenshots = relationship("Screenshot", back_populates="user")
    tasks       = relationship("Task", back_populates="user")


class Screenshot(Base):
    """
    Stores screenshots captured from the desktop app.
    image_data holds the screenshot as a base64-encoded string.
    """
    __tablename__ = "screenshots"

    id         = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename   = Column(String(255))
    image_data = Column(Text, nullable=False)   # base64 string — no file system needed
    file_size  = Column(Integer)                # size in bytes (before base64 encoding)
    taken_at   = Column(DateTime, default=datetime.utcnow)

    # Each screenshot belongs to one user
    user = relationship("User", back_populates="screenshots")


class ActivityLog(Base):
    """
    One row = one 10-minute tracking window.
    Stores active/idle seconds and derived activity percentage.
    """
    __tablename__ = "activity_logs"

    id               = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    window_start     = Column(DateTime, nullable=False)
    window_end       = Column(DateTime, nullable=False)
    active_seconds   = Column(Integer, default=0)
    idle_seconds     = Column(Integer, default=0)
    activity_percent = Column(Float, default=0.0)
    mouse_events     = Column(Integer, default=0)
    keyboard_events  = Column(Integer, default=0)
    created_at       = Column(DateTime, default=datetime.utcnow)


class AppLog(Base):
    """
    One row = one continuous session on a single application window.
    Created by the desktop app every time the active window changes.
    Example: user spent 4 minutes on "VS Code" with title "main.py"
    """
    __tablename__ = "app_logs"

    id            = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    app_name      = Column(String(255))          # e.g. "Google Chrome", "VS Code"
    window_title  = Column(String(500))          # e.g. "GitHub - Google Chrome"
    url           = Column(String(1000))         # only filled for browsers
    start_time    = Column(DateTime, nullable=False)
    end_time      = Column(DateTime, nullable=False)
    duration_sec  = Column(Integer, default=0)   # end_time - start_time in seconds
    created_at    = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    """
    One row = one task submitted by an employee for a specific day.
    Employees can have multiple tasks per day.
    """
    __tablename__ = "tasks"

    id                       = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id                  = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title                    = Column(String(200), nullable=False)
    description              = Column(Text, nullable=True)
    priority                 = Column(String(20), nullable=False, default="medium")  # low/medium/high
    status                   = Column(String(20), nullable=False, default="pending")  # pending/in_progress/completed
    expected_completion_time = Column(String(50), nullable=True)   # free text: "by 3pm", "2h", "EOD"
    task_date                = Column(Date, nullable=False, index=True)
    completed_at             = Column(DateTime, nullable=True)
    created_at               = Column(DateTime, default=datetime.utcnow)
    updated_at               = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user  = relationship("User", back_populates="tasks")
    notes = relationship("TaskNote", back_populates="task", cascade="all, delete-orphan")


class TaskNote(Base):
    """
    One row = one progress note/comment on a task.
    Many notes can belong to a single task.
    """
    __tablename__ = "task_notes"

    id         = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id    = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    note       = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="notes")
    user = relationship("User")
