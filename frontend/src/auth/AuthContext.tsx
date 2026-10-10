import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { AuthApi } from "@lingo/shared/api/endpoints";
import {
  ApiError,
  clearAuthTokens,
  setUnauthorizedHandler,
} from "@lingo/shared/api/client";
import type { AuthUser, SocialCredential, SocialProvider } from "@lingo/shared/api/types";
import { queryClient } from "../queryClient";

// Three genuinely different situations used to collapse into `user ===
// null`, and every consumer read all three as "logged out":
//
//   - "unauthenticated" — no stored token at all, OR a stored token the
//     server DEFINITIVELY rejected (a 401 that survived the client's
//     silent-refresh attempt). The session really is gone; the login
//     screen is the honest answer.
//   - "unverified" — a stored token we could NOT evaluate: device
//     offline, backend restarting, 5xx, DNS failure. The session is
//     probably still perfectly valid, we just don't know yet. Showing
//     the login screen here is a DATA-LOSS bug, not a cosmetic one: the
//     natural next click is "Continue as guest", which registers a
//     BRAND-NEW account and overwrites both tokens — the real guest
//     account still exists server-side but is permanently unreachable,
//     since its generated password was never shown to anyone. Repeat the
//     loop a few times and the backend's 5-registrations-per-hour-per-IP
//     limit locks the user out of the app entirely.
//   - "authenticated" — verified against GET /auth/me this session.
//
// "loading" is only ever the initial bootstrap of a stored token.
export type AuthStatus =
  | "loading"
  | "authenticated"
  | "unauthenticated"
  | "unverified";

interface AuthContextValue {
  user: AuthUser | null;
  status: AuthStatus;
  // Convenience alias for `status === "loading"`, kept so existing
  // consumers don't have to care about the wider state machine. Note it
  // is NOT "we don't have a user yet" — see AuthStatus above.
  loading: boolean;
  // True while a retrySession() attempt is in flight (button state only;
  // `status` deliberately stays "unverified" so the retry doesn't unmount
  // the screen the user is looking at).
  retrying: boolean;
  // Re-runs the GET /auth/me verification with the tokens already in
  // storage. Resolves the "unverified" state without a reload and
  // without re-authenticating. Never rejects.
  retrySession: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    displayName?: string,
  ) => Promise<void>;
  continueAsGuest: (username: string) => Promise<void>;
  // Google/Apple sign-in (POST /auth/social).
  socialSignIn: (credential: SocialCredential) => Promise<void>;
  // Attach Google/Apple to the signed-in account (POST /auth/social/link).
  // For a guest this converts the account in place, keeping its progress;
  // any other account proves it is the owner with its current password or,
  // without one, with `reauth`: a fresh sign-in through a linked provider.
  linkSocial: (credential: SocialCredential, currentPassword?: string, reauth?: SocialCredential) => Promise<void>;
  // Remove a linked sign-in (POST /auth/social/unlink).
  unlinkSocial: (provider: SocialProvider, currentPassword?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// Same key main.tsx hands to configureApi()'s tokenStorage seam. This
// layer only ever READS it (to tell "no session" apart from "a session we
// couldn't check"); writes go through the seam.
const ACCESS_TOKEN_STORAGE_KEY = "access_token";
const CACHED_USER_STORAGE_KEY = "user";

// Tokens (access + refresh) are stored by AuthApi.login/register/logout
// themselves through the tokenStorage seam configured in main.tsx — this
// layer only owns the cached "user" object.
function storeSession(user: AuthUser) {
  localStorage.setItem(CACHED_USER_STORAGE_KEY, JSON.stringify(user));
}

function clearSession() {
  // clearAuthTokens() removes both the access and refresh tokens via the
  // same tokenStorage seam the client's silent-refresh logic uses.
  clearAuthTokens();
  localStorage.removeItem(CACHED_USER_STORAGE_KEY);
}

// The last user object GET /auth/me returned on this device. Deliberately
// NOT used to populate `user` (an unverified cache must never grant access
// to the app): it exists so the "can't reach the server" screen can name
// who is still signed in, which is the single strongest signal that the
// right move is Retry, not "continue as guest".
export function readCachedUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(CACHED_USER_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AuthUser | null;
    return parsed && typeof parsed.display_name === "string" ? parsed : null;
  } catch {
    // Malformed/absent cache is not an error — it just means no name.
    return null;
  }
}

