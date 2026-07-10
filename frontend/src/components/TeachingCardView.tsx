import { useTranslation } from "react-i18next";
import type { TeachingCard } from "@lingo/shared/api/types";
import { TextBlockList } from "./TextBlock";
import { EmphasizedText } from "./EmphasizedText";

const KIND_KEY: Record<TeachingCard["kind"], string> = {
  vocabulary: "teaching_card.vocabulary",
  phrase: "teaching_card.phrase",
  grammar_note: "teaching_card.grammar_note",
  dialogue: "teaching_card.dialogue",
  pronunciation_note: "teaching_card.pronunciation_note",
  cultural_note: "teaching_card.cultural_note",
  reading: "teaching_card.reading",
};

// For "vocabulary" and "phrase" cards, the overlay's `title` is always a
// bare restatement of the gloss text block that follows it (e.g. title
// "Two" immediately above a text block reading "2 — two") -- pure visual
// duplication of the same English word/phrase, confirmed across every
// unit's overlay content, not just one language. "dialogue"/"reading"/
// "grammar_note"/etc. titles are genuinely different short summaries of
// their (often much longer) gloss text, so they still render normally.
const KINDS_WITH_REDUNDANT_TITLE: ReadonlySet<TeachingCard["kind"]> = new Set([
  "vocabulary",
  "phrase",
]);

export function TeachingCardView({ card }: { card: TeachingCard }) {
  const { t } = useTranslation();
  const showTitle = card.title && !KINDS_WITH_REDUNDANT_TITLE.has(card.kind);
  const examples = card.examples ?? [];
  return (
    <div className="card" style={{ margin: "16px 0" }}>
      <span className="badge">{t(KIND_KEY[card.kind])}</span>
      {showTitle && <h3 style={{ margin: "10px 0 8px" }}>{card.title}</h3>}
      <TextBlockList blocks={card.text_blocks} />
      {examples.length > 0 && (
        <div className="teaching-examples">
          <span className="teaching-examples-label">
            {t("teaching_card.example")}
          </span>
          {examples.map((example, i) => (
            <TextBlockList blocks={example.text_blocks} key={i} />
          ))}
        </div>
      )}
      {card.note && (
        <p className="muted" style={{ margin: 0 }}>
          <EmphasizedText text={card.note} />
        </p>
      )}
    </div>
  );
}
