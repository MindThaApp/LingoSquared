import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { VirtualKeyboard } from "../VirtualKeyboard";
import { VoiceCaptureControls } from "../VoiceCaptureControls";
import { answerScriptForExercise, scriptNeedsVirtualKeyboard } from "../../lib/scripts";
import { useKeyboardFocus } from "../../lib/useKeyboardFocus";
import type { ExerciseComponentProps } from "./types";

// Dialogue-context exercises compile to a free-text reply matched against
// an accepted-answers list, not preset options — same shape as Translation.
// speak_response (added 2026-07-06) additionally gets a mic/keyboard
// toggle — dialogue_response (its non-speaking sibling using this same
// component) stays typed-only, no toggle shown.
export function DialogueResponse({ exercise, onAnswer, disabled }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const script = answerScriptForExercise(exercise);
  const { showKeyboard, dismissKeyboard, inputProps } = useKeyboardFocus();
  const canSpeak = exercise.type === "speak_response";
  const answerLanguageCode = exercise.prompt.answer_language_code ?? "en";

  return (
    <div className="exercise-shell">
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
      <div className="form-field">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={disabled}
          placeholder={t("exercise.type_your_reply")}
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
        {t("exercise.respond")}
      </button>
    </div>
  );
}
