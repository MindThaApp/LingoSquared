import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import type { ExerciseComponentProps } from "./types";

export function Flashcard({ exercise, onAnswer, disabled }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [flipped, setFlipped] = useState(false);
  const backBlocks = exercise.prompt.back_text_blocks as
    | typeof exercise.prompt.text_blocks
    | undefined;

  return (
    <div className="exercise-shell">
      <div className="card flashcard-face" style={{ flexDirection: "column", gap: 12 }}>
        <TextBlockList blocks={exercise.prompt.text_blocks} />
        {flipped && backBlocks && <TextBlockList blocks={backBlocks} />}
      </div>
      {!flipped ? (
        <button className="btn btn-block" disabled={disabled} onClick={() => setFlipped(true)}>
          {t("exercise.show_answer")}
        </button>
      ) : (
        <div className="answer-actions">
          <button
            className="btn btn-secondary"
            style={{ flex: 1 }}
            disabled={disabled}
            onClick={() => onAnswer("unknown")}
          >
            {t("exercise.didnt_know")}
          </button>
          <button className="btn" style={{ flex: 1 }} disabled={disabled} onClick={() => onAnswer("known")}>
            {t("exercise.got_it")}
          </button>
        </div>
      )}
    </div>
  );
}
