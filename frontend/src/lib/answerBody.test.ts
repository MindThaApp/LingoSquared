import { describe, expect, it } from "vitest";
import { answerBody } from "@lingo/shared/api/endpoints";

describe("answerBody", () => {
  it("typed answers send only { response } — no input_mode key", () => {
    const body = answerBody("eet");
    expect(body).toEqual({ response: "eet" });
    expect("input_mode" in body).toBe(false);
  });
  it("spoken answers add input_mode: spoken", () => {
    expect(answerBody("eet", { inputMode: "spoken" })).toEqual({ response: "eet", input_mode: "spoken" });
  });
});

describe("answerBody self-grade and latency", () => {
  it("adds self_grade and latency_ms only when given", async () => {
    const { answerBody } = await import("@lingo/shared/api/endpoints");
    expect(answerBody("known", { selfGrade: "hard", latencyMs: 1234.6 })).toEqual({
      response: "known",
      self_grade: "hard",
      latency_ms: 1235,
    });
    expect(answerBody("known")).toEqual({ response: "known" });
  });
});
