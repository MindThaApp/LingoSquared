import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ApiError, configureApi } from "@lingo/shared/api/client";
import { AuthApi } from "@lingo/shared/api/endpoints";
import type { AuthUser } from "@lingo/shared/api/types";
import { AuthProvider, useAuth } from "./AuthContext";
import { ProtectedRoute } from "../components/layout/ProtectedRoute";
import { LoginPage } from "../pages/LoginPage";

// Regression suite for the "transient backend failure looks like a logout"
// data-loss bug: a NON-401 (or unverifiable-401) failure of GET /auth/me
// used to leave `user === null`, which ProtectedRoute read as "logged
// out". The user landed on the login screen with a working session in
// storage, clicked "Continue as guest" — the obvious next action — and
// got a BRAND-NEW account whose registration overwrote both tokens. The
// original guest account survives server-side but is unreachable forever
// (its generated password was never shown to anyone), and a few such
// loops trip the backend's 5-registrations-per-hour-per-IP limit.
//
// These tests pin the three states that must never be conflated again:
// unauthenticated / unverified / authenticated.

// Web Storage shim. On this toolchain (Node 26 + jsdom 29) Node's own
// experimental `localStorage`/`sessionStorage` globals shadow jsdom's and
// resolve to `undefined` unless node is started with --localstorage-file,
// so anything touching Web Storage is untestable without this. No other
// test file has needed it yet — they don't touch storage.
class MemoryStorage {
  private data = new Map<string, string>();
  get length() {
    return this.data.size;
  }
  clear() {
    this.data.clear();
  }
  getItem(key: string) {
    return this.data.has(key) ? this.data.get(key)! : null;
  }
  key(index: number) {
    return Array.from(this.data.keys())[index] ?? null;
  }
  removeItem(key: string) {
    this.data.delete(key);
  }
  setItem(key: string, value: string) {
    this.data.set(key, String(value));
  }
}
for (const name of ["localStorage", "sessionStorage"] as const) {
  if (!globalThis[name]) {
    Object.defineProperty(globalThis, name, {
      value: new MemoryStorage() as unknown as Storage,
      configurable: true,
      writable: true,
    });
  }
}

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

vi.mock("@lingo/shared/api/endpoints", () => ({
  AuthApi: {
    me: vi.fn(),
    logout: vi.fn(async () => {}),
    login: vi.fn(),
    register: vi.fn(),
  },
}));

const ACCESS = "access_token";
const REFRESH = "refresh_token";

const USER: AuthUser = {
  id: "u-1",
  email: "guest-abc@example.com",
  display_name: "Ramin",
};

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  // The real token seam, exactly as main.tsx configures it — so
  // clearAuthTokens() genuinely clears jsdom's localStorage and the
  // "did the token survive?" discriminator is exercised for real.
  configureApi({
    baseUrl: "http://backend.test",
    feedbackBaseUrl: "http://backend.test",
    tokenStorage: {
      get: () => localStorage.getItem(ACCESS),
      set: (t) => localStorage.setItem(ACCESS, t),
      getRefresh: () => localStorage.getItem(REFRESH),
      setRefresh: (t) => localStorage.setItem(REFRESH, t),
      clear: () => {
        localStorage.removeItem(ACCESS);
        localStorage.removeItem(REFRESH);
      },
    },
  });
});

function StatusProbe() {
  const { status, user } = useAuth();
  return <div data-testid="status">{`${status}|${user?.display_name ?? "-"}`}</div>;
}

function renderProbe() {
  return render(
    <AuthProvider>
      <StatusProbe />
    </AuthProvider>,
  );
}

async function expectStatus(value: string) {
  await waitFor(() =>
    expect(screen.getByTestId("status")).toHaveTextContent(new RegExp(`^${value}\\|`)),
  );
}

