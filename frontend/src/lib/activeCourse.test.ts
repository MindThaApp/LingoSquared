import { afterEach, describe, expect, it, vi } from "vitest";
import { clearActiveCourse, getActiveCourse, learnPath, setActiveCourse } from "./activeCourse";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("activeCourse", () => {
  it("sets and gets", () => {
    setActiveCourse("u1", "c1");
    expect(getActiveCourse("u1")).toBe("c1");
    expect(learnPath("u1")).toBe("/courses/c1");
  });
  it("is scoped per user", () => {
    setActiveCourse("u1", "c1");
    expect(getActiveCourse("u2")).toBeNull();
    expect(learnPath("u2")).toBe("/courses");
  });
  it("clears", () => {
    setActiveCourse("u1", "c1");
    clearActiveCourse("u1");
    expect(getActiveCourse("u1")).toBeNull();
  });
  it("does not throw when storage throws", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("denied");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("denied");
    });
    vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => {
      throw new Error("denied");
    });
    expect(() => setActiveCourse("u1", "c1")).not.toThrow();
    expect(getActiveCourse("u1")).toBeNull();
    expect(() => clearActiveCourse("u1")).not.toThrow();
  });
  it("ignores missing user", () => {
    setActiveCourse(null, "c1");
    expect(getActiveCourse(undefined)).toBeNull();
  });
});
