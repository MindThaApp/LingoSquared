import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { VirtualKeyboard } from "../VirtualKeyboard";
import { answerScriptForExercise, scriptDirection, scriptNeedsVirtualKeyboard } from "../../lib/scripts";
import { useKeyboardFocus } from "../../lib/useKeyboardFocus";
import { correctOptionFromResponse, optionClassName } from "./optionHighlight";
import type { ExerciseComponentProps } from "./types";

// Some grammar_check exercises are authored as a closed yes/no (or other
// fixed-choice) question via `options` (e.g. "Does Dari run from right to
// left?") rather than an open-ended "correct this sentence" prompt — the
// compiled prompt has always carried `options` for these (confirmed
// against both a fresh compile and the live-imported DB), but this
// component never read it and always rendered a free-text input
// regardless, showing no visible choices for a yes/no question. Render as
// selectable options when present (same pattern as MultipleChoice), and
// keep the original free-text correction UI as the fallback for
// open-ended grammar_check exercises that have no `options`.
export function GrammarCheck({ exercise, onAnswer, disabled, gradedResult }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const script = answerScriptForExercise(exercise);
  const { showKeyboard, dismissKeyboard, inputProps } = useKeyboardFocus();
  const options = exercise.prompt.options;

  if (options && options.length > 0) {
    const correctOption = gradedResult
      ? correctOptionFromResponse(gradedResult.correctResponse, options)
      : null;
    // No fixed "Correct the grammar in this sentence" header here — that
    // copy is specific to the open-ended free-text mode below and is
    // misleading for a closed question (e.g. yes/no); the actual question
    // is already authored into the exercise's own text_blocks.
    return (
      <div className="exercise-shell">
        <TextBlockList blocks={exercise.prompt.text_blocks} />
        <div className="exercise-options">
          {options.map((option) => (
            <button
              key={option}
              type="button"
              className={optionClassName(option, selected, gradedResult, correctOption)}
              onClick={() => !disabled && setSelected(option)}
              disabled={disabled}
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

  return (
    <div className="exercise-shell">
      <p className="exercise-instruction">{t("exercise.grammar_check_instruction")}</p>
      <TextBlockList blocks={exercise.prompt.text_blocks} />
      <div className="form-field">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={disabled}
          placeholder={t("exercise.grammar_check_placeholder")}
          dir={scriptDirection(script)}
          {...inputProps}
        />
      </div>
      {showKeyboard && scriptNeedsVirtualKeyboard(script) && !disabled && (
        <VirtualKeyboard
          script={script!}
          onInsert={(char) => setValue((v) => v + char)}
          onBackspace={() => setValue((v) => v.slice(0, -1))}
          onDismiss={dismissKeyboard}
        />
      )}
      <button
        className="btn btn-block"
        disabled={disabled || !value.trim()}
        onClick={() => onAnswer(value.trim())}
      >
        {t("common.check")}
      </button>
    </div>
  );
}
