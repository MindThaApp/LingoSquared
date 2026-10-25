import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import { CoursePickerPage } from "./CoursePickerPage";
import { DailyGoalPicker } from "../components/DailyGoalPicker";
import { setActiveCourse } from "../lib/activeCourse";
import { setLevelPreference } from "../lib/levelPreferences";
import { getOnboarding, setOnboarding, type OnboardingState } from "../lib/onboarding";

const STAGES = ["course", "goal", "start"] as const;

/**
 * Guided first start: language pair + course (the existing picker), daily
 * goal (the existing picker), then placement test or "start from the
 * beginning". Skippable at any point and resumable (state is stored per user).
 * There is no reminder-time step: the backend stores no per-user reminder time
 * (reminders go out in a fixed server-side local-time window).
 */
export function OnboardingPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  const userId = user?.id;
  const [state, setState] = useState<OnboardingState>(() => getOnboarding(userId));

  function update(next: OnboardingState) {
    setOnboarding(userId, next);
    setState(next);
  }

  function skip() {
    update({ ...state, status: "skipped" });
    navigate(state.courseId ? `/courses/${state.courseId}` : "/", { replace: true });
  }

  function finish(path: (courseId: string) => string) {
    const courseId = state.courseId;
    if (!courseId) return;
    update({ ...state, status: "done", stage: "start" });
    navigate(path(courseId), { replace: true });
  }

  const stepNumber = STAGES.indexOf(state.stage) + 1;
  const courseId = state.courseId;

  return (
    <div className="onboarding">
      <div className="onboarding-header">
        <span className="badge">{t("onboarding.step_of", { current: stepNumber, total: STAGES.length })}</span>
        <button type="button" className="btn btn-secondary" style={{ padding: "4px 12px" }} onClick={skip}>
          {t("onboarding.skip")}
        </button>
      </div>

      {state.stage === "course" && (
        <CoursePickerPage
          onPickCourse={(course) => {
            setActiveCourse(userId, course.id);
            update({ status: "active", stage: "goal", courseId: course.id });
          }}
        />
      )}

      {state.stage === "goal" && (
        <>
          <h1>{t("onboarding.goal_heading")}</h1>
          <p className="muted">{t("onboarding.goal_body")}</p>
          <DailyGoalPicker />
          <button
            type="button"
            className="btn btn-block"
            style={{ marginTop: 16 }}
            onClick={() => courseId && update({ status: "active", stage: "start", courseId })}
          >
            {t("onboarding.continue")}
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-block"
            style={{ marginTop: 8 }}
            onClick={() => update({ status: "active", stage: "course" })}
          >
            {t("onboarding.back")}
          </button>
        </>
      )}

      {state.stage === "start" && (
        <>
          <h1>{t("onboarding.start_heading")}</h1>
          <p className="muted">{t("onboarding.start_body")}</p>
          <button
            type="button"
            className="card continue-card"
            style={{ width: "100%", textAlign: "start", font: "inherit", color: "inherit", cursor: "pointer" }}
            onClick={() => finish((id) => `/courses/${id}/placement`)}
          >
            <div className="continue-info">
              <h3 style={{ margin: "0 0 4px" }}>{t("onboarding.placement_title")}</h3>
              <span className="muted">{t("onboarding.placement_body")}</span>
            </div>
          </button>
          <button
            type="button"
            className="card continue-card"
            style={{ width: "100%", textAlign: "start", font: "inherit", color: "inherit", cursor: "pointer", marginTop: 12 }}
            onClick={() => {
              if (courseId) setLevelPreference(courseId, "beginner");
              finish((id) => `/courses/${id}`);
            }}
          >
            <div className="continue-info">
              <h3 style={{ margin: "0 0 4px" }}>{t("onboarding.beginning_title")}</h3>
              <span className="muted">{t("onboarding.beginning_body")}</span>
            </div>
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-block"
            style={{ marginTop: 16 }}
            onClick={() => courseId && update({ status: "active", stage: "goal", courseId })}
          >
            {t("onboarding.back")}
          </button>
        </>
      )}
    </div>
  );
}
