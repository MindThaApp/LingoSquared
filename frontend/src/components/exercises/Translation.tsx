import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { VirtualKeyboard } from "../VirtualKeyboard";
import { SpeakButton } from "../SpeakButton";
import { answerScriptForExercise, scriptDirection, scriptNeedsVirtualKeyboard } from "@lingo/shared/lib/scripts";
import { useKeyboardFocus } from "../../lib/useKeyboardFocus";
import type { ExerciseComponentProps } from "./types";

// Shared by "translation", "reverse_translation", and "listen_type" — same
// UI; listen_type additionally carries audio_text/audio_language_code for
// a hidden target-language phrase the learner must hear before typing.
export function Translation({ exercise, onAnswer, disabled }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const script = answerScriptForExercise(exercise);
  const { audio_text, audio_language_code, media_asset_key } = exercise.prompt;
  const { showKeyboard, dismissKeyboard, inputProps } = useKeyboardFocus();

  return (
    <div className="exercise-shell">
      <TextBlockList blocks={exercise.prompt.text_blocks} />
      {audio_text && audio_language_code && (
        <div className="exercise-audio-prompt">
          <SpeakButton text={audio_text} languageCode={audio_language_code} mediaAssetKey={media_asset_key} />
          <span className="muted">{t("exercise.tap_to_listen")}</span>
        </div>
      )}
      <div className="form-field">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={disabled}
          placeholder={t("exercise.translation_placeholder")}
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
