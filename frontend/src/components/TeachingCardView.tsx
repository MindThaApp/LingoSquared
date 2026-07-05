import { useTranslation } from "react-i18next";
import type { TeachingCard } from "../api/types";
import { TextBlockList } from "./TextBlock";

const KIND_KEY: Record<TeachingCard["kind"], string> = {
  vocabulary: "teaching_card.vocabulary",
  phrase: "teaching_card.phrase",
  grammar_note: "teaching_card.grammar_note",
  dialogue: "teaching_card.dialogue",
  pronunciation_note: "teaching_card.pronunciation_note",
  cultural_note: "teaching_card.cultural_note",
  reading: "teaching_card.reading",
};

export function TeachingCardView({ card }: { card: TeachingCard }) {
  const { t } = useTranslation();
  return (
    <div className="card" style={{ margin: "16px 0" }}>
      <span className="badge">{t(KIND_KEY[card.kind])}</span>
      {card.title && <h3 style={{ margin: "10px 0 8px" }}>{card.title}</h3>}
      <TextBlockList blocks={card.text_blocks} />
      {card.note && <p className="muted" style={{ margin: 0 }}>{card.note}</p>}
    </div>
  );
}
