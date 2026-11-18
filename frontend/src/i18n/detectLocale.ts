// First-run UI-language detection from the browser's preferred languages.
// Pure (no DOM access) so it is unit-testable; the caller only uses it when
// the user has no stored explicit choice.

// UI languages the app ships locale bundles for (see LanguageSwitcher).
const SUPPORTED = new Set([
  "en", "nl", "fa", "prs", "es", "fr", "ru", "it", "ar", "pl", "hi", "ro", "ko", "zh", "ja",
]);

/** Map one BCP-47 tag (e.g. "fa-AF", "nl-BE", "zh-Hans-CN") to a UI language code, or null. */
export function mapLocaleTag(tag: string): string | null {
  const parts = tag.toLowerCase().replace(/_/g, "-").split("-");
  const lang = parts[0];
  const region = parts.find((p, i) => i > 0 && p.length === 2);
  // Dari (Afghan Persian) is its own UI language, distinct from Iranian fa.
  if (lang === "prs" || (lang === "fa" && region === "af")) return "prs";
  return SUPPORTED.has(lang) ? lang : null;
}

/** First supported language in the browser's preference order, else "en". */
export function detectUiLanguage(preferred: readonly string[] | undefined): string {
  for (const tag of preferred ?? []) {
    const mapped = mapLocaleTag(tag);
    if (mapped) return mapped;
  }
  return "en";
}
