import type { CSSProperties } from "react";
import type { ExercisePrompt } from "@lingo/shared/api/types";
import { sourceTextDirection } from "@lingo/shared/lib/scripts";
import { EmphasizedText } from "./EmphasizedText";

// An answer's `feedback` text is written in the learner's source language (the
// gloss language of the prompt), so it carries an explicit `dir` derived from the
// prompt's text blocks, exactly like the other feedback surfaces (AnswerFeedbackExtras,
// TeachingCardView). With no prompt it falls back to "auto".
export function FeedbackParagraph({
  text,
  prompt,
  style,
}: {
  text: string;
  prompt?: Pick<ExercisePrompt, "text_blocks" | "answer_language_code"> | null;
  style?: CSSProperties;
}) {
  return (
    <p dir={sourceTextDirection(prompt?.text_blocks, prompt?.answer_language_code)} style={{ fontWeight: 400, ...style }}>
      <EmphasizedText text={text} />
    </p>
  );
}
