// pages/index.js — Login Page with per-field validation

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import styles from "../styles/Login.module.css";
import Link from "next/link";
import API from "../config";

const EMAIL_RE = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;

function validateEmail(v) {
  const s = v.trim();
  if (!s) return "Email is required";
  if (/\s/.test(s)) return "Spaces are not allowed in email";
  if (!EMAIL_RE.test(s)) return "Enter a valid email address (e.g. name@domain.com)";
  return "";
}

function validatePassword(v) {
  if (!v || !v.trim()) return "Password is required";
  return "";
}

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
  const [apiError, setApiError] = useState("");
  const [loading,  setLoading]  = useState(false);
  const [showPass, setShowPass] = useState(false);

  const [errors,  setErrors]  = useState({});
  const [touched, setTouched] = useState({});

  const setFieldError = useCallback((field, msg) => {
    setErrors(prev => ({ ...prev, [field]: msg }));
  }, []);

  useEffect(() => {
    const { reason } = router.query;
    if (reason === "account_not_found") {
      setApiError("Your account was not found on the server. Please register or sign in with the correct credentials.");
    }
  }, [router.query]);

  function validateAll() {
    const e = {
      email:    validateEmail(email),
      password: validatePassword(password),
    };
    setErrors(e);
    setTouched({ email: true, password: true });
    return Object.values(e).every(v => !v);
  }

  async function handleLogin(e) {
    e.preventDefault();
    setApiError("");
    if (!validateAll()) return;
    setLoading(true);
    try {
      const res  = await fetch(`${API}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        localStorage.setItem("user", JSON.stringify(data));
        router.push(data.user_type === "admin" ? "/admin" : "/dashboard");
      } else {
        const detail = data.detail || "";
        if (typeof detail === "object" && Array.isArray(detail)) {
          setApiError(detail.map(d => d.msg).join(" | "));
        } else {
          setApiError(detail || "Login failed. Please try again.");
        }
      }
    } catch {
      setApiError("Cannot connect to server. Is the backend running?");
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

            <form onSubmit={handleLogin} className={styles.form} noValidate>
              {/* Email */}
              <div className={styles.fieldGroup}>
                <label className={styles.label}>
                  Email Address<span className={styles.required}>*</span>
                </label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m2 7 10 7 10-7"/></svg>
                  </span>
                  <input
                    type="email"
                    className={`${styles.input} ${touched.email && errors.email ? styles.inputError : ""}`}
                    placeholder="you@example.com"
                    value={email}
                    onChange={e => {
                      const val = e.target.value.replace(/\s/g, "");
                      setEmail(val);
                      if (touched.email) setFieldError("email", validateEmail(val));
                    }}
                    onBlur={() => {
                      setTouched(prev => ({ ...prev, email: true }));
                      setFieldError("email", validateEmail(email));
                    }}
                    autoComplete="email"
                    disabled={loading}
                  />
                </div>
                {touched.email && errors.email && (
                  <span className={styles.fieldError}>⚠ {errors.email}</span>
                )}
              </div>

              {/* Password */}
              <div className={styles.fieldGroup}>
                <label className={styles.label}>
                  Password<span className={styles.required}>*</span>
                </label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                  </span>
                  <input
                    type={showPass ? "text" : "password"}
                    className={`${styles.input} ${touched.password && errors.password ? styles.inputError : ""}`}
                    placeholder="••••••••"
                    value={password}
                    onChange={e => {
                      setPassword(e.target.value);
                      if (touched.password) setFieldError("password", validatePassword(e.target.value));
                    }}
                    onBlur={() => {
                      setTouched(prev => ({ ...prev, password: true }));
                      setFieldError("password", validatePassword(password));
                    }}
                    autoComplete="current-password"
                    disabled={loading}
                  />
                  <button type="button" className={styles.eyeBtn} onClick={() => setShowPass(p => !p)} tabIndex={-1}>
                    {showPass ? "Hide" : "Show"}
                  </button>
                </div>
                {touched.password && errors.password && (
                  <span className={styles.fieldError}>⚠ {errors.password}</span>
                )}
              </div>

              <div style={{ textAlign: "right", marginTop: -8, marginBottom: 4 }}>
                <Link href="/forgot-password" style={{ fontSize: 13, color: "#4F63D2", textDecoration: "none" }}>
                  Forgot Password?
                </Link>
              </div>

              {apiError && <div className={styles.errorBox}><span>⚠ {apiError}</span></div>}

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
