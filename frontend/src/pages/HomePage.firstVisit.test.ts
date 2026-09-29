import { describe, expect, it } from "vitest";
import type { Progress, Streak, Xp } from "@lingo/shared/api/types";
import { isBrandNewUser } from "./HomePage";

const progress = (started: number, completed: number) =>
  ({ lessons_started: started, lessons_completed: completed }) as Progress;
const xp = (total: number) => ({ total_xp: total }) as Xp;
const streak = (days: number) => ({ streak_days: days }) as Streak;

describe("isBrandNewUser", () => {
  it("is true only with loaded data and zero activity", () => {
    expect(isBrandNewUser(progress(0, 0), xp(0), streak(0))).toBe(true);
  });
  it("is false while data is missing", () => {
    expect(isBrandNewUser(undefined, xp(0), streak(0))).toBe(false);
    expect(isBrandNewUser(progress(0, 0), undefined, streak(0))).toBe(false);
    expect(isBrandNewUser(progress(0, 0), xp(0), undefined)).toBe(false);
  });
  it("is false with any activity", () => {
    expect(isBrandNewUser(progress(1, 0), xp(0), streak(0))).toBe(false);
    expect(isBrandNewUser(progress(0, 0), xp(5), streak(0))).toBe(false);
    expect(isBrandNewUser(progress(0, 0), xp(0), streak(2))).toBe(false);
  });
});
