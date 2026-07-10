import { useState } from "react";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { FeedbackApi } from "@lingo/shared/api/endpoints";
import type { ContentIssueCategory } from "@lingo/shared/api/types";

const CATEGORY_KEY: Record<ContentIssueCategory, string> = {
  app_bug: "feedback_widget.category.app_bug",
  general_feedback: "feedback_widget.category.general_feedback",
  wrong_answer_key: "report_issue.category.wrong_answer_key",
  mistranslation: "report_issue.category.mistranslation",
  untaught_vocabulary: "report_issue.category.untaught_vocabulary",
  audio_issue: "report_issue.category.audio_issue",
  unclear_instruction: "report_issue.category.unclear_instruction",
  other: "report_issue.category.other",
};

// Only the two general categories make sense from an arbitrary page --
// the exercise-specific ones (wrong_answer_key etc.) stay on
// ReportIssueButton, which is scoped to an actual exercise/practice item.
const WIDGET_CATEGORIES: ContentIssueCategory[] = ["app_bug", "general_feedback"];

// Mounted once at the app root (see App.tsx) so it's available on every
// route, including logged-out screens -- POST /feedback is deliberately
// unauthenticated for exactly this reason. Floating rather than inline
// so it doesn't need per-page wiring the way ReportIssueButton does.
export function FeedbackWidget() {
  const { t } = useTranslation();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState<ContentIssueCategory>("app_bug");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      await FeedbackApi.submit({
        category,
        description: description || undefined,
        page_path: location.pathname,
      });
      setSent(true);
      setTimeout(() => {
        setSent(false);
        setOpen(false);
        setDescription("");
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
              onClick={() => setOpen(false)}
              className="muted"
              style={{ background: "none", border: "none", cursor: "pointer", fontSize: "1rem" }}
              aria-label={t("common.cancel")}
            >
              ✕
            </button>
          </div>
          <div className="form-field">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as ContentIssueCategory)}
            >
              {WIDGET_CATEGORIES.map((value) => (
                <option key={value} value={value}>
                  {t(CATEGORY_KEY[value])}
                </option>
              ))}
            </select>
          </div>
          <div className="form-field">
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t("feedback_widget.details_placeholder")}
            />
          </div>
          <button className="btn" disabled={submitting} onClick={handleSubmit} style={{ width: "100%" }}>
            {t("common.submit")}
          </button>
        </>
      )}
    </div>
  );
}
