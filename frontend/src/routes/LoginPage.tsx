import { Eye, EyeOff, KeyRound, Lock, Mail, ShieldAlert } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { loginStep1, loginStep2 } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [step, setStep] = useState<"credentials" | "mfa">("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  const [mfaBridgeToken, setMfaBridgeToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleCredentialsSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const bridgeToken = await loginStep1(email, password);
      setMfaBridgeToken(bridgeToken);
      setStep("mfa");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleMfaSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await loginStep2(mfaBridgeToken, otpCode);
      const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/";
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "MFA verification failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-icon-badge">
        <ShieldAlert size={26} />
      </div>
      <h1 className="auth-title">SC-TPCRS</h1>
      <p className="auth-subtitle">Supply Chain &amp; Third-Party Cybersecurity Risk System</p>

      <div className="auth-card">
        {step === "credentials" && (
          <>
            <h2 className="auth-card-title">Administrator Login</h2>
            <p className="auth-card-subtitle">Restricted access — authorised personnel only</p>

            <form onSubmit={handleCredentialsSubmit}>
              <label className="auth-field-label" htmlFor="email">
                Email
              </label>
              <div className="auth-input-wrap">
                <span className="auth-input-icon">
                  <Mail size={16} />
                </span>
                <input
                  id="email"
                  type="email"
                  placeholder="Enter email address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="username"
                />
              </div>

              <label className="auth-field-label" htmlFor="password">
                Password
              </label>
              <div className="auth-input-wrap">
                <span className="auth-input-icon">
                  <Lock size={16} />
                </span>
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="has-toggle"
                />
                <button
                  type="button"
                  className="auth-input-toggle"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>

              {error && <p className="error-text" style={{ marginBottom: 12 }}>{error}</p>}
              <button type="submit" className="btn" disabled={busy} style={{ width: "100%" }}>
                {busy ? "Signing in..." : "Sign In"}
              </button>
            </form>

            <div className="auth-disclaimer">
              This system is restricted to authorised users only. All access attempts are logged and monitored in
              accordance with the CBN Risk-Based Cybersecurity Framework.
            </div>
          </>
        )}

        {step === "mfa" && (
          <>
            <h2 className="auth-card-title">Two-Factor Verification</h2>
            <p className="auth-card-subtitle">
              Enter the 6-digit code from your authenticator app. In development, fetch it via{" "}
              <code>GET /api/auth/dev/mfa-code?email=...</code>.
            </p>

            <form onSubmit={handleMfaSubmit}>
              <label className="auth-field-label" htmlFor="otp">
                Verification Code
              </label>
              <div className="auth-input-wrap">
                <span className="auth-input-icon">
                  <KeyRound size={16} />
                </span>
                <input
                  id="otp"
                  inputMode="numeric"
                  placeholder="Enter 6-digit code"
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value)}
                  required
                  autoComplete="one-time-code"
                />
              </div>

              {error && <p className="error-text" style={{ marginBottom: 12 }}>{error}</p>}
              <button type="submit" className="btn" disabled={busy} style={{ width: "100%" }}>
                {busy ? "Verifying..." : "Verify"}
              </button>
            </form>
          </>
        )}
      </div>

      <p className="auth-footer-tag">SC-TPCRS v1.0 · Nigerian Fintech Ecosystem · Confidential</p>
    </div>
  );
}
