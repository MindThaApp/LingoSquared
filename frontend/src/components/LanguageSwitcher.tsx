import { useTranslation } from "react-i18next";

// Each language's own name in its own script — fixed regardless of the
// current UI language, so a Dari speaker can still find "English" and an
// English speaker can still find "دری" in the dropdown.
const UI_LANGUAGES: { code: string; nativeName: string }[] = [
  { code: "en", nativeName: "English" },
  { code: "fa", nativeName: "فارسی" },
  { code: "prs", nativeName: "دری" },
];

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation();

  return (
    <select
      className="language-switcher"
      value={i18n.language}
      onChange={(e) => i18n.changeLanguage(e.target.value)}
      aria-label={t("language_switcher.aria_label")}
    >
      {UI_LANGUAGES.map((lang) => (
        <option key={lang.code} value={lang.code}>
          {lang.nativeName}
        </option>
      ))}
    </select>
  );
}
