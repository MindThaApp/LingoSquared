import type { TextBlock as TextBlockType } from "../api/types";
import { SpeakButton } from "./SpeakButton";

// Each block carries its own language/direction (see docs/CONTRACT.md) —
// never inherit direction from the page or lesson. Every block gets a
// speak control so TTS is available everywhere text_blocks render, not
// just in one exercise type. `mediaAssetKey` (Phase D4) is optional and
// caller-supplied — a text_block itself doesn't carry one, only the
// enclosing exercise/teaching-card prompt does, so callers that know
// their prompt has a recorded asset pass it through explicitly.
export function TextBlockView({
  block,
  mediaAssetKey,
}: {
  block: TextBlockType;
  mediaAssetKey?: string;
}) {
  return (
    <span className="text-block-row">
      {block.speaker && <span className="speaker-label">{block.speaker}:</span>}
      <span dir={block.direction} lang={block.language_code} className="text-block">
        {block.text}
      </span>
      <SpeakButton text={block.text} languageCode={block.language_code} mediaAssetKey={mediaAssetKey} />
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
