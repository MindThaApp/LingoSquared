import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DesktopSidebar } from "./DesktopSidebar";

const streak = vi.fn();
const xp = vi.fn();
const progress = vi.fn();
const quests = vi.fn();
const due = vi.fn();

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) =>
      options ? `${key}:${Object.values(options).join("/")}` : key,
  }),
}));
vi.mock("../../auth/AuthContext", () => ({ useAuth: () => ({ user: { id: "user-1" } }) }));
vi.mock("@lingo/shared/api/endpoints", () => ({
  ProgressApi: {
    streak: (...args: unknown[]) => streak(...args),
    xp: (...args: unknown[]) => xp(...args),
    progress: (...args: unknown[]) => progress(...args),
    quests: (...args: unknown[]) => quests(...args),
  },
  ReviewApi: { due: (...args: unknown[]) => due(...args) },
  CatalogApi: { units: vi.fn(), lessons: vi.fn() },
}));

function renderSidebar() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <DesktopSidebar />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  localStorage.clear();
  streak.mockReset().mockResolvedValue({ streak_days: 3 });
  xp.mockReset().mockResolvedValue({ xp_today: 30, total_xp: 200, daily_goal: 20 });
  progress.mockReset().mockResolvedValue({ lesson_progress: [] });
  quests.mockReset().mockResolvedValue({ quests: [] });
  due.mockReset().mockResolvedValue({ due_count: 0 });
});

describe("DesktopSidebar", () => {
  it("caps a completed daily goal and shows the nothing-due state", async () => {
    renderSidebar();
    const goal = await screen.findByRole("progressbar");
    await waitFor(() => expect(goal).toHaveAttribute("aria-valuenow", "20"));
    expect(goal.firstElementChild).toHaveStyle({ width: "100%" });
    expect(screen.getByText(/home\.daily_goal_done/)).toBeInTheDocument();
    expect(await screen.findByText("nav.nothing_due")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "home.review" })).not.toBeInTheDocument();
  });

  it("hides goal progress and displays a fallback when the XP request fails", async () => {
    xp.mockRejectedValue(new Error("offline"));
    renderSidebar();
    await waitFor(() => expect(screen.getByTestId("sidebar-xp-today")).toHaveTextContent("—"));
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });
});
