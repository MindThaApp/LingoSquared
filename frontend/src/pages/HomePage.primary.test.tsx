import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { HomePage } from "./HomePage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language: "en" } }),
}));
vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ user: { id: "u1" } }) }));
vi.mock("../components/layout/DesktopSidebar", () => ({ DesktopSidebar: () => null }));
vi.mock("../lib/onboarding", () => ({ shouldShowOnboarding: () => false }));
vi.mock("@lingo/shared/api/endpoints", () => ({
  ProgressApi: {
    streak: async () => ({ streak_days: 2, active_today: true }),
    xp: async () => ({ total_xp: 10, xp_today: 0, daily_goal: 20 }),
    progress: async () => ({ lessons_started: 1, lessons_completed: 0, lesson_progress: [] }),
    achievements: async () => [],
    quests: async () => ({ quests: [] }),
  },
  ReviewApi: { due: async () => ({ due_count: 3 }) },
}));

describe("HomePage primary action", () => {
  it("shows the main learn action before the stats and secondary review card", async () => {
    const { container } = render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <HomePage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    const learn = await screen.findByText("home.learn");
    const review = await screen.findByText("home.review");
    const stats = container.querySelector(".stat-grid")!;
    expect(learn.compareDocumentPosition(stats) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(learn).toHaveClass("btn");
    expect(learn).not.toHaveClass("btn-secondary");
    expect(review).toHaveClass("btn-secondary");
    expect(container.querySelector(".home-primary")).toContainElement(learn);
  });
});
