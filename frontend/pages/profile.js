// pages/profile.js — User Profile Page

import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import Link from "next/link";
import styles from "../styles/Profile.module.css";
import API from "../config";
import TagInput from "../components/TagInput";

export default function ProfilePage() {
  const router = useRouter();

  const [user, setUser]             = useState(null);
  const [profile, setProfile]       = useState(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileError,   setProfileError]   = useState("");
  const [editing, setEditing]       = useState(false);
  const [loading, setLoading]       = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg]     = useState("");

  // Edit form state
  const [editUsername, setEditUsername]       = useState("");
  const [editDesignation, setEditDesignation] = useState("");
  const [editProject, setEditProject]         = useState("");
  const [editSkills, setEditSkills]           = useState([]);  // string[] for TagInput

  useEffect(() => {
    const stored = localStorage.getItem("user");
    if (!stored) { router.push("/"); return; }
    const u = JSON.parse(stored);
    setUser(u);
    fetchProfile(u.user_id);
  }, []);

  async function fetchProfile(userId) {
    setProfileLoading(true);
    setProfileError("");
    try {
      const res = await fetch(`${API}/api/users/${userId}/profile`);
      if (res.ok) {
        const data = await res.json();
        setProfile(data);
      } else if (res.status === 404) {
        localStorage.removeItem("user");
        router.replace("/?reason=account_not_found");
      } else {
        setProfileError(`Server error ${res.status}. Your session may be stale — try signing out and back in.`);
      }
    } catch {
      setProfileError("Cannot connect to server. Make sure the backend is running.");
    } finally {
      setProfileLoading(false);
    }
  }

  function startEdit() {
    setEditUsername(profile?.username || "");
    setEditDesignation(profile?.designation || "");
    setEditProject(profile?.project || "");
    setEditSkills(
      profile?.skills
        ? profile.skills.split(",").map(s => s.trim()).filter(Boolean)
        : []
    );
    setSuccessMsg("");
    setErrorMsg("");
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
    setSuccessMsg("");
    setErrorMsg("");
  }

  async function saveProfile(e) {
    e.preventDefault();
    if (!editUsername.trim()) { setErrorMsg("Name cannot be empty."); return; }
    setLoading(true);
    setErrorMsg("");
    try {
      const res = await fetch(`${API}/api/users/${user.user_id}/profile`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: editUsername.trim(),
          designation: editDesignation.trim() || null,
          project: editProject || null,
          skills: editSkills.length ? editSkills.join(", ") : null,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setProfile(data);
        // Update localStorage so sidebar shows the new name
        const stored = JSON.parse(localStorage.getItem("user"));
        localStorage.setItem("user", JSON.stringify({ ...stored, username: data.username }));
        setUser(u => ({ ...u, username: data.username }));
        setSuccessMsg("Profile updated successfully.");
        setEditing(false);
      } else {
        setErrorMsg(data.detail || "Failed to update profile.");
      }
    } catch {
      setErrorMsg("Cannot connect to server.");
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    localStorage.removeItem("user");
    router.push("/");
  }

  function formatDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString([], { year: "numeric", month: "long", day: "numeric" });
  }

  if (!user) return null;

  if (profileLoading) return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", fontFamily: "sans-serif", color: "#64748B" }}>
      Loading profile…
    </div>
  );

  if (profileError) return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "100vh", fontFamily: "sans-serif", gap: 12 }}>
      <div style={{ color: "#EF4444", fontSize: 15 }}>⚠ {profileError}</div>
      <button onClick={() => fetchProfile(user.user_id)} style={{ padding: "8px 18px", borderRadius: 8, background: "#4F63D2", color: "#fff", border: "none", cursor: "pointer" }}>
        Retry
      </button>
    </div>
  );

  if (!profile) return null;

  return (
    <>
      <Head><title>Realisieren Pulse — Profile</title></Head>
      <div className={styles.page}>

        {/* ── Sidebar ─────────────────────────────────── */}
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
            <Link className={`${styles.navItem} ${styles.active}`} href="/profile"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg> Profile</Link>
            {user.user_type === "admin" && (
              <Link className={styles.navItem} href="/admin"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> Admin Portal</Link>
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

        {/* ── Main ────────────────────────────────────── */}
        <main className={styles.main}>
          <div className={styles.profileWrap}>

            {/* Top bar */}
            <div className={styles.topBar}>
              <div>
                <h1 className={styles.pageTitle}>My Profile</h1>
                <p className={styles.pageSubtitle}>View and update your account details</p>
              </div>
              {!editing && (
                <button className={styles.editBtn} onClick={startEdit}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  Edit Profile
                </button>
              )}
            </div>

            <div className={styles.profileCard}>
              {!editing ? (
                <>
                  {/* ── Hero identity ──────────────────── */}
                  <div className={styles.heroSection}>
                    <div className={styles.heroBigAvatar}>
                      {profile.username?.charAt(0).toUpperCase()}
                    </div>
                    <div className={styles.heroInfo}>
                      <h2 className={styles.heroName}>{profile.username}</h2>
                      <p className={styles.heroDesig}>{profile.designation || "No designation set"}</p>
                      <div className={styles.heroBadges}>
                        <span className={profile.isactive ? styles.pillActive : styles.pillInactive}>
                          {profile.isactive && <span className={styles.activeDot} />}
                          {profile.isactive ? "Active" : "Inactive"}
                        </span>
                        <span className={styles.pillType}>{profile.user_type}</span>
                      </div>
                    </div>
                  </div>

                  {successMsg && (
                    <div className={styles.successMsg} style={{ margin: "0 36px 4px" }}>{successMsg}</div>
                  )}

                  <div className={styles.profileDivider} />

                  {/* ── 3-column info sections ─────────── */}
                  <div className={styles.sectionsGrid}>
                    <div className={styles.profileSection}>
                      <p className={styles.sectionLabel}>Contact</p>
                      <div className={styles.sectionField}>
                        <span className={styles.fieldLabel}>Email</span>
                        <span className={styles.fieldValue}>{profile.email}</span>
                      </div>
                    </div>

                    <div className={styles.profileSection}>
                      <p className={styles.sectionLabel}>Work Details</p>
                      <div className={styles.sectionField}>
                        <span className={styles.fieldLabel}>Project</span>
                        {profile.project
                          ? <span className={styles.chipProject}>{profile.project}</span>
                          : <span className={styles.chipEmpty}>Not added yet</span>}
                      </div>
                      <div className={styles.sectionField}>
                        <span className={styles.fieldLabel}>Designation</span>
                        {profile.designation
                          ? <span className={styles.fieldValue}>{profile.designation}</span>
                          : <span className={styles.chipEmpty}>Not added yet</span>}
                      </div>
                      <div className={styles.sectionField}>
                        <span className={styles.fieldLabel}>Skills</span>
                        {profile.skills ? (
                          <div className={styles.chipRow}>
                            {profile.skills.split(",").map(s => s.trim()).filter(Boolean).map((s, i) => (
                              <span key={i} className={styles.chipSkill}>{s}</span>
                            ))}
                          </div>
                        ) : (
                          <span className={styles.chipEmpty}>Not added yet</span>
                        )}
                      </div>
                    </div>

                    <div className={styles.profileSection}>
                      <p className={styles.sectionLabel}>Account</p>
                      <div className={styles.sectionField}>
                        <span className={styles.fieldLabel}>Member Since</span>
                        <span className={styles.fieldValue}>{formatDate(profile.created_at)}</span>
                      </div>
                      <div className={styles.sectionField}>
                        <span className={styles.fieldLabel}>Account Type</span>
                        <span className={styles.pillType}>{profile.user_type}</span>
                      </div>
                      <div className={styles.sectionField}>
                        <span className={styles.fieldLabel}>Status</span>
                        <span className={profile.isactive ? styles.pillActive : styles.pillInactive}>
                          {profile.isactive && <span className={styles.activeDot} />}
                          {profile.isactive ? "Active" : "Inactive"}
                        </span>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div className={styles.editHeader}>
                    <h2 className={styles.editTitle}>Edit Profile</h2>
                    <p className={styles.editSubtitle}>Update your personal and work details</p>
                  </div>
                  <div className={styles.editBody}>
                    <form onSubmit={saveProfile} className={styles.editForm}>
                      <div className={styles.editGrid}>
                        <div className={styles.formField}>
                          <label className={styles.formLabel}>Full Name</label>
                          <input
                            className={styles.formInput}
                            type="text"
                            value={editUsername}
                            onChange={(e) => setEditUsername(e.target.value)}
                            placeholder="Your name"
                            disabled={loading}
                          />
                        </div>

                        <div className={styles.formField}>
                          <label className={styles.formLabel}>Email</label>
                          <div className={styles.formInputReadonly}>{profile.email}</div>
                        </div>

                        <div className={styles.formField}>
                          <label className={styles.formLabel}>Project</label>
                          <select
                            className={styles.formInput}
                            value={editProject}
                            onChange={(e) => setEditProject(e.target.value)}
                            disabled={loading}
                          >
                            <option value="">Select project...</option>
                            <option value="Bold">Bold</option>
                            <option value="MView">MView</option>
                          </select>
                        </div>

                        <div className={styles.formField}>
                          <label className={styles.formLabel}>Designation</label>
                          <input
                            className={styles.formInput}
                            type="text"
                            value={editDesignation}
                            onChange={(e) => setEditDesignation(e.target.value)}
                            placeholder="e.g. Frontend Dev, Marketing"
                            disabled={loading}
                          />
                        </div>
                      </div>

                      <div className={styles.formField} style={{ marginTop: 4 }}>
                        <label className={styles.formLabel}>
                          Skills <span style={{ color: "#94A3B8", fontWeight: 400, fontSize: 11 }}>(Enter, comma, or space to add)</span>
                        </label>
                        <TagInput tags={editSkills} onChange={setEditSkills} placeholder="e.g. Python, React, UI/UX" disabled={loading} />
                      </div>

                      {errorMsg   && <div className={styles.errorMsg}>{errorMsg}</div>}
                      {successMsg && <div className={styles.successMsg}>{successMsg}</div>}

                      <div className={styles.formActions}>
                        <button type="submit" className={styles.saveBtn} disabled={loading}>
                          {loading ? "Saving..." : "Save Changes"}
                        </button>
                        <button type="button" className={styles.cancelBtn} onClick={cancelEdit} disabled={loading}>
                          Cancel
                        </button>
                      </div>
                    </form>
                  </div>
                </>
              )}
            </div>
          </div>
        </main>
      </div>
    </>
  );
}
