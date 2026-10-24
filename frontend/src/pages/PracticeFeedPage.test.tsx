import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CatalogApi, PracticeApi, ProgressApi } from "@lingo/shared/api/endpoints";
import { PracticeFeedPage } from "./PracticeFeedPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

vi.mock("@lingo/shared/api/endpoints", () => ({
  ProgressApi: { progress: vi.fn() },
  CatalogApi: { course: vi.fn() },
  PracticeApi: { batch: vi.fn(), answer: vi.fn(), reportIssue: vi.fn() },
}));

// Render just the item id so the test can see which batch's items are shown.
vi.mock("../components/exercises/ExerciseRenderer", () => ({
  ExerciseRenderer: ({
    exercise,
    onAnswer,
  }: {
    exercise: { id: string };
    onAnswer: (response: string) => void;
  }) => (
    <div data-testid="item">
      {exercise.id}
      <button onClick={() => onAnswer("x")}>submit-answer</button>
    </div>
  ),
}));
vi.mock("../components/ConversationRunner", () => ({ ConversationRunner: () => null }));
vi.mock("../components/ReportIssueButton", () => ({ ReportIssueButton: () => null }));

const store = new Map<string, string>();
Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  value: {
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    setItem: (k: string, v: string) => void store.set(k, String(v)),
    removeItem: (k: string) => void store.delete(k),
    clear: () => store.clear(),
  },
});

function deferred<T>() {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

const item = (id: string) => ({ id, type: "multiple_choice", prompt: {} });

beforeEach(() => {
  store.clear();
  vi.clearAllMocks();
  vi.mocked(ProgressApi.progress).mockResolvedValue({
    skill_progress: [{ course_id: "c-1", completed_lessons: 2 }],
  } as never);
  vi.mocked(CatalogApi.course).mockResolvedValue({ id: "c-1", title: "Dutch" } as never);
});

describe("PracticeFeedPage mode switch during an in-flight batch", () => {
  it("drops the stale response and issues the new mode's load", async () => {
    const stale = deferred<never>();
    const fresh = deferred<never>();
    vi.mocked(PracticeApi.batch)
      .mockReturnValueOnce(stale.promise)
      .mockReturnValueOnce(fresh.promise);

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <PracticeFeedPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await waitFor(() => expect(PracticeApi.batch).toHaveBeenCalledTimes(1));
    expect(vi.mocked(PracticeApi.batch).mock.calls[0][2]).toBe("mixed");

    // Switch mode while the "mixed" batch is still in flight.
    fireEvent.click(screen.getByRole("button", { name: "practice.mode_speaking" }));

    // The new mode's load must be issued (old code: blocked by the stale
    // request's still-set in-flight flag, so this never reached 2 calls).
    await waitFor(() => expect(PracticeApi.batch).toHaveBeenCalledTimes(2));
    expect(vi.mocked(PracticeApi.batch).mock.calls[1][2]).toBe("speaking");

    // Old mode's response lands FIRST, then the new mode's.
    await act(async () => {
      stale.resolve({ locked: false, items: [item("old-mixed")] } as never);
    });
    await act(async () => {
      fresh.resolve({ locked: false, items: [item("new-speaking")] } as never);
    });

    await waitFor(() => expect(screen.getAllByTestId("item")).toHaveLength(1));
    expect(screen.getByTestId("item")).toHaveTextContent("new-speaking");
  });
});

describe("PracticeFeedPage template feedback", () => {
  function renderFeed() {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <PracticeFeedPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
  }

  it("shows the authored feedback after an incorrect answer", async () => {
    vi.mocked(PracticeApi.batch).mockResolvedValue({ locked: false, items: [item("a")] } as never);
    vi.mocked(PracticeApi.answer).mockResolvedValue({
      correct: false,
      result: "incorrect",
      correct_response: "one",
      xp_awarded: 0,
      feedback: "uno is the number one.",
    } as never);
    renderFeed();
    fireEvent.click(await screen.findByRole("button", { name: "submit-answer" }));
    expect(await screen.findByText("uno is the number one.")).toBeInTheDocument();
  });

  it("renders no feedback line when the server sends none", async () => {
    vi.mocked(PracticeApi.batch).mockResolvedValue({ locked: false, items: [item("a")] } as never);
    vi.mocked(PracticeApi.answer).mockResolvedValue({
      correct: true,
      result: "correct",
      correct_response: "one",
      xp_awarded: 5,
    } as never);
    renderFeed();
    fireEvent.click(await screen.findByRole("button", { name: "submit-answer" }));
    await waitFor(() => expect(PracticeApi.answer).toHaveBeenCalled());
    expect(screen.queryByText("uno is the number one.")).toBeNull();
  });
});
