import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Bell } from "lucide-react";
import {
  dismissPushPrompt,
  isPushPromptDismissed,
  subscribeToPush,
} from "../lib/pushNotifications";
import { usePushState } from "../lib/usePushState";

/**
 * Dismissible HomePage card offering to enable review-reminder
 * notifications (Phase E4). Deliberately NOT a modal — an inline card the
 * user can permanently wave away ("Not now" persists per-device in
 * localStorage). Renders nothing unless every precondition holds: browser
 * support, server VAPID config, permission not already denied, not
 * already subscribed, not previously dismissed. Full enable/disable
 * control lives on ProfilePage (NotificationSettings) regardless of what
 * happens here.
 */
export function PushPrompt() {
  const { t } = useTranslation();
  const { supported, configured, checking, subscribed, refreshSubscribed } = usePushState();
  const [dismissed, setDismissed] = useState(isPushPromptDismissed);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!supported || !configured || checking || subscribed || dismissed) return null;
  // Denied at the browser level: the permission prompt can never re-fire,
  // so this card would be a dead button. ProfilePage's settings card
  // explains where to unblock it; here we just stay out of the way.
  if (Notification.permission === "denied") return null;

  const enable = async () => {
    setBusy(true);
    setError(null);
    try {
      await subscribeToPush();
      // On success `subscribed` flips true and the card disappears; on
      // "permission_denied" the guard above takes over next render.
      await refreshSubscribed();
    } catch {
      setError(t("push.error"));
    }
    setBusy(false);
  };

  const notNow = () => {
    dismissPushPrompt();
    setDismissed(true);
  };

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <h3 style={{ marginTop: 0 }}>
        <Bell size={16} style={{ verticalAlign: -2, marginRight: 6 }} />
        {t("push.prompt_title")}
      </h3>
      <p className="muted" style={{ marginTop: 0 }}>
        {t("push.prompt_body")}
      </p>
      <div style={{ display: "flex", gap: 8 }}>
        <button type="button" className="btn" disabled={busy} onClick={enable}>
          {busy ? t("push.enabling") : t("push.enable")}
        </button>
        <button type="button" className="btn btn-secondary" disabled={busy} onClick={notNow}>
          {t("push.not_now")}
        </button>
      </div>
      {error && (
        <p className="form-error" style={{ marginTop: 10 }}>
          {error}
        </p>
      )}
    </div>
  );
}
