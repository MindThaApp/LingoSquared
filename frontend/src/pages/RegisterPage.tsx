import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Trans, useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "@lingo/shared/api/client";

export function RegisterPage() {
  const { t } = useTranslation();
  const { register, status } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(email, password, displayName || undefined);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("register.error_default"));
    } finally {
      setSubmitting(false);
    }
  }

  // Already signed in: nothing to do here (and a second registration would
  // orphan the live session's account).
  if (status === "authenticated") return <Navigate to="/" replace />;

  return (
    <div className="auth-page">
      <h1 style={{ textAlign: "center", color: "var(--accent)" }}>{t("login.brand")}</h1>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>{t("register.title")}</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="reg-name">{t("register.display_name")}</label>
            <input
              id="reg-name"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>
          <div className="form-field">
            <label htmlFor="reg-email">{t("register.email")}</label>
            <input
              id="reg-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="form-field">
            <label htmlFor="reg-password">{t("register.password")}</label>
            <input
              id="reg-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          {error && <div className="form-error">{error}</div>}
          <button type="submit" className="btn btn-block" disabled={submitting}>
            {submitting ? t("register.submitting") : t("register.submit")}
          </button>
          <p className="muted" style={{ fontSize: "0.85rem", textAlign: "center", marginBottom: 0 }}>
            <Trans
              i18nKey="legal.agree_notice"
              components={{ terms: <Link to="/terms" />, privacy: <Link to="/privacy" /> }}
            />
          </p>
        </form>
      </div>
      <p className="muted" style={{ textAlign: "center", marginTop: 16 }}>
        {t("register.has_account")} <Link to="/login">{t("register.login_link")}</Link>
      </p>
    </div>
  );
}
