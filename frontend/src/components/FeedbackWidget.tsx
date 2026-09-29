import { useRef, useState } from "react";
import { matchPath, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { FeedbackApi } from "@lingo/shared/api/endpoints";
import type { ContentIssueCategory } from "@lingo/shared/api/types";
import { downscaleImage } from "../lib/downscaleImage";

// Contract limits -- docs/CONTRACT.md "Feedback attachments": image
// content types only (sniffed server-side from magic bytes, but the
// client still pre-filters for a fast, friendly error), max 5 MB per
// file, max 3 attachment_keys per report.
const MAX_ATTACHMENTS = 3;
const MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024;
const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp"];

type AttachmentStatus = "uploading" | "done" | "failed";

interface Attachment {
  localId: string;
  previewUrl: string;
  status: AttachmentStatus;
  // Set once the upload succeeds -- this is what actually gets sent as
  // attachment_keys on submit. A "failed" attachment has no key and is
  // never included (feedback text must never be blocked/lost over it).
  attachmentKey: string | null;
}

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
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [attachmentError, setAttachmentError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function resetFlow() {
    setStep("kind");
    setKind(null);
    setHereChoice(null);
    setLocationHint("");
    setDescription("");
    attachments.forEach((a) => URL.revokeObjectURL(a.previewUrl));
    setAttachments([]);
    setAttachmentError(null);
  }

  async function addAttachment(file: File) {
    setAttachmentError(null);
    if (attachments.length >= MAX_ATTACHMENTS) {
      setAttachmentError(t("feedback_widget.attachments.error_too_many"));
      return;
    }
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setAttachmentError(t("feedback_widget.attachments.error_unsupported_type"));
      return;
    }
    if (file.size > MAX_ATTACHMENT_BYTES) {
      setAttachmentError(t("feedback_widget.attachments.error_too_large"));
      return;
    }

    const localId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const previewUrl = URL.createObjectURL(file);
    setAttachments((prev) => [...prev, { localId, previewUrl, status: "uploading", attachmentKey: null }]);

    try {
      const upload = await downscaleImage(file);
      // Still under the size cap after downscale? Enforce again -- a
      // downscale failure (falls back to the original file) could leave
      // an oversized file that the server would reject anyway.
      if (upload.size > MAX_ATTACHMENT_BYTES) {
        setAttachments((prev) =>
          prev.map((a) => (a.localId === localId ? { ...a, status: "failed" } : a)),
        );
        setAttachmentError(t("feedback_widget.attachments.error_too_large"));
        return;
      }
      const result = await FeedbackApi.uploadAttachment(upload, upload.name);
      setAttachments((prev) =>
        prev.map((a) =>
          a.localId === localId ? { ...a, status: "done", attachmentKey: result.attachment_key } : a,
        ),
      );
    } catch {
      // Upload failure must never lose the typed feedback text -- mark
      // this one attachment failed and let the rest of the flow continue
      // uninterrupted; submit() below simply omits its key.
      setAttachments((prev) =>
        prev.map((a) => (a.localId === localId ? { ...a, status: "failed" } : a)),
      );
      setAttachmentError(t("feedback_widget.attachments.error_upload_failed"));
    }
  }

  function removeAttachment(localId: string) {
    setAttachments((prev) => {
      const target = prev.find((a) => a.localId === localId);
      if (target) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((a) => a.localId !== localId);
    });
  }

  function handleFileInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []);
    e.target.value = ""; // allow re-selecting the same file later
    // Only take as many as fit within the remaining slots -- addAttachment
    // itself also guards this, but slicing here avoids a burst of
    // identical "too many" errors when several files are picked at once.
    const remaining = MAX_ATTACHMENTS - attachments.length;
    files.slice(0, Math.max(remaining, 0)).forEach((file) => void addAttachment(file));
    if (files.length > remaining) {
      setAttachmentError(t("feedback_widget.attachments.error_too_many"));
    }
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
      const attachmentKeys = attachments
        .filter((a): a is Attachment & { attachmentKey: string } => a.status === "done" && a.attachmentKey !== null)
        .map((a) => a.attachmentKey);
      await FeedbackApi.submit({
        category: CATEGORY_FOR_KIND[kind],
        description: description || undefined,
        page_path: location.pathname,
        client_context: clientContext,
        attachment_keys: attachmentKeys.length > 0 ? attachmentKeys : undefined,
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
        <p className="muted" role="status" style={{ margin: 0 }}>{t("feedback_widget.thanks")}</p>
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
              <span aria-hidden="true">✕</span>
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
                  aria-label={t("feedback_widget.details_placeholder")}
                />
              </div>

              <div className="feedback-widget-attachments">
                {attachments.map((a) => (
                  <div
                    key={a.localId}
                    className={`feedback-widget-attachment-thumb${a.status === "uploading" ? " is-uploading" : ""}`}
                  >
                    <img src={a.previewUrl} alt={t("feedback_widget.attachments.thumbnail_alt")} />
                    <button
                      type="button"
                      className="feedback-widget-attachment-remove"
                      onClick={() => removeAttachment(a.localId)}
                      aria-label={t("feedback_widget.attachments.remove")}
                    >
                      ✕
                    </button>
                  </div>
                ))}
                {attachments.length < MAX_ATTACHMENTS && (
                  <button
                    type="button"
                    className="feedback-widget-attachment-add"
                    onClick={() => fileInputRef.current?.click()}
                    aria-label={t("feedback_widget.attachments.add_photo")}
                  >
                    📷
                  </button>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  multiple
                  hidden
                  onChange={handleFileInputChange}
                />
              </div>
              {attachments.length > 0 && (
                <p className="muted" style={{ fontSize: "0.75rem", margin: "0 0 6px" }}>
                  {t("feedback_widget.attachments.count_hint", { count: attachments.length })}
                </p>
              )}
              {attachments.some((a) => a.status === "uploading") && (
                <p className="muted" style={{ fontSize: "0.75rem", margin: "0 0 6px" }}>
                  {t("feedback_widget.attachments.uploading")}
                </p>
              )}
              {attachmentError && (
                <p role="alert" className="form-error" style={{ fontSize: "0.75rem", padding: "6px 8px", margin: "0 0 6px" }}>
                  {attachmentError}
                </p>
              )}

              <div style={{ display: "flex", gap: 8 }}>
                <button
                  className="btn"
                  disabled={submitting || attachments.some((a) => a.status === "uploading")}
                  onClick={handleSubmit}
                  style={{ flex: 1 }}
                >
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
