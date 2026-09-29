import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApiError } from "@lingo/shared/api/client";
import { LessonApi, ReviewApi } from "@lingo/shared/api/endpoints";
import { LessonRunnerPage } from "./LessonRunnerPage";

// `t` must be referentially stable (as in real react-i18next) - the start
// effect lists it as a dependency.
const stableT = (key: string, opts?: { defaultValue?: string; answer?: string }) =>
  opts?.answer !== undefined ? `${key}|${opts.answer}` : (opts?.defaultValue ?? key);
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: stableT }),
}));

vi.mock("@lingo/shared/api/endpoints", () => ({
  LessonApi: {
    get: vi.fn(),
    start: vi.fn(),
    answer: vi.fn(),
    complete: vi.fn(),
    reportIssue: vi.fn(),
  },
  ReviewApi: { due: vi.fn(), session: vi.fn() },
}));

// The real renderer is irrelevant here; a single button submits an answer.
vi.mock("../components/exercises/ExerciseRenderer", () => ({
  ExerciseRenderer: ({ onAnswer, disabled }: { onAnswer: (r: string) => void; disabled?: boolean }) => (
    <button disabled={disabled} onClick={() => onAnswer("x")}>
      answer-btn
    </button>
  ),
}));
vi.mock("../components/ReportIssueButton", () => ({ ReportIssueButton: () => null }));
vi.mock("../components/SpeakButton", () => ({ SpeakButton: () => null }));

const lesson = {
  id: "l1",
  unit_id: "u1",
  title: "L",
  teaching: [],
  exercises: [{ id: "e1", type: "translation", order: 1, prompt: { text_blocks: [] } }],
};

const mocked = {
  get: vi.mocked(LessonApi.get),
  start: vi.mocked(LessonApi.start),
  answer: vi.mocked(LessonApi.answer),
  complete: vi.mocked(LessonApi.complete),
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/lessons/l1"]}>
        <Routes>
          <Route path="/lessons/:lessonId" element={<LessonRunnerPage />} />
          <Route path="/lessons/:lessonId/done" element={<p>done-page</p>} />
          <Route path="/" element={<p>home-page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function answerAndContinue() {
  fireEvent.click(await screen.findByText("answer-btn"));
  const cont = await screen.findByText("lesson_runner.continue");
  return cont;
}

beforeEach(() => {
  vi.mocked(ReviewApi.due).mockResolvedValue({ by_course: [] } as never);
  mocked.get.mockResolvedValue(lesson as never);
  mocked.answer.mockResolvedValue({
    correct: true,
    correct_response: "x",
    xp_awarded: 1,
    feedback: null,
  } as never);
  mocked.start.mockResolvedValue({ started_at: "now" } as never);
  mocked.complete.mockResolvedValue({ completed_at: "now", xp_awarded: 1, accuracy: 1 } as never);
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe("LessonRunnerPage start retry", () => {
  it("retries LessonApi.start with backoff on failure", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mocked.start
      .mockRejectedValueOnce(new Error("net"))
      .mockRejectedValueOnce(new Error("net"))
      .mockResolvedValueOnce({ started_at: "now" } as never);
    renderPage();
    await waitFor(() => expect(mocked.start).toHaveBeenCalledTimes(1));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(mocked.start).toHaveBeenCalledTimes(2);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(mocked.start).toHaveBeenCalledTimes(3);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(mocked.start).toHaveBeenCalledTimes(3);
  });

  it("does not retry speaking_locked", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mocked.start.mockRejectedValue(new ApiError(403, "speaking_locked", "locked"));
    renderPage();
    expect(await screen.findByText("lesson_runner.speaking_locked")).toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(mocked.start).toHaveBeenCalledTimes(1);
  });
});

describe("LessonRunnerPage finish", () => {
  it("starts then retries complete exactly once on lesson_not_started", async () => {
    mocked.complete
      .mockRejectedValueOnce(new ApiError(409, "lesson_not_started", "nope"))
      .mockResolvedValueOnce({ completed_at: "now", xp_awarded: 1, accuracy: 1 } as never);
    renderPage();
    fireEvent.click(await answerAndContinue());
    expect(await screen.findByText("done-page")).toBeInTheDocument();
    expect(mocked.complete).toHaveBeenCalledTimes(2);
    // once on mount, once from the lesson_not_started recovery
    expect(mocked.start).toHaveBeenCalledTimes(2);
  });

  it("shows Go back on finishError, and it leaves the runner", async () => {
    mocked.complete.mockRejectedValue(new ApiError(500, "server_error", "boom"));
    renderPage();
    fireEvent.click(await answerAndContinue());
    expect(await screen.findByText("lesson_runner.finish_error")).toBeInTheDocument();
    fireEvent.click(screen.getByText("lesson_runner.go_back"));
    expect(await screen.findByText("home-page")).toBeInTheDocument();
  });

  it("guards against double submit: one complete call and a Saving state", async () => {
    let resolveComplete: (v: unknown) => void = () => {};
    mocked.complete.mockReturnValue(new Promise((r) => (resolveComplete = r)) as never);
    renderPage();
    const cont = await answerAndContinue();
    fireEvent.click(cont);
    fireEvent.click(cont);
    expect(await screen.findByText("Saving…")).toBeInTheDocument();
    expect(screen.queryByText("answer-btn")).not.toBeInTheDocument();
    expect(mocked.complete).toHaveBeenCalledTimes(1);
    await act(async () => {
      resolveComplete({ completed_at: "now", xp_awarded: 1, accuracy: 1 });
    });
    expect(await screen.findByText("done-page")).toBeInTheDocument();
    expect(mocked.complete).toHaveBeenCalledTimes(1);
  });

  it("focuses the Continue button when the result banner mounts", async () => {
    renderPage();
    const cont = await answerAndContinue();
    await waitFor(() => expect(cont).toHaveFocus());
  });
});
