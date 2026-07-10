import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "@lingo/shared/api/client";

export function LoginPage() {
  const { t } = useTranslation();
  const { login, continueAsGuest } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [guestOpen, setGuestOpen] = useState(false);
  const [guestName, setGuestName] = useState("");
  const [guestError, setGuestError] = useState<string | null>(null);
  const [guestSubmitting, setGuestSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("login.error_default"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGuest(e: FormEvent) {
    e.preventDefault();
    setGuestError(null);
    setGuestSubmitting(true);
    try {
      await continueAsGuest(guestName.trim());
      navigate("/");
    } catch (err) {
      setGuestError(err instanceof ApiError ? err.message : t("login.guest_error_default"));
    } finally {
      setGuestSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <h1 style={{ textAlign: "center", color: "var(--accent)" }}>{t("login.brand")}</h1>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>{t("login.title")}</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="login-email">{t("login.email")}</label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="form-field">
            <label htmlFor="login-password">{t("login.password")}</label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error && <div className="form-error">{error}</div>}
          <button type="submit" className="btn btn-block" disabled={submitting}>
            {submitting ? t("login.submitting") : t("login.submit")}
          </button>
        </form>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        {!guestOpen ? (
          <button
            type="button"
            className="btn btn-secondary btn-block"
            onClick={() => setGuestOpen(true)}
          >
            {t("login.continue_as_guest")}
          </button>
        ) : (
          <form onSubmit={handleGuest}>
            <div className="form-field">
              <label htmlFor="guest-name">{t("login.pick_name")}</label>
              <input
                id="guest-name"
                type="text"
                value={guestName}
                onChange={(e) => setGuestName(e.target.value)}
                required
                placeholder={t("login.name_placeholder")}
              />
            </div>
            <div className="form-error" style={{ background: "var(--surface-2)", color: "var(--text-soft)" }}>
              {t("login.guest_warning")}
            </div>
            {guestError && <div className="form-error">{guestError}</div>}
            <button type="submit" className="btn btn-block" disabled={guestSubmitting}>
              {guestSubmitting ? t("login.guest_submitting") : t("login.guest_submit")}
            </button>
          </form>
        )}
      </div>

      <p className="muted" style={{ textAlign: "center", marginTop: 16 }}>
        {t("login.no_account")} <Link to="/register">{t("login.register_link")}</Link>
      </p>
    </div>
  );
}
