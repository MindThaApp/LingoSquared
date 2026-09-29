import { useMemo, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { answerDirectionForExercise } from "@lingo/shared/lib/scripts";
import type { AnswerResponse, CefrLevel, Exercise } from "@lingo/shared/api/types";
import { useAuth } from "../../auth/AuthContext";
import { useTargetLanguage } from "../targetLanguageContext";
import { buildWordBank } from "../../lib/wordBankTiles";
import {
  defaultAnswerMode,
  getWordBankPreference,
  setWordBankPreference,
  type AnswerMode,
} from "../../lib/wordBankPreference";
import { WordBankInput } from "./WordBankInput";

interface AnswerModeSwitchProps {
  exercise: Exercise;
  courseLevel?: CefrLevel | null;
  lessonExercises?: Exercise[];
  answerHint?: string;
  // Off for exercise types that must stay typed-only.
  enabled?: boolean;
  disabled: boolean;
  onAnswer: (response: AnswerResponse) => void;
  // The component's existing, unchanged typed input (+ submit button).
  // `toggle` is the "Use word bank" button (or null when no bank exists).
  renderTyping: (toggle: ReactNode) => ReactNode;
}

// With no courseLevel (review/practice/checkpoint, or level still loading) or
// enabled=false this renders the typed input only and never touches auth, so
// every existing caller keeps its exact behavior.
export function AnswerModeSwitch(props: AnswerModeSwitchProps) {
  if (props.enabled === false) return <>{props.renderTyping(null)}</>;
  if (!props.courseLevel) return <>{props.renderTyping(null)}</>;
  return <BankAwareInput {...props} courseLevel={props.courseLevel} />;
}

function BankAwareInput({
  exercise,
  courseLevel,
  lessonExercises,
  answerHint,
  disabled,
  onAnswer,
  renderTyping,
}: AnswerModeSwitchProps & { courseLevel: CefrLevel }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const targetLanguage = useTargetLanguage();
  const [override, setOverride] = useState<AnswerMode | null>(() => getWordBankPreference(userId));
  const mode: AnswerMode = override ?? defaultAnswerMode(courseLevel);

  const bank = useMemo(
    () => buildWordBank({ exercise, lessonExercises, answerHint, targetLanguage }),
    [exercise, lessonExercises, answerHint, targetLanguage],
  );
  const bankAvailable = bank.tiles.length >= 2;

  function choose(next: AnswerMode) {
    setOverride(next);
    setWordBankPreference(userId, next);
  }

  if (!bankAvailable) return <>{renderTyping(null)}</>;

  if (mode === "type") {
    return (
      <>
        {renderTyping(
          <button type="button" className="btn btn-secondary btn-block" onClick={() => choose("bank")}>
            {t("exercise.use_word_bank")}
          </button>,
        )}
      </>
    );
  }

  return (
    <>
      <WordBankInput
        tiles={bank.tiles}
        direction={answerDirectionForExercise(exercise)}
        disabled={disabled}
        onSubmit={onAnswer}
      />
      <button type="button" className="btn btn-secondary btn-block" onClick={() => choose("type")}>
        {t("exercise.type_instead")}
      </button>
    </>
  );
}
