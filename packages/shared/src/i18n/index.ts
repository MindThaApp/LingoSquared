import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import type { BackendModule } from "i18next";

// en is the fallback language and stays in the entry chunk. Every other locale
// is an explicit dynamic import (its own chunk), fetched by i18next's own
// backend hook BEFORE changeLanguage switches/emits "languageChanged".
const LOCALE_LOADERS: Record<string, () => Promise<{ default: Record<string, unknown> }>> = {
  fa: () => import("./locales/fa.json"),
  prs: () => import("./locales/prs.json"),
  nl: () => import("./locales/nl.json"),
};

const lazyLocaleBackend: BackendModule = {
  type: "backend",
  init() {},
  read(language, _namespace, callback) {
    const loader = LOCALE_LOADERS[language];
    // Unknown codes resolve to an empty bundle so lookups fall back to en.
    if (!loader) {
      callback(null, {});
      return;
    }
    loader().then(
      (m) => callback(null, m.default),
      (err) => callback(err instanceof Error ? err : new Error(String(err)), null),
    );
  },
};

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
  i18n.use(lazyLocaleBackend).use(initReactI18next).init({
    resources: { en: { translation: en } },
    partialBundledLanguages: true,
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
