import { useState } from "react";

// Tracks whether the associated text input is focused, so the virtual
// keyboard can show only while the learner is actively typing into that
// field — mirrors how a real on-screen keyboard behaves. Safe to pair with
// VirtualKeyboard's onMouseDown+preventDefault handlers, which keep the
// input focused while a key is clicked (so this never flickers closed
// mid-interaction).
//
// `dismissed` lets the learner hide the custom script keyboard for this
// focus session and fall back to their device's own keyboard (e.g. to type
// Latin characters or numbers) — it resets on every fresh focus so the
// custom keyboard is the default each time they tap back into the field.
export function useKeyboardFocus() {
  const [focused, setFocused] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  return {
    showKeyboard: focused && !dismissed,
    dismissKeyboard: () => setDismissed(true),
    inputProps: {
      onFocus: () => {
        setFocused(true);
        setDismissed(false);
      },
      onBlur: () => setFocused(false),
    },
  };
}
