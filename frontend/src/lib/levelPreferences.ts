// Self-reported starting level per course, client-side only. Used to
// recommend a starting unit, not to unlock/skip anything server-side —
// reading/writing units are already freely navigable regardless of
// completion, so this only ever affects which unit gets highlighted as
// the recommended starting point.
export type SelfReportedLevel = "beginner" | "some_basics" | "conversational";

const STORAGE_PREFIX = "course-level-";

export function getLevelPreference(courseId: string): SelfReportedLevel | null {
  const value = localStorage.getItem(STORAGE_PREFIX + courseId);
  return value === "beginner" || value === "some_basics" || value === "conversational"
    ? value
    : null;
}

export function setLevelPreference(courseId: string, level: SelfReportedLevel): void {
  localStorage.setItem(STORAGE_PREFIX + courseId, level);
}

// CEFR sublevels in ascending difficulty order. A unit's own level is
// parsed from its content_key (see parseCefrLevel below) rather than
// fetched from any dedicated API field -- Course.level is a single fixed
// value set at course creation and never updated as higher-level content
// gets appended later (see backend/app/models/entities.py), so it can't be
// trusted to reflect "does this course actually have A2/B1 content now."
const CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"];

// How many units within a SINGLE CEFR level are treated as genuine,
// increasing-difficulty progression before further units in that same
// level are assumed to be topic/venue variety rather than harder content.
// This is a deliberate heuristic cap, not a precise measurement -- it
// exists because content authoring can grow one CEFR level far past its
// original size via same-difficulty venue-transaction topics (confirmed
// real: nl's A1 level grew to 72 units via zoo/pet-store/florist/ice-cream-
// parlor-style additions, none of which are harder than unit 20). Without
// this cap, "conversational" would recommend the literal last unit of a
// level just because it has the highest index, which is exactly the bug
// this file was rewritten to fix -- see CLAUDE.md's description of the
// nl-72-unit incident for the full story.
const MAX_LEVEL_PROGRESSION_UNITS = 20;

// Parses the CEFR sublevel out of a unit's content_key, e.g.
// "nl.a1.unit72.dierenwinkel" -> "A1", "fa.b1.unit01.necessity" -> "B1".
// Confirmed consistent across every realization file under
// docs/content/realizations/ (en/nl/fa/prs/de/fr/es/ro/pl/hi), all of
// which use "{lang}.{cefr_level}.unit{NN}.{slug}". Returns null for a
// missing/unparseable content_key (units imported before content_key
// tracking existed) so callers can fall back gracefully rather than
// silently misclassify legacy content as some arbitrary level.
export function parseCefrLevel(contentKey: string | null | undefined): string | null {
  if (!contentKey) return null;
  const segment = contentKey.split(".")[1];
  if (!segment) return null;
  const upper = segment.toUpperCase();
  return CEFR_ORDER.includes(upper) ? upper : null;
}

// Pick a recommended starting unit index (0-based) out of N reading/writing
// units, given a self-reported level and each unit's content_key (in the
// same order as the unit list this index will be applied to).
//
// Levels within a course are CEFR-clustered by construction: content
// import only ever APPENDS new units to a course (see CLAUDE.md's
// "content_key-based update-in-place" note), it never interleaves a
// higher-level unit in among lower-level ones -- so a course's units, read
// in order, walk through complete CEFR levels one at a time (all of A1,
// then all of A2, etc.), not a single steadily-increasing difficulty
// ramp across its ENTIRE unit list. The old version of this function
// treated the whole flat unit list as one difficulty ramp and picked
// unitCount - 1 for "conversational" -- correct back when content was
// small and each level was short, but wrong once a level like nl's A1
// grew to 72 units mostly via same-difficulty topic variety: it recommended
// the pet-store unit (the literal last unit) for a "conversational"
// self-report on a course that's still 90%+ A1 content.
//
// Fixed behavior:
//   - "beginner" -> the very first unit, always.
//   - "conversational" -> the first unit of the HIGHEST CEFR level actually
//     present, if the course has more than one level (real harder content
//     exists, so point there instead of deeper into the same level). If
//     only one CEFR level exists, cap the recommendation at
//     MAX_LEVEL_PROGRESSION_UNITS into that level rather than its literal
//     last unit.
//   - "some_basics" -> the midpoint of the CURRENT (lowest) CEFR level,
//     capped the same way -- someone with "some basics" is assumed to
//     still be within the entry level, not ready to jump into A2/B1.
//   - If no unit's content_key parses to a known CEFR level at all
//     (entirely legacy content), falls back to the old coarse whole-list
//     heuristic, capped the same way, rather than crashing or guessing.
export function recommendedUnitIndex(
  level: SelfReportedLevel,
  unitContentKeys: Array<string | null | undefined>,
): number {
  const unitCount = unitContentKeys.length;
  if (unitCount <= 1) return 0;
  if (level === "beginner") return 0;

  const cefrLevels = unitContentKeys.map(parseCefrLevel);
  const distinctLevels = Array.from(
    new Set(cefrLevels.filter((lvl): lvl is string => lvl !== null)),
  ).sort((a, b) => CEFR_ORDER.indexOf(a) - CEFR_ORDER.indexOf(b));

  if (distinctLevels.length === 0) {
    // No parseable CEFR metadata anywhere in this unit list -- old coarse
    // behavior, still capped so it can't walk to an arbitrarily-distant
    // last unit on a long, unmarked list.
    if (level === "conversational") {
      return Math.min(unitCount - 1, MAX_LEVEL_PROGRESSION_UNITS - 1);
    }
    return Math.floor(Math.min(unitCount, MAX_LEVEL_PROGRESSION_UNITS) / 2);
  }

  if (level === "conversational" && distinctLevels.length > 1) {
    const highestLevel = distinctLevels[distinctLevels.length - 1];
    const firstIndexOfHighest = cefrLevels.findIndex((lvl) => lvl === highestLevel);
    return firstIndexOfHighest === -1 ? unitCount - 1 : firstIndexOfHighest;
  }

  // Either "some_basics", or "conversational" on a course with only one
  // CEFR level present: work within the current (lowest) level only, and
  // cap how deep into it we recommend.
  const currentLevel = distinctLevels[0];
  const levelIndices: number[] = [];
  cefrLevels.forEach((lvl, idx) => {
    if (lvl === currentLevel) levelIndices.push(idx);
  });
  const levelStart = levelIndices[0];
  const levelDepth = Math.min(levelIndices.length, MAX_LEVEL_PROGRESSION_UNITS);

  if (level === "conversational") {
    return levelStart + levelDepth - 1;
  }
  return levelStart + Math.floor((levelDepth - 1) / 2);
}
