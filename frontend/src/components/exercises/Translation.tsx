import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { VirtualKeyboard } from "../VirtualKeyboard";
import { SpeakButton } from "../SpeakButton";
import { isListeningExercise } from "../../lib/listeningTypes";
import { answerScriptForExercise, scriptDirection, scriptNeedsVirtualKeyboard } from "@lingo/shared/lib/scripts";
import { useKeyboardFocus } from "../../lib/useKeyboardFocus";
import { AnswerModeSwitch } from "./AnswerModeSwitch";
import { VoiceAnswerButton } from "../VoiceAnswerButton";
import { submitAnswer } from "../../lib/voiceAnswer";
import type { ExerciseComponentProps } from "./types";

// Shared by "translation", "reverse_translation", and "listen_type" — same
// UI; listen_type additionally carries audio_text/audio_language_code for
// a hidden target-language phrase the learner must hear before typing.
export function Translation({ exercise, onAnswer, disabled, courseLevel, lessonExercises, answerHint }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [spoken, setSpoken] = useState(false);
  const script = answerScriptForExercise(exercise);
  const { audio_text, audio_language_code, media_asset_key } = exercise.prompt;
  const { showKeyboard, inputProps, keyboardProps } = useKeyboardFocus({ value, setValue, script, disabled });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (disabled || !value.trim()) return;
    submitAnswer(onAnswer, value.trim(), spoken);
  }

  return (
    <form className="exercise-shell" onSubmit={handleSubmit}>
      <TextBlockList blocks={exercise.prompt.text_blocks} />
      {audio_text && audio_language_code && (
        <div className="exercise-audio-prompt">
          <SpeakButton text={audio_text} languageCode={audio_language_code} mediaAssetKey={media_asset_key} autoPlay={isListeningExercise(exercise.type)} />
          <span className="muted">{t("exercise.tap_to_listen")}</span>
        </div>
      )}
      <AnswerModeSwitch
        exercise={exercise}
        courseLevel={courseLevel}
        lessonExercises={lessonExercises}
        answerHint={answerHint}
        enabled={exercise.type === "translation"}
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
              placeholder={t("exercise.translation_placeholder")}
              aria-label={t("exercise.translation_placeholder")}
              lang={exercise.prompt.answer_language_code}
              dir={scriptDirection(script)}
              {...inputProps}
            />
          </div>
          {/* Listening types (listen_type/dictation) stay typed-only: speaking what you just heard isn't the exercise. */}
          {(exercise.type === "translation" || exercise.type === "reverse_translation") && (
            <VoiceAnswerButton exercise={exercise} disabled={disabled} onTranscript={(text) => { setValue(text); setSpoken(true); }} />
          )}
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
            {toggle}
          </>
        )}
      />
    </form>
  );
}
