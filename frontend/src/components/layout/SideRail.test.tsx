import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { setActiveCourse } from "../../lib/activeCourse";
import { SideRail } from "./SideRail";

let currentUser: { id: string } | null = { id: "user-1" };

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock("../../auth/AuthContext", () => ({ useAuth: () => ({ user: currentUser }) }));

function renderRail(route = "/") {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <SideRail />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  localStorage.clear();
  currentUser = { id: "user-1" };
});

describe("SideRail", () => {
  it("is absent for signed-out visitors", () => {
    currentUser = null;
    const { container } = renderRail();
    expect(container).toBeEmptyDOMElement();
  });

  it("uses the saved course for Learn while retaining all desktop destinations", () => {
    setActiveCourse("user-1", "course-fr");
    renderRail("/courses/course-fr/units");
    const nav = screen.getByRole("navigation", { name: "nav.main_nav" });
    const links = within(nav).getAllByRole("link");
    expect(links).toHaveLength(7);
    expect(within(nav).getByRole("link", { name: /nav\.learn/ })).toHaveAttribute("href", "/courses/course-fr");
    expect(within(nav).getByRole("link", { name: /nav\.learn/ })).toHaveClass("active");
    expect(within(nav).getByRole("link", { name: /nav\.vocabulary/ })).toHaveAttribute("href", "/vocabulary");
  });
});
