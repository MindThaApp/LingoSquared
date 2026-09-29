import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
import en from "../../../packages/shared/src/i18n/locales/en.json";
import { AlmostFeedback } from "./AlmostFeedback";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, vars?: Record<string, string>) => {
      const raw = (key.split(".").reduce((o: any, k) => o?.[k], en as any) as string) ?? key;
      return raw.replace(/\{\{(\w+)\}\}/g, (_m, k) => vars?.[k] ?? "");
    },
  }),
}));

describe("AlmostFeedback", () => {
  it("typed almost keeps the spelling copy and diff", () => {
    const { container } = render(<AlmostFeedback learner="huis" correct="huize" dir="ltr" />);
    expect(container.textContent).toContain("Almost!");
    expect(container.textContent).toContain("You wrote:");
    expect(container.textContent).not.toContain("We heard");
    expect(container.querySelector("mark")).not.toBeNull();
  });

  it("spoken almost says we heard something close, in bdi, no spelling diff", () => {
    const { container } = render(<AlmostFeedback learner="huis" correct="huize" dir="ltr" spoken />);
    expect(container.textContent).toContain("Close!");
    expect(container.textContent).toContain("We heard:");
    expect(container.textContent).not.toContain("You wrote:");
    expect(container.querySelector("mark")).toBeNull();
    const bdis = Array.from(container.querySelectorAll("bdi")).map((b) => b.textContent);
    expect(bdis).toEqual(["huize", "huis"]);
    expect(container.querySelector(".visually-hidden")?.textContent).toBe(
      "Close. We heard: huis. Correct answer: huize",
    );
  });
});
