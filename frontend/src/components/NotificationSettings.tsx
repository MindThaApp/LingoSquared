import { useState } from "react";
import { useTranslation } from "react-i18next";
import { subscribeToPush, unsubscribeFromPush } from "../lib/pushNotifications";
import { usePushState } from "../lib/usePushState";

/**
 * ProfilePage settings card for web push (Phase E4): enable/disable
 * review-reminder notifications on this device. Renders NOTHING when the
 * browser doesn't support Web Push (iOS Safari outside an installed PWA)
 * or the server has no VAPID keys configured — hidden, not disabled, per
 * docs/CONTRACT.md's "Web push notifications" section.
 */
export function NotificationSettings() {
  const { t } = useTranslation();
  const { supported, configured, checking, subscribed, refreshSubscribed } = usePushState();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!supported || !configured || checking) return null;

  // Read at render time so it stays current across the permission prompt
  // (every state change below re-renders).
  const permissionDenied = Notification.permission === "denied";

  const enable = async () => {
    setBusy(true);
    setError(null);
    try {
      await subscribeToPush();
      // "permission_denied" needs no special handling here: the refresh
      // below re-renders, and the permissionDenied branch takes over.
      await refreshSubscribed();
    } catch {
      setError(t("push.error"));
    }
    setBusy(false);
  };

  const disable = async () => {
    setBusy(true);
    setError(null);
    try {
      await unsubscribeFromPush();
      await refreshSubscribed();
    } catch {
      setError(t("push.error"));
    }
    setBusy(false);
  };

  return (
    <div className="card">
      <h2 style={{ marginTop: 0 }}>{t("push.settings_title")}</h2>
      <p className="muted">{t("push.settings_body")}</p>
      {subscribed ? (
        <>
          <p className="muted">{t("push.status_on")}</p>
          <button
            type="button"
            className="btn btn-secondary btn-block"
            disabled={busy}
            onClick={disable}
          >
            {busy ? t("push.disabling") : t("push.disable")}
          </button>
        </>
      ) : permissionDenied ? (
        // Permission was denied at the browser level — a subscribe button
        // would be a dead button (the prompt can't even be re-shown); say
        // honestly where to fix it instead.
        <p className="muted">{t("push.blocked")}</p>
      ) : (
        <button type="button" className="btn btn-block" disabled={busy} onClick={enable}>
          {busy ? t("push.enabling") : t("push.enable")}
        </button>
      )}
      {error && (
        <p className="form-error" role="alert" style={{ marginTop: 10 }}>
          {error}
        </p>
      )}
    </div>
  );
}
