import type { UnitSummary } from "@lingo/shared/api/types";

// Units carry track: "core" | "situation". Older servers omit it -> core.
export function isCoreUnit(u: Pick<UnitSummary, "track">): boolean {
  return (u.track ?? "core") !== "situation";
}

export function partitionUnits<T extends Pick<UnitSummary, "track">>(
  units: T[],
): { core: T[]; situation: T[] } {
  const core: T[] = [];
  const situation: T[] = [];
  for (const u of units) (isCoreUnit(u) ? core : situation).push(u);
  return { core, situation };
}

const PREFIX = "course-situations-open-";

export function getSituationsOpen(courseId: string): boolean {
  try {
    return localStorage.getItem(PREFIX + courseId) === "1";
  } catch {
    return false;
  }
}

export function setSituationsOpen(courseId: string, open: boolean): void {
  try {
    localStorage.setItem(PREFIX + courseId, open ? "1" : "0");
  } catch {
    /* ignore */
  }
}
