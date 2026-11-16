// Farsi (fa) and Dari (prs) courses launch with a visible "beta" label until
// native speakers have finished reviewing them (Ramin, 2026-11-16).
export const BETA_LANGUAGES: ReadonlySet<string> = new Set(["fa", "prs"]);

export function isBetaLanguage(code: string | undefined | null): boolean {
  return !!code && BETA_LANGUAGES.has(code);
}

export function isBetaCourse(c: { source_language?: string; target_language?: string }): boolean {
  return isBetaLanguage(c.source_language) || isBetaLanguage(c.target_language);
}
