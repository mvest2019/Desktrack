// pages/screenshots.js
import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import Link from "next/link";
import styles from "../styles/Screenshots.module.css";
import API from "../config";

// ── helpers ─────────────────────────────────────────────────
function toLocalDateStr(iso) {
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
}
function groupLabel(dateStr) {
  const today     = toLocalDateStr(new Date());
  const yesterday = toLocalDateStr(new Date(Date.now() - 86400000));
  if (dateStr === today)     return "Today";
  if (dateStr === yesterday) return "Yesterday";
  return new Date(dateStr + "T00:00:00").toLocaleDateString([], { weekday: "long", month: "long", day: "numeric", year: "numeric" });
}

// ── Mini calendar ────────────────────────────────────────────
function MiniCalendar({ activeDates, selectedDate, onSelect }) {
  const [viewYear, setViewYear]   = useState(new Date().getFullYear());
  const [viewMonth, setViewMonth] = useState(new Date().getMonth());

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
    <div className={styles.calendar}>
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
          const hasSnaps = activeDates.has(ds);
          const isSelected = selectedDate === ds;
          return (
            <button
              key={ds}
              className={`${styles.calDay} ${hasSnaps ? styles.calDayActive : ""} ${isSelected ? styles.calDaySelected : ""}`}
              onClick={() => hasSnaps && onSelect(isSelected ? null : ds)}
              disabled={!hasSnaps}
            >{d}</button>
          );
        })}
      </div>
    </div>
  );
}

