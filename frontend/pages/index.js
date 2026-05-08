// ============================================================
// pages/index.js — Login Page
// ============================================================
// This is the first page users see. It sends email + password
// to the FastAPI backend and redirects to the dashboard on success.

import { useState } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import styles from "../styles/Login.module.css";
import API from "../config";

export default function LoginPage() {
  const router = useRouter();

  // Form state — tracks what the user types
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);
  const [showPass, setShowPass] = useState(false);

  // ── Handle login form submit ─────────────────────────────
  async function handleLogin(e) {
    e.preventDefault();   // Don't reload the page
    setError("");

    // Basic validation
    if (!email || !password) {
      setError("Please fill in all fields.");
      return;
    }

    setLoading(true);

    try {
      // Call the FastAPI backend
      const res = await fetch(`${API}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        // ✅ Login success — save user data and route by role
        localStorage.setItem("user", JSON.stringify(data));
        if (data.user_type === "admin") {
          router.push("/admin");
        } else {
          router.push("/dashboard");
        }
      } else {
        // ❌ Login failed — show error message from API
        setError(data.detail || "Login failed. Please try again.");
      }
    } catch (err) {
      // Network error (backend not running, etc.)
      setError("Cannot connect to server. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Head>
        <title>Syntra — Login</title>
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className={styles.page}>
        {/* Animated background blobs */}
        <div className={styles.blob1} />
        <div className={styles.blob2} />

        {/* Login Card */}
        <div className={styles.card}>
          {/* Icon + Title */}
          <div className={styles.header}>
            <div className={styles.iconWrap}>
              <img src="/app_icon.png" alt="Syntra" className={styles.iconImg} />
            </div>
            <h1 className={styles.title}>Syntra</h1>
            <p className={styles.subtitle}>Real-time work sync & tracking</p>
          </div>

          {/* Form */}
          <form onSubmit={handleLogin} className={styles.form}>
            {/* Email field */}
            <div className={styles.fieldGroup}>
              <label className={styles.label}>Email Address</label>
              <div className={styles.inputWrap}>
                <span className={styles.inputIcon}>✉</span>
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

            {/* Password field */}
            <div className={styles.fieldGroup}>
              <label className={styles.label}>Password</label>
              <div className={styles.inputWrap}>
                <span className={styles.inputIcon}>🔒</span>
                <input
                  type={showPass ? "text" : "password"}
                  className={styles.input}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  disabled={loading}
                />
                <button
                  type="button"
                  className={styles.eyeBtn}
                  onClick={() => setShowPass(!showPass)}
                  tabIndex={-1}
                >
                  {showPass ? "🙈" : "👁"}
                </button>
              </div>
            </div>

            {/* Error message */}
            {error && (
              <div className={styles.errorBox}>
                <span>⚠ {error}</span>
              </div>
            )}

            {/* Submit button */}
            <button
              type="submit"
              className={`${styles.loginBtn} ${loading ? styles.loading : ""}`}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className={styles.spinner} />
                  Signing in...
                </>
              ) : (
                "Sign In →"
              )}
            </button>
          </form>

          {/* Register link */}
          <p className={styles.registerText}>
            No account?{" "}
            <a href="/register" className={styles.registerLink}>
              Create one here
            </a>
          </p>
        </div>
      </div>
    </>
  );
}
