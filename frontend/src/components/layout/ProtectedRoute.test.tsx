import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

let auth = { user: null as null | { id: string }, status: "loading", retrySession: vi.fn(), retrying: false, logout: vi.fn() };
vi.mock("../../auth/AuthContext", () => ({
  useAuth: () => auth,
  readCachedUser: () => null,
}));
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

import { ProtectedRoute } from "./ProtectedRoute";

function LoginDestination() {
  const location = useLocation();
  return <div>login from:{(location.state as { from?: string } | null)?.from}</div>;
}

function renderRoute(url = "/private?tab=2#details") {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/private" element={<ProtectedRoute><div>private content</div></ProtectedRoute>} />
        <Route path="/login" element={<LoginDestination />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ProtectedRoute", () => {
  it("shows a labelled loading state while authentication is unresolved", () => {
    auth = { ...auth, user: null, status: "loading" };
    renderRoute();
    expect(screen.getByRole("status")).toHaveTextContent("common.loading");
  });

  it("preserves the full attempted URL when redirecting a signed-out user", () => {
    auth = { ...auth, user: null, status: "anonymous" };
    renderRoute();
    expect(screen.getByText("login from:/private?tab=2#details")).toBeInTheDocument();
  });

  it("renders children for an authenticated user and the unavailable screen for an unverified session", () => {
    auth = { ...auth, user: { id: "u1" }, status: "authenticated" };
    const first = renderRoute();
    expect(screen.getByText("private content")).toBeInTheDocument();
    first.unmount();

    auth = { ...auth, user: null, status: "unverified" };
    renderRoute();
    expect(screen.getByRole("heading", { name: "session_unavailable.title" })).toBeInTheDocument();
    expect(screen.queryByText(/login from:/)).toBeNull();
  });
});
