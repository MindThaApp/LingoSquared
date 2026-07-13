import { useTranslation } from "react-i18next";
import type { SpokenWord } from "../api/stt";

// Below this confidence the recognizer was unsure what word it heard, which
// in practice means the word came out unclear. It is a CLARITY signal, not an
// accent score — never label it as "wrong pronunciation", only as unclear.
const UNCLEAR_BELOW = 0.55;

export function unclearWords(words: SpokenWord[]): SpokenWord[] {
  return words.filter((w) => w.probability < UNCLEAR_BELOW);
}

export function PronunciationFeedback({ words }: { words: SpokenWord[] | null }) {
  const { t } = useTranslation();
  if (!words || words.length === 0) return null;

  const unclear = unclearWords(words);

  return (
    <div className="pronunciation-feedback" aria-live="polite">
      <p className="muted" style={{ fontSize: "0.85rem", marginBottom: "0.25rem" }}>
        {unclear.length === 0
          ? t("exercise.pronunciation_all_clear")
          : t("exercise.pronunciation_unclear_hint")}
      </p>
      <p style={{ lineHeight: 1.9 }}>
        {words.map((w, i) => {
          const isUnclear = w.probability < UNCLEAR_BELOW;
          return (
            <span
              key={`${w.start}-${i}`}
              className={isUnclear ? "pron-word pron-word-unclear" : "pron-word"}
              title={
                isUnclear
                  ? t("exercise.pronunciation_word_unclear")
                  : t("exercise.pronunciation_word_clear")
              }
            >
              {w.word.trim()}
            </span>
          );
        })}
      </p>
    </div>
  );
}
