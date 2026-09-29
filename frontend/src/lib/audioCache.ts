// In-memory LRU of synthesized-audio blob URLs keyed by (text, lang, rate).
// URLs are revoked ONLY on eviction (or explicit clear) -- a cached URL must
// stay valid for replays, so playback code must never revoke it itself.
export const AUDIO_CACHE_CAP = 50;

export function audioCacheKey(text: string, lang: string, rate: number): string {
  return JSON.stringify([text, lang, rate]);
}

export class AudioUrlCache {
  private map = new Map<string, string>();
  private cap: number;
  constructor(cap = AUDIO_CACHE_CAP) {
    this.cap = cap;
  }

  get(key: string): string | undefined {
    const url = this.map.get(key);
    if (url === undefined) return undefined;
    // Refresh recency: Map iterates in insertion order.
    this.map.delete(key);
    this.map.set(key, url);
    return url;
  }

  set(key: string, url: string): void {
    const existing = this.map.get(key);
    if (existing !== undefined && existing !== url) URL.revokeObjectURL(existing);
    this.map.delete(key);
    this.map.set(key, url);
    while (this.map.size > this.cap) {
      const oldest = this.map.keys().next().value as string;
      const oldUrl = this.map.get(oldest)!;
      this.map.delete(oldest);
      URL.revokeObjectURL(oldUrl);
    }
  }

  get size(): number {
    return this.map.size;
  }

  clear(): void {
    for (const url of this.map.values()) URL.revokeObjectURL(url);
    this.map.clear();
  }
}

export const audioCache = new AudioUrlCache();
