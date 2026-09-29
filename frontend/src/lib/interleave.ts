import type { Exercise, TeachingCard, TextBlock } from "@lingo/shared/api/types";

// Interleaves teaching cards with practice exercises so a learner never sits
// through a wall of cards before the first question. The lesson payload does
// NOT carry the correct answer (only `prompt`), so matching is done on
// whatever the prompt itself shows: text_blocks, options, word_bank, pairs,
// audio_text and any other string field.

export interface LessonBlock {
  cards: TeachingCard[];
  exercises: Exercise[];
}

export type InterleaveMode = "matched" | "rhythm";

export interface LessonBlocks {
  blocks: LessonBlock[];
  mode: InterleaveMode;
}

/** Most cards shown in a row before an exercise. */
export const MAX_CARDS_PER_BLOCK = 3;
/** Rhythm fallback: this many cards, then this many exercises, repeating. */
export const RHYTHM_CARDS = 2;
export const RHYTHM_EXERCISES = 2;
/** Matched mode needs at least this share of exercises tied to a card. */
export const MIN_MATCH_RATIO = 0.5;
// A token shared by more than this share of cards (>= MIN_DF_ITEMS cards) or
// of "source-language" exercise tokens carries no signal (e.g. "choose",
// "translate", a word every card repeats) and is dropped from matching.
const MAX_DF_RATIO = 0.5;
const MIN_DF_ITEMS = 4;

// Small closed-class list so English glosses ("the", "a") and common
// Dutch/German/French/Spanish/Persian function words never create matches.
// Deliberately short: the length floor and the document-frequency filter
// do most of the work and are language-agnostic.
const STOPWORDS = new Set(
  (
    "the and for you your are was were with this that what how not but have has " +
    "from they them his her its our their who whom which when where why can will " +
    "een het van dat die dit met voor zijn ben bent heb hebt niet ook maar naar " +
    "der die das und ein eine ist nicht mit les des une est pas que qui dans pour " +
    "los las una por con que del est" +
    " است این که را با برای از در به یک"
  ).split(/\s+/),
);

const CJK = /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}]/u;
const NON_WORD = /[^\p{L}\p{N}\p{M}]+/u;

/** Lowercase + NFC + split on anything that is not a letter/number/mark. */
export function normalizeWords(text: string): string[] {
  return text
    .normalize("NFC")
    .toLowerCase()
    .split(NON_WORD)
    .filter((w) => w.length > 0);
}

function wordTokens(word: string): string[] {
  if (CJK.test(word)) {
    // No spaces in CJK: character bigrams (plus the lone char for 1-char words).
    const chars = Array.from(word);
    if (chars.length === 1) return [word];
    const out: string[] = [];
    for (let i = 0; i < chars.length - 1; i++) out.push(chars[i] + chars[i + 1]);
    return out;
  }
  if (Array.from(word).length < 3 || STOPWORDS.has(word) || /^\p{N}+$/u.test(word)) return [];
  return [word];
}

/** Meaningful content tokens of a string. */
export function contentTokens(text: string): string[] {
  return normalizeWords(text).flatMap(wordTokens);
}

// Fields that hold codes/keys/ids, never learner-visible content.
const NON_CONTENT_KEY = /(_code|_key|_id)$|^(id|type|direction|speaker)$/;

interface ExerciseTokens {
  own: Set<string>; // target-ish: options, word_bank, pairs, audio_text, target-language blocks
  source: Set<string>; // text_blocks in a non-card language (instructions / prompts to translate)
}

function collectStrings(value: unknown, out: string[]): void {
  if (typeof value === "string") out.push(value);
  else if (Array.isArray(value)) value.forEach((v) => collectStrings(v, out));
  else if (value && typeof value === "object") {
    for (const [k, v] of Object.entries(value)) if (!NON_CONTENT_KEY.test(k)) collectStrings(v, out);
  }
}

function exerciseTokens(exercise: Exercise, targetCodes: Set<string>): ExerciseTokens {
  const own = new Set<string>();
  const source = new Set<string>();
  const prompt = exercise.prompt;
  for (const block of prompt.text_blocks ?? []) {
    const bucket = targetCodes.size === 0 || targetCodes.has(block.language_code) ? own : source;
    contentTokens(block.text).forEach((t) => bucket.add(t));
  }
  const rest: string[] = [];
  for (const [k, v] of Object.entries(prompt)) {
    if (k === "text_blocks" || NON_CONTENT_KEY.test(k)) continue;
    collectStrings(v, rest);
  }
  rest.forEach((s) => contentTokens(s).forEach((t) => own.add(t)));
  return { own, source };
}

