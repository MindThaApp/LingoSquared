import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LessonApi, ReviewApi } from "@lingo/shared/api/endpoints";
import { LessonRunnerPage } from "./LessonRunnerPage";

const stableT = (key: string, opts?: { defaultValue?: string; answer?: string; count?: number }) =>
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
  ReviewApi: { due: vi.fn(), session: vi.fn(), answer: vi.fn() },
}));

vi.mock("../components/exercises/ExerciseRenderer", () => ({
  ExerciseRenderer: ({ exercise }: { exercise: { id: string } }) => <p>exercise:{exercise.id}</p>,
}));
vi.mock("../components/TeachingCardView", () => ({
  TeachingCardView: ({ card }: { card: { title?: string } }) => <p>card:{card.title}</p>,
}));
vi.mock("../components/ReportIssueButton", () => ({ ReportIssueButton: () => null }));
vi.mock("../components/SpeakButton", () => ({ SpeakButton: () => null }));

const words = ["appel", "banaan", "kaas", "melk", "brood", "water", "koffie", "thee"];
const lesson = {
  id: "l1",
  unit_id: "u1",
  title: "L",
  teaching: words.map((w, i) => ({
    kind: "vocabulary",
    title: `c${i + 1}`,
    text_blocks: [
      { text: w, language_code: "nl", direction: "ltr" },
      { text: `gloss${i}word`, language_code: "en", direction: "ltr" },
    ],
  })),
  // e{i} tests the i-th word, so exercise 1 needs only card 1, etc.
  exercises: words.map((w, i) => ({
    id: `e${i + 1}`,
    type: "translation",
    order: i + 1,
    prompt: { text_blocks: [], audio_text: w },
  })),
};

function renderPage(state?: { courseId: string }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[{ pathname: "/lessons/l1", state }]}>
        <Routes>
          <Route path="/lessons/:lessonId" element={<LessonRunnerPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(LessonApi.get).mockResolvedValue(lesson as never);
  vi.mocked(LessonApi.start).mockResolvedValue({ started_at: "now" } as never);
  vi.mocked(ReviewApi.due).mockResolvedValue({ by_course: [] } as never);
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("LessonRunnerPage interleaving", () => {
  it("shows an exercise after at most 3 of the 8 teaching cards", async () => {
    renderPage();
    let cardsSeen = 0;
    // Click Next through cards until an exercise shows up.
    while (screen.queryByText(/^exercise:/) === null) {
      await screen.findByText(`card:c${cardsSeen + 1}`);
      cardsSeen++;
      expect(cardsSeen).toBeLessThanOrEqual(3);
      fireEvent.click(
        screen.getByText(screen.queryByText("lesson_runner.start_practice") ? "lesson_runner.start_practice" : "lesson_runner.next"),
      );
    }
    expect(cardsSeen).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("exercise:e1")).toBeInTheDocument();
  });

  it("labels the last card of a group 'start practice' and earlier ones 'next'", async () => {
    renderPage();
    await screen.findByText("card:c1");
    expect(screen.getByText("lesson_runner.next")).toBeInTheDocument();
    fireEvent.click(screen.getByText("lesson_runner.next"));
    await screen.findByText("card:c2");
    fireEvent.click(screen.getByText("lesson_runner.next"));
    await screen.findByText("card:c3");
    expect(screen.getByText("lesson_runner.start_practice")).toBeInTheDocument();
  });

  it("lets the learner skip the review warm-up", async () => {
    vi.mocked(ReviewApi.due).mockResolvedValue({ by_course: [{ course_id: "c1", due_count: 2 }] } as never);
    vi.mocked(ReviewApi.session).mockResolvedValue({
      items: [
        { id: "r1", type: "translation", prompt: { text_blocks: [] } },
        { id: "r2", type: "translation", prompt: { text_blocks: [] } },
      ],
    } as never);
    renderPage({ courseId: "c1" });
    expect(await screen.findByText("exercise:r1")).toBeInTheDocument();
    expect(screen.getByText("lesson_runner.review_warmup_hint")).toBeInTheDocument();
    fireEvent.click(screen.getByText("lesson_runner.review_warmup_skip"));
    expect(await screen.findByText("card:c1")).toBeInTheDocument();
    expect(screen.queryByText(/^exercise:r/)).toBeNull();
    expect(ReviewApi.answer).not.toHaveBeenCalled();
  });
});
