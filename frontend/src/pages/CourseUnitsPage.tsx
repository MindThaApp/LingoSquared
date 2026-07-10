import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Lock } from "lucide-react";
import { CatalogApi, ProgressApi } from "@lingo/shared/api/endpoints";
import type { UnitSummary } from "@lingo/shared/api/types";
import { getLevelPreference, recommendedUnitIndex } from "../lib/levelPreferences";
import { getLastVisitedUnit, setLastVisitedUnit } from "../lib/lastUnitPreferences";
import { unitIcon } from "@lingo/shared/lib/unitIcons";

function PathNode({
  unit,
  recommended,
  current,
  courseId,
}: {
  unit: UnitSummary;
  recommended?: boolean;
  current?: boolean;
  courseId: string;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const locked = unit.locked;
  const Icon = unitIcon(unit.content_key);
  return (
    <div id={`unit-${unit.id}`} className={`path-node${locked ? " locked" : ""}${current ? " current" : ""}`}>
      <button
        className="path-bubble"
        aria-label={locked ? `${unit.title}${t("course_units.locked_suffix")}` : unit.title}
        disabled={locked}
        onClick={() => {
          if (locked) return;
          setLastVisitedUnit(courseId, unit.id);
          navigate(`/units/${unit.id}`, { state: { courseId } });
        }}
        style={{ border: recommended ? "2px solid var(--accent)" : undefined }}
      >
        {locked ? <Lock size={24} /> : <Icon size={24} />}
      </button>
      <span className="path-title">{unit.title}</span>
      <span className="path-meta">
        {locked
          ? t("course_units.locked_hint")
          : unit.completed_lesson_count >= unit.lesson_count && unit.lesson_count > 0
            ? t("course_units.unit_complete")
            : t("course_units.lesson_progress", {
                completed: unit.completed_lesson_count,
                total: unit.lesson_count,
              })}
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
  const progressQuery = useQuery({
    queryKey: ["progress"],
    queryFn: () => ProgressApi.progress(),
  });

  // Course-level "X of Y lessons completed" summary rather than a
  // per-unit completion badge: the units response (UnitSummary) has
  // lesson_count but not per-unit lesson ids, and lesson_progress rows
  // only carry lesson_id — joining units to lessons client-side would
  // need an N+1 CatalogApi.lessons(unitId) fetch per unit (up to ~40
  // per course). skill_progress.completed_lessons already gives an
  // honest, single-request course-wide total instead.
  const skillProgress = progressQuery.data?.skill_progress.find(
    (sp) => sp.course_id === courseId,
  );
  const totalLessons = unitsQuery.data?.reduce((sum, u) => sum + u.lesson_count, 0) ?? 0;

  const readingWriting =
    unitsQuery.data?.filter((u) => u.section === "reading_writing") ?? [];
  const speaking = unitsQuery.data?.filter((u) => u.section === "speaking") ?? [];

  const level = getLevelPreference(courseId);
  const recommendedIndex =
    level && readingWriting.length > 1
      ? recommendedUnitIndex(
          level,
          readingWriting.map((u) => u.content_key),
        )
      : -1;

  const lastUnitId = getLastVisitedUnit(courseId);
  useEffect(() => {
    if (!lastUnitId || !unitsQuery.data) return;
    document.getElementById(`unit-${lastUnitId}`)?.scrollIntoView({ block: "center" });
    // Only re-run when the fetched unit list actually changes -- lastUnitId
    // itself never changes without a navigation that unmounts this page.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unitsQuery.data]);

  return (
    <div>
      <h1 style={{ marginBottom: 4 }}>{courseQuery.data?.title ?? t("course_units.default_title")}</h1>
      {courseQuery.data && <p className="muted">{courseQuery.data.description}</p>}
      {skillProgress && totalLessons > 0 && (
        <p className="muted course-units__progress-summary">
          {t("course_units.lessons_completed_summary", {
            completed: skillProgress.completed_lessons,
            total: totalLessons,
          })}
        </p>
      )}

      {/* Without this, a failed units fetch renders a completely empty
          path -- a misleading "no units" look, not an error. */}
      {unitsQuery.isError && (
        <div className="feedback-banner error">
          <p style={{ margin: "0 0 10px" }}>{t("course_units.units_fetch_error")}</p>
          <button className="btn btn-block" onClick={() => unitsQuery.refetch()}>
            {t("common.retry")}
          </button>
        </div>
      )}

      <div className="path">
        {readingWriting.length > 0 && (
          <span className="path-section-label">{t("course_units.core_path")}</span>
        )}
        {readingWriting.map((unit, i) => (
          <PathNode
            key={unit.id}
            unit={unit}
            recommended={i === recommendedIndex}
            current={unit.id === lastUnitId}
            courseId={courseId}
          />
        ))}

        {speaking.length > 0 && (
          <span className="path-section-label">{t("course_units.speaking")}</span>
        )}
        {speaking.map((unit) => (
          <PathNode key={unit.id} unit={unit} current={unit.id === lastUnitId} courseId={courseId} />
        ))}
      </div>
    </div>
  );
}
