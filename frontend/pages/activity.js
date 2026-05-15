// ============================================================
// pages/activity.js — App & Window Activity Page
// ============================================================
// Shows which applications and websites the user spent time on.
// Data comes from POST /api/applogs/batch (sent by desktop app)
// and is displayed via GET /api/applogs/{userId} and /summary.

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import Link from "next/link";
import styles from "../styles/Activity.module.css";
import API from "../config";

// ── Mini calendar (same design as Screenshots page) ──────────
function MiniCalendar({ activeDates, selectedDate, onSelect }) {
  const [viewYear, setViewYear]   = useState(() => new Date().getFullYear());
  const [viewMonth, setViewMonth] = useState(() => new Date().getMonth());

  const daysInMonth  = new Date(viewYear, viewMonth + 1, 0).getDate();
  const firstWeekday = new Date(viewYear, viewMonth, 1).getDay();
  const monthLabel   = new Date(viewYear, viewMonth).toLocaleDateString([], { month: "long", year: "numeric" });

  function prevMonth() {
    if (viewMonth === 0) { setViewYear(y => y - 1); setViewMonth(11); }
    else setViewMonth(m => m - 1);
  }
  function nextMonth() {
    if (viewMonth === 11) { setViewYear(y => y + 1); setViewMonth(0); }
    else setViewMonth(m => m + 1);
  }

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
        {["Su","Mo","Tu","We","Th","Fr","Sa"].map(d => (
          <span key={d} className={styles.calDayName}>{d}</span>
        ))}
        {cells.map((d, i) => {
          if (!d) return <span key={`e${i}`} />;
          const ds = `${viewYear}-${String(viewMonth+1).padStart(2,"0")}-${String(d).padStart(2,"0")}`;
          const isActive   = activeDates.has(ds);
          const isSelected = selectedDate === ds;
          return (
            <button
              key={ds}
              className={`${styles.calDay} ${isActive ? styles.calDayActive : ""} ${isSelected ? styles.calDaySelected : ""}`}
              onClick={() => isActive && onSelect(ds)}
              disabled={!isActive}
            >{d}</button>
          );
        })}
      </div>
    </div>
  );
}

