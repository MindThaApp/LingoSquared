import { useState } from "react";
import { useTranslation } from "react-i18next";

interface DeleteAccountConfirmProps {
  email: string;
  // Guest accounts have a generated guest-…@example.com address the user
  // has never seen and could not reasonably retype — for them the gate is
  // a second explicit confirm click inside this dialog (the button that
  // opened the dialog being the first), instead of the email-typing gate.
  isGuest: boolean;
  deleting: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}

// Same overlay pattern as QuitConfirm.tsx (plain conditional div, no modal
// library), but deliberately NOT the same component: account deletion is
// irreversible, so this dialog adds a typed-email confirmation gate and a
// destructive-styled commit button rather than QuitConfirm's symmetric
// two-button layout.
export function DeleteAccountConfirm({
  email,
  isGuest,
  deleting,
  error,
  onCancel,
  onConfirm,
}: DeleteAccountConfirmProps) {
  const { t } = useTranslation();
  const [typedEmail, setTypedEmail] = useState("");
  // Case-insensitive: the backend lowercases emails at registration, but a
  // user who types their address with its original capitalization has
  // still unambiguously confirmed intent.
  const emailMatches = typedEmail.trim().toLowerCase() === email.toLowerCase();
  const confirmEnabled = (isGuest || emailMatches) && !deleting;

  return (
    <div className="confirm-overlay" role="dialog" aria-modal="true">
      <div className="confirm-overlay-card">
        <h2 style={{ marginTop: 0 }}>{t("profile.delete_confirm_title")}</h2>
        <p style={{ margin: "0 0 16px" }}>
          {isGuest
            ? t("profile.delete_confirm_body_guest")
            : t("profile.delete_confirm_body")}
        </p>
        {!isGuest && (
          <div className="form-field" style={{ textAlign: "start" }}>
            <label htmlFor="delete-confirm-email">
              {t("profile.delete_type_email", { email })}
            </label>
            <input
              id="delete-confirm-email"
              type="email"
              value={typedEmail}
              onChange={(e) => setTypedEmail(e.target.value)}
              placeholder={t("profile.delete_email_placeholder")}
              autoComplete="off"
            />
          </div>
        )}
        {error && <div className="form-error">{error}</div>}
        <div className="confirm-overlay-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onCancel}
            disabled={deleting}
          >
            {t("common.cancel")}
          </button>
          <button
            type="button"
            className="btn btn-danger"
            onClick={onConfirm}
            disabled={!confirmEnabled}
          >
            {deleting
              ? t("profile.delete_deleting")
              : t("profile.delete_confirm_button")}
          </button>
        </div>
      </div>
    </div>
  );
}
