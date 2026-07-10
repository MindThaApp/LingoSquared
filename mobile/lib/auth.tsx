import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ApiError, setUnauthorizedHandler } from "@lingo/shared/api/client";
import { AuthApi } from "@lingo/shared/api/endpoints";
import type { AuthUser } from "@lingo/shared/api/types";

import { tokenStorage } from "./tokenStorage";

// Session state for the whole app. "loading" only ever happens once, during
// the launch-time check of a persisted token; the root layout holds
// navigation until it resolves so the auth gate never flashes the wrong
// screen.
type AuthStatus = "loading" | "signedOut" | "signedIn";

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (
    email: string,
    password: string,
    displayName?: string,
  ) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // No persisted token means there's nothing to validate -- start signed
  // out immediately. "loading" only applies while a persisted token is
  // being checked against the server (the effect below).
  const [status, setStatus] = useState<AuthStatus>(() =>
    tokenStorage.get() ? "loading" : "signedOut",
  );
  const [user, setUser] = useState<AuthUser | null>(null);

  const signOut = useCallback(() => {
    // Local-only sign-out: the shared client doesn't hold a refresh token
    // (refresh-token support in @lingo/shared is a separate pending task),
    // so there's nothing to revoke via POST /auth/logout yet -- discarding
    // the short-lived (30 min) access token is the whole operation.
    tokenStorage.clear();
    setUser(null);
    setStatus("signedOut");
  }, []);

  // Any authenticated request that comes back 401 (expired/revoked access
  // token) drops the session and lands the user on the login screen via the
  // root layout's guard -- same pattern as the web app's App.tsx handler.
  useEffect(() => {
    setUnauthorizedHandler(signOut);
    return () => setUnauthorizedHandler(() => {});
  }, [signOut]);

  // Launch-time session restore: validate any persisted token against
  // GET /auth/me rather than trusting its presence. With 30-minute access
  // tokens and no client-side refresh yet, a relaunch after >30 min will
  // correctly land back on login -- that's the accepted gap until
  // @lingo/shared grows refresh-token support.
  useEffect(() => {
    // Initial status was derived from token presence above; only a
    // persisted token needs server-side validation.
    if (!tokenStorage.get()) return;
    let cancelled = false;
    AuthApi.me()
      .then((me) => {
        if (cancelled) return;
        setUser(me);
        setStatus("signedIn");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          // The unauthorized handler above already cleared the token; make
          // the state transition explicit anyway in case handler wiring and
          // this promise race.
          tokenStorage.clear();
        }
        // Non-401 (backend unreachable, etc.): keep the token on disk so a
        // later launch can retry, but show login now -- logging in again
        // simply overwrites it.
        setUser(null);
        setStatus("signedOut");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await AuthApi.login(email, password);
    tokenStorage.set(result.access_token);
    setUser(result.user);
    setStatus("signedIn");
  }, []);

  const signUp = useCallback(
    async (email: string, password: string, displayName?: string) => {
      const result = await AuthApi.register(email, password, displayName);
      tokenStorage.set(result.access_token);
      setUser(result.user);
      setStatus("signedIn");
    },
    [],
  );

  const value = useMemo(
    () => ({ status, user, signIn, signUp, signOut }),
    [status, user, signIn, signUp, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth() must be used inside <AuthProvider>");
  }
  return ctx;
}
