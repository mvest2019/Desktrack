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
      } else {
        setProfileError(`Server error ${res.status}. Please try again.`);
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
            <Link className={styles.navItem} href="/dashboard"><span>DB</span> Dashboard</Link>
            <Link className={styles.navItem} href="/screenshots"><span>SC</span> Screenshots</Link>
            <Link className={styles.navItem} href="/activity"><span>AC</span> Activity</Link>
            <Link className={styles.navItem} href="/tasks"><span>TK</span> My Tasks</Link>
            <Link className={`${styles.navItem} ${styles.active}`} href="/profile"><span>PF</span> Profile</Link>
            {user.user_type === "admin" && (
              <Link className={styles.navItem} href="/admin"><span>AD</span> Admin Portal</Link>
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
          <div className={styles.topBar}>
            <h1 className={styles.pageTitle}>My Profile</h1>
            <p className={styles.pageSubtitle}>View and update your account details</p>
          </div>

          <div className={styles.card}>
            {!editing ? (
              <>
                <div className={styles.cardHeader}>
                  <span className={styles.cardTitle}>Account Details</span>
                  <button className={styles.editBtn} onClick={startEdit}>Edit Profile</button>
                </div>

                {/* Avatar + name row */}
                <div className={styles.avatarRow}>
                  <div className={styles.bigAvatar}>
                    {profile.username?.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <p className={styles.avatarName}>{profile.username}</p>
                    <p className={styles.avatarSub}>{profile.designation || "No designation set"}</p>
                  </div>
                </div>

                {successMsg && <div className={styles.successMsg}>{successMsg}</div>}

                {/* Fields grid */}
                <div className={styles.fieldsGrid}>
                  <div className={styles.fieldItem}>
                    <span className={styles.fieldLabel}>Email</span>
                    <span className={styles.fieldValue}>{profile.email}</span>
                  </div>

                  <div className={styles.fieldItem}>
                    <span className={styles.fieldLabel}>Account Type</span>
                    <span className={styles.fieldValue} style={{ textTransform: "capitalize" }}>{profile.user_type}</span>
                  </div>

                  <div className={styles.fieldItem}>
                    <span className={styles.fieldLabel}>Project</span>
                    {profile.project
                      ? <span className={styles.projectBadge}>{profile.project}</span>
                      : <span className={styles.fieldEmpty}>Not set</span>}
                  </div>

                  <div className={styles.fieldItem}>
                    <span className={styles.fieldLabel}>Designation</span>
                    {profile.designation
                      ? <span className={styles.fieldValue}>{profile.designation}</span>
                      : <span className={styles.fieldEmpty}>Not set</span>}
                  </div>

                  <div className={styles.fieldItem}>
                    <span className={styles.fieldLabel}>Skills</span>
                    {profile.skills ? (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 2 }}>
                        {profile.skills.split(",").map(s => s.trim()).filter(Boolean).map((s, i) => (
                          <span key={i} style={{ background: "#EEF2FF", color: "#4F63D2", borderRadius: 20, padding: "3px 10px", fontSize: 12, fontWeight: 600 }}>
                            {s}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className={styles.fieldEmpty}>Not set</span>
                    )}
                  </div>

                  <div className={styles.fieldItem}>
                    <span className={styles.fieldLabel}>Member Since</span>
                    <span className={styles.fieldValue}>{formatDate(profile.created_at)}</span>
                  </div>

                  <div className={styles.fieldItem}>
                    <span className={styles.fieldLabel}>Status</span>
                    <span className={styles.fieldValue} style={{ color: profile.isactive ? "#34D399" : "#F87171" }}>
                      {profile.isactive ? "Active" : "Inactive"}
                    </span>
                  </div>
                </div>
              </>
            ) : (
              <>
                <div className={styles.cardHeader}>
                  <span className={styles.cardTitle}>Edit Profile</span>
                </div>

                <form onSubmit={saveProfile} className={styles.editForm}>
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
                    <label className={styles.formLabel}>Email (cannot be changed)</label>
                    <div className={styles.formInputReadonly}>{profile.email}</div>
                  </div>

                  <div className={styles.formField}>
                    <label className={styles.formLabel}>Project / Website</label>
                    <select
                      className={styles.formInput}
                      value={editProject}
                      onChange={(e) => setEditProject(e.target.value)}
                      disabled={loading}
                      style={{ cursor: "pointer", background: "#1e2436", color: "#ffffff" }}
                    >
                      <option value=""   style={{ background: "#1e2436", color: "#ffffff" }}>Select project...</option>
                      <option value="Bold"  style={{ background: "#1e2436", color: "#ffffff" }}>Bold</option>
                      <option value="MView" style={{ background: "#1e2436", color: "#ffffff" }}>MView</option>
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

                  <div className={styles.formField}>
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
              </>
            )}
          </div>
        </main>
      </div>
    </>
  );
}
