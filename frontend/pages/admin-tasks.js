// pages/admin-tasks.js — Admin Task Overview
import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import Link from "next/link";
import styles from "../styles/AdminTasks.module.css";
import API from "../config";

export default function AdminTasksPage() {
  const router = useRouter();

  const todayStr = () => new Date().toLocaleDateString("en-CA");

  const [user,       setUser]       = useState(null);
  const [tasks,      setTasks]      = useState([]);
  const [stats,      setStats]      = useState(null);
  const [users,      setUsers]      = useState([]);
  const [loading,    setLoading]    = useState(true);

  // Filters
  const [dateFilter,    setDateFilter]    = useState(todayStr);
  const [userFilter,    setUserFilter]    = useState("");
  const [statusFilter,  setStatusFilter]  = useState("");
  const [projectFilter, setProjectFilter] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem("user");
    if (!stored) { router.push("/"); return; }
    const u = JSON.parse(stored);
    if (u.user_type !== "admin") { router.push("/dashboard"); return; }
    setUser(u);
    fetchUsers(u.user_id);
    // Pre-fill user filter from query param
    if (router.query.user_id) setUserFilter(String(router.query.user_id));
  }, []);

  useEffect(() => {
    if (!user) return;
    fetchData(user.user_id);
  }, [user, dateFilter, userFilter, statusFilter, projectFilter]);

  async function fetchUsers(adminId) {
    try {
      const res = await fetch(`${API}/api/admin/users?admin_id=${adminId}`);
      if (res.ok) setUsers((await res.json()).users || []);
    } catch (_) {}
  }

  async function fetchData(adminId) {
    setLoading(true);
    try {
      const params = new URLSearchParams({ admin_id: adminId, date: dateFilter });
      if (userFilter)    params.set("user_id", userFilter);
      if (statusFilter)  params.set("status", statusFilter);
      if (projectFilter) params.set("project", projectFilter);

      const [tasksRes, statsRes] = await Promise.all([
        fetch(`${API}/api/admin/tasks?${params}`),
        fetch(`${API}/api/admin/tasks/stats?${params}`),
      ]);
      if (tasksRes.ok) setTasks((await tasksRes.json()).tasks || []);
      if (statsRes.ok) setStats(await statsRes.json());
    } catch (_) {}
    finally { setLoading(false); }
  }

  function logout() { localStorage.removeItem("user"); router.push("/"); }

  function clearFilters() {
    setDateFilter(todayStr());
    setUserFilter("");
    setStatusFilter("");
    setProjectFilter("");
  }

  function fmtTime(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function fmtDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString([], { month: "short", day: "numeric" });
  }

  if (!user) return null;

  const isFiltered = userFilter || statusFilter || projectFilter || dateFilter !== todayStr();

  return (
    <>
      <Head><title>Realisieren Pulse — Task Overview</title></Head>
      <div className={styles.page}>

        {/* Sidebar */}
        <aside className={styles.sidebar}>
          <div className={styles.logo}>
            <img src="/app_icon.png" alt="Realisieren Pulse" className={styles.logoImg} />
            <span className={styles.logoText}>Realisieren Pulse</span>
          </div>
          <nav className={styles.nav}>
            <Link className={styles.navItem} href="/dashboard"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg> Dashboard</Link>
            <Link className={styles.navItem} href="/screenshots"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg> Screenshots</Link>
            <Link className={styles.navItem} href="/activity"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg> Activity</Link>
            <Link className={styles.navItem} href="/tasks"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg> My Tasks</Link>
            <Link className={styles.navItem} href="/profile"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg> Profile</Link>
            <Link className={styles.navItem} href="/admin"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> Admin Portal</Link>
            <Link className={`${styles.navItem} ${styles.active}`} href="/admin-tasks"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg> Task Overview</Link>
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

        {/* Main */}
        <main className={styles.main}>
          <div className={styles.topBar}>
            <div>
              <h1 className={styles.pageTitle}>Task Overview</h1>
              <p className={styles.pageSubtitle}>Monitor team task progress and productivity</p>
            </div>
          </div>

          {/* Stats strip */}
          {stats && (
            <div className={styles.statsStrip}>
              <div className={styles.statCard}>
                <div className={styles.statLabel}>Total Tasks</div>
                <div className={styles.statValue} style={{ color: "#e2e8f0" }}>{stats.total_tasks}</div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statLabel}>Completed</div>
                <div className={styles.statValue} style={{ color: "#34D399" }}>{stats.completed}</div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statLabel}>In Progress</div>
                <div className={styles.statValue} style={{ color: "#4A9EFF" }}>{stats.in_progress}</div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statLabel}>Pending</div>
                <div className={styles.statValue} style={{ color: "rgba(255,255,255,0.5)" }}>{stats.pending}</div>
              </div>
              <div className={styles.statCard}>
                <div className={styles.statLabel}>Completion</div>
                <div className={styles.statValue} style={{ color: stats.completion_pct >= 70 ? "#34D399" : stats.completion_pct >= 40 ? "#F59E0B" : "#F87171" }}>
                  {stats.completion_pct.toFixed(0)}%
                </div>
              </div>
            </div>
          )}

          {/* Filters */}
          <div className={styles.filtersBar}>
            <span className={styles.filterLabel}>Date:</span>
            <input type="date" className={styles.filterInput}
              value={dateFilter} onChange={e => setDateFilter(e.target.value)} />

            <span className={styles.filterLabel}>Employee:</span>
            <select className={styles.filterSelect} value={userFilter} onChange={e => setUserFilter(e.target.value)}>
              <option value="">All employees</option>
              {users.map(u => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
            </select>

            <span className={styles.filterLabel}>Status:</span>
            <select className={styles.filterSelect} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
              <option value="">All statuses</option>
              <option value="pending">Pending</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
            </select>

            <span className={styles.filterLabel}>Project:</span>
            <select className={styles.filterSelect} value={projectFilter} onChange={e => setProjectFilter(e.target.value)}>
              <option value="">All projects</option>
              <option value="Bold">Bold</option>
              <option value="MView">MView</option>
            </select>

            {isFiltered && (
              <button className={styles.btnClear} onClick={clearFilters}>✕ Clear</button>
            )}
          </div>

          {/* Task table */}
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Tasks</h2>
              <span className={styles.badge}>{tasks.length} tasks</span>
            </div>

            {loading ? (
              <div className={styles.loading}>Loading tasks…</div>
            ) : tasks.length === 0 ? (
              <div className={styles.empty}>
                <div className={styles.emptyIcon}>📋</div>
                <div className={styles.emptyText}>No tasks found for the selected filters.</div>
              </div>
            ) : (
              <div className={styles.taskCards}>
                {tasks.map(t => (
                  <div key={t.task_id} className={styles.taskCard}>
                    <div className={styles.taskCardLeft}>
                      <div className={styles.userCell}>
                        <div className={styles.userAvatar}>{t.username?.charAt(0).toUpperCase()}</div>
                        <div>
                          <span className={styles.userName2}>{t.username}</span>
                          {t.project && <span className={styles.projectBadge}>{t.project}</span>}
                        </div>
                      </div>
                      <div className={styles.taskTitle}>{t.title}</div>
                    </div>
                    <div className={styles.taskCardRight}>
                      <span className={`${styles.statusBadge} ${
                        t.status === "completed"   ? styles.statusCompleted  :
                        t.status === "in_progress" ? styles.statusInProgress : styles.statusPending
                      }`}>
                        {t.status === "in_progress" ? "In Progress" :
                         t.status === "completed"   ? "Completed"   : "Pending"}
                      </span>
                      <span className={styles.taskTime}>{fmtTime(t.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Per-employee breakdown */}
          {stats && stats.by_employee && stats.by_employee.length > 0 && (
            <div className={styles.section} style={{ marginTop: 24 }}>
              <div className={styles.sectionHeader}>
                <h2 className={styles.sectionTitle}>Employee Breakdown</h2>
                <span className={styles.badge}>{stats.by_employee.length} employees</span>
              </div>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Employee</th>
                      <th>Project</th>
                      <th>Total</th>
                      <th>Completed</th>
                      <th>In Progress</th>
                      <th>Pending</th>
                      <th>Completion %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.by_employee.map(e => (
                      <tr key={e.user_id}>
                        <td>
                          <div className={styles.userCell}>
                            <div className={styles.userAvatar}>{e.username?.charAt(0).toUpperCase()}</div>
                            <span className={styles.userName2}>{e.username}</span>
                          </div>
                        </td>
                        <td>{e.project && <span className={styles.projectBadge}>{e.project}</span>}</td>
                        <td>{e.total}</td>
                        <td style={{ color: "#34D399" }}>{e.completed}</td>
                        <td style={{ color: "#4A9EFF" }}>{e.in_progress}</td>
                        <td style={{ color: "rgba(255,255,255,0.5)" }}>{e.pending}</td>
                        <td>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <div style={{ flex: 1, height: 4, background: "rgba(255,255,255,0.08)", borderRadius: 2, minWidth: 60 }}>
                              <div style={{ width: `${e.completion_pct}%`, height: "100%", borderRadius: 2, background: e.completion_pct >= 70 ? "#34D399" : e.completion_pct >= 40 ? "#F59E0B" : "#F87171" }} />
                            </div>
                            <span style={{ fontSize: 12, color: e.completion_pct >= 70 ? "#34D399" : e.completion_pct >= 40 ? "#F59E0B" : "#F87171", minWidth: 36 }}>
                              {e.completion_pct.toFixed(0)}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </main>
      </div>
    </>
  );
}
