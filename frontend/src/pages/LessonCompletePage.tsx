import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { LessonCompleteResult } from "../api/types";
import { MissedWordsSummary } from "./LessonRunnerPage";

export function LessonCompletePage() {
  const { t } = useTranslation();
  const location = useLocation();
  const state = location.state as
    | {
        completion: LessonCompleteResult;
        totalXp: number;
        missedWords?: { text: string; languageCode?: string }[];
      }
    | null;

  return (
    <div style={{ textAlign: "center", paddingTop: 40 }}>
      <div style={{ fontSize: "4rem", marginBottom: 8 }}>🎉</div>
      <h1>{t("lesson_complete.title")}</h1>
      {state ? (
        <div className="stat-grid" style={{ maxWidth: 360, margin: "20px auto" }}>
          <div className="stat-card">
            <span className="stat-value">⭐ {state.completion.xp_awarded}</span>
            <span className="stat-label">{t("lesson_complete.xp_earned")}</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">
              {Math.round(state.completion.accuracy * 100)}%
            </span>
            <span className="stat-label">{t("lesson_complete.accuracy")}</span>
          </div>
        </div>
      ) : (
        <p className="muted">{t("lesson_complete.finished")}</p>
      )}
      {state?.missedWords && <MissedWordsSummary words={state.missedWords} />}
      <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 24 }}>
        <Link className="btn btn-secondary" to="/courses">
          {t("lesson_complete.back_to_courses")}
        </Link>
        <Link className="btn" to="/review">
          {t("lesson_complete.go_to_review")}
        </Link>
      </div>
    </div>
  );
}
