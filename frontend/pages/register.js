// pages/register.js — Register Page (split-screen dark layout)

import { useState } from "react";
import API from "../config";
import { useRouter } from "next/router";
import Head from "next/head";
import styles from "../styles/Login.module.css";
import TagInput from "../components/TagInput";

export default function RegisterPage() {
  const router = useRouter();

  const [username,    setUsername]    = useState("");
  const [email,       setEmail]       = useState("");
  const [password,    setPassword]    = useState("");
  const [showPass,    setShowPass]    = useState(false);
  const [userType,    setUserType]    = useState("user");
  const [project,     setProject]     = useState("");
  const [designation, setDesignation] = useState("");
  const [skills,      setSkills]      = useState([]);  // array of tag strings
  const [error,       setError]       = useState("");
  const [loading,     setLoading]     = useState(false);

  async function handleRegister(e) {
    e.preventDefault();
    setError("");
    if (!username || !email || !password || !project) {
      setError("Please fill in all required fields.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setLoading(true);
    try {
      const res  = await fetch(`${API}/api/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password, user_type: userType, project, designation, skills: skills.join(", ") }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        localStorage.setItem("user", JSON.stringify({
          user_id: data.user_id, username, email,
          user_type: userType, project, designation, skills: skills.join(", "),
        }));
        router.push("/dashboard");
      } else {
        setError(data.detail || "Registration failed.");
      }
    } catch {
      setError("Cannot connect to server. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Head>
        <title>Realisieren Pulse — Register</title>
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className={styles.page}>
        {/* ── Hero panel (left) ─────────────────────────── */}
        <div className={styles.heroPanel}>
          <div className={styles.heroInner}>
            <div className={styles.heroBrand}>
              <img src="/app_icon.png" alt="Realisieren Pulse" className={styles.heroBrandImg} />
              <div className={styles.heroBrandText}>
                <div className={styles.heroBrandName}>Realisieren</div>
                <div className={styles.heroBrandSub}>PULSE</div>
              </div>
            </div>

            <div className={styles.heroPill}>AI-powered workforce intelligence</div>

            <h1 className={styles.heroTitle}>
              Track every second of <span className={styles.heroAccent}>productivity.</span>
            </h1>
            <p className={styles.heroDesc}>
              Empower your team with smarter workflows, seamless collaboration, and AI-powered task analysis that helps turn daily work into actionable insights.
            </p>

            <div className={styles.heroStats}>
              <div className={styles.heroStat}>
                <span className={styles.heroStatVal}>Real‑time</span>
                <span className={styles.heroStatLabel}>Screenshot sync</span>
              </div>
              <div className={styles.heroStatDivider} />
              <div className={styles.heroStat}>
                <span className={styles.heroStatVal}>AI‑powered</span>
                <span className={styles.heroStatLabel}>Activity insights</span>
              </div>
              <div className={styles.heroStatDivider} />
              <div className={styles.heroStat}>
                <span className={styles.heroStatVal}>Secure</span>
                <span className={styles.heroStatLabel}>End‑to‑end data</span>
              </div>
            </div>

          </div>
        </div>

        {/* ── Form panel (right) ────────────────────────── */}
        <div className={styles.formPanel}>
          <div className={styles.formInner}>
            <h2 className={styles.formTitle}>Create account</h2>
            <p className={styles.formSubtitle}>Join your workspace on Realisieren Pulse.</p>

            <form onSubmit={handleRegister} className={styles.form}>
              <div className={styles.fieldGroup}>
                <label className={styles.label}>Full Name</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                  </span>
                  <input type="text" className={styles.input} placeholder="Your name"
                    value={username} onChange={(e) => setUsername(e.target.value)}
                    autoComplete="name" disabled={loading} />
                </div>
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.label}>Email Address</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m2 7 10 7 10-7"/></svg>
                  </span>
                  <input type="email" className={styles.input} placeholder="you@example.com"
                    value={email} onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email" disabled={loading} />
                </div>
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.label}>Password</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                  </span>
                  <input type={showPass ? "text" : "password"} className={styles.input}
                    placeholder="Min. 6 characters" value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password" disabled={loading} />
                  <button type="button" className={styles.eyeBtn}
                    onClick={() => setShowPass(!showPass)} tabIndex={-1}>
                    {showPass ? "Hide" : "Show"}
                  </button>
                </div>
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.label}>Account Type</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                  </span>
                  <select className={styles.input} value={userType}
                    onChange={(e) => setUserType(e.target.value)} disabled={loading}>
                    <option value="user">Employee (User)</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.label}>Project</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
                  </span>
                  <select className={styles.input} value={project}
                    onChange={(e) => setProject(e.target.value)} disabled={loading}>
                    <option value="">Select project...</option>
                    <option value="Bold">Bold</option>
                    <option value="MView">MView</option>
                  </select>
                </div>
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.label}>Designation</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
                  </span>
                  <input type="text" className={styles.input}
                    placeholder="e.g. Frontend Dev, Marketing"
                    value={designation} onChange={(e) => setDesignation(e.target.value)}
                    disabled={loading} />
                </div>
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.label}>Skills <span style={{ color: "#94A3B8", fontWeight: 400, fontSize: 11 }}>(type then press Enter, comma, or space)</span></label>
                <TagInput tags={skills} onChange={setSkills} placeholder="e.g. React, Node, UI/UX" disabled={loading} />
              </div>

              {error && <div className={styles.errorBox}><span>{error}</span></div>}

              <button type="submit" className={styles.loginBtn} disabled={loading}>
                {loading ? (<><span className={styles.spinner} /> Creating...</>) : "Create account"}
              </button>
            </form>

            <p className={styles.registerText}>
              Already have an account?{" "}
              <a href="/" className={styles.registerLink}>Sign in</a>
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
