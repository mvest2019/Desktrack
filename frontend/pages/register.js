// pages/register.js — Register Page with full validation

import { useState, useCallback } from "react";
import API from "../config";
import { useRouter } from "next/router";
import Head from "next/head";
import styles from "../styles/Login.module.css";
import TagInput from "../components/TagInput";

// ── Shared validation rules (mirrors backend) ──────────────────────────────
const EMAIL_RE = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;
const SPECIAL_CHARS_RE = /[!@#$%^&*()\[\]{}\-_=+|\\;:'",.<>?/`~]/;

function validateName(v) {
  const s = v.trim();
  if (!s) return "Full name is required";
  if (/\d/.test(s)) return "Numbers are not allowed in name";
  if (/[^a-zA-Z\s]/.test(s)) return "Special characters are not allowed in name";
  return "";
}

function validateEmail(v) {
  const s = v.trim();
  if (!s) return "Email is required";
  if (/\s/.test(s)) return "Spaces are not allowed in email";
  if (!EMAIL_RE.test(s)) return "Enter a valid email address (e.g. name@domain.com)";
  return "";
}

function validatePassword(v) {
  if (!v) return "Password is required";
  if (/\s/.test(v)) return "Spaces are not allowed in password";
  if (v.length < 8) return "Password must be at least 8 characters";
  if (!/[A-Z]/.test(v)) return "Password must contain at least one uppercase letter";
  if (!/[a-z]/.test(v)) return "Password must contain at least one lowercase letter";
  if (!/\d/.test(v)) return "Password must contain at least one number";
  if (!SPECIAL_CHARS_RE.test(v)) return "Password must contain at least one special character";
  return "";
}

function getPasswordStrength(v) {
  if (!v) return 0;
  let score = 0;
  if (v.length >= 8) score++;
  if (/[A-Z]/.test(v) && /[a-z]/.test(v)) score++;
  if (/\d/.test(v)) score++;
  if (SPECIAL_CHARS_RE.test(v)) score++;
  return score;
}

const STRENGTH_LABELS = ["", "Weak", "Fair", "Good", "Strong"];
const STRENGTH_CLASS  = ["", "s1",   "s2",  "s3",  "s4"];

export default function RegisterPage() {
  const router = useRouter();

  const [username,    setUsername]    = useState("");
  const [email,       setEmail]       = useState("");
  const [password,    setPassword]    = useState("");
  const [showPass,    setShowPass]    = useState(false);
  const [userType,    setUserType]    = useState("user");
  const [project,     setProject]     = useState("");
  const [designation, setDesignation] = useState("");
  const [skills,      setSkills]      = useState([]);
  const [loading,     setLoading]     = useState(false);
  const [apiError,    setApiError]    = useState("");

  // Per-field errors (only shown after blur or submit attempt)
  const [errors,   setErrors]   = useState({});
  const [touched,  setTouched]  = useState({});

  const strength      = getPasswordStrength(password);
  const strengthLabel = STRENGTH_LABELS[strength];
  const strengthClass = STRENGTH_CLASS[strength];

  const setFieldError = useCallback((field, msg) => {
    setErrors(prev => ({ ...prev, [field]: msg }));
  }, []);

  const handleBlur = (field, validator, value) => {
    setTouched(prev => ({ ...prev, [field]: true }));
    setFieldError(field, validator(value));
  };

  function validateAll() {
    const e = {
      username: validateName(username),
      email:    validateEmail(email),
      password: validatePassword(password),
      project:  project ? "" : "Please select a project",
    };
    setErrors(e);
    setTouched({ username: true, email: true, password: true, project: true });
    return Object.values(e).every(v => !v);
  }

  async function handleRegister(e) {
    e.preventDefault();
    setApiError("");
    if (!validateAll()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/register`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({
          username:    username.trim(),
          email:       email.trim().toLowerCase(),
          password,
          user_type:   userType,
          project:     project || null,
          designation: designation.trim() || null,
          skills:      skills.join(", ") || null,
        }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        localStorage.setItem("user", JSON.stringify({
          user_id: data.user_id, username: username.trim(),
          email:   email.trim().toLowerCase(),
          user_type: userType, project, designation, skills: skills.join(", "),
        }));
        router.push("/dashboard");
      } else {
        const detail = data.detail || "";
        if (typeof detail === "object" && Array.isArray(detail)) {
          const msgs = detail.map(d => d.msg).join(" | ");
          setApiError(msgs);
        } else {
          setApiError(detail || "Registration failed. Please try again.");
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

            <form onSubmit={handleRegister} className={styles.form} noValidate>

              {/* Full Name */}
              <div className={styles.fieldGroup}>
                <label className={styles.label}>
                  Full Name<span className={styles.required}>*</span>
                </label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                  </span>
                  <input
                    type="text"
                    className={`${styles.input} ${touched.username && errors.username ? styles.inputError : ""}`}
                    placeholder="Your full name"
                    value={username}
                    onChange={e => {
                      const val = e.target.value.replace(/[^a-zA-Z\s]/g, "");
                      setUsername(val);
                      if (touched.username) setFieldError("username", validateName(val));
                    }}
                    onBlur={() => handleBlur("username", validateName, username)}
                    autoComplete="name"
                    disabled={loading}
                  />
                </div>
                {touched.username && errors.username && (
                  <span className={styles.fieldError}>⚠ {errors.username}</span>
                )}
              </div>

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
                    onBlur={() => handleBlur("email", validateEmail, email)}
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
                    placeholder="Min. 8 characters"
                    value={password}
                    onChange={e => {
                      const val = e.target.value.replace(/\s/g, "");
                      setPassword(val);
                      if (touched.password) setFieldError("password", validatePassword(val));
                    }}
                    onBlur={() => handleBlur("password", validatePassword, password)}
                    autoComplete="new-password"
                    disabled={loading}
                  />
                  <button type="button" className={styles.eyeBtn}
                    onClick={() => setShowPass(p => !p)} tabIndex={-1}>
                    {showPass ? "Hide" : "Show"}
                  </button>
                </div>
                {/* Strength bar — shown once user starts typing */}
                {password.length > 0 && (
                  <>
                    <div className={styles.strengthBar}>
                      {[1, 2, 3, 4].map(i => (
                        <div key={i} className={`${styles.strengthSeg} ${strength >= i ? styles[strengthClass] : ""}`} />
                      ))}
                    </div>
                    <span className={`${styles.strengthLabel} ${styles[strengthClass]}`}>
                      {strengthLabel}
                    </span>
                  </>
                )}
                {touched.password && errors.password && (
                  <span className={styles.fieldError}>⚠ {errors.password}</span>
                )}
              </div>

              {/* Account Type */}
              <div className={styles.fieldGroup}>
                <label className={styles.label}>Account Type</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                  </span>
                  <select className={styles.input} value={userType}
                    onChange={e => setUserType(e.target.value)} disabled={loading}>
                    <option value="user">Employee (User)</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
              </div>

              {/* Project */}
              <div className={styles.fieldGroup}>
                <label className={styles.label}>
                  Project<span className={styles.required}>*</span>
                </label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
                  </span>
                  <select
                    className={`${styles.input} ${touched.project && errors.project ? styles.inputError : ""}`}
                    value={project}
                    onChange={e => {
                      setProject(e.target.value);
                      if (touched.project) setFieldError("project", e.target.value ? "" : "Please select a project");
                    }}
                    onBlur={() => {
                      setTouched(prev => ({ ...prev, project: true }));
                      setFieldError("project", project ? "" : "Please select a project");
                    }}
                    disabled={loading}>
                    <option value="">Select project...</option>
                    <option value="Bold">Bold</option>
                    <option value="MView">MView</option>
                  </select>
                </div>
                {touched.project && errors.project && (
                  <span className={styles.fieldError}>⚠ {errors.project}</span>
                )}
              </div>

              {/* Designation */}
              <div className={styles.fieldGroup}>
                <label className={styles.label}>Designation</label>
                <div className={styles.inputWrap}>
                  <span className={styles.inputIcon}>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
                  </span>
                  <input type="text" className={styles.input}
                    placeholder="e.g. Frontend Dev, Marketing"
                    value={designation} onChange={e => setDesignation(e.target.value)}
                    disabled={loading} />
                </div>
              </div>

              {/* Skills */}
              <div className={styles.fieldGroup}>
                <label className={styles.label}>
                  Skills{" "}
                  <span style={{ color: "#94A3B8", fontWeight: 400, fontSize: 11 }}>
                    (type then press Enter, comma, or space)
                  </span>
                </label>
                <TagInput tags={skills} onChange={setSkills} placeholder="e.g. React, Node, UI/UX" disabled={loading} />
              </div>

              {/* API-level error */}
              {apiError && <div className={styles.errorBox}><span>⚠ {apiError}</span></div>}

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