function blockTokens(blocks: TextBlock[] | undefined, into: Set<string>): void {
  for (const b of blocks ?? []) contentTokens(b.text).forEach((t) => into.add(t));
}

function cardTokens(card: TeachingCard): Set<string> {
  const tokens = new Set<string>();
  if (card.title) contentTokens(card.title).forEach((t) => tokens.add(t));
  blockTokens(card.text_blocks, tokens);
  for (const ex of card.examples ?? []) blockTokens(ex.text_blocks, tokens);
  return tokens;
}

/** Sizes of `cardCount` cards in groups of <= 3, as even as possible (no lone 1-card group unless n=1). */
export function chunkSizes(cardCount: number, maxPer = MAX_CARDS_PER_BLOCK): number[] {
  if (cardCount <= 0) return [];
  const groups = Math.ceil(cardCount / maxPer);
  const base = Math.floor(cardCount / groups);
  const extra = cardCount % groups;
  return Array.from({ length: groups }, (_, i) => base + (i < extra ? 1 : 0));
}

function slice<T>(items: T[], sizes: number[]): T[][] {
  const out: T[][] = [];
  let at = 0;
  for (const s of sizes) {
    out.push(items.slice(at, at + s));
    at += s;
  }
  return out;
}

/**
 * For each exercise, the index of the LATEST card it shares a meaningful token
 * with, or -1 when it matches none.
 */
export function matchExercisesToCards(cards: TeachingCard[], exercises: Exercise[]): number[] {
  const cardSets = cards.map(cardTokens);

  // Card-side document-frequency filter: a token on most cards is noise.
  const cardDf = new Map<string, number>();
  cardSets.forEach((s) => s.forEach((t) => cardDf.set(t, (cardDf.get(t) ?? 0) + 1)));
  const cardNoise = (t: string) =>
    cards.length >= MIN_DF_ITEMS && (cardDf.get(t) ?? 0) / cards.length > MAX_DF_RATIO;

  // The card language(s): the language of each card's first (headword) block.
  const targetCodes = new Set<string>();
  for (const c of cards) {
    const code = c.text_blocks[0]?.language_code;
    if (code) targetCodes.add(code);
  }

  const exTokens = exercises.map((e) => exerciseTokens(e, targetCodes));

  // Exercise-side DF filter for source-language tokens only ("choose",
  // "listen", "translate"...). Target-language tokens are never filtered here:
  // a headword legitimately recurs across a lesson's exercises.
  const srcDf = new Map<string, number>();
  exTokens.forEach((e) => e.source.forEach((t) => srcDf.set(t, (srcDf.get(t) ?? 0) + 1)));
  const srcNoise = (t: string) =>
    exercises.length >= MIN_DF_ITEMS && (srcDf.get(t) ?? 0) / exercises.length > MAX_DF_RATIO;

  return exTokens.map((e) => {
    const usable = [
      ...[...e.own].filter((t) => !cardNoise(t)),
      ...[...e.source].filter((t) => !cardNoise(t) && !srcNoise(t)),
    ];
    for (let i = cardSets.length - 1; i >= 0; i--) {
      if (usable.some((t) => cardSets[i].has(t))) return i;
    }
    return -1;
  });
}

function rhythmBlocks(cards: TeachingCard[], exercises: Exercise[]): LessonBlock[] {
  // Number of (cards, exercises) rounds: as many 2-card rounds as the cards
  // need, but never more than the exercises can fill (each round must end in
  // an exercise, so no cards are left dangling after the last one).
  const rounds = Math.max(1, Math.min(Math.ceil(cards.length / RHYTHM_CARDS), Math.floor(exercises.length / RHYTHM_EXERCISES)));
  const cardGroups = slice(cards, chunkSizes(cards.length, Math.ceil(cards.length / rounds)));
  const blocks: LessonBlock[] = cardGroups.map((g, i) => ({
    cards: g,
    exercises: exercises.slice(i * RHYTHM_EXERCISES, (i + 1) * RHYTHM_EXERCISES),
  }));
  // Leftover exercises go to the end of the last block.
  blocks[blocks.length - 1].exercises.push(...exercises.slice(blocks.length * RHYTHM_EXERCISES));
  return blocks;
}

