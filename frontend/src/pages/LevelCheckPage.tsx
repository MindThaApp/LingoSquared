import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { CatalogApi } from "../api/endpoints";
import { getLevelPreference, setLevelPreference, type SelfReportedLevel } from "../lib/levelPreferences";

const LEVELS: SelfReportedLevel[] = ["beginner", "some_basics", "conversational"];

export function LevelCheckPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { courseId = "" } = useParams();

  const unitsQuery = useQuery({
    queryKey: ["units", courseId],
    queryFn: () => CatalogApi.units(courseId),
  });

  const readingWritingCount =
    unitsQuery.data?.filter((u) => u.section === "reading_writing").length ?? 0;

  // Nothing to ask about: skip straight through if there's only one unit,
  // or the user already answered for this course before.
  const alreadyAnswered = getLevelPreference(courseId) !== null;
  const skip = unitsQuery.isSuccess && (readingWritingCount <= 1 || alreadyAnswered);

  useEffect(() => {
    if (skip) navigate(`/courses/${courseId}`, { replace: true });
  }, [skip, courseId, navigate]);

  if (!unitsQuery.isSuccess || skip) return null;

  function choose(level: SelfReportedLevel) {
    setLevelPreference(courseId, level);
    navigate(`/courses/${courseId}`);
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
    </div>
  );
}
