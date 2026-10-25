import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { runInNewContext } from "node:vm";
import { describe, expect, it, vi } from "vitest";

// public/sw.js is a classic script, so evaluate it in a vm with a mocked
// worker global and capture the registered listeners.
const SRC = readFileSync(resolve(__dirname, "../../public/sw.js"), "utf8");

function load() {
  const handlers: Record<string, (e: any) => void> = {};
  const store = new Map<string, any>();
  const cache = { addAll: vi.fn(async () => {}), put: vi.fn(async (r: any, v: any) => { store.set(r.url, v); }) };
  const deleted: string[] = [];
  const self: any = {
    location: { origin: "https://app.test" },
    addEventListener: (t: string, h: any) => (handlers[t] = h),
    skipWaiting: vi.fn(),
    clients: { claim: vi.fn(async () => {}), matchAll: vi.fn(async () => []), openWindow: vi.fn(async () => {}) },
    registration: { showNotification: vi.fn(async () => {}) },
  };
  const caches = {
    open: vi.fn(async () => cache),
    keys: vi.fn(async () => ["lingo2-shell-v1", "lingo2-shell-v2", "other"]),
    delete: vi.fn(async (k: string) => { deleted.push(k); return true; }),
    match: vi.fn(async () => undefined),
  };
  const fetchMock = vi.fn();
  runInNewContext(SRC, { self, caches, URL, Response, fetch: fetchMock, Promise });
  return { handlers, self, cache, caches, deleted, fetchMock };
}

async function doFetch(env: ReturnType<typeof load>, url: string, res: any, method = "GET") {
  env.fetchMock.mockResolvedValue(res);
  let p: Promise<any> | undefined;
  env.handlers.fetch({ request: { url, method, mode: "navigate" }, respondWith: (x: any) => (p = x) });
  if (p) await p;
  await Promise.resolve();
  return p !== undefined;
}
const fakeRes = (status: number, type = "basic") => ({ status, type, clone: () => ({}) });

describe("sw.js", () => {
  it("does not skipWaiting on install", async () => {
    const env = load();
    const waits: Promise<unknown>[] = [];
    env.handlers.install({ waitUntil: (p: Promise<unknown>) => waits.push(p) });
    await Promise.all(waits);
    expect(env.self.skipWaiting).not.toHaveBeenCalled();
  });

  it("deletes old caches on activate and keeps the current one", async () => {
    const env = load();
    let p: Promise<unknown> = Promise.resolve();
    env.handlers.activate({ waitUntil: (x: Promise<unknown>) => (p = x) });
    await p;
    expect(env.deleted.sort()).toEqual(["lingo2-shell-v1", "other"]);
  });

  it("caches only 200 basic responses", async () => {
    const env = load();
    await doFetch(env, "https://app.test/assets/a.js", fakeRes(200));
    await Promise.resolve();
    expect(env.cache.put).toHaveBeenCalledTimes(1);
    for (const r of [fakeRes(404), fakeRes(206), fakeRes(200, "opaque"), fakeRes(200, "cors")]) {
      await doFetch(env, "https://app.test/assets/b.js", r);
    }
    expect(env.cache.put).toHaveBeenCalledTimes(1);
  });

  it("does not intercept API, wasm/model files, cross-origin or non-GET", async () => {
    const env = load();
    for (const u of [
      "https://app.test/api/x",
      "https://app.test/assets/ort-wasm-simd.wasm",
      "https://app.test/models/m.onnx",
      "https://other.test/a.js",
    ]) {
      expect(await doFetch(env, u, fakeRes(200))).toBe(false);
    }
    expect(await doFetch(env, "https://app.test/x", fakeRes(200), "POST")).toBe(false);
  });

  it("push: only same-origin urls survive", async () => {
    const cases: [any, string][] = [
      ["/courses/1?x=1", "/courses/1?x=1"],
      ["https://app.test/review", "/review"],
      ["https://evil.test/phish", "/"],
      ["//evil.test/x", "/"],
      ["javascript:alert(1)", "/"],
      [undefined, "/"],
    ];
    for (const [input, expected] of cases) {
      const env = load();
      env.handlers.push({ data: { json: () => ({ title: "t", url: input }) }, waitUntil: () => {} });
      const opts = env.self.registration.showNotification.mock.calls[0][1];
      expect(opts.data.url).toBe(expected);
    }
  });

  it("notificationclick re-validates the stored url", async () => {
    const env = load();
    let p: Promise<unknown> = Promise.resolve();
    env.handlers.notificationclick({
      notification: { close: () => {}, data: { url: "https://evil.test/" } },
      waitUntil: (x: Promise<unknown>) => (p = x),
    });
    await p;
    expect(env.self.clients.openWindow).toHaveBeenCalledWith("/");
  });
});
