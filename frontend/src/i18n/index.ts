// Web-only wrapper around @lingo/shared's platform-agnostic i18next core
// (see packages/shared/src/i18n/index.ts). localStorage persistence and
// document.documentElement RTL/lang mutation are DOM APIs that don't exist
// in React Native, so they live here rather than in the shared package --
// this file's job is just to restore the exact previous end-to-end
// behavior (persist + apply direction on every language change, including
// the very first load) on top of the shared init function.
import { initI18n, RTL_LANGUAGES } from "@lingo/shared/i18n";

const STORAGE_KEY = "ui-language";

function applyDocumentDirection(language: string) {
  document.documentElement.dir = RTL_LANGUAGES.has(language) ? "rtl" : "ltr";
  document.documentElement.lang = language;
}

const storedLanguage = localStorage.getItem(STORAGE_KEY) ?? "en";

const i18n = initI18n({
  language: storedLanguage,
  onLanguageChanged: (language) => {
    localStorage.setItem(STORAGE_KEY, language);
    applyDocumentDirection(language);
  },
});

applyDocumentDirection(storedLanguage);

export default i18n;
