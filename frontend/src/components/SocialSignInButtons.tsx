import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "@lingo/shared/api/client";
import type { SocialCredential } from "@lingo/shared/api/types";
import {
  isAppleCancellation,
  renderGoogleButton,
  signInWithApple,
  type SocialConfig,
} from "../lib/socialSignIn";
import { useSocialConfig } from "../lib/useSocialConfig";

interface Props {
  // Receives a provider credential; resolve on success, throw to show an
  // error under the buttons.
  onCredential: (credential: SocialCredential) => Promise<void>;
  // Which providers to offer. Defaults to the build's configuration
  // narrowed to what the backend accepts (useSocialConfig).
  config?: SocialConfig;
}

// "Continue with Google" / "Continue with Apple". Renders nothing at all
// unless at least one provider is configured for this build AND accepted
// by the backend, so a build or server without social sign-in looks
// exactly as before.
export function SocialSignInButtons({ onCredential, config }: Props) {
  const { t, i18n } = useTranslation();
  const serverConfig = useSocialConfig(config !== undefined);
  const resolved = config ?? serverConfig;
  const googleRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Kept in a ref so the Google button is rendered once, not on every
  // parent re-render that hands us a new callback.
  const onCredentialRef = useRef(onCredential);
  useEffect(() => {
    onCredentialRef.current = onCredential;
  }, [onCredential]);

  async function submit(credential: SocialCredential) {
    setError(null);
    setBusy(true);
    try {
      await onCredentialRef.current(credential);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("social.error_default"));
    } finally {
      setBusy(false);
    }
  }
  const submitRef = useRef(submit);
  useEffect(() => {
    submitRef.current = submit;
  });

  const googleClientId = resolved.google?.clientId ?? null;
  useEffect(() => {
    const parent = googleRef.current;
    if (!googleClientId || !parent) return;
    let cancelled = false;
    let stopRenewal: (() => void) | undefined;
    renderGoogleButton(parent, googleClientId, {
      locale: i18n.language,
      onCredential: (credential) => {
        if (!cancelled) void submitRef.current(credential);
      },
      onError: () => {
        if (!cancelled) setError(t("social.error_default"));
      },
    })
      .then((stop) => {
        if (typeof stop !== "function") return;
        if (cancelled) stop();
        else stopRenewal = stop;
      })
      .catch(() => {
        if (!cancelled) setError(t("social.unavailable"));
      });
    return () => {
      cancelled = true;
      stopRenewal?.();
      parent.replaceChildren();
    };
  }, [googleClientId, i18n.language, t]);

  if (!resolved.google && !resolved.apple) return null;

  async function handleApple() {
    if (!resolved.apple) return;
    setError(null);
    let credential: SocialCredential;
    try {
      credential = await signInWithApple(resolved.apple.clientId, resolved.apple.redirectUri);
    } catch (err) {
      if (!isAppleCancellation(err)) setError(t("social.error_default"));
      return;
    }
    await submit(credential);
  }

  return (
    <div className="social-sign-in" aria-busy={busy || undefined}>
      {resolved.google && <div ref={googleRef} className="social-google" data-testid="google-sign-in" />}
      {resolved.apple && (
        <button
          type="button"
          className="btn btn-block social-apple"
          onClick={() => void handleApple()}
          disabled={busy}
        >
          <svg aria-hidden="true" width="16" height="18" viewBox="0 0 814 1000" fill="currentColor">
            <path d="M788 341c-6 4-110 63-110 193 0 151 132 204 136 206-1 3-21 73-70 145-43 63-89 126-158 126s-87-40-167-40c-78 0-106 41-169 41s-107-58-158-129C33 798 0 650 0 509c0-226 147-346 292-346 77 0 141 51 189 51 46 0 118-54 206-54 33 0 153 3 232 116zM555 152c36-43 62-103 62-163 0-8-1-17-2-23-59 2-129 39-171 88-33 37-64 97-64 158 0 9 2 18 2 21 4 1 10 2 16 2 53 0 120-36 157-83z" />
          </svg>
          {t("social.continue_with_apple")}
        </button>
      )}
      {error && (
        <div className="form-error" role="alert">
          {error}
        </div>
      )}
    </div>
  );
}
