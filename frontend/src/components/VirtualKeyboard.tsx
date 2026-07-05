import { useTranslation } from "react-i18next";
import type { ScriptCode } from "../api/types";
import { KEYBOARD_LAYOUTS } from "../lib/scripts";

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
      {layout.rows.map((row, i) => (
        <div className="virtual-keyboard-row" key={i}>
          {row.map((char) => (
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
      ))}
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
