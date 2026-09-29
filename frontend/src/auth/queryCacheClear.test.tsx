import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ApiError, configureApi } from "@lingo/shared/api/client";
import { AuthApi } from "@lingo/shared/api/endpoints";
import { AuthProvider, useAuth } from "./AuthContext";
import { queryClient } from "../queryClient";

// Query keys (["progress"], ["streak"], ["xp"], ...) are not user-scoped, so
// the cache must be dropped when the session ends -- via explicit logout AND
// via the client's 401 (unauthorized handler) path -- or a second user on the
// same device sees the first user's numbers.

// Capture the handler AuthProvider registers so the test can fire it exactly
// as client.ts does on a definitive 401.
let unauthorizedHandler: (() => void) | null = null;
vi.mock("@lingo/shared/api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@lingo/shared/api/client")>();
  return {
    ...actual,
    setUnauthorizedHandler: (fn: (() => void) | null) => {
      unauthorizedHandler = fn;
    },
  };
});

vi.mock("@lingo/shared/api/endpoints", () => ({
  AuthApi: {
    me: vi.fn(),
    logout: vi.fn(async () => {}),
    login: vi.fn(),
    register: vi.fn(),
  },
}));

const store = new Map<string, string>();
Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  value: {
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    setItem: (k: string, v: string) => void store.set(k, String(v)),
    removeItem: (k: string) => void store.delete(k),
    clear: () => store.clear(),
  },
});

function LogoutButton() {
  const { status, logout } = useAuth();
  return (
    <>
      <div data-testid="status">{status}</div>
      <button onClick={logout}>logout</button>
    </>
  );
}

beforeEach(() => {
  store.clear();
  unauthorizedHandler = null;
  vi.clearAllMocks();
  store.set("access_token", "tok");
  configureApi({
    baseUrl: "http://backend.test",
    feedbackBaseUrl: "http://backend.test",
    tokenStorage: {
      get: () => store.get("access_token") ?? null,
      set: (t) => void store.set("access_token", t),
      getRefresh: () => store.get("refresh_token") ?? null,
      setRefresh: (t) => void store.set("refresh_token", t),
      clear: () => {
        store.delete("access_token");
        store.delete("refresh_token");
      },
    },
  });
  vi.mocked(AuthApi.me).mockResolvedValue({ id: "u", email: "a@b.c", display_name: "A" } as never);
  queryClient.setQueryData(["streak"], { streak_days: 9 });
  queryClient.setQueryData(["xp"], { total_xp: 500 });
});

async function mountAuthenticated() {
  render(
    <AuthProvider>
      <LogoutButton />
    </AuthProvider>,
  );
  await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
  expect(queryClient.getQueryData(["xp"])).toBeDefined();
}

describe("query cache is cleared when the session ends", () => {
  it("explicit logout clears the cache", async () => {
    await mountAuthenticated();
    fireEvent.click(screen.getByRole("button", { name: "logout" }));
    expect(queryClient.getQueryData(["streak"])).toBeUndefined();
    expect(queryClient.getQueryData(["xp"])).toBeUndefined();
  });

  it("the 401 unauthorized handler clears the cache", async () => {
    await mountAuthenticated();
    expect(unauthorizedHandler).not.toBeNull();
    act(() => unauthorizedHandler!());
    expect(queryClient.getQueryData(["streak"])).toBeUndefined();
    expect(queryClient.getQueryData(["xp"])).toBeUndefined();
    void ApiError; // (import kept for parity with AuthContext.test.tsx setup)
  });
});
