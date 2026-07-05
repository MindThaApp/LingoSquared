import { useState } from "react";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { SpeakButton } from "../SpeakButton";
import type { ExerciseComponentProps } from "./types";

export function MultipleChoice({ exercise, onAnswer, disabled }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<string | null>(null);
  const options = exercise.prompt.options ?? [];
  const { audio_text, audio_language_code, media_asset_key } = exercise.prompt;

  return (
    <div className="exercise-shell">
      <TextBlockList blocks={exercise.prompt.text_blocks} />
      {audio_text && audio_language_code && (
        <div className="exercise-audio-prompt">
          <SpeakButton text={audio_text} languageCode={audio_language_code} mediaAssetKey={media_asset_key} />
          <span className="muted">{t("exercise.tap_to_listen")}</span>
        </div>
      )}
      <div className="exercise-options">
        {options.map((option) => (
          <button
            key={option}
            type="button"
            className={`exercise-option${selected === option ? " selected" : ""}`}
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
