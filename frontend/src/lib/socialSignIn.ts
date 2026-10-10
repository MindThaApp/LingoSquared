import { AuthApi } from "@lingo/shared/api/endpoints";
import type { SocialCredential } from "@lingo/shared/api/types";

// Google and Apple sign-in for the web app. Everything here is OFF unless
// the build is configured: a provider's button only renders when its
// client ID (and, for Apple, its return URL) is set at build time. See
// docs/SOCIAL_SIGN_IN.md. The backend has its own switch
// (SOCIAL_SIGN_IN_ENABLED), reported by GET /auth/social/config, and the
// buttons follow it too (useSocialConfig.ts). It verifies every token
// itself; nothing here is trusted by the server.

const GOOGLE_SCRIPT = "https://accounts.google.com/gsi/client";
const APPLE_SCRIPT =
  "https://appleid.cdn-apple.com/appleauth/static/jsapi/appleid/1/en_US/appleid.auth.js";

export interface SocialConfig {
  google: { clientId: string } | null;
  apple: { clientId: string; redirectUri: string } | null;
}

function envValue(value: string | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

export function socialConfig(): SocialConfig {
  const env = import.meta.env;
  const googleClientId = envValue(env.VITE_GOOGLE_CLIENT_ID);
  const appleClientId = envValue(env.VITE_APPLE_CLIENT_ID);
  const appleRedirectUri = envValue(env.VITE_APPLE_REDIRECT_URI);
  return {
    google: googleClientId ? { clientId: googleClientId } : null,
    apple:
      appleClientId && appleRedirectUri
        ? { clientId: appleClientId, redirectUri: appleRedirectUri }
        : null,
  };
}

export function hasAnySocialProvider(config: SocialConfig = socialConfig()): boolean {
  return Boolean(config.google || config.apple);
}

function randomUrlSafe(bytes = 32): string {
  const values = crypto.getRandomValues(new Uint8Array(bytes));
  let binary = "";
  for (const value of values) binary += String.fromCharCode(value);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

export interface SignInNonce {
  raw: string;
  hashed: string;
  expiresInSeconds: number;
}

// The backend issues the nonce (POST /auth/social/nonce) and accepts it
// once, for a few minutes. The provider embeds the HASHED nonce in its ID
// token; the raw value goes back to our backend with the token, which
// checks the two match and uses the nonce up, so a captured sign-in
// request cannot be replayed.
export async function createNonce(
  issue: () => Promise<{ nonce: string; expires_in: number }> = AuthApi.socialNonce,
): Promise<SignInNonce> {
  const issued = await issue();
  return { raw: issued.nonce, hashed: await sha256Hex(issued.nonce), expiresInSeconds: issued.expires_in };
}

const scriptLoads = new Map<string, Promise<void>>();

function loadScript(src: string): Promise<void> {
  let pending = scriptLoads.get(src);
  if (!pending) {
    pending = new Promise<void>((resolve, reject) => {
      const script = document.createElement("script");
      script.src = src;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => {
        scriptLoads.delete(src);
        reject(new Error(`Could not load ${src}`));
      };
      document.head.appendChild(script);
    });
    scriptLoads.set(src, pending);
  }
  return pending;
}

// ---- Google Identity Services -------------------------------------------

interface GoogleIdApi {
  initialize(options: {
    client_id: string;
    callback: (response: { credential?: string }) => void;
    nonce?: string;
    ux_mode?: "popup" | "redirect";
    auto_select?: boolean;
    itp_support?: boolean;
  }): void;
  renderButton(parent: HTMLElement, options: Record<string, unknown>): void;
}

function googleIdApi(): GoogleIdApi | null {
  const google = (window as unknown as { google?: { accounts?: { id?: GoogleIdApi } } }).google;
  return google?.accounts?.id ?? null;
}

// Renders Google's own "Continue with Google" button into `parent` (Google's
// branding rules require its button, not a look-alike). Each successful
// sign-in calls onCredential; a fresh nonce is prepared for the next one,
// and the current one is replaced shortly before it expires, since the
// button may sit on screen for a while before it is clicked. Returns a
// function that stops that renewal.
export async function renderGoogleButton(
  parent: HTMLElement,
  clientId: string,
  options: {
    locale?: string;
    onCredential: (credential: SocialCredential) => void;
    onError: (error: Error) => void;
  },
): Promise<() => void> {
  await loadScript(GOOGLE_SCRIPT);
  const api = googleIdApi();
  if (!api) throw new Error("Google sign-in is unavailable");

  let renewTimer: ReturnType<typeof setTimeout> | undefined;
  let stopped = false;
  const arm = async () => {
    clearTimeout(renewTimer);
    if (stopped) return;
    const nonce = await createNonce();
    if (stopped) return;
    renewTimer = setTimeout(
      () => void arm().catch(options.onError),
      Math.max(30, nonce.expiresInSeconds - 60) * 1000,
    );
    api.initialize({
      client_id: clientId,
      nonce: nonce.hashed,
      ux_mode: "popup",
      auto_select: false,
      itp_support: true,
      callback: (response) => {
        if (!response.credential) {
          options.onError(new Error("Google sign-in did not return a credential"));
          return;
        }
        options.onCredential({ provider: "google", idToken: response.credential, nonce: nonce.raw });
        void arm().catch(options.onError);
      },
    });
  };
  await arm();
  api.renderButton(parent, {
    type: "standard",
    theme: "outline",
    size: "large",
    text: "continue_with",
    shape: "rectangular",
    logo_alignment: "left",
    width: Math.min(400, Math.max(200, parent.clientWidth || 320)),
    locale: options.locale,
  });
  return () => {
    stopped = true;
    clearTimeout(renewTimer);
  };
}

// ---- Sign in with Apple JS ----------------------------------------------

interface AppleSignInResponse {
  authorization?: { id_token?: string; state?: string };
  user?: { name?: { firstName?: string; lastName?: string } };
}

interface AppleIdApi {
  auth: {
    init(options: {
      clientId: string;
      scope: string;
      redirectURI: string;
      state: string;
      nonce: string;
      usePopup: boolean;
    }): void;
    signIn(): Promise<AppleSignInResponse>;
  };
}

export async function signInWithApple(clientId: string, redirectUri: string): Promise<SocialCredential> {
  await loadScript(APPLE_SCRIPT);
  const api = (window as unknown as { AppleID?: AppleIdApi }).AppleID;
  if (!api) throw new Error("Apple sign-in is unavailable");
  const nonce = await createNonce();
  const state = randomUrlSafe(16);
  api.auth.init({
    clientId,
    scope: "name email",
    redirectURI: redirectUri,
    state,
    nonce: nonce.hashed,
    usePopup: true,
  });
  const response = await api.auth.signIn();
  const idToken = response.authorization?.id_token;
  if (!idToken || response.authorization?.state !== state) {
    throw new Error("Apple sign-in did not complete");
  }
  // Apple shares the user's name only on the very first authorization.
  const name = response.user?.name;
  const displayName = [name?.firstName, name?.lastName].filter(Boolean).join(" ").trim();
  return { provider: "apple", idToken, nonce: nonce.raw, displayName: displayName || undefined };
}

// The Apple popup rejects with { error: "popup_closed_by_user" } when the
// user simply closes it; that is not an error worth showing.
export function isAppleCancellation(error: unknown): boolean {
  const code = (error as { error?: unknown } | null)?.error;
  return code === "popup_closed_by_user" || code === "user_cancelled_authorize";
}
