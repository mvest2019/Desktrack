import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import Link from "next/link";
import {
  PieChart, Pie, Cell, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import styles from "../styles/Dashboard.module.css";
import API from "../config";

const APP_COLORS = ["#4F63D2", "#22C55E", "#F97316", "#7C3AED", "#0EA5E9", "#EF4444"];
const ACTIVITY_COLORS = ["#4F63D2", "#E2E8F0"];
const TASK_COLORS = ["#22C55E", "#4F63D2", "#F97316"];

function appIcon(name = "") {
  const n = name.toLowerCase();
  if (n.includes("chrome") || n.includes("firefox") || n.includes("edge") || n.includes("safari") || n.includes("browser")) return "🌐";
  if (n.includes("code") || n.includes("vscode") || n.includes("visual studio")) return "💻";
  if (n.includes("slack")) return "💬";
  if (n.includes("terminal") || n.includes("cmd") || n.includes("powershell") || n.includes("bash")) return "⌨️";
  if (n.includes("zoom") || n.includes("meet") || n.includes("teams")) return "📹";
  if (n.includes("figma") || n.includes("sketch") || n.includes("xd")) return "🎨";
  if (n.includes("notion") || n.includes("obsidian")) return "📝";
  if (n.includes("excel") || n.includes("sheets")) return "📊";
  if (n.includes("word") || n.includes("docs")) return "📄";
  if (n.includes("spotify") || n.includes("music")) return "🎵";
  if (n.includes("postman") || n.includes("insomnia")) return "🔧";
  if (n.includes("git") || n.includes("github") || n.includes("sourcetree")) return "🌿";
  return "🖥";
}

function fmtSecs(s) {
  if (!s) return "0m";
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export default function Dashboard() {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState({ total_screenshots: 0 });
  const [screenshots, setScreenshots] = useState([]);
  const [selectedImg, setSelectedImg] = useState(null);
  const [activity, setActivity] = useState(null);
  const [taskSummary, setTaskSummary] = useState(null);
  const [appSummary, setAppSummary] = useState([]);

  useEffect(() => {
    setMounted(true);
    const stored = localStorage.getItem("user");
    if (!stored) { router.push("/"); return; }
    const userData = JSON.parse(stored);
    const targetId = router.query.uid ? parseInt(router.query.uid) : userData.user_id;
    if (router.query.uid && userData.user_type !== "admin") { router.push("/dashboard"); return; }
    setUser(userData);
    fetchData(targetId);
    const interval = setInterval(() => fetchData(targetId), 30000);
    return () => clearInterval(interval);
  }, [router.query.uid]);

  async function fetchData(userId) {
    try {
      const [statsRes, screenshotsRes, activityRes, taskSumRes, appSumRes] = await Promise.all([
        fetch(`${API}/api/stats/${userId}`),
        fetch(`${API}/api/screenshots/${userId}?limit=8`),
        fetch(`${API}/api/activity/${userId}?limit=20`),
        fetch(`${API}/api/tasks/${userId}/summary`),
        fetch(`${API}/api/applogs/${userId}/summary`),
      ]);
      if (statsRes.ok) setStats(await statsRes.json());
      if (screenshotsRes.ok) { const d = await screenshotsRes.json(); setScreenshots(d.screenshots || []); }
      if (activityRes.ok) setActivity(await activityRes.json());
      if (taskSumRes.ok) setTaskSummary(await taskSumRes.json());
      if (appSumRes.ok) { const d = await appSumRes.json(); setAppSummary(d.entries || []); }
    } catch {}
  }

  function logout() { localStorage.removeItem("user"); router.push("/"); }

  if (!user) return null;

  const pct = activity?.today_percent ?? 0;
  const activeSec = activity?.today_active_sec ?? 0;
  const idleSec = activity?.today_idle_sec ?? 0;
  const logs = activity?.logs ? [...activity.logs].reverse() : [];
  const { total = 0, pending = 0, in_progress = 0, completed = 0, completion_pct = 0 } = taskSummary || {};

  const hasActivityData = activeSec + idleSec > 0;
  const activityDonut = hasActivityData
    ? [{ name: "Active", value: activeSec }, { name: "Idle", value: idleSec }]
    : [{ name: "No data", value: 1 }];

  const hasTaskData = total > 0;
  const taskDonut = hasTaskData
    ? [{ name: "Done", value: completed }, { name: "Active", value: in_progress }, { name: "Pending", value: pending }].filter(d => d.value > 0)
    : [{ name: "No tasks", value: 1 }];

  const timelineData = logs.map(w => ({
    time: new Date(w.window_start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false }),
    pct: w.activity_percent,
    fill: w.activity_percent >= 70 ? "#22C55E" : w.activity_percent >= 40 ? "#F97316" : "#EF4444",
  }));

  const totalAppSec = appSummary.reduce((s, e) => s + e.total_sec, 0) || 1;
  const topApps = appSummary.slice(0, 6);
  const greetHour = new Date().getHours();
  const greet = greetHour < 12 ? "Good morning" : greetHour < 17 ? "Good afternoon" : "Good evening";

  return (
    <>
      <Head><title>Realisieren Pulse — Dashboard</title></Head>
      <div className={styles.page}>

        {/* ── Sidebar ──────────────────────────────── */}
        <aside className={styles.sidebar}>
          <div className={styles.logo}>
            <img src="/app_icon.png" alt="Realisieren Pulse" className={styles.logoImg} />
            <span className={styles.logoText}>Realisieren Pulse</span>
          </div>
          <nav className={styles.nav}>
            <Link className={`${styles.navItem} ${styles.active}`} href="/dashboard">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg>
              Dashboard
            </Link>
            <Link className={styles.navItem} href="/screenshots">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
              Screenshots
            </Link>
            <Link className={styles.navItem} href="/activity">
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
            {user.user_type === "admin" && (
              <>
                <Link className={styles.navItem} href="/admin">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                  Admin Portal
                </Link>
                <Link className={styles.navItem} href="/admin-tasks">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
                  Task Overview
                </Link>
              </>
            )}
          </nav>
          <div className={styles.sidebarFooter}>
            <div className={styles.userBadge}>
              <div className={styles.avatar}>{user.username?.charAt(0).toUpperCase()}</div>
              <div style={{ minWidth: 0 }}>
                <div className={styles.userName}>{user.username}</div>
                <div className={styles.userEmail}>{user.email}</div>
              </div>
            </div>
            <button onClick={logout} className={styles.logoutBtn}>Logout</button>
          </div>
        </aside>

        {/* ── Main ─────────────────────────────────── */}
        <main className={styles.main}>

          {/* Greeting bar */}
          <div className={styles.topBar}>
            <div>
              <h1 className={styles.pageTitle}>
                {greet}, {user.username?.split(" ")[0]} 👋
              </h1>
              <p className={styles.pageSubtitle}>
                Here&apos;s your productivity overview for today.
              </p>
            </div>
            <div className={styles.topBarRight}>
              <span className={styles.topBarDate}>
                {new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
              </span>
              <div className={styles.statusPill}>
                <span className={styles.statusDot} /> Live Monitoring
              </div>
            </div>
          </div>

          {/* ── KPI row ──────────────────────────────── */}
          <div className={styles.kpiRow}>
            <KPICard
              icon={<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>}
              label="Activity" value={`${pct.toFixed(0)}%`}
              color={pct >= 70 ? "#16A34A" : pct >= 40 ? "#D97706" : "#DC2626"}
              bg={pct >= 70 ? "#DCFCE7" : pct >= 40 ? "#FEF9C3" : "#FEE2E2"}
              sub="of tracked time"
            />
            <KPICard
              icon={<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>}
              label="Active Time" value={fmtSecs(activeSec)}
              color="#4F63D2" bg="#EEF2FF" sub="mouse + keyboard"
            />
            <KPICard
              icon={<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>}
              label="Idle Time" value={fmtSecs(idleSec)}
              color="#7C3AED" bg="#F5F3FF" sub="no input 3+ min"
            />
            <KPICard
              icon={<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>}
              label="Tasks Done" value={`${completed}/${total}`}
              color="#16A34A" bg="#DCFCE7" sub={`${completion_pct.toFixed(0)}% complete`}
            />
            <KPICard
              icon={<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>}
              label="Screenshots" value={stats.total_screenshots}
              color="#0369A1" bg="#E0F2FE" sub="captured total"
            />
          </div>

          {/* ── Charts row 1: Activity Split + Timeline ── */}
          <div className={styles.chartsRow}>

            {/* Activity donut */}
            <div className={styles.chartCard} style={{ width: 280, flexShrink: 0 }}>
              <h3 className={styles.chartTitle}>Activity Split</h3>
              <p className={styles.chartSub}>Active vs Idle today</p>
              {mounted && (
                <div className={styles.donutWrap}>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie
                        data={activityDonut}
                        cx="50%" cy="50%"
                        innerRadius={58} outerRadius={84}
                        paddingAngle={hasActivityData ? 3 : 0}
                        dataKey="value"
                        startAngle={90} endAngle={-270}
                      >
                        {activityDonut.map((_, i) => (
                          <Cell key={i}
                            fill={hasActivityData ? ACTIVITY_COLORS[i % ACTIVITY_COLORS.length] : "#F1F5F9"}
                            strokeWidth={0}
                          />
                        ))}
                      </Pie>
                      {hasActivityData && <Tooltip formatter={v => fmtSecs(v)} contentStyle={{ fontSize: 12, borderRadius: 8 }} />}
                    </PieChart>
                  </ResponsiveContainer>
                  <div className={styles.donutCenter}>
                    <span className={styles.donutBig} style={{ color: pct >= 70 ? "#16A34A" : pct >= 40 ? "#D97706" : "#DC2626" }}>
                      {pct.toFixed(0)}%
                    </span>
                    <span className={styles.donutSub}>active</span>
                  </div>
                </div>
              )}
              <div className={styles.donutLegend}>
                <div className={styles.legendRow}>
                  <span className={styles.legendDot} style={{ background: "#4F63D2" }} />
                  Active
                  <strong className={styles.legendVal}>{fmtSecs(activeSec)}</strong>
                </div>
                <div className={styles.legendRow}>
                  <span className={styles.legendDot} style={{ background: "#E2E8F0" }} />
                  Idle
                  <strong className={styles.legendVal}>{fmtSecs(idleSec)}</strong>
                </div>
              </div>
            </div>

            {/* Timeline chart */}
            <div className={`${styles.chartCard} ${styles.chartCardFlex}`}>
              <h3 className={styles.chartTitle}>Activity Timeline</h3>
              <p className={styles.chartSub}>10-minute windows across today</p>
              {mounted && timelineData.length > 0 ? (
                <ResponsiveContainer width="100%" height={185}>
                  <BarChart data={timelineData} barSize={12} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="#F1F5F9" />
                    <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#94A3B8" }} interval="preserveStartEnd" axisLine={false} tickLine={false} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#94A3B8" }} tickFormatter={v => `${v}%`} axisLine={false} tickLine={false} />
                    <Tooltip
                      formatter={v => [`${v}%`, "Activity"]}
                      contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #E2E8F0", boxShadow: "0 4px 12px rgba(0,0,0,0.08)" }}
                    />
                    <Bar dataKey="pct" radius={[4, 4, 0, 0]}>
                      {timelineData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className={styles.chartEmpty}>
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#CBD5E1" strokeWidth="1.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                  <p>No activity data yet</p>
                </div>
              )}
              <div className={styles.legendPillRow}>
                <span className={styles.legendPill} style={{ background: "#DCFCE7", color: "#16A34A" }}>● Active ≥70%</span>
                <span className={styles.legendPill} style={{ background: "#FEF9C3", color: "#B45309" }}>● Moderate 40–69%</span>
                <span className={styles.legendPill} style={{ background: "#FEE2E2", color: "#DC2626" }}>● Idle &lt;40%</span>
              </div>
            </div>
          </div>

          {/* ── Charts row 2: Task Status + App Usage ──── */}
          <div className={styles.chartsRow}>

            {/* Task status donut */}
            <div className={styles.chartCard} style={{ width: 280, flexShrink: 0 }}>
              <h3 className={styles.chartTitle}>Task Status</h3>
              <p className={styles.chartSub}>Today&apos;s breakdown</p>
              {mounted && (
                <div className={styles.donutWrap}>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie
                        data={taskDonut}
                        cx="50%" cy="50%"
                        innerRadius={58} outerRadius={84}
                        paddingAngle={hasTaskData ? 3 : 0}
                        dataKey="value"
                        startAngle={90} endAngle={-270}
                      >
                        {taskDonut.map((_, i) => (
                          <Cell key={i}
                            fill={hasTaskData ? TASK_COLORS[i % TASK_COLORS.length] : "#F1F5F9"}
                            strokeWidth={0}
                          />
                        ))}
                      </Pie>
                      {hasTaskData && <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />}
                    </PieChart>
                  </ResponsiveContainer>
                  <div className={styles.donutCenter}>
                    <span className={styles.donutBig} style={{ color: "#16A34A" }}>{completed}</span>
                    <span className={styles.donutSub}>done</span>
                  </div>
                </div>
              )}
              <div className={styles.donutLegend}>
                <div className={styles.legendRow}>
                  <span className={styles.legendDot} style={{ background: "#22C55E" }} />
                  Done
                  <strong className={styles.legendVal}>{completed}</strong>
                </div>
                <div className={styles.legendRow}>
                  <span className={styles.legendDot} style={{ background: "#4F63D2" }} />
                  In Progress
                  <strong className={styles.legendVal}>{in_progress}</strong>
                </div>
                <div className={styles.legendRow}>
                  <span className={styles.legendDot} style={{ background: "#F97316" }} />
                  Pending
                  <strong className={styles.legendVal}>{pending}</strong>
                </div>
              </div>
            </div>

            {/* App usage */}
            <div className={`${styles.chartCard} ${styles.chartCardFlex}`}>
              <div className={styles.chartCardHeader}>
                <div>
                  <h3 className={styles.chartTitle}>App Usage</h3>
                  <p className={styles.chartSub}>Most used apps today</p>
                </div>
                <a href="/activity" className={styles.viewAllLink}>View all →</a>
              </div>
              {topApps.length > 0 ? (
                <div className={styles.appList}>
                  {topApps.map((app, i) => {
                    const barPct = Math.round((app.total_sec / totalAppSec) * 100);
                    return (
                      <div key={i} className={styles.appRow}>
                        <div className={styles.appMeta}>
                          <span className={styles.appIconEl}>{appIcon(app.app_name)}</span>
                          <span className={styles.appName}>{app.app_name}</span>
                        </div>
                        <div className={styles.appBarTrack}>
                          <div
                            className={styles.appBarFill}
                            style={{ width: `${Math.max(barPct, 3)}%`, background: APP_COLORS[i % APP_COLORS.length] }}
                          />
                        </div>
                        <span className={styles.appDuration}>{fmtSecs(app.total_sec)}</span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className={styles.chartEmpty}>
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#CBD5E1" strokeWidth="1.5"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                  <p>No app data yet — open the desktop app</p>
                </div>
              )}
            </div>
          </div>

          {/* ── Recent Screenshots ─────────────────────── */}
          <div className={styles.screenshotsSection}>
            <div className={styles.sectionHeader}>
              <h3 className={styles.chartTitle}>Recent Screenshots</h3>
              <a href="/screenshots" className={styles.viewAllLink}>{screenshots.length} shown · View all →</a>
            </div>
            {screenshots.length === 0 ? (
              <div className={styles.emptyShots}>
                <div className={styles.emptyShotsIcon}>
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#CBD5E1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
                </div>
                <p className={styles.emptyTitle}>No screenshots yet</p>
                <p className={styles.emptySub}>Open the desktop app and log in to start capturing automatically every few minutes.</p>
              </div>
            ) : (
              <div className={styles.screenshotGrid}>
                {screenshots.map(s => (
                  <div key={s.id} className={styles.screenshotCard} onClick={() => setSelectedImg(s)}>
                    <div className={styles.screenshotThumb}>
                      <img
                        src={`${API}/api/screenshots/${user.user_id}/${s.id}/image`}
                        alt=""
                        style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        onError={e => { e.target.style.display = "none"; e.target.parentNode.innerHTML = '<span style="font-size:24px;opacity:.2">📷</span>'; }}
                      />
                    </div>
                    <div className={styles.screenshotMeta}>
                      {new Date(s.taken_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>

        {/* ── Lightbox ──────────────────────────────── */}
        {selectedImg && (
          <div className={styles.modalOverlay} onClick={() => setSelectedImg(null)}>
            <div className={styles.modal} onClick={e => e.stopPropagation()}>
              <div className={styles.modalHeader}>
                <span>{new Date(selectedImg.taken_at).toLocaleString()}</span>
                <button onClick={() => setSelectedImg(null)} className={styles.closeBtn}>✕</button>
              </div>
              <div className={styles.modalBody}>
                <img
                  src={`${API}/api/screenshots/${user.user_id}/${selectedImg.id}/image`}
                  alt=""
                  className={styles.fullImage}
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

function KPICard({ icon, label, value, color, bg, sub }) {
  return (
    <div className={styles.kpiCard}>
      <div className={styles.kpiIconWrap} style={{ background: bg, color }}>
        {icon}
      </div>
      <div className={styles.kpiValue} style={{ color }}>{value}</div>
      <div className={styles.kpiLabel}>{label}</div>
      <div className={styles.kpiSub}>{sub}</div>
    </div>
  );
}
