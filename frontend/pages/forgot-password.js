// pages/forgot-password.js — Two-step password reset flow
import { useState } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import Link from "next/link";
import styles from "../styles/Login.module.css";
import API from "../config";

export default function ForgotPasswordPage() {
  const router = useRouter();

  // step: "email" | "otp" | "done"
  const [step,        setStep]        = useState("email");
  const [email,       setEmail]       = useState("");
  const [otp,         setOtp]         = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showPass,    setShowPass]    = useState(false);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState("");
  const [info,        setInfo]        = useState("");

  async function handleRequestReset(e) {
    e.preventDefault();
    if (!email.trim()) { setError("Please enter your email."); return; }
    setLoading(true); setError(""); setInfo("");
    try {
      const res  = await fetch(`${API}/api/password-reset/request`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ email: email.trim() }),
      });
      const data = await res.json();
      if (data.success) {
        setInfo(data.message);
        setStep("otp");
      } else {
        setError(data.detail || "Something went wrong. Try again.");
      }
    } catch {
      setError("Cannot connect to server.");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirmReset(e) {
    e.preventDefault();
    if (!otp.trim())         { setError("Please enter the 6-digit code."); return; }
    if (!newPassword.trim()) { setError("Please enter a new password."); return; }
    if (newPassword.length < 6) { setError("Password must be at least 6 characters."); return; }
    setLoading(true); setError(""); setInfo("");
    try {
      const res  = await fetch(`${API}/api/password-reset/confirm`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ email: email.trim(), token: otp.trim(), new_password: newPassword }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        setStep("done");
      } else {
        setError(data.detail || "Invalid or expired code.");
      }
    } catch {
      setError("Cannot connect to server.");
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

            {step === "email" && (
              <>
                <h2 className={styles.formTitle}>Forgot Password?</h2>
                <p className={styles.formSubtitle}>Enter your account email to receive a reset code.</p>
                <form onSubmit={handleRequestReset} className={styles.form}>
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
                        onChange={e => setEmail(e.target.value)}
                        autoFocus
                        disabled={loading}
                      />
                    </div>
                  </div>
                  {error && <div className={styles.errorBox}>{error}</div>}
                  <button type="submit" className={styles.loginBtn} disabled={loading}>
                    {loading ? <><span className={styles.spinner} /> Sending...</> : "Send Reset Code"}
                  </button>
                </form>
              </>
            )}

            {step === "otp" && (
              <>
                <h2 className={styles.formTitle}>Enter Reset Code</h2>
                <p className={styles.formSubtitle}>
                  We sent a 6-digit code to <strong>{email}</strong>. Enter it below along with your new password.
                </p>
                {info && (
                  <div style={{ background: "#DCFCE7", color: "#166534", border: "1px solid #BBF7D0", borderRadius: 8, padding: "10px 14px", fontSize: 13, marginBottom: 16 }}>
                    {info}
                  </div>
                )}
                <form onSubmit={handleConfirmReset} className={styles.form}>
                  <div className={styles.fieldGroup}>
                    <label className={styles.label}>6-Digit Code</label>
                    <div className={styles.inputWrap}>
                      <span className={styles.inputIcon}>
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                      </span>
                      <input
                        type="text"
                        className={styles.input}
                        placeholder="123456"
                        value={otp}
                        onChange={e => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                        maxLength={6}
                        autoFocus
                        disabled={loading}
                      />
                    </div>
                  </div>
                  <div className={styles.fieldGroup}>
                    <label className={styles.label}>New Password</label>
                    <div className={styles.inputWrap}>
                      <span className={styles.inputIcon}>
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                      </span>
                      <input
                        type={showPass ? "text" : "password"}
                        className={styles.input}
                        placeholder="Min. 6 characters"
                        value={newPassword}
                        onChange={e => setNewPassword(e.target.value)}
                        disabled={loading}
                      />
                      <button type="button" className={styles.eyeBtn} onClick={() => setShowPass(p => !p)} tabIndex={-1}>
                        {showPass ? "Hide" : "Show"}
                      </button>
                    </div>
                  </div>
                  {error && <div className={styles.errorBox}>{error}</div>}
                  <button type="submit" className={styles.loginBtn} disabled={loading}>
                    {loading ? <><span className={styles.spinner} /> Updating...</> : "Reset Password"}
                  </button>
                  <button
                    type="button"
                    onClick={() => { setStep("email"); setError(""); setOtp(""); setNewPassword(""); }}
                    style={{ width: "100%", marginTop: 8, background: "none", border: "none", color: "#64748B", fontSize: 13, cursor: "pointer", textDecoration: "underline" }}
                  >
                    Use a different email
                  </button>
                </form>
              </>
            )}

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
