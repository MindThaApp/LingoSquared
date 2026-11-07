import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AuthApi } from "@lingo/shared/api/endpoints";
import { ApiError } from "@lingo/shared/api/client";

const MIN_LENGTH = 8; // same rule as registration

// Public page reached from the emailed link (?token=...). On success the
// backend returns a fresh session; the tokens are stored and the app reloads
// at the home page so the auth context picks them up.
export function ResetPasswordPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [badLink, setBadLink] = useState(!token);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (next.length < MIN_LENGTH) return setError(t("reset.too_short"));
    if (next !== repeat) return setError(t("reset.mismatch"));
    setError(null);
    setBusy(true);
    try {
      await AuthApi.confirmPasswordReset(token, next);
      window.location.assign("/");
    } catch (err) {
      if (err instanceof ApiError && err.code === "invalid_reset_token") setBadLink(true);
      else setError(err instanceof ApiError && err.status === 429 ? t("reset.rate_limited") : t("reset.new_error"));
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <h1 style={{ textAlign: "center", color: "var(--accent)" }}>{t("login.brand")}</h1>
      <div className="card">
        <h2 style={{ marginTop: 0 }}>{t("reset.new_title")}</h2>
        {badLink ? (
          <>
            <div className="form-error" role="alert">
              {t("reset.invalid_link")}
            </div>
            <Link to="/forgot-password" className="btn btn-block">
              {t("reset.request_new_link")}
            </Link>
          </>
        ) : (
          <form onSubmit={(e) => void handleSubmit(e)}>
            <div className="form-field">
              <label htmlFor="reset-new">{t("reset.new_password")}</label>
              <input
                id="reset-new"
                type="password"
                autoComplete="new-password"
                required
                minLength={MIN_LENGTH}
                maxLength={128}
                value={next}
                onChange={(e) => setNext(e.target.value)}
              />
            </div>
            <div className="form-field">
              <label htmlFor="reset-repeat">{t("reset.confirm_password")}</label>
              <input
                id="reset-repeat"
                type="password"
                autoComplete="new-password"
                required
                maxLength={128}
                value={repeat}
                onChange={(e) => setRepeat(e.target.value)}
              />
            </div>
            {error && (
              <div className="form-error" role="alert">
                {error}
              </div>
            )}
            <button type="submit" className="btn btn-block" disabled={busy}>
              {busy ? t("reset.new_saving") : t("reset.new_submit")}
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
