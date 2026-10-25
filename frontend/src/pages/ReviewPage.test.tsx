import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CatalogApi, ReviewApi } from "@lingo/shared/api/endpoints";
import { setActiveCourse } from "../lib/activeCourse";
import { ReviewPage } from "./ReviewPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: { defaultValue?: string }) => opts?.defaultValue ?? key,
  }),
}));

vi.mock("@lingo/shared/api/endpoints", () => ({
  ReviewApi: { due: vi.fn(), session: vi.fn(), answer: vi.fn(), retry: vi.fn(), reportIssue: vi.fn(), forecast: vi.fn(), leeches: vi.fn() },
  CatalogApi: { course: vi.fn() },
}));

vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ user: { id: "u1" } }) }));
vi.mock("../components/exercises/ExerciseRenderer", () => ({ ExerciseRenderer: () => null }));
vi.mock("../components/ReportIssueButton", () => ({ ReportIssueButton: () => null }));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(ReviewApi.due).mockResolvedValue({
    total_due: 3,
    by_course: [{ course_id: "c-1", due_count: 3 }],
  } as never);
  vi.mocked(CatalogApi.course).mockResolvedValue({ id: "c-1", title: "Dutch" } as never);
  vi.mocked(ReviewApi.forecast).mockResolvedValue({ today: 0, tomorrow: 0, this_week: 0 });
  vi.mocked(ReviewApi.leeches).mockResolvedValue({ threshold: 8, items: [] });
});

describe("ReviewPage session retry", () => {
  it("Retry after a failed session load fetches the session again (was: infinite spinner)", async () => {
    vi.mocked(ReviewApi.session)
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({ items: [] } as never);

    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter>
          <ReviewPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const retry = await screen.findByRole("button", { name: "common.retry" });
    expect(ReviewApi.session).toHaveBeenCalledTimes(1);
    fireEvent.click(retry);

    await waitFor(() => expect(ReviewApi.session).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("review.all_caught_up")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue learning" })).toBeInTheDocument();
  });
});

describe("ReviewPage empty state", () => {
  it("offers a Continue learning button routed to the active course", async () => {
    setActiveCourse("u1", "c-9");
    vi.mocked(ReviewApi.due).mockResolvedValue({ total_due: 0, by_course: [] } as never);
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={["/review"]}>
          <Routes>
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/courses/:id" element={<div>course page</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Continue learning" }));
    expect(await screen.findByText("course page")).toBeInTheDocument();
  });
});
