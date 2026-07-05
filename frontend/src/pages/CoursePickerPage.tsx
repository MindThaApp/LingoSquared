import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { CatalogApi } from "../api/endpoints";
import { sortByCefr } from "../lib/cefr";
import { LANGUAGE_FLAG } from "../lib/flags";
import type { Language } from "../api/types";

const UI_SWITCHABLE_LANGUAGES: Record<string, string> = {
  fa: "language_switcher.farsi",
  prs: "language_switcher.dari",
};

function LangTile({
  lang,
  selected,
  disabled,
  unavailable,
  onClick,
}: {
  lang: Language;
  selected: boolean;
  disabled?: boolean;
  unavailable?: boolean;
  onClick: () => void;
}) {
  const { t } = useTranslation();
  const isDisabled = disabled || unavailable;
  return (
    <button
      className={`lang-tile${selected ? " selected" : ""}`}
      onClick={onClick}
      disabled={isDisabled}
      style={isDisabled ? { opacity: 0.4, cursor: "not-allowed" } : undefined}
      title={unavailable ? t("course_picker.pair_unavailable") : undefined}
    >
      <span className="lang-flag">{LANGUAGE_FLAG[lang.code] ?? "🌐"}</span>
      <span className="lang-name">{lang.name}</span>
      <span className="lang-native" dir={lang.direction}>
        {lang.native_name}
      </span>
      {unavailable && (
        <span className="muted" style={{ fontSize: "0.75rem" }}>
          {t("course_picker.coming_soon")}
        </span>
      )}
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
  const [source, setSource] = useState("");
  const [target, setTarget] = useState("");

  const languagesQuery = useQuery({
    queryKey: ["languages"],
    queryFn: () => CatalogApi.languages(),
  });

  const languagePairsQuery = useQuery({
    queryKey: ["language-pairs"],
    queryFn: () => CatalogApi.languagePairs(),
  });

  const availableTargets = new Set(
    (languagePairsQuery.data ?? [])
      .filter((pair) => pair.source_language === source && pair.course_count > 0)
      .map((pair) => pair.target_language)
  );

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
                unavailable={lang.code !== source && !availableTargets.has(lang.code)}
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
            <Link key={course.id} to={`/courses/${course.id}/level`}>
              <div className="card continue-card" style={{ marginBottom: 12 }}>
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
          ))}
        </>
      )}
    </div>
  );
}
