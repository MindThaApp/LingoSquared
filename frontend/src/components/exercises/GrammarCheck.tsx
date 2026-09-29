import { useMemo, useState } from "react";
import { seededShuffle } from "../../lib/shuffle";
import { useTranslation } from "react-i18next";
import { TextBlockList } from "../TextBlock";
import { VirtualKeyboard } from "../VirtualKeyboard";
import { answerDirectionForExercise, answerScriptForExercise, scriptDirection, scriptNeedsVirtualKeyboard } from "@lingo/shared/lib/scripts";
import { useKeyboardFocus } from "../../lib/useKeyboardFocus";
import { correctOptionFromResponse } from "./optionHighlight";
import { ChoiceOptions } from "./ChoiceOptions";
import type { ExerciseComponentProps } from "./types";

// Some grammar_check exercises are authored as a closed yes/no (or other
// fixed-choice) question via `options` (e.g. "Does Dari run from right to
// left?") rather than an open-ended "correct this sentence" prompt — the
// compiled prompt has always carried `options` for these (confirmed
// against both a fresh compile and the live-imported DB), but this
// component never read it and always rendered a free-text input
// regardless, showing no visible choices for a yes/no question. Render as
// selectable options when present (same pattern as MultipleChoice), and
// keep the original free-text correction UI as the fallback for
// open-ended grammar_check exercises that have no `options`.
export function GrammarCheck({ exercise, onAnswer, disabled, gradedResult }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const script = answerScriptForExercise(exercise);
  const { showKeyboard, inputProps, keyboardProps } = useKeyboardFocus({ value, setValue, script, disabled });
  const rawOptions = exercise.prompt.options;
  const nonce = useMemo(() => Math.random().toString(36), []);
  // Display order only; submitted payload stays the option text.
  const options = useMemo(
    () => (rawOptions ? seededShuffle(rawOptions, `${exercise.id}:${nonce}`) : rawOptions),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [exercise.id, nonce, rawOptions?.join("\u0001")],
  );

  if (options && options.length > 0) {
    const optionsDirection = answerDirectionForExercise(exercise);
    const correctOption = gradedResult
      ? correctOptionFromResponse(gradedResult.correctResponse, options)
      : null;
    // No fixed "Correct the grammar in this sentence" header here — that
    // copy is specific to the open-ended free-text mode below and is
    // misleading for a closed question (e.g. yes/no); the actual question
    // is already authored into the exercise's own text_blocks.
    return (
      <div className="exercise-shell">
        <TextBlockList blocks={exercise.prompt.text_blocks} />
        <ChoiceOptions
          options={options}
          selected={selected}
          onSelect={setSelected}
          disabled={disabled}
          gradedResult={gradedResult}
          correctOption={correctOption}
          direction={optionsDirection}
          lang={exercise.prompt.answer_language_code}
        />
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

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (disabled || !value.trim()) return;
    onAnswer(value.trim());
  }

  return (
    <form className="exercise-shell" onSubmit={handleSubmit}>
      <p className="exercise-instruction">{t("exercise.grammar_check_instruction")}</p>
      <TextBlockList blocks={exercise.prompt.text_blocks} />
      <div className="form-field">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={disabled}
          placeholder={t("exercise.grammar_check_placeholder")}
          aria-label={t("exercise.grammar_check_placeholder")}
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
