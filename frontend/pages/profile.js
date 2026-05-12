// pages/profile.js — User Profile Page

import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import Link from "next/link";
import styles from "../styles/Profile.module.css";
import API from "../config";

export default function ProfilePage() {
  const router = useRouter();

  const [user, setUser]           = useState(null);
  const [profile, setProfile]     = useState(null);
  const [editing, setEditing]     = useState(false);
  const [loading, setLoading]     = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg]   = useState("");

  // Edit form state
  const [editUsername, setEditUsername]       = useState("");
  const [editDesignation, setEditDesignation] = useState("");
  const [editProject, setEditProject]         = useState("");
  const [editSkills, setEditSkills]           = useState("");

  useEffect(() => {
    const stored = localStorage.getItem("user");
    if (!stored) { router.push("/"); return; }
    const u = JSON.parse(stored);
    setUser(u);
    fetchProfile(u.user_id);
  }, []);

  async function fetchProfile(userId) {
    try {
      const res = await fetch(`${API}/api/users/${userId}/profile`);
      if (res.ok) {
        const data = await res.json();
        setProfile(data);
      }
    } catch (_) {}
  }

  function startEdit() {
    setEditUsername(profile?.username || "");
    setEditDesignation(profile?.designation || "");
    setEditProject(profile?.project || "");
    setEditSkills(profile?.skills || "");
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
          skills: editSkills.trim() || null,
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

  if (!user || !profile) return null;

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
            <Link className={styles.navItem} href="/dashboard"><span>📊</span> Dashboard</Link>
            <Link className={styles.navItem} href="/screenshots"><span>📷</span> Screenshots</Link>
            <Link className={styles.navItem} href="/activity"><span>🖥</span> Activity</Link>
            <Link className={styles.navItem} href="/tasks"><span>✅</span> My Tasks</Link>
            <Link className={`${styles.navItem} ${styles.active}`} href="/profile"><span>👤</span> Profile</Link>
            {user.user_type === "admin" && (
              <Link className={styles.navItem} href="/admin"><span>🛡</span> Admin Portal</Link>
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
                    {profile.skills
                      ? <span className={styles.fieldValue}>{profile.skills}</span>
                      : <span className={styles.fieldEmpty}>Not set</span>}
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
                    <label className={styles.formLabel}>Skills</label>
                    <input
                      className={styles.formInput}
                      type="text"
                      value={editSkills}
                      onChange={(e) => setEditSkills(e.target.value)}
                      placeholder="e.g. Python, React, UI/UX"
                      disabled={loading}
                    />
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
