// Pure caret-aware edit helpers for the on-screen virtual keyboard. Indices
// are UTF-16 code-unit offsets, as returned by selectionStart/selectionEnd.

export type TextEdit = { value: string; caret: number };

function clamp(n: number, max: number): number {
  return Math.max(0, Math.min(n, max));
}

// Insert `text` at the caret, replacing the selection when start !== end.
export function insertAtSelection(value: string, start: number, end: number, text: string): TextEdit {
  const a = clamp(Math.min(start, end), value.length);
  const b = clamp(Math.max(start, end), value.length);
  return { value: value.slice(0, a) + text + value.slice(b), caret: a + text.length };
}

// Delete the selection, or the one character before the caret (a whole
// surrogate pair counts as one character).
export function backspaceAtSelection(value: string, start: number, end: number): TextEdit {
  const a = clamp(Math.min(start, end), value.length);
  const b = clamp(Math.max(start, end), value.length);
  if (a !== b) return { value: value.slice(0, a) + value.slice(b), caret: a };
  if (a === 0) return { value, caret: 0 };
  const prev = value.charCodeAt(a - 1);
  const isLow = prev >= 0xdc00 && prev <= 0xdfff;
  const hi = a >= 2 ? value.charCodeAt(a - 2) : 0;
  const width = isLow && hi >= 0xd800 && hi <= 0xdbff ? 2 : 1;
  return { value: value.slice(0, a - width) + value.slice(a), caret: a - width };
}
