import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SpeakButton } from "./SpeakButton";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
vi.mock("../api/tts", () => ({ speak: vi.fn() }));

describe("SpeakButton", () => {
  it("uses a generic aria-label that does not leak the spoken text", () => {
    render(<SpeakButton text="geheim antwoord" languageCode="nl" />);
    const button = screen.getByRole("button");
    expect(button).toHaveAttribute("aria-label", "speak.play_audio");
    expect(button.getAttribute("aria-label")).not.toContain("geheim");
    expect(button).not.toHaveAttribute("title");
  });
});
