import { useState } from "react";
import { useTranslation } from "react-i18next";

interface WordBankInputProps {
  tiles: string[];
  // Explicit on BOTH containers: a click-built token sequence inherits
  // direction from nowhere (fa/prs would otherwise assemble LTR).
  direction: "ltr" | "rtl" | undefined;
  disabled: boolean;
  onSubmit: (answer: string) => void;
}

// Tap-to-build answer input. Tile identity is the INDEX into `tiles`
// (duplicate texts are legal). `placed` holds bank indexes in tap order; a
// used bank slot keeps an invisible placeholder so nothing shifts, and a
// removed tile reappears in its original slot. Submits the same trimmed,
// space-joined string the typed input would.
export function WordBankInput({ tiles, direction, disabled, onSubmit }: WordBankInputProps) {
  const { t } = useTranslation();
  const [placed, setPlaced] = useState<number[]>([]);

  function place(bankIndex: number) {
    if (disabled) return;
    setPlaced((prev) => (prev.includes(bankIndex) ? prev : [...prev, bankIndex]));
  }

  function unplace(position: number) {
    if (disabled) return;
    setPlaced((prev) => prev.filter((_, i) => i !== position));
  }

  function submit() {
    if (disabled || placed.length === 0) return;
    onSubmit(placed.map((i) => tiles[i]).join(" ").trim());
  }

  return (
    <div>
      <div className="word-answer-row" dir={direction} data-testid="word-bank-answer">
        {placed.map((bankIndex, position) => (
          <button
            key={bankIndex}
            type="button"
            className="word-chip"
            onClick={() => unplace(position)}
            disabled={disabled}
          >
            {tiles[bankIndex]}
          </button>
        ))}
      </div>
      <div className="word-bank" dir={direction} data-testid="word-bank-tiles">
        {tiles.map((tile, bankIndex) => {
          const used = placed.includes(bankIndex);
          return used ? (
            <button
              key={bankIndex}
              type="button"
              className="word-chip used"
              style={{ visibility: "hidden" }}
              aria-hidden="true"
              tabIndex={-1}
              disabled
              data-testid={`word-bank-slot-${bankIndex}`}
            >
              {tile}
            </button>
          ) : (
            <button
              key={bankIndex}
              type="button"
              className="word-chip"
              onClick={() => place(bankIndex)}
              disabled={disabled}
              data-testid={`word-bank-slot-${bankIndex}`}
            >
              {tile}
            </button>
          );
        })}
      </div>
      <button
        type="button"
        className="btn btn-block"
        disabled={disabled || placed.length === 0}
        onClick={submit}
      >
        {t("common.check")}
      </button>
    </div>
  );
}
