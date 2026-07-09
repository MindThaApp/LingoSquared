import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { correctOptionFromResponse, optionClassName } from "./optionHighlight";
import type { ExerciseComponentProps } from "./types";

export function ReadingComprehension({ exercise, onAnswer, disabled, gradedResult }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<string | null>(null);
  const options = exercise.prompt.options ?? [];
  const correctOption = gradedResult
    ? correctOptionFromResponse(gradedResult.correctResponse, options)
    : null;

  return (
    <div className="exercise-shell">
      <div className="card" style={{ marginBottom: 4 }}>
        <TextBlockList blocks={exercise.prompt.text_blocks} />
      </div>
      <div className="exercise-options">
        {options.map((option) => (
          <button
            key={option}
            className={optionClassName(option, selected, gradedResult, correctOption)}
            disabled={disabled}
            onClick={() => setSelected(option)}
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