// ── Main page ────────────────────────────────────────────────
export default function ScreenshotsPage() {
  const router = useRouter();

  const [user, setUser]             = useState(null);
  const [allShots, setAllShots]     = useState([]);
  const [total, setTotal]           = useState(0);
  const [loading, setLoading]       = useState(true);
  const [calDate, setCalDate]       = useState(null);   // selected calendar date string
  const [modalIdx, setModalIdx]     = useState(null);
  const [flatList, setFlatList]     = useState([]);     // flat ordered list for modal nav

  useEffect(() => {
    const stored = localStorage.getItem("user");
    if (!stored) { router.push("/"); return; }
    const u = JSON.parse(stored);
    setUser(u);
    loadAll(u.user_id);
  }, []);

  useEffect(() => {
    function onKey(e) {
      if (modalIdx === null) return;
      if (e.key === "Escape")     setModalIdx(null);
      if (e.key === "ArrowLeft")  setModalIdx(i => Math.max(0, i - 1));
      if (e.key === "ArrowRight") setModalIdx(i => Math.min(flatList.length - 1, i + 1));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [modalIdx, flatList.length]);

  async function loadAll(userId) {
    setLoading(true);
    try {
      const [statsRes, listRes] = await Promise.all([
        fetch(`${API}/api/stats/${userId}`),
        fetch(`${API}/api/screenshots/${userId}?limit=500`),
      ]);
      const stats = statsRes.ok ? await statsRes.json() : {};
      setTotal(stats.total_screenshots || 0);
      if (listRes.ok) {
        const list = (await listRes.json()).screenshots || [];
        setAllShots(list);
      }
    } catch (_) {}
    finally { setLoading(false); }
  }

  function logout() { localStorage.removeItem("user"); router.push("/"); }

  // dates that have screenshots → for calendar dots
  const activeDates = useMemo(() => new Set(allShots.map(s => toLocalDateStr(s.taken_at))), [allShots]);

  // filter by calendar selection, then group by date
  const grouped = useMemo(() => {
    let list = allShots;
    if (calDate) list = list.filter(s => toLocalDateStr(s.taken_at) === calDate);
    // group by date string
    const map = {};
    list.forEach(s => {
      const ds = toLocalDateStr(s.taken_at);
      if (!map[ds]) map[ds] = [];
      map[ds].push(s);
    });
    // sort dates newest first
    return Object.entries(map).sort((a, b) => b[0].localeCompare(a[0]));
  }, [allShots, calDate]);

  // flat list for modal navigation (across all groups)
  useEffect(() => {
    setFlatList(grouped.flatMap(([, shots]) => shots));
  }, [grouped]);

  if (!user) return null;

  const modalSnap = modalIdx !== null ? flatList[modalIdx] : null;

  return (
    <>
      <Head><title>Screenshots — Realisieren Pulse</title></Head>
      <div className={styles.page}>

        {/* ── Sidebar ──────────────────────────────── */}
        <aside className={styles.sidebar}>
          <div className={styles.logo}>
            <img src="/app_icon.png" alt="Realisieren Pulse" className={styles.logoImg} />
            <span className={styles.logoText}>Realisieren Pulse</span>
          </div>
          <nav className={styles.nav}>
            <Link href="/dashboard" className={styles.navItem}><span>📊</span> Dashboard</Link>
            <Link href="/screenshots" className={`${styles.navItem} ${styles.active}`}><span>📷</span> Screenshots</Link>
            <Link href="/activity" className={styles.navItem}><span>🖥</span> Activity</Link>
            <Link href="/tasks" className={styles.navItem}><span>✅</span> My Tasks</Link>
            <Link href="/profile" className={styles.navItem}><span>👤</span> Profile</Link>
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

        {/* ── Main ─────────────────────────────────── */}
        <main className={styles.main}>
          <div className={styles.header}>
            <div>
              <h1 className={styles.title}>Screenshots</h1>
              <p className={styles.subtitle}>{total} total captures</p>
            </div>
            {calDate && (
              <button className={styles.clearCalBtn} onClick={() => setCalDate(null)}>
                ✕ Clear filter
              </button>
            )}
          </div>

          <div className={styles.contentWrap}>
            {/* Left: grouped screenshots */}
            <div className={styles.groupsCol}>
              {loading ? (
                <div className={styles.loadingState}>
                  <span className={styles.bigSpinner} />
                  <p>Loading screenshots...</p>
                </div>
              ) : grouped.length === 0 ? (
                <div className={styles.emptyState}>
                  <span className={styles.emptyIcon}>📷</span>
                  <h3>No screenshots {calDate ? "on this date" : "yet"}</h3>
                  <p>{calDate ? "Pick another date from the calendar." : "Open the desktop app and log in to start capturing."}</p>
                </div>
              ) : (
                grouped.map(([dateStr, shots]) => (
                  <div key={dateStr} className={styles.dateGroup}>
                    <div className={styles.dateLabel}>
                      <span className={styles.dateLabelText}>{groupLabel(dateStr)}</span>
                      <span className={styles.dateLabelCount}>{shots.length} captures</span>
                    </div>
                    <div className={styles.grid}>
                      {shots.map(s => {
                        const globalIdx = flatList.findIndex(x => x.id === s.id);
                        return (
                          <div key={s.id} className={styles.card} onClick={() => setModalIdx(globalIdx)}>
                            <div className={styles.thumb}>
                              <img
                                src={`${API}/api/screenshots/${user.user_id}/${s.id}/image`}
                                alt=""
                                className={styles.thumbImg}
                                onError={e => { e.target.style.display = "none"; e.target.nextSibling.style.display = "flex"; }}
                              />
                              <div className={styles.thumbEmpty} style={{ display: "none" }}>📷</div>
                            </div>
                            <div className={styles.cardTime}>
                              {new Date(s.taken_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Right: calendar */}
            <aside className={styles.calSidebar}>
              <p className={styles.calTitle}>📅 Jump to date</p>
              <MiniCalendar
                activeDates={activeDates}
                selectedDate={calDate}
                onSelect={setCalDate}
              />
              {calDate && (
                <p className={styles.calSelected}>
                  Showing: <strong>{groupLabel(calDate)}</strong>
                </p>
              )}
            </aside>
          </div>
        </main>

        {/* ── Lightbox modal ───────────────────────── */}
        {modalSnap && (
          <div className={styles.overlay} onClick={() => setModalIdx(null)}>
            <button className={styles.navArrow} style={{ left: 16 }}
              onClick={e => { e.stopPropagation(); setModalIdx(i => Math.max(0, i - 1)); }}>‹</button>
            <div className={styles.modal} onClick={e => e.stopPropagation()}>
              <div className={styles.modalHeader}>
                <span>{new Date(modalSnap.taken_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}</span>
                <span className={styles.modalCounter}>{modalIdx + 1} / {flatList.length}</span>
                <button className={styles.closeBtn} onClick={() => setModalIdx(null)}>✕</button>
              </div>
              <div className={styles.modalBody}>
                <img
                  src={`${API}/api/screenshots/${user.user_id}/${modalSnap.id}/image`}
                  alt=""
                  className={styles.fullImg}
                />
              </div>
            </div>
            <button className={styles.navArrow} style={{ right: 16 }}
              onClick={e => { e.stopPropagation(); setModalIdx(i => Math.min(flatList.length - 1, i + 1)); }}>›</button>
          </div>
        )}
      </div>
    </>
  );
}
