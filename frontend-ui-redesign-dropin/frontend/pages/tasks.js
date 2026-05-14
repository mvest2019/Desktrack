// pages/tasks.js — Daily Task Management
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import Link from "next/link";
import styles from "../styles/Tasks.module.css";
import API from "../config";

// ── Mini calendar (same pattern as activity.js) ───────────
function MiniCalendar({ activeDates, selectedDate, onSelect }) {
  const [viewYear,  setViewYear]  = useState(() => new Date().getFullYear());
  const [viewMonth, setViewMonth] = useState(() => new Date().getMonth());

  const daysInMonth  = new Date(viewYear, viewMonth + 1, 0).getDate();
  const firstWeekday = new Date(viewYear, viewMonth, 1).getDay();
  const monthLabel   = new Date(viewYear, viewMonth).toLocaleDateString([], { month: "long", year: "numeric" });

  function prevMonth() { if (viewMonth === 0) { setViewYear(y => y-1); setViewMonth(11); } else setViewMonth(m => m-1); }
  function nextMonth() { if (viewMonth === 11) { setViewYear(y => y+1); setViewMonth(0); } else setViewMonth(m => m+1); }

  const cells = [];
  for (let i = 0; i < firstWeekday; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  return (
    <div className={styles.calPopup}>
      <div className={styles.calHeader}>
        <button className={styles.calNav} onClick={prevMonth}>‹</button>
        <span className={styles.calMonth}>{monthLabel}</span>
        <button className={styles.calNav} onClick={nextMonth}>›</button>
      </div>
      <div className={styles.calGrid}>
        {["Su","Mo","Tu","We","Th","Fr","Sa"].map(d => <span key={d} className={styles.calDayName}>{d}</span>)}
        {cells.map((d, i) => {
          if (!d) return <span key={`e${i}`} />;
          const ds = `${viewYear}-${String(viewMonth+1).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
          const isActive   = activeDates.has(ds);
          const isSelected = selectedDate === ds;
          return (
            <button key={ds}
              className={`${styles.calDay} ${isActive ? styles.calDayActive : ""} ${isSelected ? styles.calDaySelected : ""}`}
              onClick={() => onSelect(ds)} disabled={false}>
              {d}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function TasksPage() {
  const router  = useRouter();
  const calRef  = useRef(null);

  const todayStr = () => new Date().toLocaleDateString("en-CA");

  const [user,        setUser]        = useState(null);
  const [tasks,       setTasks]       = useState([]);
  const [summary,     setSummary]     = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [dateFilter,  setDateFilter]  = useState(todayStr);
  const [calOpen,     setCalOpen]     = useState(false);
  const [showForm,    setShowForm]    = useState(false);
  const [submitting,   setSubmitting]   = useState(false);
  const [createError,  setCreateError]  = useState("");
  const [statusError,  setStatusError]  = useState("");
  const [fetchError,   setFetchError]   = useState("");
  const [editingId,    setEditingId]    = useState(null);
  const [updatingId,   setUpdatingId]   = useState(null);

  const [form, setForm] = useState({ title: "" });
  const [editTitle, setEditTitle] = useState("");

  // Close calendar on outside click
  useEffect(() => {
    function handle(e) { if (calRef.current && !calRef.current.contains(e.target)) setCalOpen(false); }
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem("user");
    if (!stored) { router.push("/"); return; }
    const u = JSON.parse(stored);
    setUser(u);
    fetchAll(u.user_id, dateFilter);
  }, []);

  useEffect(() => {
    if (!user) return;
    fetchAll(user.user_id, dateFilter);
  }, [dateFilter]);

  async function fetchAll(userId, date) {
    setLoading(true);
    setFetchError("");
    try {
      const [tasksRes, sumRes] = await Promise.all([
        fetch(`${API}/api/tasks/${userId}?date=${date}`),
        fetch(`${API}/api/tasks/${userId}/summary?date=${date}`),
      ]);
      if (tasksRes.ok) setTasks((await tasksRes.json()).tasks || []);
      else setFetchError("Failed to load tasks.");
      if (sumRes.ok) setSummary(await sumRes.json());
    } catch {
      setFetchError("Cannot connect to server. Make sure the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  function logout() { localStorage.removeItem("user"); router.push("/"); }

  // ── Create task ─────────────────────────────────────────
  async function handleCreate(e) {
    e.preventDefault();
    if (!form.title.trim()) return;
    setSubmitting(true);
    setCreateError("");
    try {
      const res = await fetch(`${API}/api/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.user_id, title: form.title.trim() }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setForm({ title: "" });
        setShowForm(false);
        fetchAll(user.user_id, dateFilter);
      } else {
        setCreateError(data.detail || "Failed to add task.");
      }
    } catch {
      setCreateError("Cannot connect to server.");
    } finally {
      setSubmitting(false);
    }
  }

  // ── Status change ────────────────────────────────────────
  async function changeStatus(taskId, status) {
    setUpdatingId(taskId);
    setStatusError("");
    try {
      const res = await fetch(`${API}/api/tasks/${taskId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.user_id, status }),
      });
      if (res.ok) {
        await fetchAll(user.user_id, dateFilter);
      } else {
        const d = await res.json();
        setStatusError(d.detail || "Status update failed.");
      }
    } catch {
      setStatusError("Cannot connect to server.");
    } finally {
      setUpdatingId(null);
    }
  }

  // ── Delete task ──────────────────────────────────────────
  async function deleteTask(taskId) {
    if (!confirm("Delete this task?")) return;
    try {
      await fetch(`${API}/api/tasks/${taskId}?user_id=${user.user_id}`, { method: "DELETE" });
      fetchAll(user.user_id, dateFilter);
    } catch (_) {}
  }

  // ── Inline edit (title only) ─────────────────────────────
  function startEdit(task) {
    setEditingId(task.id);
    setEditTitle(task.title);
  }
  async function saveEdit(taskId) {
    if (!editTitle.trim()) return;
    try {
      await fetch(`${API}/api/tasks/${taskId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.user_id, title: editTitle.trim() }),
      });
      setEditingId(null);
      fetchAll(user.user_id, dateFilter);
    } catch (_) {}
  }

  function fmtTime(iso) {
    if (!iso) return "";
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  if (!user) return null;

  const isToday = dateFilter === todayStr();

  return (
    <>
      <Head><title>Realisieren Pulse — My Tasks</title></Head>
      <div className={styles.page}>

        {/* ── Sidebar ──────────────────────────────────── */}
        <aside className={styles.sidebar}>
          <div className={styles.logo}>
            <img src="/app_icon.png" alt="Realisieren Pulse" className={styles.logoImg} />
            <span className={styles.logoText}>Realisieren Pulse</span>
          </div>
          <nav className={styles.nav}>
            <Link className={styles.navItem} href="/dashboard"><span>DB</span> Dashboard</Link>
            <Link className={styles.navItem} href="/screenshots"><span>SC</span> Screenshots</Link>
            <Link className={styles.navItem} href="/activity"><span>AC</span> Activity</Link>
            <Link className={`${styles.navItem} ${styles.active}`} href="/tasks"><span>TK</span> My Tasks</Link>
            <Link className={styles.navItem} href="/profile"><span>PF</span> Profile</Link>
            {user.user_type === "admin" && (
              <>
                <Link className={styles.navItem} href="/admin"><span>AD</span> Admin Portal</Link>
                <Link className={styles.navItem} href="/admin-tasks"><span>OV</span> Task Overview</Link>
              </>
            )}
          </nav>
          <div className={styles.sidebarFooter}>
            <div className={styles.userBadge}>
              <div className={styles.avatar}>{user.username?.charAt(0).toUpperCase()}</div>
              <div>
                <div className={styles.userName}>{user.username}</div>
                <div className={styles.userEmail}>{user.email}</div>
              </div>
            </div>
            <button onClick={logout} className={styles.logoutBtn}>Logout</button>
          </div>
        </aside>

        {/* ── Main ─────────────────────────────────────── */}
        <main className={styles.main}>

          {/* Top bar */}
          <div className={styles.topBar}>
            <div>
              <h1 className={styles.pageTitle}>My Tasks</h1>
              <p className={styles.pageSubtitle}>Plan, track, and complete your daily work</p>
            </div>
            <div className={styles.topBarRight}>
              <div className={styles.calWrap} ref={calRef}>
                <button className={styles.calToggleBtn} onClick={() => setCalOpen(o => !o)}>
                  📅 {isToday ? "Today" : dateFilter}
                </button>
                {calOpen && (
                  <MiniCalendar
                    activeDates={new Set()}
                    selectedDate={dateFilter}
                    onSelect={ds => { setDateFilter(ds); setCalOpen(false); }}
                  />
                )}
              </div>
              {isToday && (
                <button className={styles.addTaskBtn} onClick={() => setShowForm(v => !v)}>
                  {showForm ? "✕ Cancel" : "+ Add Task"}
                </button>
              )}
            </div>
          </div>

          {/* Summary strip */}
          {summary && (
            <div className={styles.summaryStrip}>
              <div className={styles.summaryCard}>
                <div className={styles.summaryLabel}>Total Tasks</div>
                <div className={styles.summaryValue} style={{ color: "#e2e8f0" }}>{summary.total}</div>
              </div>
              <div className={styles.summaryCard}>
                <div className={styles.summaryLabel}>Pending</div>
                <div className={styles.summaryValue} style={{ color: "rgba(255,255,255,0.5)" }}>{summary.pending}</div>
              </div>
              <div className={styles.summaryCard}>
                <div className={styles.summaryLabel}>In Progress</div>
                <div className={styles.summaryValue} style={{ color: "#4A9EFF" }}>{summary.in_progress}</div>
              </div>
              <div className={styles.summaryCard}>
                <div className={styles.summaryLabel}>Completed</div>
                <div className={styles.summaryValue} style={{ color: "#34D399" }}>{summary.completed}</div>
              </div>
            </div>
          )}

          {/* Create task form — title only */}
          {showForm && (
            <div className={styles.formPanel}>
              <div className={styles.formTitle}>New Task</div>
              <form onSubmit={handleCreate} style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <input
                  className={styles.formInput}
                  style={{ flex: 1 }}
                  placeholder="What do you need to do today?"
                  value={form.title}
                  onChange={e => { setForm({ title: e.target.value }); setCreateError(""); }}
                  autoFocus
                  required
                  disabled={submitting}
                />
                <button type="submit" className={styles.btnPrimary} disabled={submitting}>
                  {submitting ? "Adding…" : "Add Task"}
                </button>
                <button type="button" className={styles.btnCancel} onClick={() => { setShowForm(false); setCreateError(""); }}>Cancel</button>
              </form>
              {createError && <div style={{ color: "#EF4444", fontSize: 13, marginTop: 8 }}>⚠ {createError}</div>}
            </div>
          )}

          {statusError && (
            <div style={{ color: "#EF4444", fontSize: 13, marginBottom: 12, padding: "10px 14px", background: "#FEF2F2", borderRadius: 8, border: "1px solid #FECACA" }}>
              ⚠ {statusError}
            </div>
          )}

          {fetchError && (
            <div style={{ color: "#EF4444", fontSize: 13, marginBottom: 12, padding: "10px 14px", background: "#FEF2F2", borderRadius: 8, border: "1px solid #FECACA" }}>
              ⚠ {fetchError}
            </div>
          )}

          {/* Task list */}
          {loading ? (
            <div className={styles.emptyState}><div className={styles.emptyText}>Loading tasks…</div></div>
          ) : tasks.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>✅</div>
              <div className={styles.emptyText}>
                {isToday ? "No tasks yet. Click \"+ Add Task\" to plan your day." : "No tasks for this date."}
              </div>
            </div>
          ) : (
            <div className={styles.taskList}>
              {tasks.map(task => {
                const isEditing   = editingId === task.id;
                const isCompleted = task.status === "completed";

                return (
                  <div key={task.id} className={`${styles.taskCard} ${isCompleted ? styles.taskCompleted : ""}`}>
                    <div className={styles.taskCardInner}>
                      {isEditing ? (
                        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                          <input
                            className={styles.formInput}
                            style={{ flex: 1 }}
                            value={editTitle}
                            onChange={e => setEditTitle(e.target.value)}
                            onKeyDown={e => { if (e.key === "Enter") saveEdit(task.id); if (e.key === "Escape") setEditingId(null); }}
                            autoFocus
                          />
                          <button className={styles.btnPrimary} onClick={() => saveEdit(task.id)}>Save</button>
                          <button className={styles.btnCancel} onClick={() => setEditingId(null)}>Cancel</button>
                        </div>
                      ) : (
                        <div className={styles.taskCardTop}>
                          <div className={styles.taskCardLeft}>
                            <div className={styles.taskTitle}>{task.title}</div>
                            <div className={styles.taskMeta}>
                              <span className={`${styles.statusBadge} ${
                                task.status === "completed"   ? styles.statusCompleted  :
                                task.status === "in_progress" ? styles.statusInProgress : styles.statusPending
                              }`}>
                                {task.status === "in_progress" ? "In Progress" :
                                 task.status === "completed"   ? "✓ Done"      : "Pending"}
                              </span>
                              {task.completed_at && (
                                <span className={styles.taskExpected}>
                                  at {fmtTime(task.completed_at)}
                                </span>
                              )}
                            </div>
                          </div>
                          <div className={styles.taskActions}>
                            {task.status === "pending" && isToday && (
                              <button className={`${styles.actionBtn} ${styles.btnStart}`}
                                disabled={updatingId === task.id}
                                onClick={() => changeStatus(task.id, "in_progress")}>
                                {updatingId === task.id ? "…" : "Start"}
                              </button>
                            )}
                            {task.status === "in_progress" && isToday && (
                              <button className={`${styles.actionBtn} ${styles.btnComplete}`}
                                disabled={updatingId === task.id}
                                onClick={() => changeStatus(task.id, "completed")}>
                                {updatingId === task.id ? "…" : "✓ Done"}
                              </button>
                            )}
                            {isToday && !isCompleted && (
                              <button className={`${styles.actionBtn} ${styles.btnEdit}`}
                                onClick={() => startEdit(task)} title="Edit">✎</button>
                            )}
                            {isToday && (
                              <button className={`${styles.actionBtn} ${styles.btnDelete}`}
                                onClick={() => deleteTask(task.id)} title="Delete">✕</button>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </main>
      </div>
    </>
  );
}
