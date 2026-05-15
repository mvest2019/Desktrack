// pages/forgot-password.js — Two-step password reset with full validation
import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import Link from "next/link";
import styles from "../styles/Login.module.css";
import API from "../config";

// ── Shared validation (mirrors backend) ────────────────────────────────────
const EMAIL_RE = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;
const SPECIAL_CHARS_RE = /[!@#$%^&*()\[\]{}\-_=+|\\;:'",.<>?/`~]/;

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
  let s = 0;
  if (v.length >= 8) s++;
  if (/[A-Z]/.test(v) && /[a-z]/.test(v)) s++;
  if (/\d/.test(v)) s++;
  if (SPECIAL_CHARS_RE.test(v)) s++;
  return s;
}

const STRENGTH_LABELS = ["", "Weak", "Fair", "Good", "Strong"];
const STRENGTH_CLASS  = ["", "s1",   "s2",  "s3",  "s4"];

const RESEND_COOLDOWN = 30;

export default function ForgotPasswordPage() {
  const router = useRouter();

  const [step,        setStep]        = useState("email");
  const [email,       setEmail]       = useState("");
  const [otp,         setOtp]         = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showPass,    setShowPass]    = useState(false);
  const [loading,     setLoading]     = useState(false);
  const [info,        setInfo]        = useState("");

  const [emailError,  setEmailError]  = useState("");
  const [emailTouched, setEmailTouched] = useState(false);
  const [otpError,    setOtpError]    = useState("");
  const [passError,   setPassError]   = useState("");
  const [passTouched, setPassTouched] = useState(false);
  const [apiError,    setApiError]    = useState("");

  // Resend OTP timer
  const [resendSeconds, setResendSeconds] = useState(0);
  const timerRef = useRef(null);

  const strength      = getPasswordStrength(newPassword);
  const strengthLabel = STRENGTH_LABELS[strength];
  const strengthClass = STRENGTH_CLASS[strength];

  function startResendTimer() {
    setResendSeconds(RESEND_COOLDOWN);
    clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setResendSeconds(prev => {
        if (prev <= 1) { clearInterval(timerRef.current); return 0; }
        return prev - 1;
      });
    }, 1000);
  }

  useEffect(() => () => clearInterval(timerRef.current), []);

  async function handleRequestReset(e) {
    e.preventDefault();
    const err = validateEmail(email);
    setEmailTouched(true);
    setEmailError(err);
    if (err) return;
    setLoading(true); setApiError(""); setInfo("");
    try {
      const res  = await fetch(`${API}/api/password-reset/request`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      const data = await res.json();
      if (data.success) {
        setInfo(data.message);
        setStep("otp");
        startResendTimer();
      } else {
        const detail = data.detail || "";
        if (typeof detail === "object" && Array.isArray(detail)) {
          setApiError(detail.map(d => d.msg).join(" | "));
        } else {
          setApiError(detail || "Something went wrong. Try again.");
        }
      }
    } catch {
      setApiError("Cannot connect to server.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResendOtp() {
    if (resendSeconds > 0 || loading) return;
    setLoading(true); setApiError(""); setInfo("");
    try {
      const res  = await fetch(`${API}/api/password-reset/request`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ email: email.trim().toLowerCase() }),
      });
      const data = await res.json();
      if (data.success) {
        setInfo("A new reset code has been sent to your email.");
        startResendTimer();
      } else {
        const detail = data.detail || "";
        setApiError(typeof detail === "string" ? detail : "Failed to resend code.");
      }
    } catch {
      setApiError("Cannot connect to server.");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirmReset(e) {
    e.preventDefault();
    let valid = true;

    if (!otp.trim() || otp.length !== 6) {
      setOtpError("Please enter the 6-digit verification code");
      valid = false;
    } else {
      setOtpError("");
    }

    const pErr = validatePassword(newPassword);
    setPassTouched(true);
    setPassError(pErr);
    if (pErr) valid = false;

    if (!valid) return;

    setLoading(true); setApiError(""); setInfo("");
    try {
      const res  = await fetch(`${API}/api/password-reset/confirm`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ email: email.trim().toLowerCase(), token: otp.trim(), new_password: newPassword }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setStep("done");
      } else {
        const detail = data.detail || "";
        if (typeof detail === "object" && Array.isArray(detail)) {
          setApiError(detail.map(d => d.msg).join(" | "));
        } else {
          setApiError(detail || "Invalid or expired code. Please try again.");
        }
      }
    } catch {
      setApiError("Cannot connect to server.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Head><title>Realisieren Pulse — Reset Password</title></Head>
      <div className={styles.page}>

        {/* Left hero panel */}
        <div className={styles.heroPanel}>
          <div className={styles.heroInner}>
            <div className={styles.heroBrand}>
              <img src="/app_icon.png" alt="Realisieren Pulse" className={styles.heroBrandImg} />
              <div className={styles.heroBrandText}>
                <div className={styles.heroBrandName}>Realisieren</div>
                <div className={styles.heroBrandSub}>PULSE</div>
              </div>
            </div>
            <div className={styles.heroPill}>Account recovery</div>
            <h1 className={styles.heroTitle}>
              Reset your <span className={styles.heroAccent}>password.</span>
            </h1>
            <p className={styles.heroDesc}>
              Enter your email and we&apos;ll send you a 6-digit code to reset your password securely.
            </p>
          </div>
        </div>

        {/* Right form panel */}
        <div className={styles.formPanel}>
          <div className={styles.formInner}>

            {/* ── STEP 1: Email ── */}
            {step === "email" && (
              <>
                <h2 className={styles.formTitle}>Forgot Password?</h2>
                <p className={styles.formSubtitle}>Enter your account email to receive a reset code.</p>
                <form onSubmit={handleRequestReset} className={styles.form} noValidate>
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
                        className={`${styles.input} ${emailTouched && emailError ? styles.inputError : ""}`}
                        placeholder="you@example.com"
                        value={email}
                        onChange={e => {
                          const val = e.target.value.replace(/\s/g, "");
                          setEmail(val);
                          if (emailTouched) setEmailError(validateEmail(val));
                        }}
                        onBlur={() => {
                          setEmailTouched(true);
                          setEmailError(validateEmail(email));
                        }}
                        autoFocus
                        disabled={loading}
                      />
                    </div>
                    {emailTouched && emailError && (
                      <span className={styles.fieldError}>⚠ {emailError}</span>
                    )}
                  </div>
                  {apiError && <div className={styles.errorBox}><span>⚠ {apiError}</span></div>}
                  <button type="submit" className={styles.loginBtn} disabled={loading}>
                    {loading ? <><span className={styles.spinner} /> Sending...</> : "Send Reset Code"}
                  </button>
                </form>
              </>
            )}

            {/* ── STEP 2: OTP + New Password ── */}
            {step === "otp" && (
              <>
                <h2 className={styles.formTitle}>Enter Reset Code</h2>
                <p className={styles.formSubtitle}>
                  We sent a 6-digit code to <strong>{email}</strong>. Enter it below along with your new password.
                </p>
                {info && (
                  <div className={styles.successBox} style={{ marginBottom: 16 }}>
                    {info}
                  </div>
                )}
                <form onSubmit={handleConfirmReset} className={styles.form} noValidate>

                  {/* OTP field */}
                  <div className={styles.fieldGroup}>
                    <label className={styles.label}>
                      6-Digit Code<span className={styles.required}>*</span>
                    </label>
                    <div className={styles.inputWrap}>
                      <span className={styles.inputIcon}>
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                      </span>
                      <input
                        type="text"
                        className={`${styles.input} ${otpError ? styles.inputError : ""}`}
                        placeholder="123456"
                        value={otp}
                        onChange={e => {
                          const val = e.target.value.replace(/\D/g, "").slice(0, 6);
                          setOtp(val);
                          if (otpError) setOtpError(val.length === 6 ? "" : "Please enter the 6-digit verification code");
                        }}
                        maxLength={6}
                        inputMode="numeric"
                        autoFocus
                        disabled={loading}
                      />
                    </div>
                    {otpError && <span className={styles.fieldError}>⚠ {otpError}</span>}

                    {/* Resend OTP */}
                    <div className={styles.resendRow}>
                      <span>Didn&apos;t receive the code?</span>
                      <button
                        type="button"
                        className={styles.resendBtn}
                        onClick={handleResendOtp}
                        disabled={resendSeconds > 0 || loading}
                      >
                        {resendSeconds > 0 ? `Resend in ${resendSeconds}s` : "Resend OTP"}
                      </button>
                    </div>
                  </div>

                  {/* New Password */}
                  <div className={styles.fieldGroup}>
                    <label className={styles.label}>
                      New Password<span className={styles.required}>*</span>
                    </label>
                    <div className={styles.inputWrap}>
                      <span className={styles.inputIcon}>
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                      </span>
                      <input
                        type={showPass ? "text" : "password"}
                        className={`${styles.input} ${passTouched && passError ? styles.inputError : ""}`}
                        placeholder="Min. 8 characters"
                        value={newPassword}
                        onChange={e => {
                          const val = e.target.value.replace(/\s/g, "");
                          setNewPassword(val);
                          if (passTouched) setPassError(validatePassword(val));
                        }}
                        onBlur={() => {
                          setPassTouched(true);
                          setPassError(validatePassword(newPassword));
                        }}
                        disabled={loading}
                      />
                      <button type="button" className={styles.eyeBtn} onClick={() => setShowPass(p => !p)} tabIndex={-1}>
                        {showPass ? "Hide" : "Show"}
                      </button>
                    </div>
                    {/* Strength indicator */}
                    {newPassword.length > 0 && (
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
                    {passTouched && passError && (
                      <span className={styles.fieldError}>⚠ {passError}</span>
                    )}
                  </div>

                  {apiError && <div className={styles.errorBox}><span>⚠ {apiError}</span></div>}

                  <button type="submit" className={styles.loginBtn} disabled={loading}>
                    {loading ? <><span className={styles.spinner} /> Updating...</> : "Reset Password"}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setStep("email"); setApiError(""); setOtp(""); setNewPassword(""); setOtpError(""); setPassError(""); setPassTouched(false); }}
                    style={{ width: "100%", marginTop: 8, background: "none", border: "none", color: "#64748B", fontSize: 13, cursor: "pointer", textDecoration: "underline" }}
                  >
                    Use a different email
                  </button>
                </form>
              </>
            )}

            {/* ── STEP 3: Done ── */}
            {step === "done" && (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", padding: "32px 0" }}>
                <div style={{ fontSize: 52, marginBottom: 20 }}>✅</div>
                <h2 className={styles.formTitle} style={{ marginBottom: 10 }}>Password Updated!</h2>
                <p className={styles.formSubtitle} style={{ marginBottom: 32 }}>
                  Your password has been reset successfully. You can now sign in with your new password.
                </p>
                <button
                  className={styles.loginBtn}
                  style={{ width: "100%" }}
                  onClick={() => router.push("/")}
                >
                  Back to Sign In
                </button>
              </div>
            )}

            {step !== "done" && (
              <p className={styles.registerText} style={{ marginTop: 20 }}>
                Remembered it?{" "}
                <Link href="/" className={styles.registerLink}>Back to Sign In</Link>
              </p>
            )}

          </div>
        </div>
      </div>
    </>
  );
}
