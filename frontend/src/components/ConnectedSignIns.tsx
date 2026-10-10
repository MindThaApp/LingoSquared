import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "@lingo/shared/api/client";
import type { SocialCredential, SocialProvider } from "@lingo/shared/api/types";
import { useAuth } from "../auth/AuthContext";
import { hasAnySocialProvider, type SocialConfig } from "../lib/socialSignIn";
import { useSocialConfig } from "../lib/useSocialConfig";
import { SocialSignInButtons } from "./SocialSignInButtons";

const PROVIDER_NAMES: Record<SocialProvider, string> = { google: "Google", apple: "Apple" };

function onlyProviders(config: SocialConfig, keep: (provider: SocialProvider) => boolean): SocialConfig {
  return {
    google: keep("google") ? config.google : null,
    apple: keep("apple") ? config.apple : null,
  };
}

function isReauthRequired(err: unknown): boolean {
  return err instanceof ApiError && err.status === 403 && err.code === "reauthentication_required";
}

interface Props {
  // The providers on offer; defaults to useSocialConfig().
  config?: SocialConfig;
}

// Profile card for a signed-in (non-guest) account: lists the linked
// Google/Apple sign-ins, connects another one, or disconnects one. A
// session token alone cannot change how the account signs in: an account
// with a password confirms it, and one without first signs in again with a
// provider it already uses (the backend checks both).
export function ConnectedSignIns({ config }: Props) {
  const { t } = useTranslation();
  const { user, linkSocial, unlinkSocial } = useAuth();
  const serverConfig = useSocialConfig(config !== undefined);
  const offered = config ?? serverConfig;
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Passwordless accounts: the fresh sign-in with a linked provider.
  const [reauth, setReauth] = useState<SocialCredential | null>(null);
  // Password accounts: a provider sign-in refused only because the
  // password was wrong. The backend keeps its nonce, so it can be sent
  // again with the corrected password instead of reopening the popup.
  const [pending, setPending] = useState<SocialCredential | null>(null);
  const identities = user?.identities ?? [];
  const linked = new Set(identities.map((identity) => identity.provider));
  const passwordless = user?.has_password === false;
  const linkedConfig = onlyProviders(offered, (provider) => linked.has(provider));
  const unlinkedConfig = onlyProviders(offered, (provider) => !linked.has(provider));

  function messageFor(err: unknown): string {
    return err instanceof ApiError ? err.message : t("social.error_default");
  }

  async function handleLink(credential: SocialCredential) {
    setError(null);
    if (passwordless) {
      const proof = reauth;
      // Both sign-ins are single-use, so either way the next attempt
      // starts again from the confirmation step.
      setReauth(null);
      try {
        await linkSocial(credential, undefined, proof ?? undefined);
      } catch (err) {
        setError(messageFor(err));
      }
      return;
    }
    try {
      await linkSocial(credential, password);
      setPassword("");
      setPending(null);
    } catch (err) {
      setPending(isReauthRequired(err) ? credential : null);
      // Shown by SocialSignInButtons itself.
      throw err;
    }
  }

  async function retryPending() {
    if (!pending) return;
    setError(null);
    setBusy(true);
    try {
      await linkSocial(pending, password);
      setPassword("");
      setPending(null);
    } catch (err) {
      if (!isReauthRequired(err)) setPending(null);
      setError(messageFor(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleUnlink(provider: SocialProvider) {
    setError(null);
    setBusy(true);
    try {
      await unlinkSocial(provider, passwordless ? undefined : password);
      setPassword("");
    } catch (err) {
      setError(messageFor(err));
    } finally {
      setBusy(false);
    }
  }

  let connect: ReactNode = null;
  if (hasAnySocialProvider(unlinkedConfig)) {
    if (!passwordless) {
      connect = <SocialSignInButtons key="connect" onCredential={handleLink} config={unlinkedConfig} />;
    } else if (reauth) {
      connect = (
        <>
          <p className="muted">{t("social.reauth_done")}</p>
          <SocialSignInButtons key="connect" onCredential={handleLink} config={unlinkedConfig} />
        </>
      );
    } else if (hasAnySocialProvider(linkedConfig)) {
      connect = (
        <>
          <p className="muted">{t("social.reauth_title")}</p>
          <SocialSignInButtons
            key="reauth"
            onCredential={async (credential) => {
              setError(null);
              setReauth(credential);
            }}
            config={linkedConfig}
          />
        </>
      );
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
      {!passwordless && (
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
      )}
      {pending && !passwordless && (
        <button
          type="button"
          className="btn btn-block"
          disabled={busy || !password}
          onClick={() => void retryPending()}
        >
          {t("social.retry_link")}
        </button>
      )}
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
      {connect}
    </div>
  );
}
