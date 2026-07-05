import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CatalogApi } from "../api/endpoints";
import type { UnitSummary } from "../api/types";
import { getLevelPreference, recommendedUnitIndex } from "../lib/levelPreferences";

const UNIT_ICONS = ["👋", "🔤", "🔢", "👨‍👩‍👧", "🍽️", "🛍️", "🧭", "🗓️", "✈️", "🏥", "💼", "🏠"];

function PathNode({
  unit,
  icon,
  recommended,
  courseId,
}: {
  unit: UnitSummary;
  icon: string;
  recommended?: boolean;
  courseId: string;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const locked = unit.locked;
  return (
    <div className={`path-node${locked ? " locked" : ""}`}>
      <button
        className="path-bubble"
        aria-label={locked ? `${unit.title}${t("course_units.locked_suffix")}` : unit.title}
        disabled={locked}
        onClick={() =>
          !locked && navigate(`/units/${unit.id}`, { state: { courseId } })
        }
        style={{ border: recommended ? "2px solid var(--accent)" : undefined }}
      >
        {locked ? "🔒" : icon}
      </button>
      <span className="path-title">{unit.title}</span>
      <span className="path-meta">
        {locked
          ? t("course_units.locked_hint")
          : t("course_units.lesson_count", { count: unit.lesson_count })}
      </span>
      {recommended && !locked && (
        <span className="badge" style={{ marginTop: 4 }}>
          {t("course_units.recommended_for_you")}
        </span>
      )}
      {recommended && !locked && !unit.checkpoint_passed && (
        <Link
          className="btn btn-secondary"
          style={{ marginTop: 6, fontSize: "0.85rem", padding: "4px 10px" }}
          to={`/units/${unit.id}/checkpoint`}
        >
          {t("course_units.test_out")}
        </Link>
      )}
      {unit.checkpoint_passed && (
        <span className="badge" style={{ marginTop: 4 }}>
          {t("course_units.checkpoint_passed")}
        </span>
      )}
    </div>
  );
}

export function CourseUnitsPage() {
  const { t } = useTranslation();
  const { courseId = "" } = useParams();

  const courseQuery = useQuery({
    queryKey: ["course", courseId],
    queryFn: () => CatalogApi.course(courseId),
  });
  const unitsQuery = useQuery({
    queryKey: ["units", courseId],
    queryFn: () => CatalogApi.units(courseId),
  });

  const readingWriting =
    unitsQuery.data?.filter((u) => u.section === "reading_writing") ?? [];
  const speaking = unitsQuery.data?.filter((u) => u.section === "speaking") ?? [];

  const level = getLevelPreference(courseId);
  const recommendedIndex =
    level && readingWriting.length > 1 ? recommendedUnitIndex(level, readingWriting.length) : -1;

  return (
    <div>
      <h1 style={{ marginBottom: 4 }}>{courseQuery.data?.title ?? t("course_units.default_title")}</h1>
      {courseQuery.data && <p className="muted">{courseQuery.data.description}</p>}

      <div className="path">
        {readingWriting.length > 0 && (
          <span className="path-section-label">{t("course_units.core_path")}</span>
        )}
        {readingWriting.map((unit, i) => (
          <PathNode
            key={unit.id}
            unit={unit}
            icon={UNIT_ICONS[i % UNIT_ICONS.length]}
            recommended={i === recommendedIndex}
            courseId={courseId}
          />
        ))}

        {speaking.length > 0 && (
          <span className="path-section-label">{t("course_units.speaking")}</span>
        )}
        {speaking.map((unit) => (
          <PathNode key={unit.id} unit={unit} icon="🗣️" courseId={courseId} />
        ))}
      </div>
    </div>
  );
}
