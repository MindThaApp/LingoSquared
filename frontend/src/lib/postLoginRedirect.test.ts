import { describe, expect, it } from "vitest";
import { redirectFromState, safeRedirectPath } from "./postLoginRedirect";

describe("post-login redirect", () => {
  it("accepts same-app paths incl. query and hash", () => {
    expect(safeRedirectPath("/courses/abc?x=1#y")).toBe("/courses/abc?x=1#y");
    expect(redirectFromState({ from: "/review" })).toBe("/review");
  });

  it("defaults to / when missing or malformed", () => {
    expect(redirectFromState(null)).toBe("/");
    expect(redirectFromState({})).toBe("/");
    expect(safeRedirectPath(42)).toBe("/");
  });

  it("rejects open-redirect shapes", () => {
    for (const bad of [
      "//evil.com",
      "https://evil.com",
      "javascript:alert(1)",
      "/\\evil.com",
      "evil.com",
      "/login",
    ]) {
      expect(safeRedirectPath(bad)).toBe("/");
    }
  });
});