describe("AuthContext session state machine", () => {
  it("(a) no stored token -> unauthenticated, without even calling /auth/me", async () => {
    renderProbe();
    await expectStatus("unauthenticated");
    expect(AuthApi.me).not.toHaveBeenCalled();
  });

  it("(b) backend unreachable (fetch rejects) -> unverified, tokens preserved", async () => {
    localStorage.setItem(ACCESS, "real-access");
    localStorage.setItem(REFRESH, "real-refresh");
    vi.mocked(AuthApi.me).mockRejectedValue(new TypeError("Failed to fetch"));

    renderProbe();

    await expectStatus("unverified");
    expect(localStorage.getItem(ACCESS)).toBe("real-access");
    expect(localStorage.getItem(REFRESH)).toBe("real-refresh");
  });

  it("(b) backend 5xx -> unverified, tokens preserved", async () => {
    localStorage.setItem(ACCESS, "real-access");
    localStorage.setItem(REFRESH, "real-refresh");
    vi.mocked(AuthApi.me).mockRejectedValue(
      new ApiError(503, "unavailable", "Service Unavailable"),
    );

    renderProbe();

    await expectStatus("unverified");
    expect(localStorage.getItem(ACCESS)).toBe("real-access");
  });

  it("(b) 401 whose refresh could not be evaluated (tokens left in place) -> unverified", async () => {
    // client.ts's RefreshOutcome "unavailable" path: /auth/me 401s, the
    // /auth/refresh call itself fails on the network, so the client
    // deliberately does NOT clear the tokens — but still throws the very
    // same ApiError(401) as the definitive case. The old code cleared the
    // session here, destroying a live (guest) account.
    localStorage.setItem(ACCESS, "real-access");
    localStorage.setItem(REFRESH, "real-refresh");
    vi.mocked(AuthApi.me).mockRejectedValue(
      new ApiError(401, "unauthorized", "Session expired"),
    );

    renderProbe();

    await expectStatus("unverified");
    expect(localStorage.getItem(ACCESS)).toBe("real-access");
    expect(localStorage.getItem(REFRESH)).toBe("real-refresh");
  });

  it("(c) definitively rejected 401 (client cleared the tokens) -> unauthenticated", async () => {
    localStorage.setItem(ACCESS, "dead-access");
    localStorage.setItem(REFRESH, "dead-refresh");
    vi.mocked(AuthApi.me).mockImplementation(async () => {
      // Exactly what client.ts does when refreshSession() returns
      // "invalid": clear both tokens, then throw.
      localStorage.removeItem(ACCESS);
      localStorage.removeItem(REFRESH);
      throw new ApiError(401, "unauthorized", "Session expired");
    });

    renderProbe();

    await expectStatus("unauthenticated");
    expect(localStorage.getItem(ACCESS)).toBeNull();
  });

  it("verified session -> authenticated", async () => {
    localStorage.setItem(ACCESS, "real-access");
    vi.mocked(AuthApi.me).mockResolvedValue(USER);

    renderProbe();

    await expectStatus("authenticated");
    expect(screen.getByTestId("status")).toHaveTextContent("authenticated|Ramin");
  });
});

describe("recovering from an unverified session", () => {
  it("Retry restores the session in place — no reload, no re-authentication", async () => {
    localStorage.setItem(ACCESS, "real-access");
    localStorage.setItem(REFRESH, "real-refresh");
    vi.mocked(AuthApi.me)
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValue(USER);

    render(
      <MemoryRouter>
        <AuthProvider>
          <ProtectedRoute>
            <div>secret content</div>
          </ProtectedRoute>
        </AuthProvider>
      </MemoryRouter>,
    );

    // The honest screen, NOT the login screen.
    await screen.findByText("session_unavailable.title");
    expect(screen.queryByText("login.continue_as_guest")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "common.retry" }));

    await screen.findByText("secret content");
    // Same tokens throughout: nothing was re-issued, nothing was cleared.
    expect(localStorage.getItem(ACCESS)).toBe("real-access");
    expect(localStorage.getItem(REFRESH)).toBe("real-refresh");
    expect(AuthApi.register).not.toHaveBeenCalled();
  });

  it("regaining connectivity retries by itself", async () => {
    localStorage.setItem(ACCESS, "real-access");
    vi.mocked(AuthApi.me)
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValue(USER);

    renderProbe();
    await expectStatus("unverified");

    window.dispatchEvent(new Event("online"));

    await expectStatus("authenticated");
  });

  it("the login screen refuses to offer 'continue as guest' while a session is unverified", async () => {
    localStorage.setItem(ACCESS, "real-access");
    vi.mocked(AuthApi.me).mockRejectedValue(new TypeError("Failed to fetch"));

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    await screen.findByText("session_unavailable.title");
    expect(screen.queryByText("login.continue_as_guest")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("login.email")).not.toBeInTheDocument();
  });

  it("continueAsGuest is refused at the context level even if a caller bypasses the UI", async () => {
    localStorage.setItem(ACCESS, "real-access");
    vi.mocked(AuthApi.me).mockRejectedValue(new TypeError("Failed to fetch"));

    let guest: ((name: string) => Promise<void>) | null = null;
    function Probe() {
      const { status, continueAsGuest } = useAuth();
      guest = continueAsGuest;
      return <div data-testid="status">{`${status}|-`}</div>;
    }
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await expectStatus("unverified");

    await expect(guest!("Sneaky")).rejects.toThrow(/unverified/);
    expect(AuthApi.register).not.toHaveBeenCalled();
  });
});

describe("logout is still an explicit, immediate transition", () => {
  it("signing out from the unavailable screen returns to the login form", async () => {
    localStorage.setItem(ACCESS, "real-access");
    localStorage.setItem(REFRESH, "real-refresh");
    vi.mocked(AuthApi.me).mockRejectedValue(new TypeError("Failed to fetch"));
    vi.mocked(AuthApi.logout).mockImplementation(async () => {
      localStorage.removeItem(ACCESS);
      localStorage.removeItem(REFRESH);
    });

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    await screen.findByText("session_unavailable.title");
    fireEvent.click(screen.getByRole("button", { name: "session_unavailable.sign_out" }));

    await screen.findByText("login.continue_as_guest");
    expect(localStorage.getItem(ACCESS)).toBeNull();
  });
});
