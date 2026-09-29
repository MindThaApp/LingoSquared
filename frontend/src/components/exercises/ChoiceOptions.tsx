import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { optionClassName, optionGradeState } from "./optionHighlight";
import type { GradedResult } from "./types";

interface ChoiceOptionsProps {
  options: string[];
  selected: string | null;
  onSelect: (option: string) => void;
  disabled: boolean;
  gradedResult?: GradedResult;
  correctOption: string | null;
  direction?: "ltr" | "rtl";
}

/**
 * Shared option group for MultipleChoice / GrammarCheck (options branch) /
 * ReadingComprehension: radiogroup semantics, first-option autofocus on
 * mount, and a non-colour-only correct/incorrect marker after grading.
 * Options are keyed by INDEX; the submitted payload stays the option text.
 */
export function ChoiceOptions({
  options,
  selected,
  onSelect,
  disabled,
  gradedResult,
  correctOption,
  direction,
}: ChoiceOptionsProps) {
  const { t } = useTranslation();
  const firstRef = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    if (!disabled) firstRef.current?.focus({ preventScroll: true });
    // Focus once on mount only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="exercise-options" dir={direction} role="radiogroup" aria-label={t("exercise.options_label")}>
      {options.map((option, i) => {
        const state = optionGradeState(option, selected, gradedResult, correctOption);
        return (
          <button
            key={i}
            ref={i === 0 ? firstRef : undefined}
            type="button"
            role="radio"
            aria-checked={selected === option}
            className={optionClassName(option, selected, gradedResult, correctOption)}
            onClick={() => !disabled && onSelect(option)}
            disabled={disabled}
          >
            {option}
            {state && (
              <>
                {" "}
                <span aria-hidden="true" className="exercise-option-icon">
                  {state === "correct" ? "✓" : "✗"}
                </span>
                <span className="visually-hidden">
                  {state === "correct" ? t("exercise.option_correct") : t("exercise.option_incorrect")}
                </span>
              </>
            )}
          </button>
        );
      })}
    </div>
  );
}
