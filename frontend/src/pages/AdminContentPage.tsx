import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { AdminApi } from "@lingo/shared/api/endpoints";
import { ApiError } from "@lingo/shared/api/client";
import { formatCorrectResponse } from "@lingo/shared/lib/formatAnswer";
import type { ContentIssue, ExercisePrompt } from "@lingo/shared/api/types";
import { useAuth } from "../auth/AuthContext";

const STATUS_OPTIONS = ["open", "triaged", "resolved", "wontfix", "duplicate"];

// One-line human summary of a prompt payload (Exercise.prompt or a
// generated PracticeItem's stored prompt -- same shape family). Joins the
// teaching text_blocks; falls back to audio_text for listen-type prompts
// whose text lives there instead.
function promptSummary(prompt: ExercisePrompt): string {
  const blocks = Array.isArray(prompt.text_blocks) ? prompt.text_blocks : [];
  const text = blocks
    .map((b) => (b.speaker ? `${b.speaker}: ${b.text}` : b.text))
    .filter(Boolean)
    .join(" / ");
  if (text) return text;
  return typeof prompt.audio_text === "string" ? prompt.audio_text : "";
}

export function AdminContentPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("open");
  const [updateError, setUpdateError] = useState<string | null>(null);

  // Gate on the real is_admin flag from the authenticated session so a
  // non-admin who navigates here directly gets the access-required screen
  // without this page ever firing admin API calls. UX only -- the backend's
  // admin_user dependency (401/403 on every /admin/* route) is the actual
  // security boundary; the 403 check below stays as the fallback for any
  // stale locally-stored session that predates the is_admin field.
  const isAdmin = user?.is_admin === true;

  const coverageQuery = useQuery({
    queryKey: ["admin-coverage"],
    queryFn: () => AdminApi.coverage(),
    enabled: isAdmin,
  });
  const issuesQuery = useQuery({
    queryKey: ["admin-issues", statusFilter],
    queryFn: () => AdminApi.issues(statusFilter || undefined),
    enabled: isAdmin,
  });

  async function setIssueStatus(issueId: string, status: string) {
    setUpdateError(null);
    // The backend hard-requires duplicate_of_id when marking an issue
    // duplicate (422 duplicate_target_required) -- this button used to
    // send only {status} and fail silently on every use.
    let duplicateOfId: string | undefined;
    if (status === "duplicate") {
      const target = window.prompt(t("admin.duplicate_target_prompt"));
      if (!target) return;
      duplicateOfId = target.trim();
    }
    try {
      await AdminApi.updateIssue(issueId, { status, duplicate_of_id: duplicateOfId });
      queryClient.invalidateQueries({ queryKey: ["admin-issues"] });
      queryClient.invalidateQueries({ queryKey: ["admin-coverage"] });
    } catch {
      setUpdateError(t("admin.update_status_error"));
    }
  }

  async function saveTriageNotes(issueId: string, notes: string) {
    setUpdateError(null);
    try {
      await AdminApi.updateIssue(issueId, { triage_notes: notes });
      queryClient.invalidateQueries({ queryKey: ["admin-issues"] });
    } catch {
      // The card's Save button re-enables on failure by itself: it is
      // disabled only while the draft matches the last-saved value, and a
      // failed save never updates issue.triage_notes.
      setUpdateError(t("admin.update_status_error"));
    }
  }

  const forbidden =
    !isAdmin ||
    (coverageQuery.error instanceof ApiError && coverageQuery.error.status === 403) ||
    (issuesQuery.error instanceof ApiError && issuesQuery.error.status === 403);

  if (forbidden) {
    return (
      <div className="card">
        <h2 style={{ marginTop: 0 }}>{t("admin.access_required_title")}</h2>
        <p className="muted">{t("admin.access_required_body")}</p>
      </div>
    );
  }

  return (
    <div>
      <h1>{t("admin.heading")}</h1>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>{t("admin.coverage_title")}</h2>
        {coverageQuery.isLoading && <p className="muted">{t("admin.loading")}</p>}
        {coverageQuery.data && (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid var(--border)" }}>
                <th style={{ padding: "6px 8px" }}>{t("admin.table.pair")}</th>
                <th style={{ padding: "6px 8px" }}>{t("admin.table.courses")}</th>
                <th style={{ padding: "6px 8px" }}>{t("admin.table.units")}</th>
                <th style={{ padding: "6px 8px" }}>{t("admin.table.lessons")}</th>
                <th style={{ padding: "6px 8px" }}>{t("admin.table.open_issues")}</th>
              </tr>
            </thead>
            <tbody>
              {coverageQuery.data.map((row) => (
                <tr
                  key={`${row.source_language}-${row.target_language}`}
                  style={{ borderBottom: "1px solid var(--border)" }}
                >
                  <td style={{ padding: "6px 8px" }}>
                    {row.source_language} → {row.target_language}
                  </td>
                  <td style={{ padding: "6px 8px" }}>{row.course_count}</td>
                  <td style={{ padding: "6px 8px" }}>{row.total_unit_count}</td>
                  <td style={{ padding: "6px 8px" }}>{row.total_lesson_count}</td>
                  <td style={{ padding: "6px 8px" }}>
                    {row.open_issue_count > 0 ? (
                      <span className="badge" style={{ background: "var(--incorrect-soft)", color: "var(--incorrect)" }}>
                        {row.open_issue_count}
                      </span>
                    ) : (
                      row.open_issue_count
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h2 style={{ margin: 0 }}>{t("admin.issues_title")}</h2>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">{t("admin.all_statuses")}</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        {updateError && <p className="feedback-banner error">{updateError}</p>}
        {issuesQuery.isLoading && <p className="muted">{t("admin.loading")}</p>}
        {issuesQuery.data?.length === 0 && <p className="muted">{t("admin.no_issues")}</p>}
        {issuesQuery.data?.map((issue) => (
          <IssueCard
            key={issue.id}
            issue={issue}
            onSetStatus={setIssueStatus}
            onSaveNotes={saveTriageNotes}
          />
        ))}
      </div>
    </div>
  );
}

function IssueCard({
  issue,
  onSetStatus,
  onSaveNotes,
}: {
  issue: ContentIssue;
  onSetStatus: (issueId: string, status: string) => void;
  onSaveNotes: (issueId: string, notes: string) => Promise<void>;
}) {
  const { t } = useTranslation();
  // Draft triage notes, seeded from the stored value. The Save button is
  // disabled while the draft matches what's stored, so a successful save
  // (which refetches and updates issue.triage_notes) re-disables it and a
  // failed one leaves it enabled for retry.
  const [notes, setNotes] = useState(issue.triage_notes ?? "");
  const [savingNotes, setSavingNotes] = useState(false);
  const savedNotes = issue.triage_notes ?? "";

  const prompt = issue.exercise_prompt ?? issue.practice_item_prompt;
  const promptText = prompt ? promptSummary(prompt) : "";
  const hasAnswers = issue.learner_response != null || issue.exercise_correct_response != null;

  async function saveNotes() {
    setSavingNotes(true);
    try {
      await onSaveNotes(issue.id, notes.trim());
    } finally {
      setSavingNotes(false);
    }
  }

  return (
    <div className="card" style={{ marginTop: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <span style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          <span className="badge">{issue.category}</span>
          {(issue.open_report_count ?? 0) > 1 && (
            <span
              className="badge"
              style={{ background: "var(--incorrect-soft)", color: "var(--incorrect)" }}
              title={t("admin.open_report_count_title")}
            >
              {t("admin.open_report_count", { count: issue.open_report_count ?? 0 })}
            </span>
          )}
        </span>
        <span className="muted" style={{ fontSize: "0.8rem" }}>
          {new Date(issue.created_at).toLocaleString()}
        </span>
      </div>
      <p className="muted" style={{ fontSize: "0.85rem" }}>
        {issue.exercise_id
          ? t("admin.exercise_label", { id: issue.exercise_id })
          : issue.practice_item_id
            ? t("admin.practice_item_label", { id: issue.practice_item_id })
            : t("admin.page_label", { path: issue.page_path })}
      </p>
      {promptText && (
        <p style={{ margin: "0 0 6px" }}>
          <span className="muted" style={{ fontSize: "0.8rem" }}>{t("admin.prompt_label")}</span>{" "}
          {/* dir="auto": prompt/answer text can be RTL (fa/prs) regardless of the admin UI language */}
          <span dir="auto">{promptText}</span>
        </p>
      )}
      {hasAnswers && (
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", margin: "0 0 8px" }}>
          {issue.learner_response != null && (
            <div>
              <div className="muted" style={{ fontSize: "0.8rem" }}>{t("admin.learner_answer_label")}</div>
              <div dir="auto" style={{ color: "var(--incorrect)" }}>
                {formatCorrectResponse(issue.learner_response)}
              </div>
            </div>
          )}
          {issue.exercise_correct_response != null && (
            <div>
              <div className="muted" style={{ fontSize: "0.8rem" }}>{t("admin.correct_answer_label")}</div>
              <div dir="auto" style={{ color: "var(--correct)" }}>
                {formatCorrectResponse(issue.exercise_correct_response)}
              </div>
            </div>
          )}
        </div>
      )}
      {issue.description && <p style={{ margin: "0 0 8px" }}>{issue.description}</p>}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {STATUS_OPTIONS.filter((s) => s !== issue.status).map((s) => (
          <button
            key={s}
            className="btn btn-secondary"
            style={{ padding: "4px 10px", fontSize: "0.8rem" }}
            onClick={() => onSetStatus(issue.id, s)}
          >
            {t("admin.mark_status", { status: s })}
          </button>
        ))}
      </div>
      <div style={{ marginTop: 8 }}>
        <label className="muted" style={{ fontSize: "0.8rem", display: "block", marginBottom: 4 }}>
          {t("admin.triage_notes_label")}
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            maxLength={5000}
            placeholder={t("admin.triage_notes_placeholder")}
            style={{ width: "100%", resize: "vertical", marginTop: 4 }}
          />
        </label>
        <button
          className="btn btn-secondary"
          style={{ padding: "4px 10px", fontSize: "0.8rem" }}
          disabled={savingNotes || notes.trim() === savedNotes}
          onClick={saveNotes}
        >
          {savingNotes ? t("admin.saving_notes") : t("admin.save_notes")}
        </button>
      </div>
    </div>
  );
}
