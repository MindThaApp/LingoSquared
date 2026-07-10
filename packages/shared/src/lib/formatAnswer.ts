/**
 * Render an exercise's correct_response (server-held answer key, arbitrary
 * shape depending on exercise type) as human-readable text for feedback
 * banners and lesson-completion "missed words" summaries.
 *
 * Known shapes, by exercise type:
 * - word_order / listen_order: string[] of words in order.
 * - matching_pairs: {left, right}[] (see MatchingPairs.tsx) - MUST be
 *   handled explicitly, since `String()`/`Array.prototype.join` on an array
 *   of objects silently produces the literal text "[object Object]" per
 *   item (found live in the browser, 2026-07-05 - this function exists
 *   specifically because that shipped to every matching_pairs exercise
 *   across every course/language).
 * - flashcard / free-text / choice types: a plain string.
 * - legacy flat {left: right} dict some call sites still pass through.
 */
export function formatCorrectResponse(value: unknown): string {
  if (Array.isArray(value)) {
    if (value.every((item) => item !== null && typeof item === "object" && "left" in item && "right" in item)) {
      return (value as { left: unknown; right: unknown }[])
        .map((pair) => `${String(pair.left)} → ${String(pair.right)}`)
        .join(", ");
    }
    return value.map((item) => formatCorrectResponse(item)).join(" ");
  }
  if (value !== null && typeof value === "object") {
    return Object.entries(value as Record<string, unknown>)
      .map(([left, right]) => `${left} → ${String(right)}`)
      .join(", ");
  }
  return String(value);
}
