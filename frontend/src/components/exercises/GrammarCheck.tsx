import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { VirtualKeyboard } from "../VirtualKeyboard";
import { answerScriptForExercise, scriptNeedsVirtualKeyboard } from "../../lib/scripts";
import { useKeyboardFocus } from "../../lib/useKeyboardFocus";
import type { ExerciseComponentProps } from "./types";

export function GrammarCheck({ exercise, onAnswer, disabled }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const script = answerScriptForExercise(exercise);
  const { showKeyboard, dismissKeyboard, inputProps } = useKeyboardFocus();

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
          dir={script === "arabic" ? "rtl" : undefined}
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
