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
