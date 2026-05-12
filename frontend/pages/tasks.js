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
  const [submitting,  setSubmitting]  = useState(false);
  const [expandedNotes, setExpandedNotes] = useState({});
  const [noteInputs,  setNoteInputs]  = useState({});
  const [editingId,   setEditingId]   = useState(null);
  const [editForm,    setEditForm]    = useState({});
  const [updatingId,  setUpdatingId]  = useState(null);

  const [form, setForm] = useState({
    title: "", description: "", priority: "medium",
    expected_completion_time: "", notes: "",
  });
  const [durNum,  setDurNum]  = useState("");
  const [durUnit, setDurUnit] = useState("hr");
  const [editDurNum,  setEditDurNum]  = useState("");
  const [editDurUnit, setEditDurUnit] = useState("hr");

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
    try {
      const [tasksRes, sumRes] = await Promise.all([
        fetch(`${API}/api/tasks/${userId}?date=${date}`),
        fetch(`${API}/api/tasks/${userId}/summary?date=${date}`),
      ]);
      if (tasksRes.ok)  setTasks((await tasksRes.json()).tasks || []);
      if (sumRes.ok)    setSummary(await sumRes.json());
    } catch (_) {}
    finally { setLoading(false); }
  }

  function logout() { localStorage.removeItem("user"); router.push("/"); }

  // ── Create task ─────────────────────────────────────────
  async function handleCreate(e) {
    e.preventDefault();
    if (!form.title.trim()) return;
    setSubmitting(true);
    const ect = durNum.trim() ? `${durNum.trim()} ${durUnit}` : "";
    try {
      const res = await fetch(`${API}/api/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.user_id, ...form, expected_completion_time: ect }),
      });
      if (res.ok) {
        setForm({ title: "", description: "", priority: "medium", expected_completion_time: "", notes: "" });
        setDurNum(""); setDurUnit("hr");
        setShowForm(false);
        fetchAll(user.user_id, dateFilter);
      }
    } catch (_) {}
    finally { setSubmitting(false); }
  }

  // ── Status change ────────────────────────────────────────
  async function changeStatus(taskId, status) {
    setUpdatingId(taskId);
    try {
      const res = await fetch(`${API}/api/tasks/${taskId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.user_id, status }),
      });
      if (res.ok) await fetchAll(user.user_id, dateFilter);
    } catch (_) {}
    finally { setUpdatingId(null); }
  }

  // ── Delete task ──────────────────────────────────────────
  async function deleteTask(taskId) {
    if (!confirm("Delete this task?")) return;
    try {
      await fetch(`${API}/api/tasks/${taskId}?user_id=${user.user_id}`, { method: "DELETE" });
      fetchAll(user.user_id, dateFilter);
    } catch (_) {}
  }

  // ── Add note ─────────────────────────────────────────────
  async function addNote(taskId) {
    const note = (noteInputs[taskId] || "").trim();
    if (!note) return;
    try {
      await fetch(`${API}/api/tasks/${taskId}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.user_id, note }),
      });
      setNoteInputs(n => ({ ...n, [taskId]: "" }));
      fetchAll(user.user_id, dateFilter);
    } catch (_) {}
  }

  // ── Inline edit ──────────────────────────────────────────
  function startEdit(task) {
    setEditingId(task.id);
    setEditForm({ title: task.title, description: task.description || "", priority: task.priority, expected_completion_time: task.expected_completion_time || "" });
    const parts = (task.expected_completion_time || "").trim().split(" ");
    setEditDurNum(parts[0] && !isNaN(parts[0]) ? parts[0] : "");
    setEditDurUnit(parts[1] || "hr");
  }
  async function saveEdit(taskId) {
    const ect = editDurNum.trim() ? `${editDurNum.trim()} ${editDurUnit}` : "";
    try {
      await fetch(`${API}/api/tasks/${taskId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.user_id, ...editForm, expected_completion_time: ect }),
      });
      setEditingId(null);
      fetchAll(user.user_id, dateFilter);
    } catch (_) {}
  }

  function fmtTime(iso) {
    if (!iso) return "";
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  // Parse "1 hr", "2 days", "30 min" etc. → total minutes (null if unparseable)
  function parseExpectedMinutes(str) {
    if (!str) return null;
    const s = str.toLowerCase().trim();
    const match = s.match(/^([\d.]+)\s*(day|days|hr|hrs|hour|hours|min|mins|minute|minutes)$/);
    if (!match) return null;
    const val = parseFloat(match[1]);
    const unit = match[2];
    if (unit.startsWith("day"))  return Math.round(val * 1440);
    if (unit.startsWith("h"))    return Math.round(val * 60);
    if (unit.startsWith("min"))  return Math.round(val);
    return null;
  }

  function fmtDuration(minutes) {
    if (minutes < 60)  return `${minutes}m`;
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (minutes < 1440) return m > 0 ? `${h}h ${m}m` : `${h}h`;
    const d = Math.floor(minutes / 1440);
    const rh = Math.floor((minutes % 1440) / 60);
    return rh > 0 ? `${d}d ${rh}h` : `${d}d`;
  }

  // Returns completion summary info for a completed task
  function completionInfo(task) {
    if (task.status !== "completed" || !task.completed_at) return null;
    const takenMin = Math.round((new Date(task.completed_at) - new Date(task.created_at)) / 60000);
    const expectedMin = parseExpectedMinutes(task.expected_completion_time);
    return {
      completedAt: fmtTime(task.completed_at),
      taken: fmtDuration(takenMin),
      expected: expectedMin ? fmtDuration(expectedMin) : task.expected_completion_time || null,
      early: expectedMin != null ? takenMin <= expectedMin : null,
    };
  }

  const priorityDotColor = { high: "#F87171", medium: "#F59E0B", low: "#34D399" };

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
            <Link className={styles.navItem} href="/dashboard"><span>📊</span> Dashboard</Link>
            <Link className={styles.navItem} href="/screenshots"><span>📷</span> Screenshots</Link>
            <Link className={styles.navItem} href="/activity"><span>🖥</span> Activity</Link>
            <Link className={`${styles.navItem} ${styles.active}`} href="/tasks"><span>✅</span> My Tasks</Link>
            <Link className={styles.navItem} href="/profile"><span>👤</span> Profile</Link>
            {user.user_type === "admin" && (
              <>
                <Link className={styles.navItem} href="/admin"><span>🛡</span> Admin Portal</Link>
                <Link className={styles.navItem} href="/admin-tasks"><span>📋</span> Task Overview</Link>
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

          {/* Create task form */}
          {showForm && (
            <div className={styles.formPanel}>
              <div className={styles.formTitle}>New Task</div>
              <form onSubmit={handleCreate}>
                <div className={styles.formGrid}>
                  <div className={styles.formGroupFull}>
                    <label className={styles.formLabel}>Task Title *</label>
                    <input className={styles.formInput} placeholder="What do you need to do?"
                      value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} required />
                  </div>
                  <div className={styles.formGroupFull}>
                    <label className={styles.formLabel}>Description</label>
                    <textarea className={styles.formTextarea} placeholder="Any additional details..."
                      value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>Priority</label>
                    <select className={styles.formSelect} value={form.priority}
                      onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}>
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                    </select>
                  </div>
                  <div className={styles.formGroup}>
                    <label className={styles.formLabel}>Expected Completion</label>
                    <div className={styles.durationRow}>
                      <input className={styles.durationNum} type="number" min="1" placeholder="e.g. 2"
                        value={durNum} onChange={e => setDurNum(e.target.value)} />
                      <select className={styles.durationUnit} value={durUnit} onChange={e => setDurUnit(e.target.value)}
                        style={{ background: "#1e2436", color: "#ffffff" }}>
                        <option value="min"  style={{ background: "#1e2436", color: "#ffffff" }}>min</option>
                        <option value="hr"   style={{ background: "#1e2436", color: "#ffffff" }}>hr</option>
                        <option value="day"  style={{ background: "#1e2436", color: "#ffffff" }}>day</option>
                      </select>
                    </div>
                  </div>
                  <div className={styles.formGroupFull}>
                    <label className={styles.formLabel}>Starting Note (optional)</label>
                    <textarea className={styles.formTextarea} placeholder="Add a starting note..." rows={2}
                      value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
                  </div>
                </div>
                <div className={styles.formActions}>
                  <button type="submit" className={styles.btnPrimary} disabled={submitting}>
                    {submitting ? "Adding..." : "Add Task"}
                  </button>
                  <button type="button" className={styles.btnCancel} onClick={() => setShowForm(false)}>Cancel</button>
                </div>
              </form>
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
                const isEditing  = editingId === task.id;
                const notesOpen  = expandedNotes[task.id];
                const isCompleted = task.status === "completed";

                return (
                  <div key={task.id} className={`${styles.taskCard} ${isCompleted ? styles.taskCompleted : ""}`}>
                    <div className={styles.taskCardInner}>
                      {isEditing ? (
                        /* ── Inline edit form ── */
                        <div>
                          <div className={styles.formGrid} style={{ marginBottom: 10 }}>
                            <div className={styles.formGroupFull}>
                              <input className={styles.formInput} value={editForm.title}
                                onChange={e => setEditForm(f => ({ ...f, title: e.target.value }))} />
                            </div>
                            <div className={styles.formGroupFull}>
                              <textarea className={styles.formTextarea} rows={2} value={editForm.description}
                                onChange={e => setEditForm(f => ({ ...f, description: e.target.value }))} />
                            </div>
                            <div className={styles.formGroup}>
                              <select className={styles.formSelect} value={editForm.priority}
                                onChange={e => setEditForm(f => ({ ...f, priority: e.target.value }))}>
                                <option value="low">Low</option>
                                <option value="medium">Medium</option>
                                <option value="high">High</option>
                              </select>
                            </div>
                            <div className={styles.formGroup}>
                              <div className={styles.durationRow}>
                                <input className={styles.durationNum} type="number" min="1" placeholder="e.g. 2"
                                  value={editDurNum} onChange={e => setEditDurNum(e.target.value)} />
                                <select className={styles.durationUnit} value={editDurUnit} onChange={e => setEditDurUnit(e.target.value)}
                                  style={{ background: "#1e2436", color: "#ffffff" }}>
                                  <option value="min"  style={{ background: "#1e2436", color: "#ffffff" }}>min</option>
                                  <option value="hr"   style={{ background: "#1e2436", color: "#ffffff" }}>hr</option>
                                  <option value="day"  style={{ background: "#1e2436", color: "#ffffff" }}>day</option>
                                </select>
                              </div>
                            </div>
                          </div>
                          <div className={styles.formActions}>
                            <button className={styles.btnPrimary} onClick={() => saveEdit(task.id)}>Save</button>
                            <button className={styles.btnCancel} onClick={() => setEditingId(null)}>Cancel</button>
                          </div>
                        </div>
                      ) : (
                        /* ── Normal card view ── */
                        <>
                          <div className={styles.taskCardTop}>
                            <div className={styles.taskCardLeft}>
                              <div className={styles.priorityDot} style={{ background: priorityDotColor[task.priority] }} />
                              <div>
                                <div className={styles.taskTitle}>{task.title}</div>
                                {task.description && <div className={styles.taskDesc}>{task.description}</div>}
                                <div className={styles.taskMeta}>
                                  <span className={`${styles.statusBadge} ${
                                    task.status === "completed" ? styles.statusCompleted :
                                    task.status === "in_progress" ? styles.statusInProgress : styles.statusPending
                                  }`}>
                                    {task.status === "in_progress" ? "⏳ In Progress" :
                                     task.status === "completed"   ? "✓ Done"         : "Pending"}
                                  </span>
                                  <span className={`${styles.priorityBadge} ${
                                    task.priority === "high" ? styles.priorityHigh :
                                    task.priority === "low"  ? styles.priorityLow  : styles.priorityMedium
                                  }`}>
                                    {task.priority.charAt(0).toUpperCase() + task.priority.slice(1)}
                                  </span>
                                  {task.expected_completion_time && task.status !== "completed" && (
                                    <span className={styles.taskExpected}>⏱ {task.expected_completion_time}</span>
                                  )}
                                </div>
                                {/* Completion info strip */}
                                {(() => {
                                  const info = completionInfo(task);
                                  if (!info) return null;
                                  return (
                                    <div className={styles.completionStrip}>
                                      <span>✓ Completed at {info.completedAt}</span>
                                      <span className={styles.completionDot}>·</span>
                                      <span>Took {info.taken}</span>
                                      {info.expected && (<>
                                        <span className={styles.completionDot}>·</span>
                                        <span>Expected: {info.expected}</span>
                                        <span className={styles.completionDot}>·</span>
                                        <span className={info.early ? styles.completionEarly : styles.completionLate}>
                                          {info.early ? "✓ Within time" : "⏰ Overtime"}
                                        </span>
                                      </>)}
                                    </div>
                                  );
                                })()}
                              </div>
                            </div>
                            <div className={styles.taskActions}>
                              {task.status === "pending" && isToday && (
                                <button className={`${styles.actionBtn} ${styles.btnStart}`}
                                  disabled={updatingId === task.id}
                                  onClick={() => changeStatus(task.id, "in_progress")}>
                                  {updatingId === task.id ? "..." : "Start"}
                                </button>
                              )}
                              {task.status === "in_progress" && isToday && (
                                <button className={`${styles.actionBtn} ${styles.btnComplete}`}
                                  disabled={updatingId === task.id}
                                  onClick={() => changeStatus(task.id, "completed")}>
                                  {updatingId === task.id ? "..." : "✓ Done"}
                                </button>
                              )}
                              {isToday && !isCompleted && (
                                <button className={`${styles.actionBtn} ${styles.btnEdit}`} onClick={() => startEdit(task)} title="Edit">✎</button>
                              )}
                              {isToday && (
                                <button className={`${styles.actionBtn} ${styles.btnDelete}`} onClick={() => deleteTask(task.id)} title="Delete">✕</button>
                              )}
                            </div>
                          </div>
                        </>
                      )}
                    </div>

                    {/* Notes toggle */}
                    <div className={styles.notesToggle} onClick={() => setExpandedNotes(n => ({ ...n, [task.id]: !n[task.id] }))}>
                      <span>{notesOpen ? "▲" : "▼"}</span>
                      <span>{task.notes.length} note{task.notes.length !== 1 ? "s" : ""}</span>
                    </div>

                    {/* Notes section */}
                    {notesOpen && (
                      <div className={styles.notesSection}>
                        {task.notes.length === 0 && (
                          <div style={{ fontSize: 12, color: "rgba(255,255,255,0.25)", marginBottom: 10 }}>No notes yet.</div>
                        )}
                        {task.notes.map(n => (
                          <div key={n.id} className={styles.noteItem}>
                            <div className={styles.noteDot} />
                            <div>
                              <div className={styles.noteText}>{n.note}</div>
                              <div className={styles.noteTime}>{new Date(n.created_at).toLocaleString()}</div>
                            </div>
                          </div>
                        ))}
                        {isToday && (
                          <div className={styles.addNoteForm}>
                            <input
                              className={styles.noteInput}
                              placeholder="Add a progress note…"
                              value={noteInputs[task.id] || ""}
                              onChange={e => setNoteInputs(n => ({ ...n, [task.id]: e.target.value }))}
                              onKeyDown={e => { if (e.key === "Enter") addNote(task.id); }}
                            />
                            <button className={styles.btnNote} onClick={() => addNote(task.id)}>Add Note</button>
                          </div>
                        )}
                      </div>
                    )}
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