// Query keys aren't user-scoped. Registering/logging in while another
// account's session is still live (never logged out) would otherwise keep
// showing the previous user's streak/XP/progress from the cache.
function resetCacheForNewSession() {
  queryClient.clear();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  // No stored token means there is nothing to verify: start
  // "unauthenticated" immediately rather than flashing a loading state,
  // and — more importantly — never leave a window in which a user who
  // DOES hold a session is shown the login screen's guest button.
  const [status, setStatus] = useState<AuthStatus>(() =>
    localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY) ? "loading" : "unauthenticated",
  );
  const [retrying, setRetrying] = useState(false);

  // Mirror of `status` for callbacks that must read it without taking it
  // as a dependency (continueAsGuest's guard below). Written in an effect
  // rather than during render: the ref is only read from event handlers,
  // which can't run before the commit that updated it.
  const statusRef = useRef(status);
  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  const logout = useCallback(() => {
    // AuthApi.logout() synchronously captures + clears both tokens, then
    // best-effort revokes the refresh token server-side (a later reuse of
    // it must then fail). Errors are swallowed: the local session is
    // already gone either way. This function also doubles as the
    // setUnauthorizedHandler callback below -- in that path client.ts has
    // already cleared the tokens itself, so AuthApi.logout() finds no
    // refresh token and skips the network call entirely (no loop).
    void AuthApi.logout().catch(() => {});
    clearSession();
    // Query keys aren't user-scoped: drop every cached result so the next
    // user on this device never sees this one's progress/streak/XP.
    queryClient.clear();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
  }, [logout]);

  // One shared in-flight verification: StrictMode's double-invoked mount
  // effect, an "online" event and a Retry click can all land at once, and
  // each extra GET /auth/me would race the others' state writes.
  const verifyInFlight = useRef<Promise<void> | null>(null);

  const verifySession = useCallback((): Promise<void> => {
    if (verifyInFlight.current) return verifyInFlight.current;

    const run = (async () => {
      if (!localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)) {
        clearSession();
        setUser(null);
        setStatus("unauthenticated");
        return;
      }
      try {
        const me = await AuthApi.me();
        storeSession(me);
        setUser(me);
        setStatus("authenticated");
      } catch (err) {
        // How to tell state (c) from state (b) — this is the whole fix:
        //
        // client.ts throws the SAME ApiError(401, "unauthorized") for two
        // opposite outcomes, because /auth/me 401s either way:
        //   (c) the refresh token was definitively rejected — it calls
        //       tokenStorage.clear() and fires the unauthorized handler
        //       (i.e. logout() above) before throwing;
        //   (b) the refresh itself was "unavailable" (network drop / 5xx
        //       mid-refresh) — it deliberately leaves the tokens in
        //       place so a later retry can still use them.
        // The error object is identical, so the discriminator is whether
        // the access token SURVIVED the call. Never re-add a bare
        // `err.status === 401 -> clearSession()` here: in case (b) that
        // destroys a live session (unrecoverable for guest accounts).
        //
        // Everything else (fetch rejection when offline, 5xx, DNS) never
        // even reaches the 401 path and is unambiguously state (b).
        const tokenSurvived =
          localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY) !== null;
        if (err instanceof ApiError && err.status === 401 && !tokenSurvived) {
          clearSession();
          setUser(null);
          setStatus("unauthenticated");
          return;
        }
        setUser(null);
        setStatus("unverified");
      }
    })();

    verifyInFlight.current = run.finally(() => {
      verifyInFlight.current = null;
    });
    return verifyInFlight.current;
  }, []);

  useEffect(() => {
    void verifySession();
  }, [verifySession]);

  const retrySession = useCallback(async () => {
    setRetrying(true);
    try {
      await verifySession();
    } finally {
      setRetrying(false);
    }
  }, [verifySession]);

  // Getting connectivity back must restore the session BY ITSELF — a
  // phone that was briefly offline (locked screen, lift, tunnel) or a
  // backend that was restarting for ten seconds should land the user back
  // in the app without a reload and without re-authenticating. Three
  // triggers, all armed ONLY while the session is unverified (so there is
  // no polling whatsoever in the normal case):
  //   - the "online" event — the offline-to-online transition;
  //   - "visibilitychange" — the common Android pattern where
  //     connectivity returned while the tab was backgrounded, so the
  //     "online" event fired long before the user looked at the app;
  //   - a backed-off timer (5s, 10s, 20s, 40s, then every 60s) — covers
  //     the case neither event sees: a foreground tab on a working
  //     network whose BACKEND was down and has just come back.
  useEffect(() => {
    if (status !== "unverified") return;
    let cancelled = false;
    let attempts = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;

    // navigator.onLine === false is a reliable NEGATIVE (true is not a
    // reliable positive, which is fine — a pointless retry is cheap).
    // Never poll from a hidden tab.
    const worthTrying = () =>
      (typeof navigator === "undefined" || navigator.onLine !== false) &&
      (typeof document === "undefined" || document.visibilityState === "visible");

    const schedule = () => {
      if (cancelled) return;
      const delay = Math.min(5000 * 2 ** attempts, 60000);
      attempts += 1;
      timer = setTimeout(() => {
        if (cancelled) return;
        const done = worthTrying() ? retrySession() : Promise.resolve();
        void done.then(() => schedule());
      }, delay);
    };

    const attemptNow = () => {
      if (cancelled || !worthTrying()) return;
      void retrySession();
    };
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") attemptNow();
    };

    window.addEventListener("online", attemptNow);
    document.addEventListener("visibilitychange", onVisibilityChange);
    schedule();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      window.removeEventListener("online", attemptNow);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [status, retrySession]);

  const login = useCallback(async (email: string, password: string) => {
    const result = await AuthApi.login(email, password);
    storeSession(result.user);
    resetCacheForNewSession();
    setUser(result.user);
    setStatus("authenticated");
  }, []);

  const register = useCallback(
    async (email: string, password: string, displayName?: string) => {
      const result = await AuthApi.register(email, password, displayName);
      storeSession(result.user);
      resetCacheForNewSession();
      setUser(result.user);
      setStatus("authenticated");
    },
    [],
  );

  // Local-only convenience: a real backend account under the hood (same
  // register endpoint, same JWT session), just with generated throwaway
  // credentials so there's no email/password step. Not a separate
  // unauthenticated session mechanism — if this browser's localStorage is
  // cleared, the account still exists server-side but is unrecoverable
  // since the generated password was never shown to the user.
  const continueAsGuest = useCallback(
    async (username: string) => {
      // Defense in depth behind the UI gate (LoginPage renders the
      // "can't reach the server" screen instead of the guest form in this
      // state): creating a guest account here would overwrite the tokens
      // of a session that is merely UNVERIFIED, orphaning a real account
      // forever. Any future caller of continueAsGuest inherits the guard.
      if (statusRef.current === "unverified") {
        throw new Error(
          "Refusing to create a guest account while an existing session is unverified.",
        );
      }
      const randomId =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      // example.com (RFC 2606) rather than .invalid: the backend's email
      // validator rejects .invalid as a "special-use" domain even though
      // that's exactly its intended purpose; example.com is already used
      // by this codebase's own test fixtures and is accepted.
      const email = `guest-${randomId}@example.com`;
      const password = crypto.randomUUID?.() ?? randomId;
      const result = await AuthApi.register(email, password, username);
      storeSession(result.user);
      resetCacheForNewSession();
      setUser(result.user);
      setStatus("authenticated");
    },
    [],
  );

  const socialSignIn = useCallback(async (credential: SocialCredential) => {
    // Same guard as continueAsGuest: never replace the tokens of a session
    // that merely could not be verified.
    if (statusRef.current === "unverified") {
      throw new Error("Refusing to sign in while an existing session is unverified.");
    }
    const result = await AuthApi.social(credential);
    storeSession(result.user);
    resetCacheForNewSession();
    setUser(result.user);
    setStatus("authenticated");
  }, []);

  const linkSocial = useCallback(async (credential: SocialCredential, currentPassword?: string, reauth?: SocialCredential) => {
    // Same account, same tokens: only the user object changes (a converted
    // guest gets its new email and identity), so the query cache stays.
    const updated = await AuthApi.linkSocial(credential, currentPassword, reauth);
    storeSession(updated);
    setUser(updated);
  }, []);

  const unlinkSocial = useCallback(async (provider: SocialProvider, currentPassword?: string) => {
    const updated = await AuthApi.unlinkSocial(provider, currentPassword);
    storeSession(updated);
    setUser(updated);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      loading: status === "loading",
      retrying,
      retrySession,
      login,
      register,
      continueAsGuest,
      socialSignIn,
      linkSocial,
      unlinkSocial,
      logout,
    }),
    [user, status, retrying, retrySession, login, register, continueAsGuest, socialSignIn, linkSocial, unlinkSocial, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function isGuestUser(user: AuthUser | null): boolean {
  return Boolean(user?.email?.startsWith("guest-") && user.email.endsWith("@example.com"));
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
