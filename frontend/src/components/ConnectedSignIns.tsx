import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "@lingo/shared/api/client";
import type { SocialCredential, SocialProvider } from "@lingo/shared/api/types";
import { useAuth } from "../auth/AuthContext";
import { SocialSignInButtons } from "./SocialSignInButtons";

const PROVIDER_NAMES: Record<SocialProvider, string> = { google: "Google", apple: "Apple" };

// Profile card for a signed-in (non-guest) account: lists the linked
// Google/Apple sign-ins, connects another one, or disconnects one. The
// backend asks for the current password for both whenever the account has
// one, so a session token alone cannot change how the account signs in.
export function ConnectedSignIns() {
  const { t } = useTranslation();
  const { user, linkSocial, unlinkSocial } = useAuth();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const identities = user?.identities ?? [];

  async function handleLink(credential: SocialCredential) {
    // Thrown errors are shown by SocialSignInButtons itself.
    await linkSocial(credential, password);
    setPassword("");
  }

  async function handleUnlink(provider: SocialProvider) {
    setError(null);
    setBusy(true);
    try {
      await unlinkSocial(provider, password);
      setPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("social.error_default"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <h2 style={{ marginTop: 0 }}>{t("social.connected_title")}</h2>
      {identities.length > 0 ? (
        <ul className="connected-sign-ins">
          {identities.map((identity) => (
            <li key={identity.provider}>
              <span>{PROVIDER_NAMES[identity.provider]}</span>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={busy}
                onClick={() => void handleUnlink(identity.provider)}
              >
                {t("social.disconnect")}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">{t("social.connected_none")}</p>
      )}
      <div className="form-field">
        <label htmlFor="connected-sign-ins-password">{t("social.current_password")}</label>
        <input
          id="connected-sign-ins-password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
      <SocialSignInButtons onCredential={handleLink} />
    </div>
  );
}
