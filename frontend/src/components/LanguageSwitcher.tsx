import { useTranslation } from "react-i18next";

// Each language's own name in its own script — fixed regardless of the
// current UI language, so a Dari speaker can still find "English" and an
// English speaker can still find "دری" in the dropdown.
const UI_LANGUAGES: { code: string; nativeName: string }[] = [
  { code: "en", nativeName: "English" },
  { code: "nl", nativeName: "Nederlands" },
  { code: "fa", nativeName: "فارسی" },
  { code: "prs", nativeName: "دری" },
  { code: "es", nativeName: "Español" },
  { code: "fr", nativeName: "Français" },
  { code: "ru", nativeName: "Русский" },
  { code: "it", nativeName: "Italiano" },
  { code: "ar", nativeName: "العربية" },
  { code: "pl", nativeName: "Polski" },
  { code: "hi", nativeName: "हिन्दी" },
  { code: "ro", nativeName: "Română" },
  { code: "ko", nativeName: "한국어" },
  { code: "zh", nativeName: "中文" },
  { code: "ja", nativeName: "日本語" },
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
        <option key={lang.code} value={lang.code} lang={lang.code}>
          {lang.nativeName}
        </option>
      ))}
    </select>
  );
}
