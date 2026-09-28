// Deterministic, seeded shuffling for DISPLAY ORDER ONLY. Authored content
// puts the correct option first / word_bank tiles in answer order, so the
// client must shuffle. Answer payloads must never depend on displayed
// position (options submit their text; word_bank submits the tapped tokens).

function hashSeed(seed: string): number {
  // xmur3-style string hash -> 32-bit
  let h = 1779033703 ^ seed.length;
  for (let i = 0; i < seed.length; i++) {
    h = Math.imul(h ^ seed.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  h = Math.imul(h ^ (h >>> 16), 2246822507);
  h = Math.imul(h ^ (h >>> 13), 3266489909);
  return (h ^= h >>> 16) >>> 0;
}

function mulberry32(a: number): () => number {
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Fisher-Yates shuffle, deterministic per seed. Returns a new array. */
export function seededShuffle<T>(items: readonly T[], seed: string): T[] {
  const out = items.slice();
  const rand = mulberry32(hashSeed(seed));
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

/**
 * Seeded shuffle whose result is guaranteed to differ (element-wise) from the
 * input order whenever that is possible (>= 2 distinct values). Used for
 * word_bank tiles, which are usually authored in answer order.
 */
export function seededShuffleNotOriginal(items: readonly string[], seed: string): string[] {
  if (new Set(items).size < 2) return items.slice();
  const same = (a: readonly string[]) => a.every((v, i) => v === items[i]);
  let out = seededShuffle(items, seed);
  for (let attempt = 1; same(out) && attempt < 20; attempt++) {
    out = seededShuffle(items, `${seed}#${attempt}`);
  }
  if (same(out)) {
    // Rotate until different (exists because >= 2 distinct values).
    for (let k = 1; k < out.length && same(out); k++) {
      out = items.slice(k).concat(items.slice(0, k));
    }
  }
  return out;
}
