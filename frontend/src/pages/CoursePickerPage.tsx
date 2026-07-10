import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CatalogApi } from "../api/endpoints";
import { sortByCefr } from "../lib/cefr";
import { LANGUAGE_FLAG } from "../lib/flags";
import { getLevelPreference } from "../lib/levelPreferences";
import type { CourseSummary, Language } from "../api/types";

const UI_SWITCHABLE_LANGUAGES: Record<string, string> = {
  fa: "language_switcher.farsi",
  prs: "language_switcher.dari",
  nl: "language_switcher.dutch",
};

// Below this total unit count for a path, it's real but still growing --
// flagged "in progress" rather than shown as a fully-ready course.
const IN_PROGRESS_UNIT_CEILING = 20;

type Availability = "available" | "in_progress" | "unavailable";

function classifyDepth(totalUnits: number): Availability {
  if (totalUnits <= 0) return "unavailable";
  if (totalUnits < IN_PROGRESS_UNIT_CEILING) return "in_progress";
  return "available";
}

// The shared dev database accumulates disposable 1-unit fixture courses from
// automated tests ("Pair en-it", "ContentKeyUpdateTest", etc.) -- no real
// content has ever shipped with a single unit, so this is a safe, objective
// way to exclude test noise without fragile title matching.
const MIN_REAL_COURSE_UNITS = 2;

/** source:target -> summed unit_count, plus each source's single best (most-developed) path. */
function buildDepthMaps(courses: CourseSummary[] | undefined) {
  const byPair = new Map<string, number>();
  const bestBySource = new Map<string, number>();
  for (const c of courses ?? []) {
    if (c.unit_count < MIN_REAL_COURSE_UNITS) continue;
    const key = `${c.source_language}:${c.target_language}`;
    byPair.set(key, (byPair.get(key) ?? 0) + c.unit_count);
  }
  for (const [key, units] of byPair) {
    const src = key.split(":")[0];
    bestBySource.set(src, Math.max(bestBySource.get(src) ?? 0, units));
  }
  return { byPair, bestBySource };
}

function LangTile({
  lang,
  selected,
  disabled,
  availability,
  onClick,
}: {
  lang: Language;
  selected: boolean;
  disabled?: boolean;
  availability: Availability;
  onClick: () => void;
}) {
  const { t } = useTranslation();
  const isUnavailable = availability === "unavailable";
  const isDisabled = disabled || isUnavailable;
  return (
    <button
      className={`lang-tile lang-tile--${availability}${selected ? " selected" : ""}`}
      onClick={onClick}
      disabled={isDisabled}
      title={
        availability === "unavailable"
          ? t("course_picker.unavailable_hint")
          : availability === "in_progress"
            ? t("course_picker.in_progress_hint")
            : undefined
      }
    >
      {availability === "in_progress" && (
        <span className="lang-tile-ribbon lang-tile-ribbon--progress">
          🚧 {t("course_picker.in_progress")}
        </span>
      )}
      {availability === "unavailable" && (
        <span className="lang-tile-ribbon lang-tile-ribbon--locked">
          🔒 {t("course_picker.coming_soon")}
        </span>
      )}
      <span className="lang-flag">{LANGUAGE_FLAG[lang.code] ?? "🌐"}</span>
      <span className="lang-name">{lang.name}</span>
      <span className="lang-native" dir={lang.direction}>
        {lang.native_name}
      </span>
    </button>
  );
}

