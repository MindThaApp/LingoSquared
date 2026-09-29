import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Check, List, Lock } from "lucide-react";
import { CatalogApi, ProgressApi } from "@lingo/shared/api/endpoints";
import type { UnitSummary } from "@lingo/shared/api/types";
import { getLevelPreference, recommendedUnitIndex } from "../lib/levelPreferences";
import { getPlacementRecommendation } from "../lib/placementPreferences";
import { getLastVisitedUnit, setLastVisitedUnit } from "../lib/lastUnitPreferences";
import { useAuth } from "../auth/AuthContext";
import { setActiveCourse } from "../lib/activeCourse";
import { unitIcon } from "@lingo/shared/lib/unitIcons";
import { DesktopSidebar } from "../components/layout/DesktopSidebar";

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
  const done = unit.completed_lesson_count >= unit.lesson_count && unit.lesson_count > 0;
  const Icon = unitIcon(unit.content_key);
  return (
    <div
      id={`unit-${unit.id}`}
      className={`path-node${locked ? " locked" : ""}${current ? " current" : ""}${done ? " done" : ""}`}
    >
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
          state={{ courseId }}
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

// Compact, collapsible numbered overview of every unit in the course.
// Long courses (en-nl is 50+ units) previously offered no way to reach a
// specific unit other than scrolling the entire path -- the auto-scroll to
// the last-visited unit only helps the "resume where I left off" case, not
// deliberate revisiting. Rows reuse the data the path already fetches
// (lesson_count / completed_lesson_count / locked / checkpoint_passed --
// zero extra requests); clicking a row scrolls the main path to that
// unit's node via the same getElementById(`unit-${id}`).scrollIntoView
// mechanism the last-visited auto-scroll uses. Locked units are jumpable
// too, on purpose: their path node shows the unlock hint in place, which
// is more informative than making the row inert.
function UnitIndex({
  sections,
  currentUnitId,
}: {
  sections: { label: string; units: UnitSummary[] }[];
  currentUnitId: string | null;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const populated = sections.filter((s) => s.units.length > 0);
  // Continuous numbering across sections, matching the top-to-bottom
  // order the path itself renders in (core path first, then speaking).
  let number = 0;
  return (
    <div className="unit-index-wrap">
      <button
        className="btn btn-secondary unit-index-toggle"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <List size={16} />
        {open ? t("course_units.unit_index_hide") : t("course_units.unit_index_show")}
      </button>
      {open && (
        <nav className="unit-index" aria-label={t("course_units.unit_index_show")}>
          {populated.map((section) => (
            <div key={section.label}>
              {populated.length > 1 && (
                <span className="unit-index__section-label">{section.label}</span>
              )}
              {section.units.map((unit) => {
                number += 1;
                const complete =
                  unit.lesson_count > 0 && unit.completed_lesson_count >= unit.lesson_count;
                return (
                  <button
                    key={unit.id}
                    className={`unit-index__row${unit.locked ? " locked" : ""}${
                      complete ? " done" : ""
                    }${unit.id === currentUnitId ? " current" : ""}`}
                    aria-label={
                      unit.locked ? `${unit.title}${t("course_units.locked_suffix")}` : unit.title
                    }
                    onClick={() => {
                      setOpen(false);
                      // Scroll after the collapsed panel has re-rendered --
                      // collapsing shifts everything below it up, so scrolling
                      // synchronously here would land off-target.
                      requestAnimationFrame(() => {
                        document
                          .getElementById(`unit-${unit.id}`)
                          ?.scrollIntoView({ block: "center", behavior: "smooth" });
                      });
                    }}
                  >
                    <span className="unit-index__num" aria-hidden="true">
                      {number}
                    </span>
                    <span className="unit-index__title">{unit.title}</span>
                    <span className="unit-index__meta">
                      {unit.locked ? (
                        <Lock size={14} aria-hidden="true" />
                      ) : complete ? (
                        <Check size={15} className="unit-index__done-check" aria-hidden="true" />
                      ) : (
                        `${unit.completed_lesson_count}/${unit.lesson_count}`
                      )}
                    </span>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
      )}
    </div>
  );
}

export function CourseUnitsPage() {
  const { t } = useTranslation();
  const { courseId = "" } = useParams();
  const { user } = useAuth();
  const userId = user?.id;
  useEffect(() => {
    if (userId && courseId) setActiveCourse(userId, courseId);
  }, [userId, courseId]);

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

  // Placement test recommendation (docs/PLACEMENT_TEST_SPEC.md §2.3) takes
  // precedence over the coarse self-report heuristic wherever both exist --
  // it points at a specific unit, resolved server-side from real graded
  // answers, not a self-reported bucket. Falls back to the self-report only
  // when there's no placement recommendation, or its unit isn't found in
  // this course's current reading/writing list (e.g. content reshuffled).
  const placementRec = getPlacementRecommendation(courseId);
  const placementIndex = placementRec
    ? readingWriting.findIndex((u) => u.id === placementRec.unitId)
    : -1;

  const level = getLevelPreference(courseId);
  const selfReportIndex =
    level && readingWriting.length > 1
      ? recommendedUnitIndex(
          level,
          readingWriting.map((u) => u.content_key),
        )
      : -1;

  const recommendedIndex = placementIndex !== -1 ? placementIndex : selfReportIndex;

  const lastUnitId = getLastVisitedUnit(courseId);
  useEffect(() => {
    if (!lastUnitId || !unitsQuery.data) return;
    document.getElementById(`unit-${lastUnitId}`)?.scrollIntoView({ block: "center" });
    // Only re-run when the fetched unit list actually changes -- lastUnitId
    // itself never changes without a navigation that unmounts this page.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [unitsQuery.data]);

  return (
    <div className="page-with-aside">
      <div className="page-main-col">
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
      {readingWriting.length + speaking.length > 1 && (
        <UnitIndex
          sections={[
            { label: t("course_units.core_path"), units: readingWriting },
            { label: t("course_units.speaking"), units: speaking },
          ]}
          currentUnitId={lastUnitId}
        />
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
      <DesktopSidebar />
    </div>
  );
}
