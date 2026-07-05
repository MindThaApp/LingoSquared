import { useMemo, useState } from "react";
import { TextBlockList } from "../TextBlock";
import { SpeakButton } from "../SpeakButton";
import type { ExerciseComponentProps } from "./types";

export function MatchingPairs({ exercise, onAnswer, disabled }: ExerciseComponentProps) {
  const pairs = exercise.prompt.pairs ?? [];
  const answerLanguageCode = exercise.prompt.answer_language_code;
  const rightOptions = useMemo(
    () => [...pairs.map((p) => p.right)].sort(() => Math.random() - 0.5),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- shuffle once per exercise, not per pairs reference
    [exercise.id],
  );
  const [matches, setMatches] = useState<Record<string, string>>({});
  const [activeLeft, setActiveLeft] = useState<string | null>(null);

  function chooseRight(right: string) {
    if (disabled || !activeLeft) return;
    setMatches((prev) => ({ ...prev, [activeLeft]: right }));
    setActiveLeft(null);
  }

  const usedRights = new Set(Object.values(matches));
  const allMatched = pairs.length > 0 && pairs.every((p) => matches[p.left]);

  return (
    <div className="exercise-shell">
      <TextBlockList blocks={exercise.prompt.text_blocks} />
      <div className="matching-grid">
        <div>
          {pairs.map((p) => (
            <div key={p.left} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
              <button
                className={`matching-item${activeLeft === p.left ? " selected" : ""}${matches[p.left] ? " matched" : ""}`}
                disabled={disabled || Boolean(matches[p.left])}
                onClick={() => setActiveLeft(p.left)}
                style={{ flex: 1, marginBottom: 0 }}
              >
                {p.left} {matches[p.left] ? `→ ${matches[p.left]}` : ""}
              </button>
              {answerLanguageCode && <SpeakButton text={p.left} languageCode={answerLanguageCode} />}
            </div>
          ))}
        </div>
        <div>
          {rightOptions.map((right) => (
            <button
              key={right}
              className={`matching-item${usedRights.has(right) ? " matched" : ""}`}
              disabled={disabled || usedRights.has(right) || !activeLeft}
              onClick={() => chooseRight(right)}
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
          onAnswer(pairs.map((p) => ({ left: p.left, right: matches[p.left] })))
        }
      >
        Check
      </button>
    </div>
  );
}
