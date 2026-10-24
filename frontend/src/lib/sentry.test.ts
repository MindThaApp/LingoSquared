import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The SDK is mocked in every test: no test can ever send a real event, and
// the DSN used below is a placeholder that is never contacted.
const sdk = vi.hoisted(() => ({
  init: vi.fn(),
  captureException: vi.fn(),
  captureFeedback: vi.fn(),
  flush: vi.fn().mockResolvedValue(true),
  withScope: vi.fn((fn: (s: unknown) => void) => fn({ setTags: vi.fn(), setExtra: vi.fn() })),
}));
vi.mock("@sentry/react", () => sdk);

const feedbackSubmit = vi.hoisted(() => vi.fn().mockResolvedValue({}));
vi.mock("@lingo/shared/api/endpoints", () => ({ FeedbackApi: { submit: feedbackSubmit } }));

async function load(dsn: string) {
  vi.resetModules();
  vi.stubEnv("VITE_SENTRY_DSN", dsn);
  return import("./sentry");
}

beforeEach(() => {
  localStorage.clear();
  Object.values(sdk).forEach((m) => m.mockClear());
  feedbackSubmit.mockClear();
});
afterEach(() => vi.unstubAllEnvs());

describe("without a DSN", () => {
  it("never initialises the SDK or captures anything", async () => {
    const m = await load("");
    localStorage.setItem("crash-report-consent", "always");
    expect(m.initSentry()).toBe(false);
    m.handleCrash(new Error("boom"));
    expect(sdk.init).not.toHaveBeenCalled();
    expect(sdk.captureException).not.toHaveBeenCalled();
  });

  it("still delivers a problem report through the app's own feedback endpoint", async () => {
    const m = await load("");
    await m.sendProblemReport({ message: "it broke", email: "" });
    expect(sdk.captureFeedback).not.toHaveBeenCalled();
    expect(feedbackSubmit).toHaveBeenCalledOnce();
  });
});

describe("with a DSN: consent gating", () => {
  const DSN = "https://public@example.invalid/1";

  it("defaults to ask: holds the crash, sends nothing until the learner agrees", async () => {
    const m = await load(DSN);
    const seen: unknown[] = [];
    m.subscribePendingCrash((p) => seen.push(p));
    m.handleCrash(new Error("boom"));
    expect(sdk.captureException).not.toHaveBeenCalled();
    expect(seen.at(-1)).not.toBeNull();
    m.answerPendingCrash(true);
    expect(sdk.captureException).toHaveBeenCalledOnce();
    expect(seen.at(-1)).toBeNull();
  });

  it("ask + decline sends nothing", async () => {
    const m = await load(DSN);
    m.handleCrash(new Error("boom"));
    m.answerPendingCrash(false);
    expect(sdk.captureException).not.toHaveBeenCalled();
  });

  it("never sends nothing and does not even prompt", async () => {
    localStorage.setItem("crash-report-consent", "never");
    const m = await load(DSN);
    const seen: unknown[] = [];
    m.subscribePendingCrash((p) => seen.push(p));
    m.handleCrash(new Error("boom"));
    expect(sdk.captureException).not.toHaveBeenCalled();
    expect(seen.every((p) => p === null)).toBe(true);
  });

  it("always sends without asking", async () => {
    localStorage.setItem("crash-report-consent", "always");
    const m = await load(DSN);
    m.handleCrash(new Error("boom"));
    expect(sdk.captureException).toHaveBeenCalledOnce();
  });

  it("beforeSend drops events nobody approved, passes approved ones scrubbed", async () => {
    const m = await load(DSN);
    m.initSentry();
    const opts = sdk.init.mock.calls[0][0];
    expect(opts.dsn).toBe(DSN);
    expect(opts.integrations([{ name: "GlobalHandlers" }, { name: "Dedupe" }])).toEqual([{ name: "Dedupe" }]);
    // An error the SDK captured on its own (not via handleCrash): dropped.
    expect(opts.beforeSend({ exception: { values: [] } }, { originalException: new Error("x") })).toBeNull();
    // One the learner approved: goes through, scrubbed.
    const err = new Error("hello me@example.com");
    m.handleCrash(err);
    m.answerPendingCrash(true);
    const out = opts.beforeSend(
      { exception: { values: [{ type: "Error", value: err.message }] } },
      { originalException: err },
    );
    expect(JSON.stringify(out)).not.toContain("me@example.com");
    // And "never" blocks even approved errors.
    localStorage.setItem("crash-report-consent", "never");
    expect(opts.beforeSend({}, { originalException: err })).toBeNull();
  });

  it("a problem report is sent whatever the consent setting", async () => {
    localStorage.setItem("crash-report-consent", "never");
    const m = await load(DSN);
    await m.sendProblemReport({ message: "it broke", email: " me@example.com " });
    expect(sdk.captureFeedback).toHaveBeenCalledOnce();
    const arg = sdk.captureFeedback.mock.calls[0][0];
    expect(arg.message).toBe("it broke");
    expect(arg.email).toBe("me@example.com");
    expect(arg.tags).toMatchObject({ route: expect.any(String), environment: expect.any(String), release: expect.any(String) });
  });
});
