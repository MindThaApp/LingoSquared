import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { AdminApi } from "../api/endpoints";
import { ApiError } from "../api/client";

const STATUS_OPTIONS = ["open", "triaged", "resolved", "wontfix", "duplicate"];

export function AdminContentPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("open");
  const [updateError, setUpdateError] = useState<string | null>(null);

  const coverageQuery = useQuery({
    queryKey: ["admin-coverage"],
    queryFn: () => AdminApi.coverage(),
  });
  const issuesQuery = useQuery({
    queryKey: ["admin-issues", statusFilter],
    queryFn: () => AdminApi.issues(statusFilter || undefined),
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

  const forbidden =
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
          <div key={issue.id} className="card" style={{ marginTop: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span className="badge">{issue.category}</span>
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
            {issue.description && <p style={{ margin: "0 0 8px" }}>{issue.description}</p>}
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {STATUS_OPTIONS.filter((s) => s !== issue.status).map((s) => (
                <button
                  key={s}
                  className="btn btn-secondary"
                  style={{ padding: "4px 10px", fontSize: "0.8rem" }}
                  onClick={() => setIssueStatus(issue.id, s)}
                >
                  {t("admin.mark_status", { status: s })}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
