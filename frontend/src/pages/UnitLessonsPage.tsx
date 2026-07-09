import { useQuery } from "@tanstack/react-query";
import { Link, useLocation, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CheckCircle } from "lucide-react";
import { CatalogApi, ProgressApi } from "../api/endpoints";
import type { LessonProgress } from "../api/types";

export function UnitLessonsPage() {
  const { t } = useTranslation();
  const { unitId = "" } = useParams();
  const location = useLocation();
  const courseId = (location.state as { courseId?: string } | null)?.courseId;

  const lessonsQuery = useQuery({
    queryKey: ["lessons", unitId],
    queryFn: () => CatalogApi.lessons(unitId),
  });
  const progressQuery = useQuery({
    queryKey: ["progress"],
    queryFn: () => ProgressApi.progress(),
  });

  const progressByLessonId = new Map<string, LessonProgress>(
    progressQuery.data?.lesson_progress.map((lp) => [lp.lesson_id, lp]) ?? [],
  );

  return (
    <div>
      <h1>{t("unit_lessons.title")}</h1>
      {lessonsQuery.data?.map((lesson) => {
        const progress = progressByLessonId.get(lesson.id);
        const completed = !!progress?.completed_at;
        const inProgress = !!progress?.started_at && !completed;
        return (
          <Link
            key={lesson.id}
            to={`/lessons/${lesson.id}`}
            state={courseId ? { courseId } : undefined}
          >
            <div
              className={`card continue-card lesson-card${completed ? " lesson-card--completed" : ""}`}
              style={{ marginBottom: 12 }}
            >
              <div className="continue-info">
                <h3 style={{ margin: "0 0 4px" }}>
                  {completed && (
                    <CheckCircle
                      size={16}
                      className="lesson-card__check"
                      aria-label={t("unit_lessons.completed")}
                    />
                  )}{" "}
                  {lesson.order}. {lesson.title}
                </h3>
                <span className="muted">
                  {t("unit_lessons.exercise_count", { count: lesson.exercise_count })}
                  {completed && progress?.accuracy != null && (
                    <>
                      {" "}
                      &middot;{" "}
                      {t("unit_lessons.accuracy", {
                        accuracy: Math.round(progress.accuracy * 100),
                      })}
                    </>
                  )}
                </span>
              </div>
              <span className="btn">
                {completed
                  ? t("unit_lessons.review")
                  : inProgress
                    ? t("unit_lessons.continue")
                    : t("unit_lessons.start")}
              </span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
