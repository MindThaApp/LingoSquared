import { useState } from "react";
import { matchPath, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { FeedbackApi } from "@lingo/shared/api/endpoints";
import type { ContentIssueCategory } from "@lingo/shared/api/types";

// Three learner-facing "kinds" the guided flow starts from. Only the
// content-error kind branches into an extra step (step 2 below) -- the
// other two go straight to the description step. This is a purely local
// UI grouping, NOT sent to the backend as-is: it maps down to the real
// ContentIssueCategory set at submit time (see CATEGORY_FOR_KIND).
type FeedbackKind = "content" | "app_bug" | "general";

// Content-error reports from this general, page-scoped widget have no
// specific exercise to pin the error to (that's what ReportIssueButton,
// scoped to an actual exercise/practice item, is for -- see the hint
// surfaced in the "content" branch below). Per the backend's existing
// category set there's no "content error, unspecified" value, so this
// maps to "other" rather than inventing a new backend category.
const CATEGORY_FOR_KIND: Record<FeedbackKind, ContentIssueCategory> = {
  content: "other",
  app_bug: "app_bug",
  general: "general_feedback",
};

type Step = "kind" | "content_location" | "details";

// Route patterns whose params are cheap, genuinely useful extra context
// for a content-error report ("which lesson/unit/course was this on").
// Matched against location.pathname since FeedbackWidget is mounted once
// at the app root (see App.tsx), outside any <Route>, so useParams()
// here would always be empty -- matchPath against the raw pathname is
// the only way to recover route params from a root-level component.
const LESSON_PATTERN = "/lessons/:lessonId";
const UNIT_PATTERN = "/units/:unitId";
const UNIT_CHECKPOINT_PATTERN = "/units/:unitId/checkpoint";
const COURSE_PATTERN = "/courses/:courseId";
const COURSE_LEVEL_PATTERN = "/courses/:courseId/level";

// Pages that render an actual exercise (and therefore already have their
// own exercise-scoped ReportIssueButton, which is far more precise since
// it attaches to a real exercise/practice-item id). Kept as an explicit
// list rather than "not a nav/list page" -- CheckpointPage deliberately
// has NO report button ("a test is a test", no error recycling either),
// so it's excluded on purpose, not an oversight.
function isInsideExerciseScreen(pathname: string): boolean {
  if (matchPath({ path: LESSON_PATTERN, end: true }, pathname)) return true;
  if (matchPath({ path: "/practice", end: true }, pathname)) return true;
  if (matchPath({ path: "/review", end: true }, pathname)) return true;
  return false;
}

// Extras go into the EXISTING client_context object only -- never new
// top-level FeedbackReportIn fields (page_path already covers the route
// path itself). courseId isn't in the URL anywhere; it only ever arrives
// via route `state` threaded from CourseUnitsPage (see LessonRunnerPage's
// identical pattern for reading it).
function autoRouteContext(pathname: string, state: unknown): Record<string, unknown> {
  const ctx: Record<string, unknown> = {};
  const lessonMatch = matchPath({ path: LESSON_PATTERN, end: true }, pathname);
  if (lessonMatch?.params.lessonId) ctx.lesson_id = lessonMatch.params.lessonId;

  const unitMatch =
    matchPath({ path: UNIT_CHECKPOINT_PATTERN, end: true }, pathname) ??
    matchPath({ path: UNIT_PATTERN, end: true }, pathname);
  if (unitMatch?.params.unitId) ctx.unit_id = unitMatch.params.unitId;

  const courseMatch =
    matchPath({ path: COURSE_LEVEL_PATTERN, end: true }, pathname) ??
    matchPath({ path: COURSE_PATTERN, end: true }, pathname);
  const courseId =
    courseMatch?.params.courseId ?? (state as { courseId?: string } | null)?.courseId;
  if (courseId) ctx.course_id = courseId;

  return ctx;
}

// Mounted once at the app root (see App.tsx) so it's available on every
// route, including logged-out screens -- POST /feedback is deliberately
// unauthenticated for exactly this reason. Floating rather than inline
// so it doesn't need per-page wiring the way ReportIssueButton does.
//
// A small guided flow (kind -> [content-error: here-or-elsewhere] ->
// description) rather than one free-text box, so content-error reports
// arrive traceable: which route, which lesson/unit/course if captured
// automatically, or a learner-typed location hint otherwise.
export function FeedbackWidget() {
  const { t } = useTranslation();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<Step>("kind");
  const [kind, setKind] = useState<FeedbackKind | null>(null);
  const [hereChoice, setHereChoice] = useState<"yes" | "no" | null>(null);
  const [locationHint, setLocationHint] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  function resetFlow() {
    setStep("kind");
    setKind(null);
    setHereChoice(null);
    setLocationHint("");
    setDescription("");
  }

  function chooseKind(next: FeedbackKind) {
    setKind(next);
    setStep(next === "content" ? "content_location" : "details");
  }

  function chooseHere(choice: "yes" | "no") {
    setHereChoice(choice);
    if (choice === "yes") setStep("details");
  }

  function goBack() {
    if (step === "details" && kind === "content") {
      setStep("content_location");
      return;
    }
    setStep("kind");
    setKind(null);
    setHereChoice(null);
  }

  async function handleSubmit() {
    if (!kind) return;
    setSubmitting(true);
    try {
      const clientContext: Record<string, unknown> =
        kind === "content" && hereChoice === "yes"
          ? { content_error_on_screen: true, ...autoRouteContext(location.pathname, location.state) }
          : kind === "content" && hereChoice === "no"
            ? { content_error_on_screen: false, location_hint: locationHint || undefined }
            : {};
      await FeedbackApi.submit({
        category: CATEGORY_FOR_KIND[kind],
        description: description || undefined,
        page_path: location.pathname,
        client_context: clientContext,
      });
      setSent(true);
      setTimeout(() => {
        setSent(false);
        setOpen(false);
        resetFlow();
      }, 2500);
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="feedback-widget-trigger"
        aria-label={t("feedback_widget.button_label")}
      >
        💬 {t("feedback_widget.button_label")}
      </button>
    );
  }

  return (
    <div className="feedback-widget-panel card">
      {sent ? (
        <p className="muted" style={{ margin: 0 }}>{t("feedback_widget.thanks")}</p>
      ) : (
        <>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <strong>{t("feedback_widget.title")}</strong>
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                resetFlow();
              }}
              className="muted"
              style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1rem" }}
              aria-label={t("common.cancel")}
            >
              ✕
            </button>
          </div>

          {step === "kind" && (
            <div className="form-field" style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <p className="muted" style={{ margin: "0 0 2px" }}>{t("feedback_widget.step_kind_title")}</p>
              <button type="button" className="btn btn-secondary" onClick={() => chooseKind("content")}>
                {t("feedback_widget.kind.content")}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => chooseKind("app_bug")}>
                {t("feedback_widget.kind.app_bug")}
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => chooseKind("general")}>
                {t("feedback_widget.kind.general")}
              </button>
            </div>
          )}

          {step === "content_location" && (
            <div className="form-field" style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <p className="muted" style={{ margin: "0 0 2px" }}>{t("feedback_widget.step_location_title")}</p>
              <div style={{ display: "flex", gap: 8 }}>
                <button type="button" className="btn btn-secondary" onClick={() => chooseHere("yes")}>
                  {t("feedback_widget.location_yes")}
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => chooseHere("no")}>
                  {t("feedback_widget.location_no")}
                </button>
              </div>
              {hereChoice === "no" && (
                <>
                  <label htmlFor="feedback-location-hint">{t("feedback_widget.location_hint_label")}</label>
                  <input
                    id="feedback-location-hint"
                    type="text"
                    value={locationHint}
                    onChange={(e) => setLocationHint(e.target.value)}
                    placeholder={t("feedback_widget.location_hint_placeholder")}
                  />
                  <button
                    type="button"
                    className="btn"
                    onClick={() => setStep("details")}
                    style={{ width: "100%" }}
                  >
                    {t("feedback_widget.continue")}
                  </button>
                </>
              )}
              <button
                type="button"
                className="muted"
                style={{ background: "none", border: "none", cursor: "pointer", textAlign: "start", padding: 0 }}
                onClick={goBack}
              >
                {t("feedback_widget.back")}
              </button>
            </div>
          )}

          {step === "details" && (
            <>
              {kind === "content" && isInsideExerciseScreen(location.pathname) && (
                <p className="muted" style={{ fontSize: "0.8rem", marginTop: 0 }}>
                  {t("feedback_widget.exercise_hint", { button: t("report_issue.button_label") })}
                </p>
              )}
              <div className="form-field">
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={t("feedback_widget.details_placeholder")}
                />
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn" disabled={submitting} onClick={handleSubmit} style={{ flex: 1 }}>
                  {t("common.submit")}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={goBack}
                >
                  {t("feedback_widget.back")}
                </button>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
