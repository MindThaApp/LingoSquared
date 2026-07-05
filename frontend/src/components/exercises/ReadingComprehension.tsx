import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import type { ExerciseComponentProps } from "./types";

export function ReadingComprehension({ exercise, onAnswer, disabled }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<string | null>(null);
  const options = exercise.prompt.options ?? [];

  return (
    <div className="exercise-shell">
      <div className="card" style={{ marginBottom: 4 }}>
        <TextBlockList blocks={exercise.prompt.text_blocks} />
      </div>
      <div className="exercise-options">
        {options.map((option) => (
          <button
            key={option}
            className={`exercise-option${selected === option ? " selected" : ""}`}
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
