import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CatalogApi, ReviewApi } from "@lingo/shared/api/endpoints";
import { ReviewPage } from "./ReviewPage";

// Interpolate counts so the "next review in X" wording can be asserted.
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: { count?: number }) =>
      opts?.count !== undefined ? `${key}:${opts.count}` : key,
  }),
}));

vi.mock("@lingo/shared/api/endpoints", () => ({
  ReviewApi: {
    due: vi.fn(), session: vi.fn(), answer: vi.fn(), retry: vi.fn(),
    reportIssue: vi.fn(), forecast: vi.fn(), leeches: vi.fn(),
  },
  CatalogApi: { course: vi.fn() },
  LexemeApi: { mistakes: vi.fn(), mistakesSummary: vi.fn() },
}));
vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ user: { id: "u1" } }) }));
vi.mock("../components/ReportIssueButton", () => ({ ReportIssueButton: () => null }));
vi.mock("../components/FixMistakes", () => ({ FixMistakes: () => null }));

const flashcard = {
  id: "p-1",
  type: "flashcard",
  prompt: {
    text_blocks: [{ text: "hallo", language_code: "nl", direction: "ltr" }],
    back_text_blocks: [{ text: "hello", language_code: "en", direction: "ltr" }],
  },
};

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter>
        <ReviewPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  vi.mocked(ReviewApi.due).mockResolvedValue({ due_count: 1, by_course: [{ course_id: "c-1", due_count: 1 }] } as never);
  vi.mocked(CatalogApi.course).mockResolvedValue({ id: "c-1", title: "Dutch" } as never);
  vi.mocked(ReviewApi.session).mockResolvedValue({ items: [flashcard] } as never);
  vi.mocked(ReviewApi.forecast).mockResolvedValue({ today: 4, tomorrow: 2, this_week: 9 });
  vi.mocked(ReviewApi.leeches).mockResolvedValue({ threshold: 8, items: [] });
});

async function flip() {
  fireEvent.click(await screen.findByRole("button", { name: "exercise.show_answer" }));
}

describe("ReviewPage SRS controls", () => {
  it("offers Again/Hard/Good/Easy on a flashcard and sends the grade with latency", async () => {
    vi.mocked(ReviewApi.answer).mockResolvedValue({
      correct: true, result: "correct", correct_response: "known", xp_awarded: 1,
      next_due_at: "2026-03-20T04:00:00Z", next_interval_days: 10,
    });
    renderPage();
    await flip();
    for (const k of ["again", "hard", "good", "easy"]) {
      expect(screen.getByRole("button", { name: `review.rate_${k}` })).toBeInTheDocument();
    }
    fireEvent.click(screen.getByRole("button", { name: "review.rate_easy" }));
    await waitFor(() => expect(ReviewApi.answer).toHaveBeenCalled());
    const [id, response, meta] = vi.mocked(ReviewApi.answer).mock.calls[0];
    expect(id).toBe("p-1");
    expect(response).toBe("known");
    expect(meta).toMatchObject({ selfGrade: "easy" });
    expect(typeof meta?.latencyMs).toBe("number");
  });

  it("Again is sent as a miss", async () => {
    vi.mocked(ReviewApi.answer).mockResolvedValue({
      correct: false, result: "incorrect", correct_response: "known", xp_awarded: 0,
      next_due_at: "2026-03-11T04:00:00Z", next_interval_days: 1,
    });
    renderPage();
    await flip();
    fireEvent.click(screen.getByRole("button", { name: "review.rate_again" }));
    await waitFor(() => expect(ReviewApi.answer).toHaveBeenCalled());
    expect(vi.mocked(ReviewApi.answer).mock.calls[0][1]).toBe("unknown");
    expect(vi.mocked(ReviewApi.answer).mock.calls[0][2]).toMatchObject({ selfGrade: "again" });
  });

  it("shows next review in X after an answer", async () => {
    vi.mocked(ReviewApi.answer).mockResolvedValue({
      correct: true, result: "correct", correct_response: "known", xp_awarded: 1,
      next_due_at: "x", next_interval_days: 21,
    });
    renderPage();
    await flip();
    fireEvent.click(screen.getByRole("button", { name: "review.rate_good" }));
    expect(await screen.findByTestId("next-review")).toHaveTextContent("review.next_review_weeks:3");
  });

  it("the toggle falls back to the plain known/unknown buttons and is remembered", async () => {
    renderPage();
    await flip();
    fireEvent.click(screen.getByRole("checkbox", { name: "review.rate_toggle" }));
    expect(screen.getByRole("button", { name: "exercise.got_it" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "review.rate_good" })).not.toBeInTheDocument();
    expect(localStorage.getItem("lingo.review.ratings")).toBe("off");
  });

  it("shows the due forecast and leeches on the all-caught-up screen", async () => {
    vi.mocked(ReviewApi.session).mockResolvedValue({ items: [] } as never);
    vi.mocked(ReviewApi.leeches).mockResolvedValue({
      threshold: 8,
      items: [{ lexeme_id: "l1", course_id: "c-1", token: "fiets", english_gloss: "bicycle", lapses: 9 }],
    });
    renderPage();
    expect(await screen.findByText("review.all_caught_up")).toBeInTheDocument();
    expect(await screen.findByText("9")).toBeInTheDocument();
    expect(screen.getByText("review.forecast_tomorrow")).toBeInTheDocument();
    expect(await screen.findByText("fiets")).toBeInTheDocument();
    expect(screen.getByText("review.leech_missed:9")).toBeInTheDocument();
  });

  it("a failing forecast does not break the screen", async () => {
    vi.mocked(ReviewApi.session).mockResolvedValue({ items: [] } as never);
    vi.mocked(ReviewApi.forecast).mockRejectedValue(new Error("boom"));
    renderPage();
    expect(await screen.findByText("review.all_caught_up")).toBeInTheDocument();
    expect(screen.queryByText("review.forecast_today")).not.toBeInTheDocument();
  });
});
