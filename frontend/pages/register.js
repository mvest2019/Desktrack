// pages/register.js — Create Account Page

import { useState } from "react";
import API from "../config";
import { useRouter } from "next/router";
import Head from "next/head";
import styles from "../styles/Login.module.css";

export default function RegisterPage() {
  const router = useRouter();

  const [username, setUsername]       = useState("");
  const [email, setEmail]             = useState("");
  const [password, setPassword]       = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [userType, setUserType]       = useState("user");
  const [project, setProject]         = useState("");
  const [designation, setDesignation] = useState("");
  const [error, setError]             = useState("");
  const [success, setSuccess]         = useState("");
  const [loading, setLoading]         = useState(false);

  async function handleRegister(e) {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!username || !email || !password || !project) {
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
        body: JSON.stringify({ username, email, password, user_type: userType, project, designation }),
      });
      const data = await res.json();

      if (res.ok && data.success) {
        // Auto-login: store user in localStorage and go straight to dashboard
        localStorage.setItem("user", JSON.stringify({
          user_id: data.user_id,
          username,
          email,
          user_type: userType,
          project,
          designation,
        }));
        router.push("/dashboard");
      } else {
        setError(data.detail || "Registration failed.");
      }
    } catch {
      setError("Cannot connect to server.");
    } finally {
      setLoading(false);
    }
  }

  // Compact input style — smaller padding so all fields fit
  const inputStyle = { padding: "10px 14px 10px 38px", fontSize: "13px" };
  const labelStyle = { fontSize: "12px" };

  return (
    <>
      <Head><title>Realisieren Pulse — Register</title></Head>
      <div className={styles.page}>
        <div className={styles.blob1} />
        <div className={styles.blob2} />

        {/* Narrower card, tighter padding */}
        <div className={styles.card} style={{ padding: "28px 32px", maxWidth: 400 }}>

          {/* Compact header */}
          <div className={styles.header} style={{ marginBottom: 20 }}>
            <div className={styles.iconWrap} style={{ width: 48, height: 48, borderRadius: 14, marginBottom: 10 }}>
              <span className={styles.icon} style={{ fontSize: 22 }}>⚡</span>
            </div>
            <h1 className={styles.title} style={{ fontSize: 22, marginBottom: 4 }}>Create Account</h1>
            <p className={styles.subtitle}>Join Realisieren Pulse today</p>
          </div>

          <form onSubmit={handleRegister} className={styles.form} style={{ gap: 12 }}>

            {/* Full Name */}
            <div className={styles.fieldGroup} style={{ gap: 5 }}>
              <label className={styles.label} style={labelStyle}>Full Name</label>
              <div className={styles.inputWrap}>
                <span className={styles.inputIcon}>👤</span>
                <input type="text" className={styles.input} style={inputStyle}
                  placeholder="Your name" value={username}
                  onChange={(e) => setUsername(e.target.value)} disabled={loading} />
              </div>
            </div>

            {/* Email */}
            <div className={styles.fieldGroup} style={{ gap: 5 }}>
              <label className={styles.label} style={labelStyle}>Email Address</label>
              <div className={styles.inputWrap}>
                <span className={styles.inputIcon}>✉</span>
                <input type="email" className={styles.input} style={inputStyle}
                  placeholder="you@example.com" value={email}
                  onChange={(e) => setEmail(e.target.value)} disabled={loading} />
              </div>
            </div>

            {/* Password + eye toggle */}
            <div className={styles.fieldGroup} style={{ gap: 5 }}>
              <label className={styles.label} style={labelStyle}>Password</label>
              <div className={styles.inputWrap}>
                <span className={styles.inputIcon}>🔒</span>
                <input
                  type={showPassword ? "text" : "password"}
                  className={styles.input}
                  style={{ ...inputStyle, paddingRight: 40 }}
                  placeholder="Min. 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={loading}
                />
                <button type="button" className={styles.eyeBtn}
                  onClick={() => setShowPassword(v => !v)}
                  tabIndex={-1}>
                  {showPassword ? "🙈" : "👁"}
                </button>
              </div>
            </div>

            {/* Account Type */}
            <div className={styles.fieldGroup} style={{ gap: 5 }}>
              <label className={styles.label} style={labelStyle}>Account Type</label>
              <div className={styles.inputWrap}>
                <span className={styles.inputIcon}>🛡</span>
                <select className={styles.input} style={{ ...inputStyle, cursor: "pointer" }}
                  value={userType} onChange={(e) => setUserType(e.target.value)} disabled={loading}>
                  <option value="user">Employee (User)</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>

            {/* Project */}
            <div className={styles.fieldGroup} style={{ gap: 5 }}>
              <label className={styles.label} style={labelStyle}>Project / Website</label>
              <div className={styles.inputWrap}>
                <span className={styles.inputIcon}>🌐</span>
                <select className={styles.input} style={{ ...inputStyle, cursor: "pointer" }}
                  value={project} onChange={(e) => setProject(e.target.value)} disabled={loading}>
                  <option value="">Select project...</option>
                  <option value="Bold">Bold</option>
                  <option value="MView">MView</option>
                </select>
              </div>
            </div>

            {/* Designation */}
            <div className={styles.fieldGroup} style={{ gap: 5 }}>
              <label className={styles.label} style={labelStyle}>Designation</label>
              <div className={styles.inputWrap}>
                <span className={styles.inputIcon}>💼</span>
                <input type="text" className={styles.input} style={inputStyle}
                  placeholder="e.g. Frontend Dev, Marketing"
                  value={designation} onChange={(e) => setDesignation(e.target.value)} disabled={loading} />
              </div>
            </div>

            {error   && <div className={styles.errorBox} style={{ padding: "9px 12px", fontSize: 12 }}><span>⚠ {error}</span></div>}
            {success && <div className={styles.successBox} style={{ padding: "9px 12px", fontSize: 12 }}><span>✅ {success}</span></div>}

            <button type="submit" className={styles.loginBtn}
              style={{ padding: "12px", fontSize: 14, marginTop: 2 }} disabled={loading}>
              {loading ? "Creating..." : "Create Account →"}
            </button>
          </form>

          <p className={styles.registerText} style={{ marginTop: 16, fontSize: 12 }}>
            Already have an account?{" "}
            <a href="/" className={styles.registerLink}>Sign in</a>
          </p>
        </div>
      </div>
    </>
  );
}
