import { beforeEach, describe, expect, it } from "vitest";
import { getOnboarding, setOnboarding, shouldShowOnboarding } from "./onboarding";

beforeEach(() => localStorage.clear());

describe("onboarding state", () => {
  it("defaults to active at the course step", () => {
    expect(getOnboarding("u1")).toEqual({ status: "active", stage: "course" });
  });

  it("persists and resumes the stage and course", () => {
    setOnboarding("u1", { status: "active", stage: "goal", courseId: "c1" });
    expect(getOnboarding("u1")).toEqual({ status: "active", stage: "goal", courseId: "c1" });
  });

  it("restarts at step 1 when a later stage has no course", () => {
    localStorage.setItem("lingo.onboarding.u1", JSON.stringify({ status: "active", stage: "start" }));
    expect(getOnboarding("u1").stage).toBe("course");
  });

  it("survives malformed storage", () => {
    localStorage.setItem("lingo.onboarding.u1", "{nope");
    expect(getOnboarding("u1").status).toBe("active");
  });

  it("shows only to brand-new users with no course and unfinished onboarding", () => {
    expect(shouldShowOnboarding("u1", true, null)).toBe(true);
    expect(shouldShowOnboarding("u1", false, null)).toBe(false);
    expect(shouldShowOnboarding("u1", true, "c1")).toBe(false);
    expect(shouldShowOnboarding(undefined, true, null)).toBe(false);
    setOnboarding("u1", { status: "skipped", stage: "course" });
    expect(shouldShowOnboarding("u1", true, null)).toBe(false);
    setOnboarding("u1", { status: "done", stage: "start", courseId: "c1" });
    expect(shouldShowOnboarding("u1", true, null)).toBe(false);
  });
});
