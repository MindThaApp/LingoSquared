import { useState } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CatalogApi } from "@lingo/shared/api/endpoints";
import { sortByCefr } from "@lingo/shared/lib/cefr";
import { LANGUAGE_FLAG } from "@lingo/shared/lib/flags";
import { localizedLanguageName } from "@lingo/shared/lib/localizedLanguageName";
import { pickerTargetLanguages, sortLanguagesByLocalizedName } from "../lib/languageSort";
import { getLevelPreference } from "../lib/levelPreferences";
import type { CourseSummary, Language } from "@lingo/shared/api/types";

const UI_SWITCHABLE_LANGUAGES: Record<string, string> = {
  fa: "language_switcher.farsi",
  prs: "language_switcher.dari",
  nl: "language_switcher.dutch",
  es: "language_switcher.spanish",
  fr: "language_switcher.french",
  ru: "language_switcher.russian",
  it: "language_switcher.italian",
  ar: "language_switcher.arabic",
  pl: "language_switcher.polish",
  hi: "language_switcher.hindi",
  ro: "language_switcher.romanian",
  ko: "language_switcher.korean",
  zh: "language_switcher.chinese",
  ja: "language_switcher.japanese",
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
      <span className="lang-name">{localizedLanguageName(lang.code, t, lang.name)}</span>
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
    <div
      className="card"
      style={{
        marginBottom: 16,
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 12,
      }}
    >
      {/* minWidth: 0 lets this text actually wrap/shrink inside the flex
          container instead of forcing the row wider than the viewport --
          without it, a long language name plus both buttons on one line
          pushed the page past 390px on an iPhone-width viewport. */}
      <span style={{ minWidth: 0 }}>{t("course_picker.ui_language_prompt", { language: languageName })}</span>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
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

export function CoursePickerPage({ onPickCourse }: { onPickCourse?: (course: CourseSummary) => void } = {}) {
  // onPickCourse is set by the guided first start (OnboardingPage): a course
  // card then selects the course instead of opening the level check, and the
  // per-course level / placement shortcuts are replaced by the next step.
  const { t, i18n } = useTranslation();
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
  const uiLocale = i18n.language;
  const sourceLanguages = sortLanguagesByLocalizedName(languages, t, uiLocale);
  const targetLanguages = pickerTargetLanguages(languages, source, byPair, t, uiLocale);
  const courses = coursesQuery.data ? sortByCefr(coursesQuery.data) : undefined;
  // Course descriptions only exist on the per-course detail endpoint.
  const detailQueries = useQueries({
    queries: (courses ?? []).map((c) => ({
      queryKey: ["course", c.id],
      queryFn: () => CatalogApi.course(c.id),
      staleTime: 5 * 60 * 1000,
    })),
  });
  const descriptionById = new Map<string, string>();
  (courses ?? []).forEach((c, i) => {
    const d = detailQueries[i]?.data?.description;
    if (d) descriptionById.set(c.id, d);
  });
  const step = !source ? 1 : !target ? 2 : 3;

  // Without this, a failed languages fetch renders an empty tile grid and a
  // failed all-courses fetch renders every language as a locked "coming
  // soon" tile -- both misleading success states, not errors.
  if (languagesQuery.isError || allCoursesQuery.isError) {
    return (
      <div className="feedback-banner error">
        <p style={{ margin: "0 0 10px" }}>{t("course_picker.catalog_fetch_error")}</p>
        <button
          className="btn btn-block"
          onClick={() => {
            if (languagesQuery.isError) languagesQuery.refetch();
            if (allCoursesQuery.isError) allCoursesQuery.refetch();
          }}
        >
          {t("common.retry")}
        </button>
      </div>
    );
  }

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
            {sourceLanguages.map((lang) => (
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
            {localizedLanguageName(source, t, languages.find((l) => l.code === source)?.name)}{" "}
            <button
              className="btn btn-secondary"
              style={{ padding: "4px 12px", marginInlineStart: 8 }}
              onClick={() => setSource("")}
            >
              {t("common.change")}
            </button>
          </p>
          <div className="lang-grid">
            {targetLanguages.map((lang) => (
              <LangTile
                key={lang.code}
                lang={lang}
                selected={false}
                availability={classifyDepth(byPair.get(`${source}:${lang.code}`) ?? 0)}
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
              name: localizedLanguageName(target, t, languages.find((l) => l.code === target)?.name),
            })}
          </h1>
          <p className="muted">
            {t("course_picker.for_speakers", {
              name: localizedLanguageName(source, t, languages.find((l) => l.code === source)?.name),
            })}{" "}
            <button
              className="btn btn-secondary"
              style={{ padding: "4px 12px", marginInlineStart: 8 }}
              onClick={() => setTarget("")}
            >
              {t("common.change")}
            </button>
          </p>

          {coursesQuery.isLoading && <p className="muted">{t("course_picker.loading_courses")}</p>}

          {coursesQuery.isError && (
            <div className="feedback-banner error">
              <p style={{ margin: "0 0 10px" }}>{t("course_picker.courses_fetch_error")}</p>
              <button className="btn btn-block" onClick={() => coursesQuery.refetch()}>
                {t("common.retry")}
              </button>
            </div>
          )}

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
              {onPickCourse ? (
                <button
                  type="button"
                  className="card continue-card"
                  style={{ width: "100%", textAlign: "start", font: "inherit", color: "inherit", cursor: "pointer" }}
                  onClick={() => onPickCourse(course)}
                >
                  <div className="continue-info">
                    <h3 style={{ margin: "0 0 4px" }}>
                      {course.title} <span className="badge">{course.level}</span>
                    </h3>
                    <span className="muted">
                      {t(`cefr.${course.level}`)} · {t("course_picker.unit_count", { count: course.unit_count })}
                      {i === 0 && courses.length > 1 && t("course_picker.start_here_hint")}
                    </span>
                  </div>
                  <span className="btn">{t("onboarding.choose")}</span>
                </button>
              ) : (
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
              )}
              {descriptionById.get(course.id) && (
                <p className="muted course-description" style={{ margin: "4px 0 0" }}>
                  {descriptionById.get(course.id)}
                </p>
              )}
              {/* Sibling of the Link above (not nested inside it) to avoid a
                  button-inside-anchor a11y anti-pattern. "Change level" is
                  only offered once a level's actually been recorded for this
                  course -- a first-time visit already opens the level check
                  via the card link above, so there's nothing to "change"
                  yet. "Take the test" always shows: it's a direct shortcut
                  into the real placement test, bypassing the level-check
                  page entirely. */}
              {!onPickCourse && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 4 }}>
                {getLevelPreference(course.id) && (
                  <button
                    className="btn btn-secondary"
                    style={{ padding: "4px 12px" }}
                    onClick={() =>
                      navigate(`/courses/${course.id}/level`, {
                        state: { returnTo: "/courses", source, target },
                      })
                    }
                  >
                    {t("course_picker.change_level")}
                  </button>
                )}
                <button
                  className="btn btn-secondary"
                  style={{ padding: "4px 12px" }}
                  onClick={() => navigate(`/courses/${course.id}/placement`)}
                >
                  {t("placement.course_picker_cta")}
                </button>
              </div>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}
