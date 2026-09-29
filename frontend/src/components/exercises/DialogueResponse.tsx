import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { VirtualKeyboard } from "../VirtualKeyboard";
import { VoiceCaptureControls } from "../VoiceCaptureControls";
import { answerScriptForExercise, scriptDirection, scriptNeedsVirtualKeyboard } from "@lingo/shared/lib/scripts";
import { useKeyboardFocus } from "../../lib/useKeyboardFocus";
import { AnswerModeSwitch } from "./AnswerModeSwitch";
import type { ExerciseComponentProps } from "./types";

// Dialogue-context exercises compile to a free-text reply matched against
// an accepted-answers list, not preset options — same shape as Translation.
// speak_response (added 2026-07-06) additionally gets a mic/keyboard
// toggle — dialogue_response (its non-speaking sibling using this same
// component) stays typed-only, no toggle shown.
export function DialogueResponse({ exercise, onAnswer, disabled, courseLevel, lessonExercises, answerHint }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const script = answerScriptForExercise(exercise);
  const { showKeyboard, inputProps, keyboardProps } = useKeyboardFocus({ value, setValue, script, disabled });
  const canSpeak = exercise.type === "speak_response";
  const answerLanguageCode = exercise.prompt.answer_language_code ?? "en";

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (disabled || !value.trim()) return;
    onAnswer(value.trim());
  }

  return (
    <form className="exercise-shell" onSubmit={handleSubmit}>
      <div className="dialogue-bubble">
        <TextBlockList blocks={exercise.prompt.text_blocks} />
      </div>
      {canSpeak && (
        <VoiceCaptureControls
          languageCode={answerLanguageCode}
          onTranscript={setValue}
          disabled={disabled}
        />
      )}
      <AnswerModeSwitch
        exercise={exercise}
        courseLevel={courseLevel}
        lessonExercises={lessonExercises}
        answerHint={answerHint}
        enabled={exercise.type === "dialogue_response"}
        disabled={disabled}
        onAnswer={onAnswer}
        renderTyping={(toggle) => (
          <>
          <div className="form-field">
            <input
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              disabled={disabled}
              placeholder={t("exercise.type_your_reply")}
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
            {t("exercise.respond")}
          </button>
            {toggle}
          </>
        )}
      />
    </form>
  );
}
