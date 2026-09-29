import { describe, expect, it } from "vitest";
import { answerOutcome, isPassingStatus, passAccuracy, resultPassed } from "./answerOutcome";

const correct = { correct: true, result: "correct" as const };
const almost = { correct: true, result: "almost" as const };
const wrong = { correct: false, result: "incorrect" as const };

describe("answerOutcome", () => {
  it("almost is a passing status", () => {
    expect(isPassingStatus("almost")).toBe(true);
    expect(isPassingStatus("correct")).toBe(true);
    expect(isPassingStatus("incorrect")).toBe(false);
    expect(resultPassed(almost)).toBe(true);
  });

  it("almost does not re-queue and is not a missed word", () => {
    expect(answerOutcome(almost, false)).toEqual({ resolved: true, requeue: false, recordMissed: false });
    expect(answerOutcome(almost, false)).toEqual(answerOutcome(correct, false));
  });

  it("incorrect re-queues and records a miss; a confirmation resolves but still records", () => {
    expect(answerOutcome(wrong, false)).toEqual({ resolved: false, requeue: true, recordMissed: true });
    expect(answerOutcome(wrong, true)).toEqual({ resolved: true, requeue: false, recordMissed: true });
  });

  it("almost counts as a pass in accuracy", () => {
    expect(passAccuracy([correct, almost, wrong, almost])).toBe(0.75);
    expect(passAccuracy([])).toBe(0);
  });
});
