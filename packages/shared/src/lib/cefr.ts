import type { CefrLevel } from "../api/types";

export const CEFR_ORDER: CefrLevel[] = ["A1", "A2", "B1", "B2", "C1", "C2"];

export function sortByCefr<T extends { level: CefrLevel }>(items: T[]): T[] {
  return [...items].sort((a, b) => CEFR_ORDER.indexOf(a.level) - CEFR_ORDER.indexOf(b.level));
}
