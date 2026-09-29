import { useTranslation } from "react-i18next";
import { TargetLanguageContext, useTargetLanguage } from "../targetLanguageContext";
import type { ExerciseComponentProps } from "./types";
import { MultipleChoice } from "./MultipleChoice";
import { Translation } from "./Translation";
import { FillInBlank } from "./FillInBlank";
import { WordOrder } from "./WordOrder";
import { MatchingPairs } from "./MatchingPairs";
import { Placeholder } from "./Placeholder";
import { DialogueResponse } from "./DialogueResponse";
import { SpeakRepeat } from "./SpeakRepeat";
import { GrammarCheck } from "./GrammarCheck";
import { Flashcard } from "./Flashcard";
import { ReadingComprehension } from "./ReadingComprehension";
import { WritingPrompt } from "./WritingPrompt";

export function ExerciseRenderer(props: ExerciseComponentProps) {
  const outer = useTargetLanguage();
  const own = props.exercise.prompt.answer_language_code;
  return (
    <TargetLanguageContext.Provider value={outer ?? (typeof own === "string" && own ? own : null)}>
      <ExerciseSwitch {...props} />
    </TargetLanguageContext.Provider>
  );
}

function ExerciseSwitch(props: ExerciseComponentProps) {
  const { t } = useTranslation();
  switch (props.exercise.type) {
    case "multiple_choice":
    case "listen_select":
    case "dialogue_comprehension":
      return <MultipleChoice {...props} />;
    case "translation":
    case "reverse_translation":
    case "listen_type":
    case "dictation":
      return <Translation {...props} />;
    case "fill_in_blank":
      return <FillInBlank {...props} />;
    case "word_order":
    case "listen_order":
      return <WordOrder {...props} />;
    case "matching_pairs":
      return <MatchingPairs {...props} />;
    case "listening_placeholder":
    case "speaking_placeholder":
      return <Placeholder {...props} />;
    case "speak_repeat":
      return <SpeakRepeat {...props} />;
    case "dialogue_response":
    case "speak_response":
      return <DialogueResponse {...props} />;
    case "grammar_check":
      return <GrammarCheck {...props} />;
    case "flashcard":
      return <Flashcard {...props} />;
    case "reading_comprehension":
      return <ReadingComprehension {...props} />;
    case "writing_prompt":
      return <WritingPrompt {...props} />;
    default:
      return <p>{t("exercise.unsupported_type", { type: props.exercise.type })}</p>;
  }
}
