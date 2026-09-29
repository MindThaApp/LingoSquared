import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { VirtualKeyboard } from "../VirtualKeyboard";
import { answerScriptForExercise, scriptDirection, scriptNeedsVirtualKeyboard } from "@lingo/shared/lib/scripts";
import { useKeyboardFocus } from "../../lib/useKeyboardFocus";
import type { ExerciseComponentProps } from "./types";

export function FillInBlank({ exercise, onAnswer, disabled }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const script = answerScriptForExercise(exercise);
  const { showKeyboard, inputProps, keyboardProps } = useKeyboardFocus({ value, setValue, script, disabled });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (disabled || !value.trim()) return;
    onAnswer(value.trim());
  }

  return (
    <form className="exercise-shell" onSubmit={handleSubmit}>
      <TextBlockList blocks={exercise.prompt.text_blocks} />
      <div className="form-field">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={disabled}
          placeholder={t("exercise.fill_in_blank_placeholder")}
          dir={scriptDirection(script)}
          {...inputProps}
        />
      </div>
      {showKeyboard && scriptNeedsVirtualKeyboard(script) && !disabled && (
        <VirtualKeyboard
          script={script!}
          {...keyboardProps}
        />
      )}
      <button
        type="submit"
        className="btn btn-block"
        disabled={disabled || !value.trim()}
        onMouseDown={(e) => e.preventDefault()}
      >
        {t("common.check")}
      </button>
    </form>
  );
}