export default function ActivityPage() {
  const router  = useRouter();
  const calRef  = useRef(null);

  const todayStr = () => new Date().toLocaleDateString("en-CA");

  const [user, setUser]             = useState(null);
  const [logs, setLogs]             = useState([]);
  const [summary, setSummary]       = useState([]);
  const [loading, setLoading]       = useState(true);
  const [dateFilter, setDateFilter] = useState(todayStr);
  const [calOpen, setCalOpen]       = useState(false);
  const [activeDates, setActiveDates] = useState(new Set());

  // Close calendar when clicking outside
  useEffect(() => {
    function handleOutside(e) {
      if (calRef.current && !calRef.current.contains(e.target)) setCalOpen(false);
    }
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem("user");
    if (!stored) { router.push("/"); return; }
    const u = JSON.parse(stored);
    setUser(u);
    fetchAll(u.user_id, dateFilter);
    fetchActiveDates(u.user_id);

    const iv = setInterval(() => fetchAll(u.user_id, dateFilter), 15000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    if (!user) return;
    fetchAll(user.user_id, dateFilter);
  }, [dateFilter]);

  // Fetch all logs (no date filter) just to know which dates have data
  async function fetchActiveDates(userId) {
    try {
      const res = await fetch(`${API}/api/applogs/${userId}`);
      if (!res.ok) return;
      const data = await res.json();
      const dates = new Set(
        (data.logs || []).map(l => {
          const d = new Date(l.start_time);
          return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
        })
      );
      setActiveDates(dates);
    } catch {}
  }

  async function fetchAll(userId, date) {
    const d = date || dateFilter;
    try {
      const [logsRes, sumRes] = await Promise.all([
        fetch(`${API}/api/applogs/${userId}?date=${d}`),
        fetch(`${API}/api/applogs/${userId}/summary?date=${d}`),
      ]);
      if (logsRes.ok) {
        const j = await logsRes.json();
        setLogs(j.logs || []);
      }
      if (sumRes.ok) {
        const j = await sumRes.json();
        setSummary(j.entries || []);
      }
    } catch (err) {
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem("user");
    router.push("/");
  }

  function fmtSec(s) {
    if (!s) return "0s";
    if (s < 60) return `${s}s`;
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${sec}s`;
    return `${sec}s`;
  }

  function fmtTime(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  function fmtDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString([], { month: "short", day: "numeric" });
  }

  // Format seconds as HH:MM:SS for top-apps table
  function fmtHHMM(s) {
    if (!s) return "0:00:00";
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  }

  // App icon emoji mapping
  function appIcon(name) {
    const n = (name || "").toLowerCase();
    if (n.includes("chrome"))   return "🌐";
    if (n.includes("edge"))     return "🌐";
    if (n.includes("brave"))    return "🦁";
    if (n.includes("firefox"))  return "🦊";
    if (n.includes("vs code") || n.includes("code")) return "💻";
    if (n.includes("excel"))    return "📊";
    if (n.includes("word"))     return "📝";
    if (n.includes("powerpoint")) return "📋";
    if (n.includes("teams"))    return "💬";
    if (n.includes("slack"))    return "💬";
    if (n.includes("zoom"))     return "📹";
    if (n.includes("terminal") || n.includes("powershell") || n.includes("cmd")) return "⬛";
    if (n.includes("python"))   return "🐍";
    if (n.includes("outlook"))  return "📧";
    if (n.includes("explorer")) return "📁";
    return "🖥";
  }

  // Color for bar based on rank
  const barColors = ["#4A9EFF", "#A78BFA", "#34D399", "#F59E0B", "#F87171"];

  const topTotal = summary[0]?.total_sec || 1;

  if (!user) return null;

  return (
    <>
      <Head><title>Realisieren Pulse — Activity</title></Head>
      <div className={styles.page}>

        {/* ── Sidebar ─────────────────────────────────── */}
        <aside className={styles.sidebar}>
          <div className={styles.logo}>
            <img src="/app_icon.png" alt="Realisieren Pulse" className={styles.logoImg} />
            <div className={styles.logoTextWrap}>
              <span className={styles.logoText}>Realisieren</span>
              <span className={styles.logoText}>Pulse</span>
            </div>
          </div>

          <nav className={styles.nav}>
            <Link className={styles.navItem} href="/dashboard">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg>
              Dashboard
            </Link>
            <Link className={styles.navItem} href="/screenshots">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
              Screenshots
            </Link>
            <Link className={`${styles.navItem} ${styles.active}`} href="/activity">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
              Activity
            </Link>
            <Link className={styles.navItem} href="/tasks">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
              My Tasks
            </Link>
            <Link className={styles.navItem} href="/profile">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              Profile
            </Link>
          </nav>

          <div className={styles.sidebarFooter}>
            <div className={styles.userBadge}>
              <div className={styles.avatar}>
                {user.username?.charAt(0).toUpperCase()}
              </div>
              <div>
                <div className={styles.userName}>{user.username}</div>
                <div className={styles.userEmail}>{user.email}</div>
              </div>
            </div>
            <button onClick={logout} className={styles.logoutBtn}>Logout</button>
          </div>
        </aside>

        {/* ── Main ────────────────────────────────────── */}
        <main className={styles.main}>
          <div className={styles.topBar}>
            <div>
              <h1 className={styles.pageTitle}>App Activity</h1>
              <p className={styles.pageSubtitle}>Which apps and websites you used today</p>
            </div>
            <div className={styles.topBarRight}>
              <div className={styles.calWrap} ref={calRef}>
                <button
                  className={styles.calToggleBtn}
                  onClick={() => setCalOpen(o => !o)}
                >
                  📅 {dateFilter === todayStr() ? "Today" : dateFilter}
                </button>
                {calOpen && (
                  <MiniCalendar
                    activeDates={activeDates}
                    selectedDate={dateFilter}
                    onSelect={ds => { setDateFilter(ds); setCalOpen(false); }}
                  />
                )}
              </div>
              <div className={styles.statusPill}>
                <span className={styles.statusDot} />
                Live
              </div>
            </div>
          </div>

          {loading ? (
            <div className={styles.loading}>Loading activity data…</div>
          ) : (
            <>
              {/* ── Top Apps summary ──────────────────── */}
              {summary.length > 0 && (
                <div className={styles.section} style={{ marginBottom: 24 }}>
                  <div className={styles.sectionHeader}>
                    <h2 className={styles.sectionTitle}>Today&apos;s Top Apps</h2>
                    <span className={styles.badge}>{summary.length} apps</span>
                  </div>

                  <table className={styles.appsTable}>
                    <thead>
                      <tr>
                        <th>App or Website</th>
                        <th>Time spent</th>
                        <th>Percent used</th>
                      </tr>
                    </thead>
                    <tbody>
                      {summary.slice(0, 5).map((entry, i) => {
                        const pct = Math.round((entry.total_sec / topTotal) * 100);
                        return (
                          <tr key={i}>
                            <td>
                              <div className={styles.appsTableApp}>
                                <span className={styles.appsTableIcon}>{appIcon(entry.app_name)}</span>
                                <span className={styles.appsTableName}>{entry.app_name}</span>
                              </div>
                            </td>
                            <td className={styles.appsTableTime}>{fmtHHMM(entry.total_sec)}</td>
                            <td>
                              <div className={styles.appsTablePctCell}>
                                <span className={styles.appsTablePct}>{pct}%</span>
                                <div className={styles.appsTableBar}>
                                  <div
                                    className={styles.appsTableBarFill}
                                    style={{ width: `${pct}%` }}
                                  />
                                </div>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* ── Activity log table ────────────────── */}
              <div className={styles.section}>
                <div className={styles.sectionHeader}>
                  <h2 className={styles.sectionTitle}>Session Log</h2>
                  <span className={styles.badge}>{logs.length} records</span>
                </div>

                {logs.length === 0 ? (
                  <div className={styles.empty}>
                    <span className={styles.emptyIcon}>🖥</span>
                    <p>No app activity yet.<br />Open the desktop app, log in, and start working — sessions appear here automatically.</p>
                  </div>
                ) : (
                  <div className={styles.tableWrap}>
                    <table className={styles.table}>
                      <thead>
                        <tr>
                          <th>App</th>
                          <th>Window Title</th>
                          <th>URL</th>
                          <th>Date</th>
                          <th>Start</th>
                          <th>End</th>
                          <th>Duration</th>
                        </tr>
                      </thead>
                      <tbody>
                        {logs.map((row) => (
                          <tr key={row.id}>
                            <td>
                              <div className={styles.appCell}>
                                <span>{appIcon(row.app_name)}</span>
                                <span className={styles.appCellName}>{row.app_name}</span>
                              </div>
                            </td>
                            <td className={styles.titleCell} title={row.window_title}>
                              {row.window_title ? row.window_title.slice(0, 48) + (row.window_title.length > 48 ? "…" : "") : "—"}
                            </td>
                            <td className={styles.urlCell}>
                              {row.url ? (
                                <a
                                  href={row.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className={styles.urlLink}
                                  title={row.url}
                                >
                                  {row.url.replace(/^https?:\/\//, "").slice(0, 36) + (row.url.length > 36 ? "…" : "")}
                                </a>
                              ) : "—"}
                            </td>
                            <td className={styles.timeCell}>{fmtDate(row.start_time)}</td>
                            <td className={styles.timeCell}>{fmtTime(row.start_time)}</td>
                            <td className={styles.timeCell}>{fmtTime(row.end_time)}</td>
                            <td>
                              <span className={styles.durBadge}>{fmtSec(row.duration_sec)}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </main>
      </div>
    </>
  );
}
