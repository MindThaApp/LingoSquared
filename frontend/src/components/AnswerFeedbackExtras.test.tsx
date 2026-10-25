import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnswerFeedbackExtras } from "./AnswerFeedbackExtras";
import { setAutoPlayAnswer } from "../lib/feedbackPreferences";
import { speak } from "../api/tts";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }));
vi.mock("../api/tts", () => ({ speak: vi.fn().mockResolvedValue(true) }));

const prompt = { text_blocks: [], answer_language_code: "nl" };
const wrong = { correct: false, result: "incorrect" as const, correct_response: "huis" };
const right = { correct: true, result: "correct" as const, correct_response: "huis" };

afterEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

describe("AnswerFeedbackExtras", () => {
  it("auto-plays the correct answer after a wrong answer", () => {
    render(<AnswerFeedbackExtras result={wrong} prompt={prompt} />);
    expect(speak).toHaveBeenCalledWith("huis", "nl", undefined);
  });

  it("does not auto-play when the setting is off or the answer was right", () => {
    setAutoPlayAnswer(false);
    render(<AnswerFeedbackExtras result={wrong} prompt={prompt} />);
    render(<AnswerFeedbackExtras result={right} prompt={prompt} />);
    expect(speak).not.toHaveBeenCalled();
  });

  it("hides Why? when the content has no explanation", () => {
    render(<AnswerFeedbackExtras result={wrong} prompt={prompt} />);
    expect(screen.queryByText("feedback.why")).toBeNull();
  });

  it("shows Why? with the authored explanation on a wrong answer only", () => {
    const withNote = { ...prompt, explanation: "Het is een de-woord." };
    const { unmount } = render(<AnswerFeedbackExtras result={wrong} prompt={withNote} />);
    expect(screen.getByText("feedback.why")).toBeInTheDocument();
    expect(screen.getByText("Het is een de-woord.")).toBeInTheDocument();
    unmount();
    render(<AnswerFeedbackExtras result={right} prompt={withNote} />);
    expect(screen.queryByText("feedback.why")).toBeNull();
  });
});
