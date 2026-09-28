import { useMemo, useState } from "react";
import { seededShuffleNotOriginal } from "../../lib/shuffle";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { SpeakButton } from "../SpeakButton";
import { answerDirectionForExercise } from "@lingo/shared/lib/scripts";
import type { ExerciseComponentProps } from "./types";

// Shared by "word_order" and "listen_order" — listen_order additionally
// carries audio_text/audio_language_code for a hidden target-language
// phrase the learner must hear before ordering the word bank.
export function WordOrder({ exercise, onAnswer, disabled }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const wordBank = exercise.prompt.word_bank ?? [];
  // Display order only: tiles are usually authored in answer order, so shuffle
  // once per mount (never leaving the initial order equal to the authored
  // one). The submitted payload is the tapped token sequence.
  const nonce = useMemo(() => Math.random().toString(36), []);
  const [available, setAvailable] = useState<string[]>(() =>
    seededShuffleNotOriginal(wordBank, `${exercise.id}:${nonce}`),
  );
  const [chosen, setChosen] = useState<string[]>([]);
  const { audio_text, audio_language_code, media_asset_key } = exercise.prompt;
  // word_bank tokens carry no direction of their own (unlike text_blocks) --
  // without this, an RTL answer (Farsi/Dari) still visually assembles
  // left-to-right regardless of the order tiles were tapped in.
  const direction = answerDirectionForExercise(exercise);

  function pick(word: string, index: number) {
    if (disabled) return;
    setAvailable((prev) => prev.filter((_, i) => i !== index));
    setChosen((prev) => [...prev, word]);
  }

  function unpick(index: number) {
    if (disabled) return;
    const word = chosen[index];
    setChosen((prev) => prev.filter((_, i) => i !== index));
    setAvailable((prev) => [...prev, word]);
  }

  return (
    <div className="exercise-shell">
      <TextBlockList blocks={exercise.prompt.text_blocks} />
      {audio_text && audio_language_code && (
        <div className="exercise-audio-prompt">
          <SpeakButton text={audio_text} languageCode={audio_language_code} mediaAssetKey={media_asset_key} />
          <span className="muted">{t("exercise.tap_to_listen")}</span>
        </div>
      )}
      <div className="word-answer-row" dir={direction}>
        {chosen.map((word, i) => (
          <button key={i} className="word-chip" onClick={() => unpick(i)} disabled={disabled}>
            {word}
          </button>
        ))}
      </div>
      <div className="word-bank" dir={direction}>
        {available.map((word, i) => (
          <button key={i} className="word-chip" onClick={() => pick(word, i)} disabled={disabled}>
            {word}
          </button>
        ))}
      </div>
      <button
        className="btn btn-block"
        disabled={disabled || chosen.length === 0}
        onClick={() => onAnswer(chosen)}
      >
        {t("common.check")}
      </button>
    </div>
  );
}
