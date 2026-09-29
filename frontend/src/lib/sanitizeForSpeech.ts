// Strips display-only decoration from text before it is synthesized/spoken.
// Apply ONLY at the speech boundary (speak()), never to displayed text.
//
// Empty-result policy: if nothing speakable remains, returns "" and the
// caller (speak()) does nothing and returns false -> SpeakButton shows its
// honest "no voice available" state. We deliberately do NOT fall back to the
// original text, since that would read the very decoration we stripped.

// Leading speaker label: 1-3 words of letters/marks (any script), then a
// colon (ASCII or fullwidth / Arabic) and whitespace. "10:30" has digits and
// no space after the colon so it never matches; mid-sentence colons are
// untouched because the pattern is anchored at the start.
const SPEAKER_LABEL = /^\s*[\p{L}\p{M}][\p{L}\p{M}'’.-]*(?:\s+[\p{L}\p{M}][\p{L}\p{M}'’.-]*){0,2}\s*(?::\s+|：\s*)/u;
const PAREN_GLOSS = /\([^()]*\)|（[^（）]*）/g;
const BRACKET_GLOSS = /\[[^\[\]]*\]|【[^【】]*】/g;
const ARROWS = /\s*(?:<=>|<->|<-|->|=>|<=|[→←⇒⇐↔⇔➔➜➞⟶⟵])\s*/g;

export function sanitizeForSpeech(text: string): string {
  let out = text.replace(SPEAKER_LABEL, "");
  out = out.replace(PAREN_GLOSS, " ").replace(BRACKET_GLOSS, " ");
  out = out.replace(ARROWS, ", ");
  out = out.replace(/\s+/g, " ").trim();
  // Arrows at the edges leave dangling commas.
  out = out.replace(/^[,\s]+|[,\s]+$/g, "");
  out = out.replace(/\s+,/g, ",").replace(/,(?:\s*,)+/g, ",");
  return out.trim();
}
