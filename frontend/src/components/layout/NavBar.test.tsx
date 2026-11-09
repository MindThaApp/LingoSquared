import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { setActiveCourse } from "../../lib/activeCourse";
import { NavBar } from "./NavBar";

let currentUser: { id: string } | null = { id: "user-1" };
const streak = vi.fn();
const xp = vi.fn();

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
vi.mock("../../auth/AuthContext", () => ({ useAuth: () => ({ user: currentUser }) }));
vi.mock("@lingo/shared/api/endpoints", () => ({
  ProgressApi: {
    streak: (...args: unknown[]) => streak(...args),
    xp: (...args: unknown[]) => xp(...args),
  },
}));
vi.mock("./SideRail", () => ({ SideRail: () => <div data-testid="side-rail" /> }));
vi.mock("../LanguageSwitcher", () => ({ LanguageSwitcher: () => <button>switch language</button> }));

function renderNav(route = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <NavBar />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  localStorage.clear();
  currentUser = { id: "user-1" };
  streak.mockReset().mockResolvedValue({ streak_days: 9 });
  xp.mockReset().mockResolvedValue({ total_xp: 450 });
});

describe("NavBar", () => {
  it("renders nothing and does not fetch progress for a signed-out visitor", () => {
    currentUser = null;
    const { container } = renderNav();
    expect(container).toBeEmptyDOMElement();
    expect(streak).not.toHaveBeenCalled();
    expect(xp).not.toHaveBeenCalled();
  });

  it("routes Learn to the active course and exposes loaded stats accessibly", async () => {
    setActiveCourse("user-1", "course-es");
    renderNav("/courses/course-es");

    const topNav = screen.getByRole("navigation", { name: "nav.main_label" });
    const learnLink = within(topNav).getByRole("link", { name: "nav.learn" });
    expect(learnLink).toHaveAttribute("href", "/courses/course-es");
    expect(learnLink).toHaveClass("active");
    await waitFor(() => expect(screen.getByRole("img", { name: "nav.day_streak: 9" })).toBeInTheDocument());
    expect(screen.getByRole("img", { name: "nav.total_xp: 450" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "switch language" }));
  });
});
