import { beforeEach, describe, expect, it, vi } from "vitest";

const submit = vi.hoisted(() => vi.fn().mockResolvedValue({}));
vi.mock("@lingo/shared/api/endpoints", () => ({ FeedbackApi: { submit } }));
vi.mock("@sentry/react", () => ({}));

async function load() {
  vi.resetModules();
  const reporter = await import("./crashReporter");
  const sentry = await import("./sentry");
  return { ...reporter, ...sentry };
}

beforeEach(() => {
  localStorage.clear();
  submit.mockClear();
});

describe("legacy crash reporter consent", () => {
  it("never: sends nothing", async () => {
    localStorage.setItem("crash-report-consent", "never");
    const m = await load();
    m.reportCrash("window_error", "boom");
    expect(submit).not.toHaveBeenCalled();
  });

  it("ask (default): holds the report until the learner agrees", async () => {
    const m = await load();
    m.reportCrash("window_error", "boom");
    expect(submit).not.toHaveBeenCalled();
    m.answerPendingCrash(true);
    expect(submit).toHaveBeenCalledOnce();
  });

  it("ask + decline: drops it", async () => {
    const m = await load();
    m.reportCrash("window_error", "boom");
    m.answerPendingCrash(false);
    expect(submit).not.toHaveBeenCalled();
  });

  it("always: sends immediately", async () => {
    localStorage.setItem("crash-report-consent", "always");
    const m = await load();
    m.reportCrash("window_error", "boom");
    expect(submit).toHaveBeenCalledOnce();
  });
});
