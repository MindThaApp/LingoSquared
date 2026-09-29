import { useMemo, useState } from "react";
import { seededShuffle } from "../../lib/shuffle";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { correctOptionFromResponse, optionClassName } from "./optionHighlight";
import type { ExerciseComponentProps } from "./types";

export function ReadingComprehension({ exercise, onAnswer, disabled, gradedResult }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<string | null>(null);
  const rawOptions = exercise.prompt.options ?? [];
  // Display order only: authored content puts the correct option first.
  // The submitted payload is still the option TEXT.
  const nonce = useMemo(() => Math.random().toString(36), []);
  const options = useMemo(
    () => seededShuffle(rawOptions, `${exercise.id}:${nonce}`),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [exercise.id, nonce, rawOptions.join("\u0001")],
  );
  const correctOption = gradedResult
    ? correctOptionFromResponse(gradedResult.correctResponse, options)
    : null;

  return (
    <div className="exercise-shell">
      <div className="card" style={{ marginBottom: 4 }}>
        <TextBlockList blocks={exercise.prompt.text_blocks} />
      </div>
      <div className="exercise-options" lang={exercise.prompt.answer_language_code}>
        {options.map((option) => (
          <button
            key={option}
            type="button"
            className={optionClassName(option, selected, gradedResult, correctOption)}
            disabled={disabled}
            onClick={() => setSelected(option)}
            aria-pressed={selected === option}
          >
            {option}
          </button>
        ))}
      </div>
      <button
        className="btn btn-block"
        disabled={disabled || !selected}
        onClick={() => selected && onAnswer(selected)}
      >
        {t("common.check")}
      </button>
    </div>
  );
}
