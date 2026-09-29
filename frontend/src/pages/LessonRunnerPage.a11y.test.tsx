import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expectNoSeriousA11yViolations } from "../test/axe";
import { LessonRunnerPage } from "./LessonRunnerPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const { lesson, answerMock } = vi.hoisted(() => ({
  lesson: {
    id: "l1",
    teaching: [
      {
        kind: "vocabulary",
        title: "Ouders",
        text_blocks: [{ text: "ouders", language_code: "nl", direction: "ltr" }],
      },
    ],
    exercises: [
      {
        id: "ex1",
        type: "multiple_choice",
        order: 1,
        prompt: {
          text_blocks: [{ text: "Kies.", language_code: "nl", direction: "ltr" }],
          options: ["ouders", "kinderen"],
          answer_language_code: "nl",
        },
      },
    ],
  },
  answerMock: vi.fn(),
}));

vi.mock("@lingo/shared/api/endpoints", () => ({
  LessonApi: {
    get: vi.fn().mockResolvedValue(lesson),
    start: vi.fn().mockResolvedValue({ started_at: "now" }),
    answer: answerMock,
    complete: vi.fn(),
    reportIssue: vi.fn(),
  },
  ReviewApi: { due: vi.fn(), session: vi.fn(), answer: vi.fn() },
}));

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/lessons/l1"]}>
        <Routes>
          <Route path="/lessons/:lessonId" element={<LessonRunnerPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("LessonRunnerPage accessibility", { timeout: 30_000 }, () => {
  beforeEach(() => {
    answerMock.mockReset();
  });

  it.each([
    ["correct", { correct: true, result: "correct" }],
    ["almost", { correct: false, result: "almost" }],
    ["incorrect", { correct: false, result: "incorrect" }],
  ])("teaching card, exercise and %s feedback have no serious violations", async (status, res) => {
    answerMock.mockResolvedValue({
      ...res,
      correct_response: "ouders",
      xp_awarded: 10,
      feedback: "Plural of *ouder*.",
    });
    const { container } = renderPage();

    // Teaching card phase.
    fireEvent.click(await screen.findByRole("button", { name: "lesson_runner.start_practice" }));
    await expectNoSeriousA11yViolations(container);

    // Exercise phase; the live region must already exist before grading.
    const live = container.querySelector('[role="status"][aria-live="polite"]');
    expect(live).not.toBeNull();
    expect(live).toBeEmptyDOMElement();
    await expectNoSeriousA11yViolations(container);

    fireEvent.click(screen.getByRole("radio", { name: "ouders" }));
    fireEvent.click(screen.getByRole("button", { name: "common.check" }));
    // "almost" is announced via AlmostFeedback's visually-hidden sr text.
    const announced = status === "almost" ? "almost_feedback.sr" : `lesson_runner.${status}`;
    await waitFor(() => expect(live).toHaveTextContent(announced));
    // Same node stayed mounted, so its content change is announced.
    expect(container.querySelector('[role="status"][aria-live="polite"]')).toBe(live);
    await expectNoSeriousA11yViolations(container);

    // Quit confirm overlay.
    fireEvent.click(screen.getByRole("button", { name: "lesson_runner.exit_label" }));
    await expectNoSeriousA11yViolations(document.body);
  });
});
