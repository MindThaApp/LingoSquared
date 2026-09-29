import { useMemo, useState } from "react";
import { seededShuffle } from "../../lib/shuffle";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { SpeakButton } from "../SpeakButton";
import { correctOptionFromResponse, optionClassName } from "./optionHighlight";
import { answerDirectionForExercise } from "@lingo/shared/lib/scripts";
import type { ExerciseComponentProps } from "./types";

export function MultipleChoice({ exercise, onAnswer, disabled, gradedResult }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<string | null>(null);
  const rawOptions = exercise.prompt.options ?? [];
  // Display order only: authored content puts the correct option first.
  // The submitted payload is still the option TEXT.
  const nonce = useMemo(() => Math.random().toString(36), []);
  const options = useMemo(
    () => seededShuffle(rawOptions, `${exercise.id}:${nonce}`),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [exercise.id, nonce, rawOptions.join("\u0001")],
  );
  // Options are raw strings with no direction of their own (unlike
  // text_blocks) -- pure-RTL options happen to render acceptably via
  // first-strong bidi detection, but an option ending in neutral punctuation
  // ("سلام!") or mixing scripts gets that punctuation on the wrong visual
  // side without an explicit base direction. Same footgun class as
  // WordOrder.tsx's word_bank fix (2026-07-09); answer_language_code is the
  // language the options/answer are in, so its script direction is the
  // right base direction for every option.
  const direction = answerDirectionForExercise(exercise);
  const { audio_text, audio_language_code, media_asset_key } = exercise.prompt;
  const correctOption = gradedResult
    ? correctOptionFromResponse(gradedResult.correctResponse, options)
    : null;

  return (
    <div className="exercise-shell">
      <TextBlockList blocks={exercise.prompt.text_blocks} />
      {audio_text && audio_language_code && (
        <div className="exercise-audio-prompt">
          <SpeakButton text={audio_text} languageCode={audio_language_code} mediaAssetKey={media_asset_key} />
          <span className="muted">{t("exercise.tap_to_listen")}</span>
        </div>
      )}
      <div className="exercise-options" dir={direction} lang={exercise.prompt.answer_language_code}>
        {options.map((option) => (
          <button
            key={option}
            type="button"
            className={optionClassName(option, selected, gradedResult, correctOption)}
            onClick={() => !disabled && setSelected(option)}
            disabled={disabled}
            aria-pressed={selected === option}
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
