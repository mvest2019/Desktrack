// ============================================================
// pages/dashboard.js — Dashboard Page
// ============================================================
// Shows after successful login.
// Displays real-time screenshot stats and a list of recent captures.

import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import Link from "next/link";
import styles from "../styles/Dashboard.module.css";
import API from "../config";

export default function Dashboard() {
  const router = useRouter();

  const [user,        setUser]        = useState(null);
  const [stats,       setStats]       = useState({ total_screenshots: 0, last_capture: null });
  const [screenshots, setScreenshots] = useState([]);
  const [selectedImg, setSelectedImg] = useState(null);
  const [activity,    setActivity]    = useState(null);
  const [taskSummary, setTaskSummary] = useState(null);
  const [showWelcome, setShowWelcome] = useState(false);

  // ── On page load: check login & fetch data ───────────────
  useEffect(() => {
    const stored = localStorage.getItem("user");
    if (!stored) {
      router.push("/");   // Not logged in → back to login
      return;
    }
    const userData = JSON.parse(stored);

    // Admin can view any user's dashboard via ?uid=<user_id>
    const targetId = router.query.uid
      ? parseInt(router.query.uid)
      : userData.user_id;

    // Non-admin users cannot view other people's dashboards
    if (router.query.uid && userData.user_type !== "admin") {
      router.push("/dashboard");
      return;
    }

    setUser(userData);
    fetchData(targetId);
    setShowWelcome(true);
    const hideWelcome = setTimeout(() => setShowWelcome(false), 4000);

    const interval = setInterval(() => fetchData(targetId), 15000);
    return () => { clearInterval(interval); clearTimeout(hideWelcome); };
  }, [router.query.uid]);

  // ── Fetch stats + screenshot list + activity ─────────────
  async function fetchData(userId) {
    try {
      const [statsRes, screenshotsRes, activityRes, taskSumRes] = await Promise.all([
        fetch(`${API}/api/stats/${userId}`),
        fetch(`${API}/api/screenshots/${userId}?limit=12`),
        fetch(`${API}/api/activity/${userId}?limit=16`),
        fetch(`${API}/api/tasks/${userId}/summary`),
      ]);

      if (statsRes.ok)       setStats(await statsRes.json());
      if (screenshotsRes.ok) {
        const data = await screenshotsRes.json();
        setScreenshots(data.screenshots || []);
      }
      if (activityRes.ok)    setActivity(await activityRes.json());
      if (taskSumRes.ok)     setTaskSummary(await taskSumRes.json());
    } catch (err) {
    }
  }

  // ── Load and show a screenshot image ────────────────────
  function viewScreenshot(screenshotId) {
    const meta = screenshots.find((s) => s.id === screenshotId) || {};
    setSelectedImg({
      ...meta,
      imgUrl: `${API}/api/screenshots/${user.user_id}/${screenshotId}/image`,
    });
  }

  function navigateModal(dir) {
    const idx = screenshots.findIndex((s) => s.id === selectedImg.id);
    const next = screenshots[idx + dir];
    if (next) viewScreenshot(next.id);
  }

  // ── Logout ───────────────────────────────────────────────
  function logout() {
    localStorage.removeItem("user");
    router.push("/");
  }

  // Format date nicely
  function formatTime(isoString) {
    if (!isoString) return "—";
    return new Date(isoString).toLocaleString();
  }

  if (!user) return null;

  return (
    <>
      <Head>
        <title>Realisieren Pulse — Dashboard</title>
      </Head>

      <div className={styles.page}>
        {/* ── Sidebar ─────────────────────────────────── */}
        <aside className={styles.sidebar}>
          <div className={styles.logo}>
            <img src="/app_icon.png" alt="Realisieren Pulse" className={styles.logoImg} />
            <span className={styles.logoText}>Realisieren Pulse</span>
          </div>

          <nav className={styles.nav}>
            <Link className={`${styles.navItem} ${styles.active}`} href="/dashboard">
              <span>📊</span> Dashboard
            </Link>
            <Link className={styles.navItem} href="/screenshots">
              <span>📷</span> Screenshots
            </Link>
            <Link className={styles.navItem} href="/activity">
              <span>🖥</span> Activity
            </Link>
            <Link className={styles.navItem} href="/tasks">
              <span>✅</span> My Tasks
            </Link>
            <Link className={styles.navItem} href="/profile">
              <span>👤</span> Profile
            </Link>
            {user.user_type === "admin" && (
              <>
                <Link className={styles.navItem} href="/admin">
                  <span>🛡</span> Admin Portal
                </Link>
                <Link className={styles.navItem} href="/admin-tasks">
                  <span>📋</span> Task Overview
                </Link>
              </>
            )}
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
            <button onClick={logout} className={styles.logoutBtn}>
              Logout
            </button>
          </div>
        </aside>

        {/* ── Main content ────────────────────────────── */}
        <main className={styles.main}>
          <div className={styles.topBar}>
            <div>
              <h1 className={styles.pageTitle}>
                {(() => {
                  const h = new Date().getHours();
                  const greet = h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
                  return `${greet}, ${user.username?.split(" ")[0]} 👋`;
                })()}
              </h1>
              <p className={styles.pageSubtitle}>
                Here&apos;s what&apos;s happening with your <strong>productivity</strong> today.
              </p>
            </div>
            <div className={styles.topBarRight}>
              <span className={styles.topBarDate}>
                {new Date().toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
              </span>
              <div className={styles.statusPill}>
                <span className={styles.statusDot} />
                Live Monitoring
              </div>
            </div>
          </div>

          {/* ── Stat cards ───────────────────────────── */}
          <div className={styles.statsGrid}>
            <StatCard
              icon="📷"
              label="Total Screenshots"
              value={stats.total_screenshots.toLocaleString()}
              sub="+captures today"
              color="#4F63D2"
              bg="#EEF2FF"
            />
            <StatCard
              icon="⏱"
              label="Capture Interval"
              value="3 min"
              sub="Every 3 minutes"
              color="#7C3AED"
              bg="#F5F3FF"
            />
            <StatCard
              icon="🕐"
              label="Last Capture"
              value={stats.last_capture ? new Date(stats.last_capture).toLocaleTimeString() : "—"}
              sub="Today"
              color="#059669"
              bg="#ECFDF5"
            />
            <StatCard
              icon="👤"
              label="Logged in as"
              value={user.username}
              sub="Active Session"
              color="#D97706"
              bg="#FFFBEB"
            />
          </div>

          {/* ── Activity tracking ────────────────────── */}
          <ActivitySection activity={activity} />

          {/* ── Task summary widget ───────────────────── */}
          <TaskSummaryWidget summary={taskSummary} />

          {/* ── Screenshot grid ──────────────────────── */}
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Recent Screenshots</h2>
              <span className={styles.count}>{screenshots.length} shown</span>
            </div>

            {screenshots.length === 0 ? (
              <div className={styles.empty}>
                <span className={styles.emptyIcon}>📷</span>
                <p>No screenshots yet. Open the desktop app and log in to start capturing.</p>
              </div>
            ) : (
              <div className={styles.screenshotGrid}>
                {screenshots.map((s) => (
                  <div
                    key={s.id}
                    className={styles.screenshotCard}
                    onClick={() => viewScreenshot(s.id)}
                  >
                    <ScreenshotThumb screenshotId={s.id} userId={user.user_id} />
                    <div className={styles.screenshotInfo}>
                      <div className={styles.screenshotTime}>
                        {formatTime(s.taken_at)}
                      </div>
                      <div className={styles.screenshotSize}>{s.file_size_kb} KB</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>

        {/* ── Welcome popup ───────────────────────────── */}
        {showWelcome && (
          <div style={{
            position: "fixed", bottom: 28, right: 28, zIndex: 300,
            background: "#FFFFFF",
            border: "1px solid #E2E8F0",
            borderRadius: 16, padding: "18px 22px",
            boxShadow: "0 8px 32px rgba(0,0,0,0.12)",
            display: "flex", alignItems: "center", gap: 14,
            animation: "slideUp 0.3s ease",
            minWidth: 260,
          }}>
            <div style={{
              width: 44, height: 44, borderRadius: "50%",
              background: "linear-gradient(135deg, #4F63D2, #818CF8)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 20, flexShrink: 0, color: "#fff", fontWeight: 700,
            }}>
              {user?.username?.charAt(0).toUpperCase()}
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#0F172A", marginBottom: 2 }}>
                Welcome back, {user?.username?.split(" ")[0]} 👋
              </div>
              <div style={{ fontSize: 12, color: "#94A3B8" }}>
                Realisieren Pulse is tracking your activity
              </div>
            </div>
            <button onClick={() => setShowWelcome(false)} style={{
              marginLeft: "auto", background: "none", border: "none",
              color: "#94A3B8", cursor: "pointer", fontSize: 16, padding: 4,
            }}>✕</button>
          </div>
        )}

        {/* ── Image viewer modal ───────────────────────── */}
        {selectedImg && (
          <div className={styles.modalOverlay} onClick={() => setSelectedImg(null)}>
            {/* Prev arrow */}
            {screenshots.findIndex((s) => s.id === selectedImg.id) > 0 && (
              <button className={styles.navArrow} style={{ left: 16 }}
                onClick={(e) => { e.stopPropagation(); navigateModal(-1); }}>
                ‹
              </button>
            )}

            <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
              <div className={styles.modalHeader}>
                <span>{selectedImg.filename || "Screenshot"}</span>
                <button onClick={() => setSelectedImg(null)} className={styles.closeBtn}>✕</button>
              </div>
              <div className={styles.modalBody}>
                <img
                  src={selectedImg.imgUrl}
                  alt={selectedImg.filename}
                  className={styles.fullImage}
                />
              </div>
              <div className={styles.modalFooter}>
                Taken at: {formatTime(selectedImg.taken_at)}
              </div>
            </div>

            {/* Next arrow */}
            {screenshots.findIndex((s) => s.id === selectedImg.id) < screenshots.length - 1 && (
              <button className={styles.navArrow} style={{ right: 16 }}
                onClick={(e) => { e.stopPropagation(); navigateModal(1); }}>
                ›
              </button>
            )}
          </div>
        )}
      </div>
    </>
  );
}

// ── Thumbnail loader — uses direct image URL ─────────────────
function ScreenshotThumb({ screenshotId, userId }) {
  const src = `${API}/api/screenshots/${userId}/${screenshotId}/image`;

  return (
    <div className={styles.screenshotThumb}>
      <img
        src={src}
        alt="screenshot"
        style={{ width: "100%", height: "100%", objectFit: "cover" }}
        onError={(e) => {
          e.target.style.display = "none";
          e.target.parentNode.innerHTML = '<span style="font-size:28px;opacity:0.25">📷</span>';
        }}
      />
    </div>
  );
}

// ── Activity section component ───────────────────────────────
function ActivitySection({ activity }) {
  // Helper: seconds → "Xh Ym" or "Xm"
  function fmtSecs(s) {
    if (!s) return "0m";
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }

  const pct        = activity?.today_percent   ?? 0;
  const activeSec  = activity?.today_active_sec ?? 0;
  const idleSec    = activity?.today_idle_sec   ?? 0;

  // Chart uses last N windows (oldest → newest)
  const logs = activity?.logs ? [...activity.logs].reverse() : [];

  return (
    <div style={{ marginBottom: 0 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <h2 className={styles.sectionTitle}>Activity</h2>
        <span className={styles.count}>Today</span>
      </div>

      {/* 3 summary cards */}
      <div className={styles.activityGrid}>
        {/* Activity % */}
        <div className={styles.activityCard}>
          <div className={styles.activityCardLabel}>Activity</div>
          <div className={styles.activityCardValue} style={{ color: pct >= 70 ? "#16A34A" : pct >= 40 ? "#D97706" : "#DC2626" }}>
            {pct.toFixed(0)}%
          </div>
          <div className={styles.activityPercBar}>
            <div className={styles.activityPercFill} style={{ width: `${pct}%` }} />
          </div>
          <div className={styles.activityCardSub}>of today&apos;s tracked time</div>
        </div>

        {/* Active time */}
        <div className={styles.activityCard}>
          <div className={styles.activityCardLabel}>Active Time</div>
          <div className={styles.activityCardValue} style={{ color: "#4F63D2" }}>
            {fmtSecs(activeSec)}
          </div>
          <div className={styles.activityCardSub}>mouse + keyboard detected</div>
        </div>

        {/* Idle time */}
        <div className={styles.activityCard}>
          <div className={styles.activityCardLabel}>Idle Time</div>
          <div className={styles.activityCardValue} style={{ color: "#7C3AED" }}>
            {fmtSecs(idleSec)}
          </div>
          <div className={styles.activityCardSub}>no input for 3+ min</div>
        </div>
      </div>

      {/* Timeline bar chart */}
      {logs.length > 0 && <TimelineChart logs={logs} />}
    </div>
  );
}

// ── Timeline bar chart component ─────────────────────────────
function TimelineChart({ logs }) {
  function timeLabel(iso) {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  }

  return (
    <div className={styles.chartWrap}>
      <div className={styles.chartTitle}>Activity Timeline (10-min windows)</div>
      <div className={styles.chartBars}>
        {logs.map((w, i) => {
          const pct  = w.activity_percent;
          const hue  = pct >= 70 ? "#22C55E" : pct >= 40 ? "#F97316" : "#EF4444";
          const hPx  = Math.max(4, Math.round((pct / 100) * 72)); // max 72px bar height
          return (
            <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <div
                className={styles.chartBar}
                style={{ height: hPx, background: hue, width: 28 }}
                title={`${timeLabel(w.window_start)} — ${pct}% active`}
              />
              <div className={styles.chartBarLabel}>{timeLabel(w.window_start)}</div>
            </div>
          );
        })}
      </div>
      <div className={styles.chartLegend}>
        <div className={styles.legendItem}>
          <div className={styles.legendDot} style={{ background: "#22C55E" }} />
          Active (≥70%)
        </div>
        <div className={styles.legendItem}>
          <div className={styles.legendDot} style={{ background: "#F97316" }} />
          Moderate (40–69%)
        </div>
        <div className={styles.legendItem}>
          <div className={styles.legendDot} style={{ background: "#EF4444" }} />
          Idle (&lt;40%)
        </div>
      </div>
    </div>
  );
}

// ── Task summary widget ──────────────────────────────────────
function TaskSummaryWidget({ summary }) {
  if (!summary) return null;
  const { total, pending, in_progress, completed, completion_pct } = summary;

  return (
    <div style={{ marginBottom: 28 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <h2 className={styles.sectionTitle}>Today&apos;s Tasks</h2>
        <a href="/tasks" style={{ fontSize: 12, color: "#4F63D2", textDecoration: "none", fontWeight: 600 }}>View All →</a>
      </div>

      <div className={styles.activityGrid}>
        <div className={styles.activityCard}>
          <div className={styles.activityCardLabel}>Completion</div>
          <div className={styles.activityCardValue} style={{ color: completion_pct >= 70 ? "#16A34A" : completion_pct >= 40 ? "#D97706" : "#DC2626" }}>
            {completion_pct.toFixed(0)}%
          </div>
          <div className={styles.activityPercBar}>
            <div className={styles.activityPercFill} style={{ width: `${completion_pct}%` }} />
          </div>
          <div className={styles.activityCardSub}>{completed} of {total} tasks done</div>
        </div>

        <div className={styles.activityCard}>
          <div className={styles.activityCardLabel}>In Progress</div>
          <div className={styles.activityCardValue} style={{ color: "#4F63D2" }}>{in_progress}</div>
          <div className={styles.activityCardSub}>tasks active now</div>
        </div>

        <div className={styles.activityCard}>
          <div className={styles.activityCardLabel}>Pending</div>
          <div className={styles.activityCardValue} style={{ color: "#7C3AED" }}>{pending}</div>
          <div className={styles.activityCardSub}>not started yet</div>
        </div>
      </div>
    </div>
  );
}

// ── Small reusable stat card component ──────────────────────
function StatCard({ icon, label, value, sub, color, bg }) {
  return (
    <div className={styles.statCard}>
      <div className={styles.statIcon} style={{ background: bg || `${color}18`, color }}>
        {icon}
      </div>
      <div className={styles.statValue}>{value}</div>
      <div className={styles.statLabel}>{label}</div>
      {sub && <div className={styles.statSub}>{sub}</div>}
    </div>
  );
}
