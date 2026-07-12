import type { TFunction } from "i18next";

/**
 * Returns the UI-language-localized name for a language code (e.g. "Duits"
 * when the UI is nl, "آلمانی" when the UI is fa) via the `language_names`
 * i18n namespace -- NOT the API's `Language.name`, which is always English
 * and previously leaked untranslated into fa/nl/prs UI (course picker, "you
 * speak" / "for speakers" strings). `native_name` (the language's name in
 * itself, e.g. "Deutsch") is a separate, intentionally-unlocalized field and
 * must keep rendering as-is.
 *
 * Falls back to `fallback` (typically the API's `Language.name`) for any
 * code not yet seeded into `language_names`, so a newly-added language never
 * renders a raw i18next missing-key string.
 */
export function localizedLanguageName(
  code: string | undefined | null,
  t: TFunction,
  fallback: string | undefined,
): string | undefined {
  if (!code) return fallback;
  const key = `language_names.${code}`;
  const translated = t(key);
  return translated === key ? fallback : translated;
}