/**
 * Split a lesson into blocks of (<=3 teaching cards, then the exercises that
 * test them). See the fill-empty-block notes below for how the "never more than
 * 3 cards before an exercise" guarantee is kept.
 */
export function buildLessonBlocks(teaching: TeachingCard[], exercises: Exercise[]): LessonBlocks {
  if (teaching.length === 0 && exercises.length === 0) return { blocks: [], mode: "matched" };
  if (exercises.length === 0) return { blocks: [{ cards: [...teaching], exercises: [] }], mode: "matched" };
  if (teaching.length === 0) return { blocks: [{ cards: [], exercises: [...exercises] }], mode: "matched" };

  const cardOf = matchExercisesToCards(teaching, exercises);
  const matchedCount = cardOf.filter((c) => c >= 0).length;
  if (matchedCount / exercises.length < MIN_MATCH_RATIO) {
    return { blocks: rhythmBlocks(teaching, exercises), mode: "rhythm" };
  }

  // Never more groups than exercises: each group must be followed by >=1
  // exercise. (Only bites when a lesson has fewer exercises than card groups,
  // where the 3-card guarantee is arithmetically impossible anyway.)
  let sizes = chunkSizes(teaching.length);
  if (sizes.length > exercises.length) sizes = chunkSizes(teaching.length, Math.ceil(teaching.length / exercises.length));
  const cardGroups = slice(teaching, sizes);
  // First card index of each group -> which group owns a given card index.
  const groupOfCard: number[] = [];
  sizes.forEach((s, g) => {
    for (let i = 0; i < s; i++) groupOfCard.push(g);
  });

  // Each exercise joins the group holding the LATEST card it matches, so
  // every card it tests has been shown by then. Authored order is preserved
  // because exercises are visited in array order.
  const groupExercises: Exercise[][] = cardGroups.map(() => []);
  const unmatched: Exercise[] = [];
  exercises.forEach((ex, i) => {
    if (cardOf[i] >= 0) groupExercises[groupOfCard[cardOf[i]]].push(ex);
    else unmatched.push(ex);
  });

  // Empty groups (no exercise tests these cards) would break the guarantee, so
  // fill each one, in order of preference:
  //  1. an exercise that matched no card (safe: needs nothing not yet taught);
  //  2. the first exercise of the nearest LATER group that has a spare (>=2);
  //     it may touch a card not shown yet, a mild pre-exposure - the cheapest
  //     way to keep the guarantee;
  //  3. the last exercise of the nearest EARLIER group that has a spare - this
  //     also covers a trailing cards-only group, so no cards ever sit after the
  //     last exercise (the finish flow fires when the exercise queue empties).
  // The unmatched exercises still left after that are appended after the last
  // block's exercises, keeping their relative order.
  for (let g = 0; g < groupExercises.length; g++) {
    if (groupExercises[g].length > 0) continue;
    if (unmatched.length > 0) {
      groupExercises[g].push(unmatched.shift() as Exercise);
      continue;
    }
    const later = groupExercises.findIndex((list, j) => j > g && list.length >= 2);
    if (later >= 0) {
      groupExercises[g].push(groupExercises[later].shift() as Exercise);
      continue;
    }
    let earlier = -1;
    for (let j = g - 1; j >= 0; j--) {
      if (groupExercises[j].length >= 2) {
        earlier = j;
        break;
      }
    }
    if (earlier >= 0) groupExercises[g].push(groupExercises[earlier].pop() as Exercise);
    // else: fewer exercises than groups, already prevented by the size cap above.
  }
  groupExercises[groupExercises.length - 1].push(...unmatched);

  const blocks = cardGroups.map((cardsInGroup, g) => ({ cards: cardsInGroup, exercises: groupExercises[g] }));
  return { blocks, mode: "matched" };
}

export interface QueuedExercise {
  exercise: Exercise;
  /** Cumulative teaching cards that must have been shown before this exercise. */
  cardsBefore: number;
}

/** Flatten blocks to the exercise order plus each exercise's `cardsBefore`. */
export function flattenBlocks(blocks: LessonBlock[]): QueuedExercise[] {
  const out: QueuedExercise[] = [];
  let shown = 0;
  for (const b of blocks) {
    shown += b.cards.length;
    for (const exercise of b.exercises) out.push({ exercise, cardsBefore: shown });
  }
  return out;
}
