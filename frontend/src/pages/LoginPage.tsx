import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import { SessionUnavailableScreen } from "../components/layout/ProtectedRoute";
import { ApiError } from "@lingo/shared/api/client";
import {
  clearAccountDeletedNotice,
  peekAccountDeletedNotice,
} from "../lib/accountDeletedNotice";

export function LoginPage() {
  const { t } = useTranslation();
  const { login, continueAsGuest, status } = useAuth();
  const navigate = useNavigate();
  // One-time confirmation after account deletion (set by ProfilePage's
  // delete flow via sessionStorage — see accountDeletedNotice.ts for why
  // route state can't carry this). Peek in the initializer, clear in an
  // effect: it stays visible for this render of the page and is gone on
  // the next full load.
  const [accountDeleted] = useState(peekAccountDeletedNotice);
  useEffect(() => {
    if (accountDeleted) clearAccountDeletedNotice();
  }, [accountDeleted]);
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

  // Both early returns must stay BELOW every hook above.
  //
  // This page is reachable directly (bookmark, back button, an old
  // redirect), so the guard can't live only in ProtectedRoute. A user who
  // holds a session we merely couldn't VERIFY must never be shown the
  // "continue as guest" button: that click registers a second account and
  // overwrites the tokens of the first, which for a guest account is
  // permanent data loss (its generated password was never shown to
  // anyone). Same reason for the loading gate — a slow/hanging /auth/me
  // must not flash the guest button at someone who is signed in.
  if (status === "unverified") return <SessionUnavailableScreen />;
  if (status === "loading") return <div className="page-loading">{t("common.loading")}</div>;

  return (
    <div className="auth-page">
      <h1 style={{ textAlign: "center", color: "var(--accent)" }}>{t("login.brand")}</h1>
      {accountDeleted && (
        <div
          className="form-error"
          style={{ background: "var(--correct-soft)", color: "var(--correct)" }}
        >
          {t("login.account_deleted")}
        </div>
      )}
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
      <p className="muted" style={{ fontSize: "0.85rem", textAlign: "center", marginTop: 8 }}>
        <Link to="/terms">{t("legal.terms")}</Link>
        {" · "}
        <Link to="/privacy">{t("legal.privacy")}</Link>
      </p>
    </div>
  );
}
