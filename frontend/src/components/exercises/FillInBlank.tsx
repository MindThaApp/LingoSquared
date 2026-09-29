import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { VirtualKeyboard } from "../VirtualKeyboard";
import { answerScriptForExercise, scriptDirection, scriptNeedsVirtualKeyboard } from "@lingo/shared/lib/scripts";
import { useKeyboardFocus } from "../../lib/useKeyboardFocus";
import { VoiceAnswerButton } from "../VoiceAnswerButton";
import { submitAnswer } from "../../lib/voiceAnswer";
import type { ExerciseComponentProps } from "./types";

export function FillInBlank({ exercise, onAnswer, disabled }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [spoken, setSpoken] = useState(false);
  const script = answerScriptForExercise(exercise);
  const { showKeyboard, inputProps, keyboardProps } = useKeyboardFocus({ value, setValue, script, disabled });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (disabled || !value.trim()) return;
    submitAnswer(onAnswer, value.trim(), spoken);
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
          aria-label={t("exercise.fill_in_blank_placeholder")}
          lang={exercise.prompt.answer_language_code}
          dir={scriptDirection(script)}
          {...inputProps}
        />
      </div>
      <VoiceAnswerButton exercise={exercise} disabled={disabled} onTranscript={(text) => { setValue(text); setSpoken(true); }} />
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
