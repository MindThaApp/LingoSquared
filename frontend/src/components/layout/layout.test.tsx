import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ProgressApi, ReviewApi } from "@lingo/shared/api/endpoints";
import { NavBar } from "./NavBar";
import { SideRail } from "./SideRail";
import { DesktopSidebar } from "./DesktopSidebar";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      opts && "earned" in opts ? `${key}:${opts.earned}/${opts.goal}` : key,
  }),
}));

vi.mock("@lingo/shared/api/endpoints", () => ({
  ProgressApi: { streak: vi.fn(), xp: vi.fn(), progress: vi.fn(), quests: vi.fn() },
  ReviewApi: { due: vi.fn() },
}));

vi.mock("../../auth/AuthContext", () => ({ useAuth: () => ({ user: { id: "u1" } }) }));
vi.mock("../LanguageSwitcher", () => ({ LanguageSwitcher: () => null }));

function wrap(ui: React.ReactNode, route = "/") {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(ProgressApi.streak).mockResolvedValue({ streak_days: 7 } as never);
  vi.mocked(ProgressApi.xp).mockResolvedValue({ total_xp: 300, xp_today: 12, daily_goal: 20 } as never);
  vi.mocked(ProgressApi.progress).mockResolvedValue({ lesson_progress: [] } as never);
  vi.mocked(ProgressApi.quests).mockResolvedValue({ quests: [] } as never);
  vi.mocked(ReviewApi.due).mockResolvedValue({ due_count: 4 } as never);
});

describe("SideRail", () => {
  it("renders a labelled nav landmark and marks the active link with aria-current=page", () => {
    wrap(<SideRail />, "/practice");
    const nav = screen.getByRole("navigation", { name: "nav.main_nav" });
    const active = within(nav).getByRole("link", { name: /nav\.practice/ });
    expect(active.getAttribute("aria-current")).toBe("page");
    expect(within(nav).getByRole("link", { name: /nav\.home/ }).getAttribute("aria-current")).toBeNull();
  });
});

describe("DesktopSidebar", () => {
  it("shows streak, goal progress, and due reviews from the shared queries", async () => {
    wrap(<DesktopSidebar />);
    const aside = screen.getByRole("complementary", { name: "nav.sidebar" });
    await waitFor(() => expect(within(aside).getByTestId("sidebar-streak").textContent).toContain("7"));
    expect(await within(aside).findByText("home.daily_goal_progress:12/20")).toBeTruthy();
    expect(await within(aside).findByRole("link", { name: "home.review" })).toBeTruthy();
  });
});

describe("NavBar (phone)", () => {
  it("still renders the bottom tab bar markup with every tab", () => {
    const { container } = wrap(<NavBar />);
    const tabbar = container.querySelector("nav.tabbar");
    expect(tabbar).not.toBeNull();
    expect(tabbar!.querySelectorAll("a")).toHaveLength(6);
  });
});
