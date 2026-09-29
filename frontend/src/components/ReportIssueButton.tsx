import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { AnswerResponse, ContentIssueCategory } from "@lingo/shared/api/types";

// Only the exercise-scoped categories are offered here -- app_bug/
// general_feedback are FeedbackWidget's (a page has no "wrong answer key").
const CATEGORY_KEY: Record<
  Exclude<ContentIssueCategory, "app_bug" | "general_feedback">,
  string
> = {
  wrong_answer_key: "report_issue.category.wrong_answer_key",
  mistranslation: "report_issue.category.mistranslation",
  untaught_vocabulary: "report_issue.category.untaught_vocabulary",
  audio_issue: "report_issue.category.audio_issue",
  unclear_instruction: "report_issue.category.unclear_instruction",
  other: "report_issue.category.other",
};

// Reused across compiled-lesson exercises (Exercise-backed), lexeme
// review sessions, unit checkpoints, and the Endless Practice feed
// (all three PracticeItem-backed) - those two content sources hit
// different report endpoints with different id shapes, so this
// component takes the actual submit action from its caller rather than
// building the request itself. Keeps the component reusable without
// needing a "kind of id" prop or a fork per page.
export function ReportIssueButton({
  lastResponse,
  onSubmit,
}: {
  lastResponse?: AnswerResponse;
  onSubmit: (
    category: ContentIssueCategory,
    description: string | undefined,
    lastResponse: AnswerResponse | undefined,
  ) => Promise<unknown>;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState<ContentIssueCategory>("wrong_answer_key");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      await onSubmit(category, description || undefined, lastResponse);
      setSent(true);
    } finally {
      setSubmitting(false);
    }
  }

  if (sent) {
    return <p className="muted" role="status" style={{ fontSize: "0.85rem" }}>{t("report_issue.thanks")}</p>;
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="muted"
        style={{
          background: "none",
          border: "none",
          padding: 0,
          fontSize: "0.8rem",
          cursor: "pointer",
          textDecoration: "underline",
        }}
      >
        {t("report_issue.button_label")}
      </button>
    );
  }

  return (
    <div className="card" style={{ marginTop: 8 }}>
      <div className="form-field">
        <label htmlFor="issue-category">{t("report_issue.whats_wrong")}</label>
        <select
          id="issue-category"
          value={category}
          onChange={(e) => setCategory(e.target.value as ContentIssueCategory)}
        >
          {Object.entries(CATEGORY_KEY).map(([value, labelKey]) => (
            <option key={value} value={value}>
              {t(labelKey)}
            </option>
          ))}
        </select>
      </div>
      <div className="form-field">
        <label htmlFor="issue-description">{t("report_issue.details_label")}</label>
        <textarea
          id="issue-description"
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={t("report_issue.details_placeholder")}
        />
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button className="btn" disabled={submitting} onClick={handleSubmit}>
          {t("common.submit")}
        </button>
        <button className="btn btn-secondary" onClick={() => setOpen(false)}>
          {t("common.cancel")}
        </button>
      </div>
    </div>
  );
}
