import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import fa from "./locales/fa.json";
import prs from "./locales/prs.json";
import nl from "./locales/nl.json";

const RTL_LANGUAGES = new Set(["fa", "prs"]);
const STORAGE_KEY = "ui-language";

function applyDocumentDirection(language: string) {
  document.documentElement.dir = RTL_LANGUAGES.has(language) ? "rtl" : "ltr";
  document.documentElement.lang = language;
}

const storedLanguage = localStorage.getItem(STORAGE_KEY) ?? "en";

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    fa: { translation: fa },
    prs: { translation: prs },
    nl: { translation: nl },
  },
  lng: storedLanguage,
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

i18n.on("languageChanged", (language) => {
  localStorage.setItem(STORAGE_KEY, language);
  applyDocumentDirection(language);
});

applyDocumentDirection(storedLanguage);

export default i18n;
