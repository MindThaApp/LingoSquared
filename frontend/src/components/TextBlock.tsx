import type { TextBlock as TextBlockType } from "@lingo/shared/api/types";
import { useTranslation } from "react-i18next";
import { SpeakButton } from "./SpeakButton";
import { EmphasizedText } from "./EmphasizedText";
import { useTargetLanguage } from "./targetLanguageContext";

export function shouldShowSpeaker(
  blockLanguage: string,
  targetLanguage: string | null | undefined,
  uiLanguage: string | undefined,
): boolean {
  if (targetLanguage) return blockLanguage === targetLanguage.split("-")[0];
  return !(uiLanguage && blockLanguage === uiLanguage);
}

// Each block carries its own language/direction (see docs/CONTRACT.md) —
// never inherit direction from the page or lesson. Every block gets a
// speak control so TTS is available everywhere text_blocks render, not
// just in one exercise type. `mediaAssetKey` (Phase D4) is optional and
// caller-supplied — a text_block itself doesn't carry one, only the
// enclosing exercise/teaching-card prompt does, so callers that know
// their prompt has a recorded asset pass it through explicitly.
//
// Renders `block.text` through `EmphasizedText` (originally wired only
// into TeachingCardView/LessonRunnerPage for `note`/`feedback` fields,
// see AUTHORING_GUIDE.md #15) rather than as a plain string. Found live
// 2026-07-06: the Endless Practice engine's generated `word_order` hint
// mixes a target-language frame with a substituted English gloss span
// (`backend/app/practice/service.py`'s `render_frame(..., emphasize=True)`)
// wrapped in the same single-asterisk convention, but every exercise
// component renders its prompt's text_blocks through this exact shared
// component (`TextBlockList` below) — without this change the asterisks
// would show up literally instead of rendering emphasized. Safe to apply
// universally: audited every text_blocks/frame text field across
// docs/content/ for stray literal asterisks and found none outside
// `review.notes` (internal authoring metadata, never rendered) — plain
// text with no asterisks renders byte-identical either way.
export function TextBlockView({
  block,
  mediaAssetKey,
}: {
  block: TextBlockType;
  mediaAssetKey?: string;
}) {
  // With a target language in context (provided by ExerciseRenderer from the
  // exercise's answer_language_code, or by a page), speak only blocks in that
  // language. Without one (teaching cards etc.), fall back to the old
  // heuristic: hide the speaker for blocks in the UI language.
  const { i18n } = useTranslation();
  const targetLanguage = useTargetLanguage();
  const blockLanguage = block.language_code.split("-")[0];
  const uiLanguage = i18n?.language?.split("-")[0];
  const showSpeaker = shouldShowSpeaker(blockLanguage, targetLanguage, uiLanguage);
  return (
    <span className="text-block-row">
      {block.speaker && <span className="speaker-label">{block.speaker}:</span>}
      <span dir={block.direction} lang={block.language_code} className="text-block">
        <EmphasizedText text={block.text} />
      </span>
      {showSpeaker && (
        <SpeakButton text={block.text} languageCode={block.language_code} mediaAssetKey={mediaAssetKey} />
      )}
    </span>
  );
}

export function TextBlockList({
  blocks,
  mediaAssetKey,
}: {
  blocks: TextBlockType[];
  mediaAssetKey?: string;
}) {
  return (
    <div className="text-block-list">
      {blocks.map((block, i) => (
        <TextBlockView block={block} mediaAssetKey={mediaAssetKey} key={i} />
      ))}
    </div>
  );
}
