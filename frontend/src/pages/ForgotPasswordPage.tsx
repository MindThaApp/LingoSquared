import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AuthApi } from "@lingo/shared/api/endpoints";
import { ApiError } from "@lingo/shared/api/client";

// Public page: ask for a password-reset email. The backend answers the same
// for every address, so the confirmation text never says whether the account
// exists.
export function ForgotPasswordPage() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await AuthApi.requestPasswordReset(email.trim());
      setSent(true);
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 429 ? t("reset.rate_limited") : t("reset.request_error"),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <h1 style={{ textAlign: "center", color: "var(--accent)" }}>{t("login.brand")}</h1>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>{t("reset.request_title")}</h2>
        {sent ? (
          <p role="status">{t("reset.request_sent")}</p>
        ) : (
          <form onSubmit={(e) => void handleSubmit(e)}>
            <p className="muted">{t("reset.request_intro")}</p>
            <div className="form-field">
              <label htmlFor="forgot-email">{t("reset.email")}</label>
              <input
                id="forgot-email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            {error && (
              <div className="form-error" role="alert">
                {error}
              </div>
            )}
            <button type="submit" className="btn btn-block" disabled={busy}>
              {busy ? t("reset.request_sending") : t("reset.request_submit")}
            </button>
          </form>
        )}
      </div>
      <p style={{ textAlign: "center", marginTop: 16 }}>
        <Link to="/login">{t("reset.back_to_login")}</Link>
      </p>
    </div>
  );
}
