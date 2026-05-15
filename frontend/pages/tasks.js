// pages/tasks.js — Daily Task Management
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import Link from "next/link";
import styles from "../styles/Tasks.module.css";
import API from "../config";

const PRIORITY = {
  high:   { label: "High",   color: "#DC2626", bg: "#FEE2E2" },
  medium: { label: "Medium", color: "#D97706", bg: "#FEF9C3" },
  low:    { label: "Low",    color: "#16A34A", bg: "#DCFCE7" },
};

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
          const isSelected = selectedDate === ds;
          return (
            <button key={ds}
              className={`${styles.calDay} ${styles.calDayActive} ${isSelected ? styles.calDaySelected : ""}`}
              onClick={() => onSelect(ds)}>
              {d}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function TasksPage() {
  const router   = useRouter();
  const calRef   = useRef(null);
  const todayStr = () => new Date().toLocaleDateString("en-CA");

  const [user,        setUser]        = useState(null);
  const [tasks,       setTasks]       = useState([]);
  const [summary,     setSummary]     = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [dateFilter,  setDateFilter]  = useState(todayStr);
  const [calOpen,     setCalOpen]     = useState(false);
  const [showForm,    setShowForm]    = useState(false);
  const [submitting,  setSubmitting]  = useState(false);
  const [createError, setCreateError] = useState("");
  const [form,        setForm]        = useState({ title: "", priority: "medium" });
  const [editingId,   setEditingId]   = useState(null);
  const [editForm,    setEditForm]    = useState({ title: "", priority: "medium" });
  const [updatingId,  setUpdatingId]  = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter,setStatusFilter]= useState("all");
  const [viewMode,    setViewMode]    = useState("kanban");
  const [statusError, setStatusError] = useState("");
  const [fetchError,  setFetchError]  = useState("");

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
    setLoading(true); setFetchError("");
    try {
      const [tasksRes, sumRes] = await Promise.all([
        fetch(`${API}/api/tasks/${userId}?date=${date}`),
        fetch(`${API}/api/tasks/${userId}/summary?date=${date}`),
      ]);
      if (tasksRes.ok) {
        setTasks((await tasksRes.json()).tasks || []);
      } else if (tasksRes.status === 404) {
        setTasks([]);
      } else {
        setFetchError(`Server error ${tasksRes.status}. Please try again or sign out and back in.`);
      }
      if (sumRes.ok) setSummary(await sumRes.json());
    } catch { setFetchError("Cannot connect to server. Make sure the backend is reachable."); }
    finally { setLoading(false); }
  }

  function logout() { localStorage.removeItem("user"); router.push("/"); }

  async function handleCreate(e) {
    e.preventDefault();
    if (!form.title.trim()) return;
    setSubmitting(true); setCreateError("");
    try {
      const res = await fetch(`${API}/api/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.user_id, title: form.title.trim(), priority: form.priority }),
      });
      const data = await res.json();
      if (res.ok && data.success) { setForm({ title: "", priority: "medium" }); setShowForm(false); fetchAll(user.user_id, dateFilter); }
      else setCreateError(data.detail || "Failed to add task.");
    } catch { setCreateError("Cannot connect to server."); }
    finally { setSubmitting(false); }
  }

  async function changeStatus(taskId, status) {
    setUpdatingId(taskId); setStatusError("");
    try {
      const res = await fetch(`${API}/api/tasks/${taskId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.user_id, status }),
      });
      if (res.ok) await fetchAll(user.user_id, dateFilter);
      else { const d = await res.json(); setStatusError(d.detail || "Status update failed."); }
    } catch { setStatusError("Cannot connect to server."); }
    finally { setUpdatingId(null); }
  }

  async function deleteTask(taskId) {
    if (!confirm("Delete this task?")) return;
    try { await fetch(`${API}/api/tasks/${taskId}?user_id=${user.user_id}`, { method: "DELETE" }); fetchAll(user.user_id, dateFilter); } catch {}
  }

  function startEdit(task) {
    setEditingId(task.id);
    setEditForm({ title: task.title, priority: task.priority || "medium" });
  }

  async function saveEdit(taskId) {
    if (!editForm.title.trim()) return;
    try {
      await fetch(`${API}/api/tasks/${taskId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.user_id, title: editForm.title.trim(), priority: editForm.priority }),
      });
      setEditingId(null);
      fetchAll(user.user_id, dateFilter);
    } catch {}
  }

  if (!user) return null;

  const isToday   = dateFilter === todayStr();
  const greetHour = new Date().getHours();
  const greet     = greetHour < 12 ? "Good morning" : greetHour < 17 ? "Good afternoon" : "Good evening";

  const filteredTasks = tasks.filter(t => {
    const matchSearch = !searchQuery || t.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchStatus = statusFilter === "all" || t.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const kanbanCols = [
    { key: "pending",     label: "Pending",     color: "#64748B" },
    { key: "in_progress", label: "In Progress", color: "#4F63D2" },
    { key: "completed",   label: "Completed",   color: "#16A34A" },
  ];

  return (
    <>
      <Head><title>Realisieren Pulse — My Tasks</title></Head>
      <div className={styles.page}>

        {/* ── Sidebar ── */}
        <aside className={styles.sidebar}>
          <div className={styles.logo}>
            <img src="/app_icon.png" alt="Realisieren Pulse" className={styles.logoImg} />
            <div className={styles.logoTextWrap}>
              <span className={styles.logoText}>Realisieren</span>
              <span className={styles.logoText}>Pulse</span>
            </div>
          </div>
          <nav className={styles.nav}>
            <Link className={styles.navItem} href="/dashboard"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg> Dashboard</Link>
            <Link className={styles.navItem} href="/screenshots"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg> Screenshots</Link>
            <Link className={styles.navItem} href="/activity"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg> Activity</Link>
            <Link className={`${styles.navItem} ${styles.active}`} href="/tasks"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg> My Tasks</Link>
            <Link className={styles.navItem} href="/profile"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg> Profile</Link>
            {user.user_type === "admin" && (
              <>
                <Link className={styles.navItem} href="/admin"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> Admin Portal</Link>
                <Link className={styles.navItem} href="/admin-tasks"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg> Task Overview</Link>
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

        {/* ── Main ── */}
        <main className={styles.main}>

          {/* Welcome banner */}
          <div className={styles.welcomeBanner}>
            <div>
              <h1 className={styles.welcomeGreet}>{greet}, {user.username?.split(" ")[0]} 👋</h1>
              <p className={styles.welcomeSub}>
                {isToday
                  ? <>You have <strong>{summary?.total ?? "…"}</strong> tasks today · <strong>{summary?.pending ?? 0}</strong> pending · <strong>{summary?.completed ?? 0}</strong> done</>
                  : <>Viewing tasks for <strong>{dateFilter}</strong></>}
              </p>
            </div>
            <div className={styles.welcomeRight}>
              <div className={styles.calWrap} ref={calRef}>
                <button className={styles.calToggleBtn} onClick={() => setCalOpen(o => !o)}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                  {isToday ? "Today" : dateFilter}
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
                <button className={styles.addTaskBtn} onClick={() => { setShowForm(v => !v); setCreateError(""); }}>
                  {showForm ? "✕ Cancel" : "+ Add Task"}
                </button>
              )}
            </div>
          </div>

          {/* KPI strip */}
          {summary && (
            <div className={styles.kpiStrip}>
              <div className={styles.kpiCard}>
                <div className={styles.kpiIcon} style={{ background: "#F1F5F9", color: "#475569" }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                </div>
                <div><div className={styles.kpiNum}>{summary.total}</div><div className={styles.kpiLbl}>Total Tasks</div></div>
              </div>
              <div className={styles.kpiCard}>
                <div className={styles.kpiIcon} style={{ background: "#FEF9C3", color: "#D97706" }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                </div>
                <div><div className={styles.kpiNum} style={{ color: "#D97706" }}>{summary.pending}</div><div className={styles.kpiLbl}>Pending</div></div>
              </div>
              <div className={styles.kpiCard}>
                <div className={styles.kpiIcon} style={{ background: "#EEF2FF", color: "#4F63D2" }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                </div>
                <div><div className={styles.kpiNum} style={{ color: "#4F63D2" }}>{summary.in_progress}</div><div className={styles.kpiLbl}>In Progress</div></div>
              </div>
              <div className={styles.kpiCard}>
                <div className={styles.kpiIcon} style={{ background: "#DCFCE7", color: "#16A34A" }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"/></svg>
                </div>
                <div><div className={styles.kpiNum} style={{ color: "#16A34A" }}>{summary.completed}</div><div className={styles.kpiLbl}>Completed</div></div>
              </div>
            </div>
          )}

          {/* Create form */}
          {showForm && (
            <div className={styles.formPanel}>
              <div className={styles.formTitle} style={{ marginBottom: 14 }}>New Task</div>
              <form onSubmit={handleCreate} className={styles.createForm}>
                <div className={styles.createFormTop}>
                  <input
                    className={styles.formInput}
                    placeholder="What do you need to do today?"
                    value={form.title}
                    onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                    autoFocus required disabled={submitting}
                  />
                  <select
                    className={`${styles.formInput} ${styles.prioritySelect}`}
                    value={form.priority}
                    onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}
                    disabled={submitting}
                  >
                    <option value="high">🔴 High</option>
                    <option value="medium">🟡 Medium</option>
                    <option value="low">🟢 Low</option>
                  </select>
                </div>
                {createError && <div className={styles.errorInline}>⚠ {createError}</div>}
                <div className={styles.formActions}>
                  <button type="submit" className={styles.btnPrimary} disabled={submitting}>{submitting ? "Adding…" : "Add Task"}</button>
                  <button type="button" className={styles.btnCancel} onClick={() => { setShowForm(false); setCreateError(""); }}>Cancel</button>
                </div>
              </form>
            </div>
          )}

          {statusError && <div className={styles.alertError}>⚠ {statusError}</div>}
          {fetchError  && <div className={styles.alertError}>⚠ {fetchError}</div>}

          {/* Filter + search + view toggle */}
          <div className={styles.filterBar}>
            <div className={styles.searchWrap} style={{ flex: 1, minWidth: 160, maxWidth: 320 }}>
              <svg className={styles.searchIcon} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input
                className={styles.searchInput}
                placeholder="Search tasks..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
            </div>
            <div className={styles.filterTabs}>
              {[["all","All"],["pending","Pending"],["in_progress","In Progress"],["completed","Done"]].map(([k,l]) => (
                <button key={k}
                  className={`${styles.filterTab} ${statusFilter === k ? styles.filterTabActive : ""}`}
                  onClick={() => setStatusFilter(k)}>
                  {l}
                </button>
              ))}
            </div>
            <div className={styles.viewToggle}>
              <button className={`${styles.viewBtn} ${viewMode === "list" ? styles.viewBtnActive : ""}`} onClick={() => setViewMode("list")} title="List view">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
              </button>
              <button className={`${styles.viewBtn} ${viewMode === "kanban" ? styles.viewBtnActive : ""}`} onClick={() => setViewMode("kanban")} title="Kanban view">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
              </button>
            </div>
          </div>

          {/* Task content */}
          {loading ? (
            <div className={styles.emptyState}><div>Loading tasks…</div></div>
          ) : filteredTasks.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>{searchQuery ? "🔍" : "✅"}</div>
              <div>{searchQuery ? `No tasks matching "${searchQuery}"` : isToday ? 'No tasks yet. Click "+ Add Task" to plan your day.' : "No tasks for this date."}</div>
            </div>
          ) : viewMode === "kanban" ? (
            <div className={styles.kanbanBoard}>
              {kanbanCols.map(col => {
                const colTasks = filteredTasks.filter(t => t.status === col.key);
                return (
                  <div key={col.key} className={styles.kanbanCol}>
                    <div className={styles.kanbanColHeader} style={{ borderTopColor: col.color }}>
                      <span className={styles.kanbanColLabel} style={{ color: col.color }}>{col.label}</span>
                      <span className={styles.kanbanColCount}>{colTasks.length}</span>
                    </div>
                    <div className={styles.kanbanCards}>
                      {colTasks.length === 0
                        ? <div className={styles.kanbanEmpty}>No tasks here</div>
                        : colTasks.map(task => (
                          <TaskCard key={task.id} task={task}
                            isToday={isToday} updatingId={updatingId}
                            editingId={editingId} editForm={editForm} setEditForm={setEditForm}
                            changeStatus={changeStatus} startEdit={startEdit} saveEdit={saveEdit}
                            cancelEdit={() => setEditingId(null)} deleteTask={deleteTask}
                          />
                        ))}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className={styles.taskList}>
              {filteredTasks.map(task => (
                <TaskCard key={task.id} task={task}
                  isToday={isToday} updatingId={updatingId}
                  editingId={editingId} editForm={editForm} setEditForm={setEditForm}
                  changeStatus={changeStatus} startEdit={startEdit} saveEdit={saveEdit}
                  cancelEdit={() => setEditingId(null)} deleteTask={deleteTask}
                />
              ))}
            </div>
          )}
        </main>
      </div>
    </>
  );
}

function TaskCard({ task, isToday, updatingId, editingId, editForm, setEditForm, changeStatus, startEdit, saveEdit, cancelEdit, deleteTask }) {
  const isEditing   = editingId === task.id;
  const isCompleted = task.status === "completed";
  const pc = PRIORITY[task.priority || "medium"];

  return (
    <div className={`${styles.tCard} ${isCompleted ? styles.tCardDone : ""}`}>
      {isEditing ? (
        <div className={styles.editInlineForm}>
          <div className={styles.createFormTop}>
            <input
              className={styles.formInput}
              value={editForm.title}
              onChange={e => setEditForm(f => ({ ...f, title: e.target.value }))}
              onKeyDown={e => { if (e.key === "Enter") saveEdit(task.id); if (e.key === "Escape") cancelEdit(); }}
              autoFocus placeholder="Task title"
            />
            <select
              className={`${styles.formInput} ${styles.prioritySelect}`}
              value={editForm.priority}
              onChange={e => setEditForm(f => ({ ...f, priority: e.target.value }))}
            >
              <option value="high">🔴 High</option>
              <option value="medium">🟡 Medium</option>
              <option value="low">🟢 Low</option>
            </select>
          </div>
          <div className={styles.formActions} style={{ marginTop: 8 }}>
            <button className={styles.btnPrimary} onClick={() => saveEdit(task.id)}>Save</button>
            <button className={styles.btnCancel} onClick={cancelEdit}>Cancel</button>
          </div>
        </div>
      ) : (
        <div className={styles.tCardMain}>
          <div className={styles.tPriorityStripe} style={{ background: pc.color }} />
          <div className={styles.tCardBody}>
            <div className={styles.tTitleRow}>
              <span className={styles.taskTitle}>{task.title}</span>
              <span className={styles.tPriorityBadge} style={{ background: pc.bg, color: pc.color }}>{pc.label}</span>
            </div>
            <div className={styles.taskMeta}>
              <span className={`${styles.statusBadge} ${task.status === "completed" ? styles.statusCompleted : task.status === "in_progress" ? styles.statusInProgress : styles.statusPending}`}>
                {task.status === "in_progress" ? "In Progress" : task.status === "completed" ? "✓ Done" : "Pending"}
              </span>
              {task.completed_at && (
                <span className={styles.taskExpected}>Done at {new Date(task.completed_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
              )}
            </div>
          </div>
          <div className={styles.taskActions}>
            {task.status === "pending" && isToday && (
              <button className={`${styles.actionBtn} ${styles.btnStart}`} disabled={updatingId === task.id} onClick={() => changeStatus(task.id, "in_progress")}>
                {updatingId === task.id ? "…" : "▶ Start"}
              </button>
            )}
            {task.status === "in_progress" && isToday && (
              <button className={`${styles.actionBtn} ${styles.btnComplete}`} disabled={updatingId === task.id} onClick={() => changeStatus(task.id, "completed")}>
                {updatingId === task.id ? "…" : "✓ Done"}
              </button>
            )}
            {isToday && !isCompleted && (
              <button className={`${styles.actionBtn} ${styles.btnEdit}`} onClick={() => startEdit(task)} title="Edit">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </button>
            )}
            {isToday && (
              <button className={`${styles.actionBtn} ${styles.btnDelete}`} onClick={() => deleteTask(task.id)} title="Delete">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
