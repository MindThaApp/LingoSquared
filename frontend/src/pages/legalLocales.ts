import type { ComponentType } from "react";

// Locale shell for the Privacy Policy and Terms of Service. The English text
// in PrivacyPolicyPage / TermsOfServicePage is the only authoritative version
// until the owner signs off the legal wording. When a translation is approved,
// add a body component here, keyed by base language code, e.g.
//   LEGAL_TRANSLATIONS.privacy = { nl: PrivacyPolicyNl };
// LegalDocument then renders it (lang/dir taken from the locale) instead of
// the English body + "English only" notice. Keep this EMPTY until sign-off.
export type LegalDocId = "privacy" | "terms";

export const LEGAL_TRANSLATIONS: Record<LegalDocId, Partial<Record<string, ComponentType>>> = {
  privacy: {},
  terms: {},
};

const RTL = new Set(["ar", "fa", "prs", "he", "ur"]);

export function legalLocaleInfo(language: string | undefined, doc: LegalDocId) {
  const base = (language ?? "en").toLowerCase().split("-")[0];
  return { base, Translated: LEGAL_TRANSLATIONS[doc][base], dir: RTL.has(base) ? "rtl" : "ltr" } as const;
}
