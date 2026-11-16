import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";
import { TRANSLIT_BETA_LANGUAGES } from "../lib/translitPreference";
import { useTranslit } from "./translitContext";

/**
 * The one place that renders target-language text together with its optional romanized
 * pronunciation. The native-script text keeps the caller's dir/lang; the romanization is a
 * separate LTR line below it (never inside the RTL run), labelled for screen readers.
 * `translit` is the string supplied by the API (text_block.translit / prompt.translit_map[text]);
 * nothing is rendered when the setting is off, the language has no store, or it is absent.
 */
export function TargetText({
  text,
  lang,
  dir,
  translit,
  reviewed,
  nativeClassName,
  bare,
  children,
}: {
  text: string;
  lang: string;
  dir?: "ltr" | "rtl";
  translit?: string | null;
  /** The API's reviewed flag for this romanization: native-reviewed text carries no beta marker. */
  reviewed?: boolean;
  /** Class for the native-script span (e.g. "text-block"). */
  nativeClassName?: string;
  /** Option / tile / pair call sites: the surrounding control already carries dir/lang, so the
   *  native text is rendered unwrapped (no attributes, no extra element when nothing extra shows). */
  bare?: boolean;
  /** Optional override of how the native text itself is rendered (e.g. emphasis). */
  children?: ReactNode;
}) {
  const { show } = useTranslit();
  const native = bare ? (
    <>{children ?? text}</>
  ) : (
    <span dir={dir} lang={lang} className={nativeClassName}>
      {children ?? text}
    </span>
  );
  // Nothing to add: keep the DOM exactly what it was before pronunciation existed.
  if (!show || !translit) return native;
  return (
    <span className="target-text">
      {bare ? <span>{children ?? text}</span> : native}
      <Pronunciation translit={translit} lang={lang} reviewed={reviewed} />
    </span>
  );
}

/** The romanization line alone, for call sites that lay out the native text themselves. */
export function Pronunciation({
  translit,
  lang,
  reviewed,
}: {
  translit?: string | null;
  lang: string;
  reviewed?: boolean;
}) {
  const { t } = useTranslation();
  const { show } = useTranslit();
  if (!show || !translit) return null;
  // Beta marker: machine-drafted languages only, and only while that entry is unreviewed.
  const beta = TRANSLIT_BETA_LANGUAGES.has(lang.split("-")[0]) && reviewed !== true;
  return (
    <span className="translit" dir="ltr" lang="und-Latn" role="note" aria-label={t("translit.aria", { text: translit })}>
      <span aria-hidden="true">{translit}</span>
      {beta && (
        <span className="translit-beta" title={t("translit.beta_title")} aria-hidden="true">
          {t("translit.beta")}
        </span>
      )}
    </span>
  );
}
