import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import type { SelfGrade } from "@lingo/shared/api/types";
import type { ExerciseComponentProps } from "./types";

const RATINGS: { grade: SelfGrade; key: string }[] = [
  { grade: "again", key: "review.rate_again" },
  { grade: "hard", key: "review.rate_hard" },
  { grade: "good", key: "review.rate_good" },
  { grade: "easy", key: "review.rate_easy" },
];

export function Flashcard({ exercise, onAnswer, disabled, ratings }: ExerciseComponentProps) {
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
      ) : ratings ? (
        <div
          role="group"
          aria-label={t("review.rate_group_label")}
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(72px, 1fr))",
            gap: 8,
            marginTop: 10,
          }}
        >
          {RATINGS.map(({ grade, key }) => (
            <button
              key={grade}
              type="button"
              className={grade === "again" ? "btn btn-secondary" : "btn"}
              style={{ minWidth: 0, paddingInline: 6 }}
              disabled={disabled}
              onClick={() =>
                onAnswer(grade === "again" ? "unknown" : "known", { selfGrade: grade })
              }
            >
              {t(key)}
            </button>
          ))}
        </div>
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
