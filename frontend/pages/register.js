// ============================================================
// pages/register.js — Create Account Page
// ============================================================

import { useState } from "react";
import API from "../config";
import { useRouter } from "next/router";
import Head from "next/head";
import styles from "../styles/Login.module.css";

export default function RegisterPage() {
  const router = useRouter();

  const [username, setUsername] = useState("");
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [userType, setUserType] = useState("user");
  const [error, setError]       = useState("");
  const [success, setSuccess]   = useState("");
  const [loading, setLoading]   = useState(false);

  async function handleRegister(e) {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!username || !email || !password) {
      setError("Please fill in all fields.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API}/api/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password, user_type: userType }),
      });
      const data = await res.json();

      if (res.ok && data.success) {
        setSuccess("Account created! Redirecting to login...");
        setTimeout(() => router.push("/"), 2000);
      } else {
        setError(data.detail || "Registration failed.");
      }
    } catch {
      setError("Cannot connect to server.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Head><title>Syntra — Register</title></Head>
      <div className={styles.page}>
        <div className={styles.blob1} />
        <div className={styles.blob2} />
        <div className={styles.card}>
          <div className={styles.header}>
            <div className={styles.iconWrap}><span className={styles.icon}>⚡</span></div>
            <h1 className={styles.title}>Create Account</h1>
            <p className={styles.subtitle}>Join Syntra today</p>
          </div>

          <form onSubmit={handleRegister} className={styles.form}>
            <div className={styles.fieldGroup}>
              <label className={styles.label}>Full Name</label>
              <div className={styles.inputWrap}>
                <span className={styles.inputIcon}>👤</span>
                <input
                  type="text"
                  className={styles.input}
                  placeholder="Your name"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

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
                  disabled={loading}
                />
              </div>
            </div>

            <div className={styles.fieldGroup}>
              <label className={styles.label}>Password</label>
              <div className={styles.inputWrap}>
                <span className={styles.inputIcon}>🔒</span>
                <input
                  type="password"
                  className={styles.input}
                  placeholder="Min. 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                />
              </div>
            </div>

            <div className={styles.fieldGroup}>
              <label className={styles.label}>Account Type</label>
              <div className={styles.inputWrap}>
                <span className={styles.inputIcon}>🛡</span>
                <select
                  className={styles.input}
                  value={userType}
                  onChange={(e) => setUserType(e.target.value)}
                  disabled={loading}
                  style={{ cursor: "pointer" }}
                >
                  <option value="user">Employee (User)</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>

            {error   && <div className={styles.errorBox}><span>⚠ {error}</span></div>}
            {success && <div className={styles.successBox}><span>✅ {success}</span></div>}

            <button type="submit" className={styles.loginBtn} disabled={loading}>
              {loading ? "Creating..." : "Create Account →"}
            </button>
          </form>

          <p className={styles.registerText}>
            Already have an account?{" "}
            <a href="/" className={styles.registerLink}>Sign in</a>
          </p>
        </div>
      </div>
    </>
  );
}
