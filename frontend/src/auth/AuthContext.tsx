import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { AuthApi } from "../api/endpoints";
import { setUnauthorizedHandler } from "../api/client";
import type { AuthUser } from "../api/types";

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

function storeSession(token: string, user: AuthUser) {
  localStorage.setItem("access_token", token);
  localStorage.setItem("user", JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
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
      .catch(() => clearSession())
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await AuthApi.login(email, password);
    storeSession(result.access_token, result.user);
    setUser(result.user);
  }, []);

  const register = useCallback(
    async (email: string, password: string, displayName?: string) => {
      const result = await AuthApi.register(email, password, displayName);
      storeSession(result.access_token, result.user);
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
      storeSession(result.access_token, result.user);
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
