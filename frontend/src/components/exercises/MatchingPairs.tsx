import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { SpeakButton } from "../SpeakButton";
import { answerDirectionForExercise } from "@lingo/shared/lib/scripts";
import type { ExerciseComponentProps } from "./types";

export function MatchingPairs({ exercise, onAnswer, disabled }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const pairs = exercise.prompt.pairs ?? [];
  const answerLanguageCode = exercise.prompt.answer_language_code;
  // The left column is the answer-language side (same answer_language_code
  // the SpeakButton below speaks p.left in). Once matched, the button text
  // becomes a MIXED-direction string -- e.g. an RTL Farsi/Dari term + an LTR
  // arrow + an English gloss -- and with no explicit base direction the
  // Unicode bidi algorithm can put the arrow/gloss on the wrong visual side.
  // Same footgun class as WordOrder.tsx's word_bank fix (2026-07-09): raw
  // token strings carry no direction of their own, unlike text_blocks.
  const direction = answerDirectionForExercise(exercise);
  const rightOptions = useMemo(
    () => [...pairs.map((p) => p.right)].sort(() => Math.random() - 0.5),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- shuffle once per exercise, not per pairs reference
    [exercise.id],
  );
  // Right tiles are tracked by POSITION, never by their text. Several units
  // legitimately map many lefts onto one right (nl a1 unit13 sends 3 items to
  // "lekker" and 3 to "leuk"); keying/disabling by value made the first match
  // consume every tile sharing that text, so the remaining lefts had nothing
  // left to match, Check never enabled, and the lesson could not be completed
  // at all (found live, 2026-07-12). Index 0 is falsy, so every "is this left
  // matched" test must compare against undefined, not truthiness.
  const [matches, setMatches] = useState<Record<string, number>>({});
  const [activeLeft, setActiveLeft] = useState<string | null>(null);

  function chooseRight(rightIndex: number) {
    if (disabled || !activeLeft) return;
    setMatches((prev) => ({ ...prev, [activeLeft]: rightIndex }));
    setActiveLeft(null);
  }

  const matchedRightFor = (left: string): string | undefined =>
    matches[left] === undefined ? undefined : rightOptions[matches[left]];

  const usedRightIndexes = new Set(Object.values(matches));
  const allMatched = pairs.length > 0 && pairs.every((p) => matches[p.left] !== undefined);

  return (
    <div className="exercise-shell">
      <TextBlockList blocks={exercise.prompt.text_blocks} />
      <div className="matching-grid">
        <div>
          {pairs.map((p) => (
            <div key={p.left} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
              <button
                className={`matching-item${activeLeft === p.left ? " selected" : ""}${matches[p.left] !== undefined ? " matched" : ""}`}
                disabled={disabled || matches[p.left] !== undefined}
                onClick={() => setActiveLeft(p.left)}
                style={{ flex: 1, marginBottom: 0 }}
                dir={direction}
                lang={answerLanguageCode}
                aria-pressed={activeLeft === p.left}
                type="button"
              >
                {/* <bdi> isolates each side so the (often English, LTR) match
                    can't reorder around the (possibly RTL) term under the bidi
                    algorithm; the explicit dir above fixes the base direction
                    so term -> arrow -> match always reads in the answer
                    language's own flow, with the arrow glyph flipped to keep
                    pointing from term to match visually in RTL. */}
                <bdi>{p.left}</bdi>
                {matchedRightFor(p.left) !== undefined && (
                  <>
                    {" "}
                    {direction === "rtl" ? "←" : "→"} <bdi>{matchedRightFor(p.left)}</bdi>
                  </>
                )}
              </button>
              {answerLanguageCode && <SpeakButton text={p.left} languageCode={answerLanguageCode} />}
            </div>
          ))}
        </div>
        <div>
          {rightOptions.map((right, rightIndex) => (
            <button
              key={rightIndex}
              className={`matching-item${usedRightIndexes.has(rightIndex) ? " matched" : ""}`}
              disabled={disabled || usedRightIndexes.has(rightIndex) || !activeLeft}
              onClick={() => chooseRight(rightIndex)}
              type="button"
            >
              {right}
            </button>
          ))}
        </div>
      </div>
      <button
        className="btn btn-block"
        disabled={disabled || !allMatched}
        onClick={() =>
          // Submit in the same [{left, right}, ...] shape every matching_pairs
          // exercise's accepted_answers is authored in (content-side, see
          // docs/content/overlays/**), in the exercise's own pair order -
          // NOT the flat {left: right} shape `matches` is kept in locally for
          // O(1) lookup/render. Sending the flat dict here compared unequal
          // to every authored answer and made matching_pairs always grade
          // incorrect regardless of what the learner picked (found live,
          // 2026-07-05).
          onAnswer(pairs.map((p) => ({ left: p.left, right: matchedRightFor(p.left) as string })))
        }
      >
        {t("common.check")}
      </button>
    </div>
  );
}
