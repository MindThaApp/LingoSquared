import { useEffect } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { CatalogApi } from "@lingo/shared/api/endpoints";
import { getLevelPreference, setLevelPreference, type SelfReportedLevel } from "../lib/levelPreferences";

const LEVELS: SelfReportedLevel[] = ["beginner", "some_basics", "conversational"];

// Present when this page was opened via CoursePickerPage's "Change level"
// affordance (step 3) rather than the normal first-visit-to-a-course entry
// point -- lets an already-answered course still show the picker instead of
// auto-skipping, and sends the learner back to the course list (with the
// same source/target selection restored) instead of into the course.
interface RelevelState {
  returnTo?: string;
  source?: string;
  target?: string;
}

export function LevelCheckPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { courseId = "" } = useParams();

  const relevel = location.state as RelevelState | null;
  const forceShow = Boolean(relevel?.returnTo);

  const unitsQuery = useQuery({
    queryKey: ["units", courseId],
    queryFn: () => CatalogApi.units(courseId),
  });

  const readingWritingCount =
    unitsQuery.data?.filter((u) => u.section === "reading_writing").length ?? 0;

  // Nothing to ask about: skip straight through if there's only one unit,
  // or the user already answered for this course before -- unless they got
  // here explicitly to redo it (forceShow), in which case an existing
  // answer should never auto-skip the picker.
  const alreadyAnswered = getLevelPreference(courseId) !== null;
  const skip = unitsQuery.isSuccess && (readingWritingCount <= 1 || (alreadyAnswered && !forceShow));

  useEffect(() => {
    if (skip) navigate(`/courses/${courseId}`, { replace: true });
  }, [skip, courseId, navigate]);

  // Without this, a failed units fetch means isSuccess never turns true and
  // the `return null` below renders a permanently blank screen -- no
  // spinner, no error, no retry, ever.
  if (unitsQuery.isError) {
    return (
      <div className="feedback-banner error">
        <p style={{ margin: "0 0 10px" }}>{t("level_check.units_fetch_error")}</p>
        <button className="btn btn-block" onClick={() => unitsQuery.refetch()}>
          {t("common.retry")}
        </button>
      </div>
    );
  }

  if (!unitsQuery.isSuccess || skip) return null;

  function returnToOrigin() {
    if (relevel?.returnTo) {
      navigate(relevel.returnTo, { state: { source: relevel.source, target: relevel.target } });
    } else {
      navigate(`/courses/${courseId}`);
    }
  }

  function choose(level: SelfReportedLevel) {
    setLevelPreference(courseId, level);
    returnToOrigin();
  }

  return (
    <div>
      <h1>{t("level_check.heading")}</h1>
      <p className="muted" style={{ marginBottom: 20 }}>{t("level_check.subheading")}</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 12, maxWidth: 480 }}>
        {LEVELS.map((level) => (
          <button
            key={level}
            className="card continue-card"
            style={{ textAlign: "start", cursor: "pointer" }}
            onClick={() => choose(level)}
          >
            <div className="continue-info">
              <h3 style={{ margin: "0 0 4px" }}>{t(`level_check.${level}_title`)}</h3>
              <span className="muted">{t(`level_check.${level}_description`)}</span>
            </div>
          </button>
        ))}
      </div>
      {forceShow && (
        <button
          className="btn btn-secondary"
          style={{ marginTop: 16 }}
          onClick={returnToOrigin}
        >
          {t("level_check.cancel")}
        </button>
      )}
    </div>
  );
}
