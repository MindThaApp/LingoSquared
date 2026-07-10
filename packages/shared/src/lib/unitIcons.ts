/**
 * Per-unit topical icons, replacing the old UNIT_ICONS array in
 * CourseUnitsPage.tsx (a fixed 12-emoji array indexed by the unit's
 * position in the list — wrapped around after 12 units and, worse, was
 * never actually aligned with a unit's real topic once realizations
 * reorder/split/combine spine outcomes, which they do: e.g. nl's unit02
 * is "numbers" but fa's unit02 is "introductions", so index-based icons
 * were already wrong for most non-English courses before this file
 * existed).
 *
 * Icons come from lucide-react (ISC license for the library, MIT for the
 * icon set — https://lucide.dev/license — self-hosted via npm, no
 * runtime network dependency, no attribution requirement beyond the
 * standard package license file).
 *
 * Topic derivation: `Unit.content_key` (e.g. "en.a1.unit06.family",
 * "nl.a1.unit05.family") is a stable authoring key whose LAST dot-segment
 * is (almost always) the unit's real spine topic — see
 * `docs/content/universal_spine.yaml` for the canonical topic list. It's
 * the only per-unit signal in the API response that's actually correlated
 * with topic; `order` isn't (see above) and `title` is localized per
 * language/direction (Dutch, Farsi script, etc.), which would need a
 * separate keyword dictionary per language to match against — far more
 * fragile than matching one language-independent authoring key.
 *
 * Not every realization's content_key final segment is the canonical
 * English topic word, though — some units were named in the target
 * language (German "familie"/"zahlen"/"uhrzeit"/"daten"/"essen", Dutch A2
 * "gemeente"/"meningen"/"bankrekening"/"huisarts"/"probleem_melden") or as
 * a compound phrase ("greetings_and_introductions",
 * "places_and_directions", "calendar_dates", "clock_time"). TOPIC_WORDS
 * below maps every word actually seen across every realization file
 * (confirmed via a full grep of every a1/a2 unit YAML's content_key
 * values under docs/content/realizations, 2026-07-07) to one of the
 * ~26 canonical topics.
 * `unitTopic()` splits the slug on non-alphanumeric characters and
 * returns the topic of the first recognized word, so compound slugs
 * resolve to their leading/dominant topic rather than crashing or falling
 * through to the generic fallback.
 */
import {
  Hand,
  UserPlus,
  Hash,
  Calendar,
  Clock,
  Users,
  UtensilsCrossed,
  ShoppingBag,
  MapPin,
  Signpost,
  Repeat,
  CalendarCheck,
  History,
  Heart,
  Scale,
  Plane,
  Stethoscope,
  Briefcase,
  Home,
  CloudSun,
  Shirt,
  Smile,
  Phone,
  MessagesSquare,
  Coins,
  Landmark,
  PiggyBank,
  BookOpen,
  type LucideIcon,
} from "lucide-react";

export type UnitTopic =
  | "greetings"
  | "introductions"
  | "numbers"
  | "dates"
  | "time"
  | "family"
  | "food"
  | "shopping"
  | "places"
  | "directions"
  | "routines"
  | "plans"
  | "past_events"
  | "preferences"
  | "comparisons"
  | "travel"
  | "health"
  | "work"
  | "housing"
  | "weather"
  | "clothing"
  | "emotions"
  | "communication"
  | "money"
  | "bureaucracy"
  | "opinions"
  | "banking"
  | "default";

// Every raw word observed in a unit-level content_key's final segment
// across every realization file (en, nl, fa, prs, de, fr, es), mapped to
// its canonical topic. "and"/"of" etc. are deliberately absent so they're
// skipped rather than matched.
const TOPIC_WORDS: Record<string, UnitTopic> = {
  greetings: "greetings",
  greeting: "greetings",
  introductions: "introductions",
  introduction: "introductions",
  numbers: "numbers",
  number: "numbers",
  zahlen: "numbers",
  dates: "dates",
  date: "dates",
  daten: "dates",
  calendar: "dates",
  time: "time",
  uhrzeit: "time",
  clock: "time",
  family: "family",
  familie: "family",
  food: "food",
  essen: "food",
  shopping: "shopping",
  places: "places",
  directions: "directions",
  routines: "routines",
  routine: "routines",
  plans: "plans",
  plan: "plans",
  past: "past_events",
  events: "past_events",
  preferences: "preferences",
  preference: "preferences",
  comparisons: "comparisons",
  comparison: "comparisons",
  travel: "travel",
  health: "health",
  doctor: "health",
  huisarts: "health",
  sick: "health",
  work: "work",
  housing: "housing",
  maintenance: "housing",
  probleem: "housing",
  melden: "housing",
  weather: "weather",
  clothing: "clothing",
  emotions: "emotions",
  emotion: "emotions",
  communication: "communication",
  money: "money",
  bureaucracy: "bureaucracy",
  gemeente: "bureaucracy",
  opinions: "opinions",
  opinion: "opinions",
  meningen: "opinions",
  banking: "banking",
  bankrekening: "banking",
};

/** Icon per canonical topic. Deliberately distinct within closely-related
 * pairs (greetings vs. introductions, health vs. bureaucracy vs. banking,
 * communication vs. opinions) so units are visually distinguishable, not
 * just "vaguely on-theme." */
export const TOPIC_ICONS: Record<UnitTopic, LucideIcon> = {
  greetings: Hand,
  introductions: UserPlus,
  numbers: Hash,
  dates: Calendar,
  time: Clock,
  family: Users,
  food: UtensilsCrossed,
  shopping: ShoppingBag,
  places: MapPin,
  directions: Signpost,
  routines: Repeat,
  plans: CalendarCheck,
  past_events: History,
  preferences: Heart,
  comparisons: Scale,
  travel: Plane,
  health: Stethoscope,
  work: Briefcase,
  housing: Home,
  weather: CloudSun,
  clothing: Shirt,
  emotions: Smile,
  communication: Phone,
  money: Coins,
  bureaucracy: Landmark,
  opinions: MessagesSquare,
  banking: PiggyBank,
  default: BookOpen,
};

/** Derives a canonical topic from a unit's content_key, e.g.
 * "nl.a1.unit05.family" -> "family", "de.a1.unit03.zahlen" -> "numbers",
 * "fa.a1.unit05.places_and_directions" -> "places" (first recognized
 * word wins for compound slugs). Returns "default" for null/missing/
 * unrecognized content_key (older content imported before content_key
 * tracking existed, or a future topic not yet added above). */
export function unitTopic(contentKey: string | null | undefined): UnitTopic {
  if (!contentKey) return "default";
  const segments = contentKey.split(".");
  const slug = segments[segments.length - 1] ?? "";
  const words = slug.split(/[^a-zA-Z]+/).filter(Boolean);
  for (const word of words) {
    const topic = TOPIC_WORDS[word.toLowerCase()];
    if (topic) return topic;
  }
  return "default";
}

/** The icon component for a unit's content_key. Use directly in JSX:
 * `const Icon = unitIcon(unit.content_key); <Icon size={28} />`. */
export function unitIcon(contentKey: string | null | undefined): LucideIcon {
  return TOPIC_ICONS[unitTopic(contentKey)];
}
