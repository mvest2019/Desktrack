// ============================================================
// pages/admin.js — Admin Portal (redesigned)
// ============================================================

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import Link from "next/link";
import styles from "../styles/Admin.module.css";
import API from "../config";

// Cycle through distinct gradients per member index
const AVATAR_GRADIENTS = [
  "linear-gradient(135deg,#4A9EFF,#A78BFA)",
  "linear-gradient(135deg,#34D399,#4A9EFF)",
  "linear-gradient(135deg,#F59E0B,#EF4444)",
  "linear-gradient(135deg,#A78BFA,#EC4899)",
  "linear-gradient(135deg,#06B6D4,#3B82F6)",
  "linear-gradient(135deg,#10B981,#059669)",
  "linear-gradient(135deg,#F97316,#FBBF24)",
  "linear-gradient(135deg,#8B5CF6,#EC4899)",
];

export default function AdminPortal() {
  const router = useRouter();

  const [admin, setAdmin]           = useState(null);
  const [users, setUsers]           = useState([]);
  const [search, setSearch]         = useState("");
  const [selected, setSelected]     = useState(null);
  const [memberData, setMemberData] = useState(null);
  const [loading, setLoading]       = useState(true);
  const [changing, setChanging]     = useState(null);
  const [modalIdx, setModalIdx]     = useState(null); // index into memberData.screenshots

  const snapshots = useMemo(() => memberData?.screenshots || [], [memberData]);

  function openModal(idx) { setModalIdx(idx); }
  function closeModal()   { setModalIdx(null); }
  function prevSnap()     { setModalIdx(i => (i > 0 ? i - 1 : snapshots.length - 1)); }
  function nextSnap()     { setModalIdx(i => (i < snapshots.length - 1 ? i + 1 : 0)); }

  useEffect(() => {
    function onKey(e) {
      if (modalIdx === null) return;
      if (e.key === "Escape")      closeModal();
      if (e.key === "ArrowLeft")   prevSnap();
      if (e.key === "ArrowRight")  nextSnap();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [modalIdx, snapshots.length]);

  useEffect(() => {
    const stored = localStorage.getItem("user");
    if (!stored) { router.push("/"); return; }
    const u = JSON.parse(stored);
    if (u.user_type !== "admin") { router.push("/dashboard"); return; }
    setAdmin(u);
    fetchUsers(u.user_id);
  }, []);

  async function fetchUsers(adminId) {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/admin/users?admin_id=${adminId}`);
      if (res.ok) {
        const data = await res.json();
        setUsers(data.users || []);
      }
    } catch (err) {
      console.error("Failed to fetch users:", err);
    } finally {
      setLoading(false);
    }
  }

  async function viewMember(user) {
    setSelected(user);
    setMemberData(null);
    try {
      const [statsRes, screensRes, actRes, appRes] = await Promise.all([
        fetch(`${API}/api/stats/${user.user_id}`),
        fetch(`${API}/api/screenshots/${user.user_id}?limit=8`),
        fetch(`${API}/api/activity/${user.user_id}?limit=14`),
        fetch(`${API}/api/applogs/${user.user_id}/summary`),
      ]);
      const stats      = statsRes.ok   ? await statsRes.json()   : {};
      const screensData= screensRes.ok ? await screensRes.json() : { screenshots: [] };
      const activity   = actRes.ok     ? await actRes.json()     : null;
      const appSummary = appRes.ok     ? await appRes.json()     : null;
      setMemberData({ stats, screenshots: screensData.screenshots || [], activity, appSummary });
    } catch (err) {
      console.error("Failed to fetch member data:", err);
    }
  }

  async function changeRole(userId, newType) {
    setChanging(userId);
    try {
      const res = await fetch(
        `${API}/api/admin/users/${userId}/type?admin_id=${admin.user_id}&new_type=${newType}`,
        { method: "PATCH" }
      );
      if (res.ok) {
        await fetchUsers(admin.user_id);
        if (selected?.user_id === userId) setSelected((p) => ({ ...p, user_type: newType }));
      }
    } finally {
      setChanging(null);
    }
  }

  function logout() { localStorage.removeItem("user"); router.push("/"); }
  function fmt(iso) { return iso ? new Date(iso).toLocaleString() : "—"; }
  function fmtSec(s) {
    if (!s) return "0m";
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  }

  const filtered = useMemo(() =>
    users.filter(u =>
      u.username.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase())
    ), [users, search]);

  const totalAdmins = users.filter(u => u.user_type === "admin").length;
  const totalActive = users.filter(u => u.isactive).length;

  if (!admin) return null;

  return (
    <>
      <Head><title>Syntra — Admin Portal</title></Head>
      <div className={styles.page}>

        {/* ── Sidebar ──────────────────────────────── */}
        <aside className={styles.sidebar}>
          <div className={styles.logo}>
            <img src="/app_icon.png" alt="Syntra" className={styles.logoImg} />
            <span className={styles.logoText}>Syntra</span>
          </div>
          <nav className={styles.nav}>
            <span className={`${styles.navItem} ${styles.active}`}>
              <span>🛡</span> Admin Portal
            </span>
          </nav>
          <div className={styles.sidebarFooter}>
            <div className={styles.userBadge}>
              <div className={styles.avatar}>{admin.username?.charAt(0).toUpperCase()}</div>
              <div>
                <div className={styles.userName}>{admin.username}</div>
                <div className={styles.userRole}>Administrator</div>
              </div>
            </div>
            <button onClick={logout} className={styles.logoutBtn}>Logout</button>
          </div>
        </aside>

        {/* ── Main ─────────────────────────────────── */}
        <main className={styles.main}>

          {/* Top bar */}
          <div className={styles.topBar}>
            <div>
              <h1 className={styles.pageTitle}>Team Overview</h1>
              <p className={styles.pageSubtitle}>Manage team members and monitor activity</p>
            </div>
            <button className={styles.refreshBtn} onClick={() => fetchUsers(admin.user_id)}>
              ↻ Refresh
            </button>
          </div>

          {/* Summary strip */}
          <div className={styles.summaryStrip}>
            <div className={styles.summaryCard}>
              <div className={styles.summaryIcon} style={{ background: "rgba(74,158,255,0.12)", color: "#4A9EFF" }}>👥</div>
              <div>
                <div className={styles.summaryLabel}>Total Members</div>
                <div className={styles.summaryValue}>{users.length}</div>
              </div>
            </div>
            <div className={styles.summaryCard}>
              <div className={styles.summaryIcon} style={{ background: "rgba(52,211,153,0.12)", color: "#34D399" }}>✅</div>
              <div>
                <div className={styles.summaryLabel}>Active</div>
                <div className={styles.summaryValue}>{totalActive}</div>
              </div>
            </div>
            <div className={styles.summaryCard}>
              <div className={styles.summaryIcon} style={{ background: "rgba(167,139,250,0.12)", color: "#A78BFA" }}>🛡</div>
              <div>
                <div className={styles.summaryLabel}>Admins</div>
                <div className={styles.summaryValue}>{totalAdmins}</div>
              </div>
            </div>
          </div>

          {/* Two-column layout */}
          <div className={styles.layout}>

            {/* Left: member list */}
            <div className={styles.memberListWrap}>
              <div className={styles.memberListHeader}>
                <p className={styles.sectionTitle}>Team Members</p>
                <div className={styles.searchWrap}>
                  <span className={styles.searchIcon}>🔍</span>
                  <input
                    className={styles.searchInput}
                    placeholder="Search by name or email..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                  />
                </div>
              </div>

              <div className={styles.memberList}>
                {loading ? (
                  <div className={styles.empty}>Loading...</div>
                ) : filtered.length === 0 ? (
                  <div className={styles.empty}>No members found.</div>
                ) : (
                  filtered.map((u, idx) => (
                    <div
                      key={u.user_id}
                      className={`${styles.memberCard} ${selected?.user_id === u.user_id ? styles.memberCardActive : ""}`}
                      onClick={() => viewMember(u)}
                    >
                      <div
                        className={styles.memberAvatar}
                        style={{ background: AVATAR_GRADIENTS[idx % AVATAR_GRADIENTS.length] }}
                      >
                        {u.username.charAt(0).toUpperCase()}
                      </div>
                      <div className={styles.memberInfo}>
                        <div className={styles.memberName}>{u.username}</div>
                        <div className={styles.memberEmail}>{u.email}</div>
                        <div className={styles.memberMeta}>
                          <span className={u.user_type === "admin" ? styles.badgeAdmin : styles.badgeUser}>
                            {u.user_type === "admin" ? "🛡 Admin" : "👤 User"}
                          </span>
                          <span className={u.isactive ? styles.badgeActive : styles.badgeInactive}>
                            {u.isactive ? "Active" : "Inactive"}
                          </span>
                        </div>
                      </div>
                      <div className={styles.memberActions} onClick={e => e.stopPropagation()}>
                        {u.user_type === "user" ? (
                          <button
                            className={styles.roleBtn}
                            disabled={changing === u.user_id}
                            onClick={() => changeRole(u.user_id, "admin")}
                          >
                            {changing === u.user_id ? "…" : "Make Admin"}
                          </button>
                        ) : u.user_id !== admin.user_id ? (
                          <button
                            className={`${styles.roleBtn} ${styles.roleBtnDanger}`}
                            disabled={changing === u.user_id}
                            onClick={() => changeRole(u.user_id, "user")}
                          >
                            {changing === u.user_id ? "…" : "Revoke"}
                          </button>
                        ) : null}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Right: member detail panel */}
            <section className={styles.memberPanel}>
              {!selected ? (
                <div className={styles.panelEmpty}>
                  <span className={styles.panelEmptyIcon}>👈</span>
                  <p>Select a team member to view their dashboard</p>
                </div>
              ) : (
                <>
                  {/* Panel header */}
                  <div className={styles.panelHeader}>
                    <div
                      className={styles.panelAvatar}
                      style={{ background: AVATAR_GRADIENTS[filtered.findIndex(u => u.user_id === selected.user_id) % AVATAR_GRADIENTS.length] }}
                    >
                      {selected.username.charAt(0).toUpperCase()}
                    </div>
                    <div className={styles.panelNameWrap}>
                      <h2 className={styles.panelName}>{selected.username}</h2>
                      <p className={styles.panelEmail}>{selected.email}</p>
                    </div>
                    <Link href={`/dashboard?uid=${selected.user_id}`} className={styles.fullViewBtn}>
                      Full Dashboard →
                    </Link>
                  </div>

                  <div className={styles.panelBody}>
                    {!memberData ? (
                      <div className={styles.empty}>Loading member data…</div>
                    ) : (
                      <>
                        {/* Stats */}
                        <div className={styles.statsGrid}>
                          <StatCard icon="📷" label="Screenshots"  value={memberData.stats.total_screenshots ?? "—"} color="#4A9EFF" />
                          <StatCard icon="⚡" label="Today Active" value={fmtSec(memberData.activity?.today_active_sec)} color="#34D399" />
                          <StatCard icon="😴" label="Today Idle"   value={fmtSec(memberData.activity?.today_idle_sec)}  color="#F59E0B" />
                          <StatCard icon="📊" label="Activity %"   value={memberData.activity ? `${memberData.activity.today_percent}%` : "—"} color="#A78BFA" />
                        </div>

                        {/* Activity timeline */}
                        {memberData.activity?.logs?.length > 0 && (
                          <div className={styles.section}>
                            <p className={styles.subTitle}>Activity Timeline</p>
                            <div className={styles.barChart}>
                              {[...memberData.activity.logs].reverse().map((log, i) => (
                                <div key={i} className={styles.barWrap} title={`${log.activity_percent}%`}>
                                  <div
                                    className={styles.bar}
                                    style={{
                                      height: `${Math.max(4, log.activity_percent)}%`,
                                      background: log.activity_percent >= 70 ? "#34D399"
                                               : log.activity_percent >= 40 ? "#F59E0B"
                                               : "#EF4444",
                                    }}
                                  />
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Top apps */}
                        {memberData.appSummary?.entries?.length > 0 && (
                          <div className={styles.section}>
                            <p className={styles.subTitle}>Top Apps Today</p>
                            <div className={styles.appList}>
                              {memberData.appSummary.entries.slice(0, 5).map((a, i) => (
                                <div key={i} className={styles.appRow}>
                                  <span className={styles.appName}>{a.app_name}</span>
                                  <span className={styles.appTime}>{fmtSec(a.total_sec)}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Recent screenshots */}
                        {memberData.screenshots.length > 0 && (
                          <div className={styles.section}>
                            <p className={styles.subTitle}>Recent Screenshots</p>
                            <div className={styles.screenshotGrid}>
                              {memberData.screenshots.map((s, idx) => {
                                const src = `${API}/api/screenshots/${selected.user_id}/${s.id}/image`;
                                return (
                                  <div
                                    key={s.id}
                                    className={styles.screenshotCard}
                                    onClick={() => openModal(idx)}
                                  >
                                    <img
                                      src={src}
                                      alt="screenshot"
                                      className={styles.screenshotImg}
                                      loading="lazy"
                                      onError={(e) => { e.target.style.opacity = "0.2"; }}
                                    />
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </>
              )}
            </section>
          </div>
        </main>
      </div>

      {/* ── Screenshot lightbox ───────────────────── */}
      {modalIdx !== null && snapshots[modalIdx] && (() => {
        const s = snapshots[modalIdx];
        const src = `${API}/api/screenshots/${selected.user_id}/${s.id}/image`;
        return (
          <div className={styles.modalOverlay} onClick={closeModal}>
            <button className={styles.modalNav} style={{ left: 16 }} onClick={e => { e.stopPropagation(); prevSnap(); }}>‹</button>
            <div className={styles.modalBox} onClick={e => e.stopPropagation()}>
              <button className={styles.modalClose} onClick={closeModal}>✕</button>
              <img src={src} alt="screenshot" className={styles.modalImg} />
            </div>
            <button className={styles.modalNav} style={{ right: 16 }} onClick={e => { e.stopPropagation(); nextSnap(); }}>›</button>
          </div>
        );
      })()}
    </>
  );
}

function StatCard({ icon, label, value, color }) {
  return (
    <div className={styles.statCard} style={{ borderColor: `${color}22` }}>
      <div className={styles.statIcon} style={{ background: `${color}15`, color }}>{icon}</div>
      <div className={styles.statLabel}>{label}</div>
      <div className={styles.statValue} style={{ color }}>{value}</div>
    </div>
  );
}
