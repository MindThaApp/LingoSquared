import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { VirtualKeyboard } from "../VirtualKeyboard";
import { VoiceCaptureControls } from "../VoiceCaptureControls";
import { answerScriptForExercise, scriptDirection, scriptNeedsVirtualKeyboard } from "@lingo/shared/lib/scripts";
import { useKeyboardFocus } from "../../lib/useKeyboardFocus";
import { submitAnswer } from "../../lib/voiceAnswer";
import type { ExerciseComponentProps } from "./types";

// speak_repeat: the target phrase is already shown in the prompt — the
// exercise is repeating it aloud, graded against the same accepted_answers
// every other free-text exercise uses (confirmed against real compiled
// content, e.g. fr.a1.unit01.lesson03.exercise07_read_liaison tests "Vous
// êtes. Un atelier."). Typing is the honest fallback when mic input isn't
// available — it does mean literally copying the visible text, which is
// pedagogically weak, but that's the accepted degrade, same as any other
// silent/out-loud toggle here.
export function SpeakRepeat({ exercise, onAnswer, disabled }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [spoken, setSpoken] = useState(false);
  const script = answerScriptForExercise(exercise);
  const { showKeyboard, inputProps, keyboardProps } = useKeyboardFocus({ value, setValue, script, disabled });
  const answerLanguageCode = exercise.prompt.answer_language_code ?? "en";

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (disabled || !value.trim()) return;
    submitAnswer(onAnswer, value.trim(), spoken);
  }

  return (
    <form className="exercise-shell" onSubmit={handleSubmit}>
      <TextBlockList blocks={exercise.prompt.text_blocks} />
      <p className="muted" style={{ fontSize: "0.9rem" }}>
        {t("exercise.speak_repeat_instruction")}
      </p>
      <VoiceCaptureControls languageCode={answerLanguageCode} onTranscript={(text) => { setValue(text); setSpoken(true); }} disabled={disabled} />
      <div className="form-field">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={disabled}
          placeholder={t("exercise.speak_repeat_type_placeholder")}
          aria-label={t("exercise.speak_repeat_type_placeholder")}
          lang={exercise.prompt.answer_language_code}
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