function UiLanguagePrompt({ sourceCode }: { sourceCode: string }) {
  const { t, i18n } = useTranslation();
  const [dismissed, setDismissed] = useState(false);
  const labelKey = UI_SWITCHABLE_LANGUAGES[sourceCode];

  if (!labelKey || dismissed || i18n.language === sourceCode) return null;

  const languageName = t(labelKey);

  return (
    <div className="card" style={{ marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
      <span>{t("course_picker.ui_language_prompt", { language: languageName })}</span>
      <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
        <button className="btn" onClick={() => i18n.changeLanguage(sourceCode)}>
          {t("course_picker.ui_language_switch", { language: languageName })}
        </button>
        <button className="btn btn-secondary" onClick={() => setDismissed(true)}>
          {t("course_picker.dismiss")}
        </button>
      </div>
    </div>
  );
}

export function CoursePickerPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  // Restores step 3's language-pair selection when returning here from
  // LevelCheckPage's "Change level" round trip (see the "Change level"
  // button below) -- normal first-time entry has no location.state and
  // falls through to the usual empty step 1.
  const returnState = location.state as { source?: string; target?: string } | null;
  const [source, setSource] = useState(returnState?.source ?? "");
  const [target, setTarget] = useState(returnState?.target ?? "");

  const languagesQuery = useQuery({
    queryKey: ["languages"],
    queryFn: () => CatalogApi.languages(),
  });

  const allCoursesQuery = useQuery({
    queryKey: ["courses", "all"],
    queryFn: () => CatalogApi.allCourses(),
    staleTime: 5 * 60 * 1000,
  });

  const { byPair, bestBySource } = buildDepthMaps(allCoursesQuery.data);

  const coursesQuery = useQuery({
    queryKey: ["courses", source, target],
    queryFn: () => CatalogApi.courses(source, target),
    enabled: Boolean(source && target && source !== target),
  });

  const languages = languagesQuery.data ?? [];
  const courses = coursesQuery.data ? sortByCefr(coursesQuery.data) : undefined;
  const step = !source ? 1 : !target ? 2 : 3;

  return (
    <div>
      <div className="picker-steps">
        <span>{step > 1 ? "✓" : "1."} {t("course_picker.step_speak")}</span>
        <span>›</span>
        <span style={step < 2 ? { opacity: 0.5 } : undefined}>
          {step > 2 ? "✓" : "2."} {t("course_picker.step_learn")}
        </span>
      </div>

      {step === 1 && (
        <>
          <h1>{t("course_picker.speak_heading")}</h1>
          <div className="lang-grid">
            {languages.map((lang) => (
              <LangTile
                key={lang.code}
                lang={lang}
                selected={false}
                availability={classifyDepth(bestBySource.get(lang.code) ?? 0)}
                onClick={() => setSource(lang.code)}
              />
            ))}
          </div>
        </>
      )}

      {step === 2 && (
        <>
          <UiLanguagePrompt sourceCode={source} />
          <h1>{t("course_picker.learn_heading")}</h1>
          <p className="muted">
            {t("course_picker.you_speak")} {LANGUAGE_FLAG[source]}{" "}
            {languages.find((l) => l.code === source)?.name}{" "}
            <button
              className="btn btn-secondary"
              style={{ padding: "4px 12px", marginInlineStart: 8 }}
              onClick={() => setSource("")}
            >
              {t("common.change")}
            </button>
          </p>
          <div className="lang-grid">
            {languages.map((lang) => (
              <LangTile
                key={lang.code}
                lang={lang}
                selected={false}
                disabled={lang.code === source}
                availability={
                  lang.code === source
                    ? "available"
                    : classifyDepth(byPair.get(`${source}:${lang.code}`) ?? 0)
                }
                onClick={() => setTarget(lang.code)}
              />
            ))}
          </div>
        </>
      )}

      {step === 3 && (
        <>
          <UiLanguagePrompt sourceCode={source} />
          <h1>
            {t("course_picker.courses_heading", {
              flag: LANGUAGE_FLAG[target],
              name: languages.find((l) => l.code === target)?.name,
            })}
          </h1>
          <p className="muted">
            {t("course_picker.for_speakers", { name: languages.find((l) => l.code === source)?.name })}{" "}
            <button
              className="btn btn-secondary"
              style={{ padding: "4px 12px", marginInlineStart: 8 }}
              onClick={() => setTarget("")}
            >
              {t("common.change")}
            </button>
          </p>

          {coursesQuery.isLoading && <p className="muted">{t("course_picker.loading_courses")}</p>}

          {courses && courses.length === 0 && (
            <div className="card">
              <h3 style={{ marginTop: 0 }}>{t("course_picker.no_courses_title")}</h3>
              <p className="muted" style={{ marginBottom: 0 }}>
                {t("course_picker.no_courses_body")}
              </p>
            </div>
          )}

          {courses?.map((course, i) => (
            <div key={course.id} style={{ marginBottom: 12 }}>
              <Link to={`/courses/${course.id}/level`}>
                <div className="card continue-card">
                  <div className="continue-info">
                    <h3 style={{ margin: "0 0 4px" }}>
                      {course.title} <span className="badge">{course.level}</span>
                    </h3>
                    <span className="muted">
                      {t(`cefr.${course.level}`)} · {t("course_picker.unit_count", { count: course.unit_count })}
                      {i === 0 && courses.length > 1 && t("course_picker.start_here_hint")}
                    </span>
                  </div>
                  <span className="btn">{t("course_picker.start")}</span>
                </div>
              </Link>
              {/* Only offered once a level's actually been recorded for this
                  course -- a first-time visit already opens the level check
                  via the card link above, so there's nothing to "change"
                  yet. Kept as a sibling of the Link (not nested inside it)
                  to avoid a button-inside-anchor a11y anti-pattern. */}
              {getLevelPreference(course.id) && (
                <button
                  className="btn btn-secondary"
                  style={{ padding: "4px 12px", marginTop: 4 }}
                  onClick={() =>
                    navigate(`/courses/${course.id}/level`, {
                      state: { returnTo: "/courses", source, target },
                    })
                  }
                >
                  {t("course_picker.change_level")}
                </button>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}
