import type { ReviewItem } from "@lingo/shared/api/types";

// Hard cap on how many /me/reviews items the "Fix your mistakes" section will
// ever pull, so a misbehaving cursor can never loop the fetch forever.
export const FIX_MISTAKES_MAX_ITEMS = 200;

/**
 * Client-side due filter (the server already filters; this is defensive).
 * An item is due when due_at <= now; an unparseable date is excluded.
 */
export function filterDueReviews(items: ReviewItem[], now: Date = new Date()): ReviewItem[] {
  const nowMs = now.getTime();
  return items.filter((item) => {
    const dueMs = Date.parse(item.due_at);
    return !Number.isNaN(dueMs) && dueMs <= nowMs;
  });
}

/** The card is shown only when at least one mistake is due. */
export function shouldShowFixCard(count: number): boolean {
  return count > 0;
}

export interface FixSummary {
  total: number;
  fixed: number;
}

/** Tally per-item outcomes (true = answered correctly) for the end summary. */
export function tallyFixResults(outcomes: boolean[]): FixSummary {
  return { total: outcomes.length, fixed: outcomes.filter(Boolean).length };
}
