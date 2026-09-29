import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { ScriptCode } from "@lingo/shared/api/types";
import { scriptNeedsVirtualKeyboard } from "@lingo/shared/lib/scripts";
import { backspaceAtSelection, insertAtSelection } from "./textEdit";

type TextEl = HTMLInputElement | HTMLTextAreaElement;

// Tracks whether the associated text input is focused, so the virtual
// keyboard can show only while the learner is actively typing into that
// field — mirrors how a real on-screen keyboard behaves. Keys use
// onMouseDown+preventDefault to keep the input focused on mouse/touch and act
// in onClick; focus that moves onto a keyboard key (Tab / Enter / Space) keeps
// the keyboard mounted via the relatedTarget checks below.
//
// Also centralises, for every free-text exercise:
//  - caret-aware insert/backspace (keyboardProps.onInsert / onBackspace),
//  - inputMode="none" while the custom keyboard is in use (so the phone OS
//    keyboard doesn't open on top), restored after "use device keyboard",
//  - auto-focus on mount (and whenever `disabled` flips back to false).
//
// `dismissed` lets the learner hide the custom script keyboard for this
// focus session and fall back to their device's own keyboard — it resets on
// every fresh focus so the custom keyboard is the default each time.
export function useKeyboardFocus<T extends TextEl = HTMLInputElement>(opts?: {
  value: string;
  setValue: (v: string) => void;
  script?: ScriptCode | null;
  disabled?: boolean;
}) {
  const value = opts?.value ?? "";
  const setValue = opts?.setValue;
  const disabled = opts?.disabled ?? false;
  const usesVirtual = scriptNeedsVirtualKeyboard(opts?.script ?? null);

  const [focused, setFocused] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const inputRef = useRef<T>(null);
  const keyboardRef = useRef<HTMLDivElement>(null);
  const pendingCaret = useRef<number | null>(null);
  const skipDismissReset = useRef(false);

  // Restore the caret after React re-renders the controlled value.
  useLayoutEffect(() => {
    const el = inputRef.current;
    if (pendingCaret.current !== null && el) {
      try {
        el.setSelectionRange(pendingCaret.current, pendingCaret.current);
      } catch {
        /* element type without selection support */
      }
    }
    pendingCaret.current = null;
  }, [value]);

  // Auto-focus on mount and whenever the input becomes enabled again.
  useEffect(() => {
    if (!disabled) inputRef.current?.focus({ preventScroll: true });
  }, [disabled]);

  function edit(fn: typeof insertAtSelection | typeof backspaceAtSelection, text?: string) {
    const el = inputRef.current;
    if (!el || !setValue) return;
    const cur = el.value;
    const start = el.selectionStart ?? cur.length;
    const end = el.selectionEnd ?? cur.length;
    const res = fn === insertAtSelection ? insertAtSelection(cur, start, end, text ?? "") : backspaceAtSelection(cur, start, end);
    if (res.value === cur) return;
    pendingCaret.current = res.caret;
    setValue(res.value);
  }

  function dismissKeyboard() {
    skipDismissReset.current = true;
    setDismissed(true);
    // Re-focus so the OS keyboard opens now that inputMode is restored.
    requestAnimationFrame(() => {
      const el = inputRef.current;
      if (!el) return;
      el.blur();
      el.focus({ preventScroll: true });
      skipDismissReset.current = false;
    });
  }

  const virtualActive = usesVirtual && !dismissed;

  return {
    showKeyboard: focused && !dismissed,
    dismissKeyboard,
    inputRef,
    inputProps: {
      ref: inputRef,
      inputMode: virtualActive ? ("none" as const) : undefined,
      onFocus: () => {
        setFocused(true);
        if (!skipDismissReset.current) setDismissed(false);
      },
      onBlur: (e: React.FocusEvent) => {
        const next = e.relatedTarget as Node | null;
        if (next && keyboardRef.current?.contains(next)) return;
        setFocused(false);
      },
    },
    keyboardProps: {
      containerRef: keyboardRef,
      onContainerBlur: (e: React.FocusEvent) => {
        const next = e.relatedTarget as Node | null;
        if (next && (keyboardRef.current?.contains(next) || next === inputRef.current)) return;
        setFocused(false);
      },
      onInsert: (char: string) => edit(insertAtSelection, char),
      onBackspace: () => edit(backspaceAtSelection),
      onDismiss: dismissKeyboard,
    },
  };
}
