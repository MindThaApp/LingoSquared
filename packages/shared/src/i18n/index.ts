import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import fa from "./locales/fa.json";
import prs from "./locales/prs.json";
import nl from "./locales/nl.json";

// Platform seam (added when this file moved from frontend/src/i18n/index.ts
// into @lingo/shared): the original file directly read/wrote
// `localStorage` and mutated `document.documentElement` for RTL layout --
// neither exists in a React Native runtime. Both are now the caller's
// responsibility: initI18n() takes the already-resolved starting language
// and an optional onLanguageChanged callback instead of reaching for
// localStorage/DOM itself. Web's frontend/src/i18n/index.ts is the thin
// wrapper that restores the exact previous behavior (see that file).
export const RTL_LANGUAGES = new Set(["fa", "prs"]);

export interface InitI18nOptions {
  language: string;
  onLanguageChanged?: (language: string) => void;
}

export function initI18n({ language, onLanguageChanged }: InitI18nOptions) {
  i18n.use(initReactI18next).init({
    resources: {
      en: { translation: en },
      fa: { translation: fa },
      prs: { translation: prs },
      nl: { translation: nl },
    },
    lng: language,
    fallbackLng: "en",
    interpolation: { escapeValue: false },
  });

  if (onLanguageChanged) {
    i18n.on("languageChanged", onLanguageChanged);
  }

  return i18n;
}

export default i18n;
