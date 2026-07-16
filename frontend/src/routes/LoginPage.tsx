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
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
      <div className="card" style={{ width: 360 }}>
        <h2 style={{ marginTop: 0 }}>SC-TPCRS</h2>

        {step === "credentials" && (
          <form onSubmit={handleCredentialsSubmit}>
            <div className="form-row">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={{ width: "100%" }}
              />
            </div>
            <div className="form-row">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={{ width: "100%" }}
              />
            </div>
            {error && <p className="error-text">{error}</p>}
            <button type="submit" className="btn" disabled={busy} style={{ width: "100%" }}>
              {busy ? "Signing in..." : "Continue"}
            </button>
          </form>
        )}

        {step === "mfa" && (
          <form onSubmit={handleMfaSubmit}>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem" }}>
              Enter the 6-digit code from your authenticator app. In development, fetch it via{" "}
              <code>GET /api/auth/dev/mfa-code?email=...</code>.
            </p>
            <div className="form-row">
              <label htmlFor="otp">MFA Code</label>
              <input
                id="otp"
                inputMode="numeric"
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value)}
                required
                style={{ width: "100%" }}
              />
            </div>
            {error && <p className="error-text">{error}</p>}
            <button type="submit" className="btn" disabled={busy} style={{ width: "100%" }}>
              {busy ? "Verifying..." : "Verify"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
