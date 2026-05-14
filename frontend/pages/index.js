// pages/index.js — Login Page (split-screen dark layout)

import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import styles from "../styles/Login.module.css";
import API from "../config";

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    const stored = localStorage.getItem("user");
    if (stored) {
      const u = JSON.parse(stored);
      router.replace(u.user_type === "admin" ? "/admin" : "/dashboard");
    }
  }, []);

  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [error,    setError]    = useState("");
  const [loading,  setLoading]  = useState(false);
  const [showPass, setShowPass] = useState(false);

  useEffect(() => {
    const { reason } = router.query;
    if (reason === "account_not_found") {
      setError("Your account was not found on the server. Please register or sign in with the correct credentials.");
    }
  }, [router.query]);

  async function handleLogin(e) {
    e.preventDefault();
    setError("");
    if (!email || !password) { setError("Please fill in all fields."); return; }
    setLoading(true);
    try {
      const res  = await fetch(`${API}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        localStorage.setItem("user", JSON.stringify(data));
        router.push(data.user_type === "admin" ? "/admin" : "/dashboard");
      } else {
        setError(data.detail || "Login failed. Please try again.");
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
        <title>Realisieren Pulse — Login</title>
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
            <h2 className={styles.formTitle}>Welcome back</h2>
            <p className={styles.formSubtitle}>Sign in to continue to your workspace.</p>

            <form onSubmit={handleLogin} className={styles.form}>
              <div className={styles.fieldGroup}>
                <label className={styles.label}>Email Address</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m2 7 10 7 10-7"/></svg>
                  </span>
                  <input
                    type="email"
                    className={styles.input}
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    disabled={loading}
                  />
                </div>
              </div>

              <div className={styles.fieldGroup}>
                <label className={styles.label}>Password</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                  </span>
                  <input
                    type={showPass ? "text" : "password"}
                    className={styles.input}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    disabled={loading}
                  />
                  <button type="button" className={styles.eyeBtn} onClick={() => setShowPass(!showPass)} tabIndex={-1}>
                    {showPass ? "Hide" : "Show"}
                  </button>
                </div>
              </div>

              {error && <div className={styles.errorBox}><span>{error}</span></div>}

              <button type="submit" className={styles.loginBtn} disabled={loading}>
                {loading ? (<><span className={styles.spinner} /> Signing in...</>) : "Sign in"}
              </button>
            </form>

            <p className={styles.registerText}>
              New to Realisieren?{" "}
              <a href="/register" className={styles.registerLink}>Create an account</a>
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
