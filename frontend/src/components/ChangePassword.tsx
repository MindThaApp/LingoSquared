import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { AuthApi } from "@lingo/shared/api/endpoints";
import { ApiError } from "@lingo/shared/api/client";

const MIN_LENGTH = 8; // same rule as registration

// Profile card: change the password of a signed-in (non-guest) account. The
// backend requires the current password and signs every other device out.
export function ChangePassword() {
  const { t } = useTranslation();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  function messageFor(err: unknown): string {
    if (err instanceof ApiError) {
      if (err.code === "invalid_current_password") return t("account.wrong_current");
      if (err.code === "password_unchanged") return t("account.same_as_current");
      if (err.code === "password_change_unavailable") return t("account.unavailable");
      if (err.code === "login_rate_limited" || err.status === 429) return t("account.rate_limited");
    }
    return t("account.error_default");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setDone(false);
    if (next.length < MIN_LENGTH) return setError(t("account.too_short"));
    if (next !== repeat) return setError(t("account.mismatch"));
    if (next === current) return setError(t("account.same_as_current"));
    setError(null);
    setBusy(true);
    try {
      await AuthApi.changePassword(current, next);
      setCurrent("");
      setNext("");
      setRepeat("");
      setDone(true);
    } catch (err) {
      setError(messageFor(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card" style={{ marginBottom: 16 }} onSubmit={(e) => void handleSubmit(e)}>
      <h2 style={{ marginTop: 0 }}>{t("account.title")}</h2>
      <div className="form-field">
        <label htmlFor="change-password-current">{t("account.current_password")}</label>
        <input
          id="change-password-current"
          type="password"
          autoComplete="current-password"
          required
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
        />
      </div>
      <div className="form-field">
        <label htmlFor="change-password-new">{t("account.new_password")}</label>
        <input
          id="change-password-new"
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
        <label htmlFor="change-password-repeat">{t("account.confirm_password")}</label>
        <input
          id="change-password-repeat"
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
      {done && <p role="status">{t("account.success")}</p>}
      <button type="submit" className="btn btn-secondary btn-block" disabled={busy}>
        {busy ? t("account.saving") : t("account.submit")}
      </button>
    </form>
  );
}
