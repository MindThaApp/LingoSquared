import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

const reportCrash = vi.fn();
const handleCrash = vi.fn();
vi.mock("../lib/crashReporter", () => ({
  reportCrash: (...args: unknown[]) => reportCrash(...args),
  truncateComponentStack: (stack?: string | null) => stack?.slice(0, 1000),
}));
vi.mock("../lib/sentry", () => ({ handleCrash: (...args: unknown[]) => handleCrash(...args) }));
vi.mock("../i18n", () => ({ default: { t: (key: string) => key } }));

import { ErrorBoundary } from "./ErrorBoundary";

let shouldThrow = true;
function UnstableChild() {
  if (shouldThrow) throw new Error("broken render");
  return <div>recovered child</div>;
}

afterEach(() => {
  vi.restoreAllMocks();
  reportCrash.mockReset();
  handleCrash.mockReset();
  shouldThrow = true;
});

describe("ErrorBoundary", () => {
  it("shows a recovery screen and reports render failures through both reporters", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(<MemoryRouter><ErrorBoundary><UnstableChild /></ErrorBoundary></MemoryRouter>);
    expect(screen.getByRole("heading", { name: "error_boundary.title" })).toBeInTheDocument();
    expect(reportCrash).toHaveBeenCalledWith(
      "error_boundary",
      "broken render",
      expect.any(String),
      { component_stack: expect.any(String) },
    );
    expect(handleCrash).toHaveBeenCalledWith(expect.objectContaining({ message: "broken render" }), expect.any(String));
  });

  it("resets the boundary when the home link is used", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(<MemoryRouter><ErrorBoundary><UnstableChild /></ErrorBoundary></MemoryRouter>);
    shouldThrow = false;
    fireEvent.click(screen.getByRole("link", { name: "error_boundary.back_home" }));
    expect(screen.getByText("recovered child")).toBeInTheDocument();
  });
});
