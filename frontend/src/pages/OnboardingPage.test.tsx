import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { OnboardingPage } from "./OnboardingPage";
import { getOnboarding, setOnboarding } from "../lib/onboarding";
import { getActiveCourse } from "../lib/activeCourse";
import { getLevelPreference } from "../lib/levelPreferences";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k), i18n: { language: "en" } }),
}));
vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ user: { id: "u1" } }) }));
vi.mock("./CoursePickerPage", () => ({
  CoursePickerPage: ({ onPickCourse }: { onPickCourse: (c: { id: string }) => void }) => (
    <button onClick={() => onPickCourse({ id: "c1" })}>pick</button>
  ),
}));
vi.mock("../components/DailyGoalPicker", () => ({ DailyGoalPicker: () => <div>goal-picker</div> }));

function renderAt() {
  return render(
    <MemoryRouter initialEntries={["/welcome"]}>
      <Routes>
        <Route path="/welcome" element={<OnboardingPage />} />
        <Route path="/" element={<div>home</div>} />
        <Route path="/courses/:id" element={<div>units</div>} />
        <Route path="/courses/:id/placement" element={<div>placement</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => localStorage.clear());

describe("OnboardingPage", () => {
  it("walks course -> goal -> start from the beginning", () => {
    renderAt();
    fireEvent.click(screen.getByText("pick"));
    expect(getActiveCourse("u1")).toBe("c1");
    expect(screen.getByText("goal-picker")).toBeInTheDocument();
    fireEvent.click(screen.getByText("onboarding.continue"));
    fireEvent.click(screen.getByText("onboarding.beginning_title"));
    expect(screen.getByText("units")).toBeInTheDocument();
    expect(getLevelPreference("c1")).toBe("beginner");
    expect(getOnboarding("u1").status).toBe("done");
  });

  it("offers the placement test", () => {
    setOnboarding("u1", { status: "active", stage: "start", courseId: "c1" });
    renderAt();
    fireEvent.click(screen.getByText("onboarding.placement_title"));
    expect(screen.getByText("placement")).toBeInTheDocument();
  });

  it("resumes at the stored stage", () => {
    setOnboarding("u1", { status: "active", stage: "goal", courseId: "c1" });
    renderAt();
    expect(screen.getByText("goal-picker")).toBeInTheDocument();
  });

  it("can be skipped and stays skipped", () => {
    renderAt();
    fireEvent.click(screen.getByText("onboarding.skip"));
    expect(screen.getByText("home")).toBeInTheDocument();
    expect(getOnboarding("u1").status).toBe("skipped");
  });
});
