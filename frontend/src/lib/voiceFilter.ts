// macOS/iOS ship a set of novelty and legacy robotic voices that are useless
// for language learning. Matched on the base name (macOS decorates newer
// voices as "Name (Language (Region))").
export const NOVELTY_VOICE_NAMES: ReadonlySet<string> = new Set(
  [
    "Albert", "Bad News", "Bahh", "Bells", "Boing", "Bubbles", "Cellos",
    "Deranged", "Fred", "Good News", "Hysterical", "Jester", "Junior",
    "Kathy", "Organ", "Pipe Organ", "Ralph", "Superstar", "Trinoids",
    "Whisper", "Wobble", "Zarvox",
  ].map((n) => n.toLowerCase()),
);

export function isNoveltyVoice(name: string): boolean {
  const base = name.replace(/\s*\(.*$/, "").trim().toLowerCase();
  return NOVELTY_VOICE_NAMES.has(base);
}
