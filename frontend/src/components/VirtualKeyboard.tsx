import { useTranslation } from "react-i18next";
import type { ScriptCode } from "@lingo/shared/api/types";
import { KEYBOARD_LAYOUTS } from "@lingo/shared/lib/scripts";

// Every key uses onMouseDown+preventDefault (not onClick alone) so clicking
// a key never blurs the associated text input — this is what lets the
// keyboard's "shows while the input is focused" behavior work without the
// input closing itself the moment a key is pressed.
export function VirtualKeyboard({
  script,
  onInsert,
  onBackspace,
  onDismiss,
}: {
  script: ScriptCode;
  onInsert: (char: string) => void;
  onBackspace: () => void;
  onDismiss: () => void;
}) {
  const { t } = useTranslation();
  const layout = KEYBOARD_LAYOUTS[script];
  if (!layout) return null;

  function keyMouseDown(e: React.MouseEvent, action: () => void) {
    e.preventDefault();
    action();
  }

  return (
    <div className="virtual-keyboard" dir={layout.direction}>
      <div className="virtual-keyboard-row" style={{ justifyContent: "flex-end" }}>
        <button
          type="button"
          className="virtual-keyboard-key virtual-keyboard-key-wide"
          onMouseDown={(e) => keyMouseDown(e, onDismiss)}
        >
          {t("keyboard.use_device_keyboard")}
        </button>
      </div>
      {/* All letters render in ONE wrapping row, not one div per
          layout.rows chunk: those chunks are a mechanical ROW_SIZE=11 split
          of a flat alphabet (see chunk() in @lingo/shared/lib/scripts), not
          semantic groupings, and an 11-key line has never fit a phone-width
          viewport anyway — with per-chunk divs each chunk wrapped into its
          own ragged pair of lines (e.g. 7+4, 7+4, 7+3 at 375px). A single
          wrapping container lets flexbox pack every line evenly (7/7/7/7/4)
          at whatever width is actually available, which matters more now
          that keys are touch-target sized (42x48, see index.css). Alphabet
          order is preserved; dir={layout.direction} on the root makes the
          wrap direction follow the script. */}
      <div className="virtual-keyboard-row">
        {layout.rows.flat().map((char) => (
          <button
            key={char}
            type="button"
            className="virtual-keyboard-key"
            onMouseDown={(e) => keyMouseDown(e, () => onInsert(char))}
          >
            {char}
          </button>
        ))}
      </div>
      <div className="virtual-keyboard-row">
        {layout.hasZwnj && (
          <button
            type="button"
            className="virtual-keyboard-key virtual-keyboard-key-wide"
            onMouseDown={(e) => keyMouseDown(e, () => onInsert("‌"))}
            title={t("keyboard.zwnj_title")}
          >
            ZWNJ
          </button>
        )}
        <button
          type="button"
          className="virtual-keyboard-key virtual-keyboard-key-wide"
          onMouseDown={(e) => keyMouseDown(e, () => onInsert(" "))}
        >
          {t("keyboard.space")}
        </button>
        <button
          type="button"
          className="virtual-keyboard-key virtual-keyboard-key-wide"
          onMouseDown={(e) => keyMouseDown(e, onBackspace)}
        >
          ⌫
        </button>
      </div>
    </div>
  );
}
