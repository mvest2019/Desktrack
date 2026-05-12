// pages/register.js — Register Page (split-screen dark layout)

import { useState } from "react";
import API from "../config";
import { useRouter } from "next/router";
import Head from "next/head";
import styles from "../styles/Login.module.css";

export default function RegisterPage() {
  const router = useRouter();

  const [username,    setUsername]    = useState("");
  const [email,       setEmail]       = useState("");
  const [password,    setPassword]    = useState("");
  const [showPass,    setShowPass]    = useState(false);
  const [userType,    setUserType]    = useState("user");
  const [project,     setProject]     = useState("");
  const [designation, setDesignation] = useState("");
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
        body: JSON.stringify({ username, email, password, user_type: userType, project, designation }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        localStorage.setItem("user", JSON.stringify({
          user_id: data.user_id, username, email,
          user_type: userType, project, designation,
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

            <div className={styles.heroPill}>⚡ AI-powered workforce intelligence</div>

            <h1 className={styles.heroTitle}>
              Track every second of <span className={styles.heroAccent}>productivity.</span>
            </h1>
            <p className={styles.heroDesc}>
              Empower your team with smarter workflows, seamless collaboration, and AI-powered task analysis that helps turn daily work into actionable insights.
            </p>
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
                  <span className={styles.inputIcon}>👤</span>
                  <input type="text" className={styles.input} placeholder="Your name"
                    value={username} onChange={(e) => setUsername(e.target.value)}
                    autoComplete="name" disabled={loading} />
                </div>
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.label}>Email Address</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>✉</span>
                  <input type="email" className={styles.input} placeholder="you@example.com"
                    value={email} onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email" disabled={loading} />
                </div>
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.label}>Password</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>🔒</span>
                  <input type={showPass ? "text" : "password"} className={styles.input}
                    placeholder="Min. 6 characters" value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password" disabled={loading} />
                  <button type="button" className={styles.eyeBtn}
                    onClick={() => setShowPass(!showPass)} tabIndex={-1}>
                    {showPass ? "🙈" : "👁"}
                  </button>
                </div>
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.label}>Account Type</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>🛡</span>
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
                  <span className={styles.inputIcon}>🌐</span>
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
                  <span className={styles.inputIcon}>💼</span>
                  <input type="text" className={styles.input}
                    placeholder="e.g. Frontend Dev, Marketing"
                    value={designation} onChange={(e) => setDesignation(e.target.value)}
                    disabled={loading} />
                </div>
              </div>

              {error && <div className={styles.errorBox}><span>⚠ {error}</span></div>}

              <button type="submit" className={styles.loginBtn} disabled={loading}>
                {loading ? (<><span className={styles.spinner} /> Creating...</>) : "Create Account →"}
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
