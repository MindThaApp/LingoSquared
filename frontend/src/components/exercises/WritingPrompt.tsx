import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { VirtualKeyboard } from "../VirtualKeyboard";
import { answerScriptForExercise, scriptDirection, scriptNeedsVirtualKeyboard } from "@lingo/shared/lib/scripts";
import { useKeyboardFocus } from "../../lib/useKeyboardFocus";
import { AnswerModeSwitch } from "./AnswerModeSwitch";
import type { ExerciseComponentProps } from "./types";

export function WritingPrompt({ exercise, onAnswer, disabled, courseLevel, lessonExercises, answerHint }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const script = answerScriptForExercise(exercise);
  const { showKeyboard, inputProps, keyboardProps } = useKeyboardFocus<HTMLTextAreaElement>({ value, setValue, script, disabled });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (disabled || !value.trim()) return;
    onAnswer(value.trim());
  }

  // Enter stays a newline (multi-sentence answers); Cmd/Ctrl+Enter submits.
  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      if (disabled || !value.trim()) return;
      onAnswer(value.trim());
    }
  }

  return (
    <form className="exercise-shell" onSubmit={handleSubmit}>
      <TextBlockList blocks={exercise.prompt.text_blocks} />
      <AnswerModeSwitch
        exercise={exercise}
        courseLevel={courseLevel}
        lessonExercises={lessonExercises}
        answerHint={answerHint}
        disabled={disabled}
        onAnswer={onAnswer}
        renderTyping={(toggle) => (
          <>
          <div className="form-field">
            <textarea
              value={value}
              onChange={(e) => setValue(e.target.value)}
              disabled={disabled}
              rows={4}
              placeholder={t("exercise.writing_placeholder")}
              dir={scriptDirection(script)}
              onKeyDown={handleKeyDown}
              {...inputProps}
            />
            <small className="muted" style={{ display: "block", marginTop: 4 }}>
              {t("exercise.writing_submit_hint")}
            </small>
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
            {t("common.submit")}
          </button>
            {toggle}
          </>
        )}
      />
    </form>
  );
}
