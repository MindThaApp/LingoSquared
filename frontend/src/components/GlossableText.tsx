import { useEffect, useRef, useState } from "react";
import type { TextBlock as TextBlockType } from "@lingo/shared/api/types";

// Reading-track tap-to-gloss (docs/READING_TRACK_SPEC.md §5). Pure
// presentational component: given a passage `TextBlock` and an authored
// `glosses` map (exact-surface-token -> in-context English gloss), it
// renders the passage with only the glossed tokens made tappable; tapping
// one shows its gloss in a small popover (dismissed on outside tap or
// Escape). Non-glossed tokens render as plain text. No browser dialog is
// ever triggered.
//
// Tokenizer: a Unicode word/separator splitter. A "word" is a run of
// letters/marks/digits, allowing internal apostrophes and hyphens (Dutch
// `'s`, French `d'`, hyphenated compounds); everything else (whitespace,
// punctuation) is preserved verbatim so the passage renders normally.
// Scripts without whitespace word boundaries (Han/Japanese/Hangul) collapse
// into a single word-run: if it isn't a gloss key it simply renders plain
// (no per-word tap) rather than crashing — acceptable for the MVP.
const WORD_OR_SEPARATOR =
  /[\p{L}\p{N}\p{M}]+(?:['’\-][\p{L}\p{N}\p{M}]+)*|[^\p{L}\p{N}\p{M}]+/gu;

// A segment is a "word" (candidate for glossing) if its first character is
// a letter/number/mark, i.e. it was produced by the word branch above.
const WORD_START = /^[\p{L}\p{N}\p{M}]/u;

interface Segment {
  text: string;
  isWord: boolean;
}

export function tokenizeForGloss(text: string): Segment[] {
  const segments: Segment[] = [];
  for (const match of text.matchAll(WORD_OR_SEPARATOR)) {
    const value = match[0];
    segments.push({ text: value, isWord: WORD_START.test(value) });
  }
  return segments;
}

export function GlossableText({
  block,
  glosses,
}: {
  block: TextBlockType;
  glosses: Record<string, string>;
}) {
  // Index of the segment whose popover is currently open (null = none).
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const containerRef = useRef<HTMLSpanElement>(null);

  // Dismiss on outside tap / Escape while a popover is open.
  useEffect(() => {
    if (openIndex === null) return;
    function onPointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpenIndex(null);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpenIndex(null);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [openIndex]);

  const segments = tokenizeForGloss(block.text);

  return (
    <span
      ref={containerRef}
      dir={block.direction}
      lang={block.language_code}
      className="glossable-text"
    >
      {segments.map((segment, i) => {
        const gloss = segment.isWord ? glosses[segment.text] : undefined;
        if (gloss === undefined) {
          // Plain text (separators and non-glossed words) — preserved
          // verbatim so the passage reads exactly as authored.
          return <span key={i}>{segment.text}</span>;
        }
        const isOpen = openIndex === i;
        return (
          <span key={i} className="glossable-word-wrap" style={{ position: "relative" }}>
            <button
              type="button"
              className="glossable-word"
              aria-expanded={isOpen}
              onClick={() => setOpenIndex(isOpen ? null : i)}
            >
              {segment.text}
            </button>
            {isOpen && (
              <span
                role="tooltip"
                className="glossable-popover"
                // The popover is English (the gloss) regardless of the
                // passage direction; force LTR so an RTL passage doesn't
                // flip the gloss text.
                dir="ltr"
                lang="en"
              >
                {gloss}
              </span>
            )}
          </span>
        );
      })}
    </span>
  );
}
