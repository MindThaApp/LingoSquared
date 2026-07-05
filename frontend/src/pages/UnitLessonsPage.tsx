import { useQuery } from "@tanstack/react-query";
import { Link, useLocation, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CatalogApi } from "../api/endpoints";

export function UnitLessonsPage() {
  const { t } = useTranslation();
  const { unitId = "" } = useParams();
  const location = useLocation();
  const courseId = (location.state as { courseId?: string } | null)?.courseId;

  const lessonsQuery = useQuery({
    queryKey: ["lessons", unitId],
    queryFn: () => CatalogApi.lessons(unitId),
  });

  return (
    <div>
      <h1>{t("unit_lessons.title")}</h1>
      {lessonsQuery.data?.map((lesson) => (
        <Link
          key={lesson.id}
          to={`/lessons/${lesson.id}`}
          state={courseId ? { courseId } : undefined}
        >
          <div className="card continue-card" style={{ marginBottom: 12 }}>
            <div className="continue-info">
              <h3 style={{ margin: "0 0 4px" }}>
                {lesson.order}. {lesson.title}
              </h3>
              <span className="muted">
                {t("unit_lessons.exercise_count", { count: lesson.exercise_count })}
              </span>
            </div>
            <span className="btn">{t("unit_lessons.start")}</span>
          </div>
        </Link>
      ))}
    </div>
  );
}
