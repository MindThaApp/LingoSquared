import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CatalogApi, ProgressApi, ReviewApi } from "@lingo/shared/api/endpoints";
import { setActiveCourse, clearActiveCourse } from "../../lib/activeCourse";
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
  CatalogApi: { units: vi.fn(), lessons: vi.fn() },
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
  clearActiveCourse("u1");
  vi.mocked(ProgressApi.streak).mockResolvedValue({ streak_days: 7 } as never);
  vi.mocked(ProgressApi.xp).mockResolvedValue({ total_xp: 300, xp_today: 12, daily_goal: 20 } as never);
  vi.mocked(ProgressApi.progress).mockResolvedValue({ lesson_progress: [] } as never);
  vi.mocked(ProgressApi.quests).mockResolvedValue({ quests: [] } as never);
  vi.mocked(ReviewApi.due).mockResolvedValue({ due_count: 4 } as never);
});

describe("SideRail", () => {
  it("brand link is not aria-current on Home; only the Home nav item is", () => {
    wrap(<SideRail />, "/");
    const nav = screen.getByRole("navigation", { name: "nav.main_nav" });
    expect(within(nav).getByRole("link", { name: "Auvel" }).getAttribute("aria-current")).toBeNull();
    expect(within(nav).getByRole("link", { name: /nav\.home/ }).getAttribute("aria-current")).toBe("page");
  });

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

describe("DesktopSidebar next-lesson card", () => {
  it("shows the actual next lesson with a Continue link when an active course exists", async () => {
    setActiveCourse("u1", "c1");
    vi.mocked(CatalogApi.units).mockResolvedValue([
      { id: "uA", title: "Unit A", order: 1, lesson_count: 2, completed_lesson_count: 2, section: "core", locked: false },
      { id: "uB", title: "Unit B", order: 2, lesson_count: 2, completed_lesson_count: 1, section: "core", locked: false },
    ] as never);
    vi.mocked(CatalogApi.lessons).mockResolvedValue([
      { id: "l2", title: "Second lesson", order: 2, exercise_count: 5 },
      { id: "l1", title: "First lesson", order: 1, exercise_count: 5 },
    ] as never);
    vi.mocked(ProgressApi.progress).mockResolvedValue({
      lesson_progress: [{ lesson_id: "l1", started_at: "2026-01-01", completed_at: "2026-01-02" }],
    } as never);
    wrap(<DesktopSidebar />);
    const el = await screen.findByTestId("sidebar-next-lesson");
    expect(el.textContent).toContain("Second lesson");
    const link = screen.getByRole("link", { name: "home.continue" });
    expect(link.getAttribute("href")).toBe("/lessons/l2");
    expect(screen.queryByText("home.choose_course")).toBeNull();
  });

  it("falls back to choose-a-course when there is no active course", async () => {
    wrap(<DesktopSidebar />);
    expect(await screen.findByText("home.choose_course")).toBeTruthy();
    expect(CatalogApi.units).not.toHaveBeenCalled();
  });
});

describe("NavBar (phone)", () => {
  it("still renders the bottom tab bar markup with five tabs (Words lives under Profile)", () => {
    const { container } = wrap(<NavBar />);
    const tabbar = container.querySelector("nav.tabbar");
    expect(tabbar).not.toBeNull();
    expect(tabbar!.querySelectorAll("a")).toHaveLength(5);
    expect(tabbar!.querySelector('a[href="/vocabulary"]')).toBeNull();
    expect(tabbar!.querySelectorAll("svg").length).toBe(5);
  });
});
