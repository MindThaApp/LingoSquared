import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Silent refresh in @lingo/shared's client.ts: the proposed successor
// token is persisted BEFORE /auth/refresh is sent, so a page closed or
// reloaded mid-request can resend the identical request later.

interface Store {
  access: string | null;
  refresh: string | null;
  pending: string | null;
}

let store: Store;

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

async function setup() {
  vi.resetModules();
  const client = await import("@lingo/shared/api/client");
  client.configureApi({
    baseUrl: "http://api.test",
    feedbackBaseUrl: "http://api.test",
    tokenStorage: {
      get: () => store.access,
      set: (t: string) => {
        store.access = t;
      },
      getRefresh: () => store.refresh,
      setRefresh: (t: string) => {
        store.refresh = t;
      },
      getPendingRefresh: () => store.pending,
      setPendingRefresh: (t: string | null) => {
        store.pending = t;
      },
      clear: () => {
        store.access = null;
        store.refresh = null;
        store.pending = null;
      },
    },
  });
  return client;
}

function refreshBodies(fetchMock: ReturnType<typeof vi.fn>) {
  return fetchMock.mock.calls
    .filter(([url]) => String(url).endsWith("/auth/refresh"))
    .map(([, init]) => JSON.parse(String((init as RequestInit).body)));
}

describe("silent refresh", () => {
  beforeEach(() => {
    store = { access: "expired", refresh: "old-refresh", pending: null };
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("persists the proposed successor before sending, then commits the response", async () => {
    let pendingWhenSent: string | null = null;
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/auth/refresh")) {
        pendingWhenSent = store.pending;
        const sent = JSON.parse(String(init?.body));
        return json(200, {
          access_token: "fresh-access",
          refresh_token: sent.next_refresh_token,
          token_type: "bearer",
          expires_in: 1800,
        });
      }
      const auth = new Headers(init?.headers).get("Authorization");
      return auth === "Bearer fresh-access" ? json(200, { ok: true }) : json(401, {});
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = await setup();

    await expect(client.get("/thing")).resolves.toEqual({ ok: true });

    const [body] = refreshBodies(fetchMock);
    expect(body.refresh_token).toBe("old-refresh");
    expect(body.next_refresh_token).toMatch(/^[A-Za-z0-9_-]{64}$/);
    expect(pendingWhenSent).toBe(body.next_refresh_token);
    expect(store.refresh).toBe(body.next_refresh_token);
    expect(store.access).toBe("fresh-access");
    expect(store.pending).toBeNull();
  });

  it("keeps the pending successor when the response is lost and resends the identical request", async () => {
    let refreshCalls = 0;
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/auth/refresh")) {
        refreshCalls += 1;
        if (refreshCalls === 1) throw new TypeError("network went away");
        const sent = JSON.parse(String(init?.body));
        return json(200, {
          access_token: "fresh-access",
          refresh_token: sent.next_refresh_token,
          token_type: "bearer",
          expires_in: 1800,
        });
      }
      const auth = new Headers(init?.headers).get("Authorization");
      return auth === "Bearer fresh-access" ? json(200, { ok: true }) : json(401, {});
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = await setup();

    await expect(client.get("/thing")).rejects.toMatchObject({ status: 401 });
    // The session survives the outage, including the pending successor.
    expect(store.refresh).toBe("old-refresh");
    const pending = store.pending;
    expect(pending).toBeTruthy();

    await expect(client.get("/thing")).resolves.toEqual({ ok: true });
    const [first, second] = refreshBodies(fetchMock);
    expect(second).toEqual(first);
    expect(second.next_refresh_token).toBe(pending);
    expect(store.refresh).toBe(pending);
    expect(store.pending).toBeNull();
  });

  it("adopts the server's token when it differs from the proposal", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/auth/refresh")) {
        return json(200, {
          access_token: "fresh-access",
          refresh_token: "server-chosen",
          token_type: "bearer",
          expires_in: 1800,
        });
      }
      const auth = new Headers(init?.headers).get("Authorization");
      return auth === "Bearer fresh-access" ? json(200, { ok: true }) : json(401, {});
    });
    vi.stubGlobal("fetch", fetchMock);
    const client = await setup();

    await client.get("/thing");
    expect(store.refresh).toBe("server-chosen");
    expect(store.pending).toBeNull();
  });

  it("clears everything, pending included, when the refresh is rejected", async () => {
    const fetchMock = vi.fn(async (url: string) =>
      url.endsWith("/auth/refresh")
        ? json(401, { error: { code: "refresh_token_reused", message: "x" } })
        : json(401, {}),
    );
    vi.stubGlobal("fetch", fetchMock);
    const client = await setup();

    await expect(client.get("/thing")).rejects.toMatchObject({ status: 401 });
    expect(store).toEqual({ access: null, refresh: null, pending: null });
  });

  it("does not refresh again when another tab rotated the tokens while it waited for the lock", async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      const auth = new Headers(init?.headers).get("Authorization");
      return auth === "Bearer other-tab-access" ? json(200, { ok: true }) : json(401, {});
    });
    vi.stubGlobal("fetch", fetchMock);
    const locks = {
      request: vi.fn(async (_name: string, callback: () => Promise<unknown>) => {
        // The other tab finished its refresh while this one was queued.
        store.access = "other-tab-access";
        store.refresh = "other-tab-refresh";
        return callback();
      }),
    };
    vi.stubGlobal("navigator", { ...navigator, locks });
    const client = await setup();

    await expect(client.get("/thing")).resolves.toEqual({ ok: true });
    expect(locks.request).toHaveBeenCalledWith("lingo-auth-refresh", expect.any(Function));
    expect(refreshBodies(fetchMock)).toHaveLength(0);
    expect(store.refresh).toBe("other-tab-refresh");
  });
});
