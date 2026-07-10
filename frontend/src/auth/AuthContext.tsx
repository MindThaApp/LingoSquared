import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { AuthApi } from "@lingo/shared/api/endpoints";
import {
  ApiError,
  clearAuthTokens,
  setUnauthorizedHandler,
} from "@lingo/shared/api/client";
import type { AuthUser } from "@lingo/shared/api/types";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    displayName?: string,
  ) => Promise<void>;
  continueAsGuest: (username: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// Tokens (access + refresh) are stored by AuthApi.login/register/logout
// themselves through the tokenStorage seam configured in main.tsx — this
// layer only owns the cached "user" object.
function storeSession(user: AuthUser) {
  localStorage.setItem("user", JSON.stringify(user));
}

function clearSession() {
  // clearAuthTokens() removes both the access and refresh tokens via the
  // same tokenStorage seam the client's silent-refresh logic uses.
  clearAuthTokens();
  localStorage.removeItem("user");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

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
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
  }, [logout]);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    AuthApi.me()
      .then(setUser)
      .catch((err) => {
        // Only a real 401 means the token is actually invalid/expired --
        // any other failure (network drop, server hiccup) must NOT clear
        // the session, since for guest accounts the generated password is
        // never shown to the user and a cleared session is permanently
        // unrecoverable (see continueAsGuest's comment below). A transient
        // failure here just means we don't know who the user is yet;
        // ProtectedRoute's redirect-to-login is the safe fallback, not a
        // silent, irreversible logout.
        if (err instanceof ApiError && err.status === 401) {
          clearSession();
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await AuthApi.login(email, password);
    storeSession(result.user);
    setUser(result.user);
  }, []);

  const register = useCallback(
    async (email: string, password: string, displayName?: string) => {
      const result = await AuthApi.register(email, password, displayName);
      storeSession(result.user);
      setUser(result.user);
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
      setUser(result.user);
    },
    [],
  );

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, continueAsGuest, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function isGuestUser(user: AuthUser | null): boolean {
  return Boolean(user?.email?.startsWith("guest-") && user.email.endsWith("@example.com"));
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
