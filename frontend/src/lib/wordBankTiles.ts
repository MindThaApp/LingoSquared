// Pure tile-building for the beginner "word bank" answer mode. Display only:
// the submitted payload is the placed tokens joined by " " (same string shape
// as typing); grading stays server-side. A bank is only ever offered when its
// tiles are guaranteed to be able to form the answer: either the server-authored
// prompt.word_bank (answer tokens + distractors, used as-is), or the retry after
// a miss (answerHint, already on screen). Nothing is ever guessed from lesson text.
import type { Exercise } from "@lingo/shared/api/types";
import { seededShuffle, seededShuffleNotOriginal } from "./shuffle";

/**
 * Split on whitespace and strip punctuation from the token EDGES (Unicode
 * aware: \p{P} covers Arabic comma/question mark/semicolon and guillemets).
 * Inner punctuation (l'homme, zo-even) is kept so the joined answer stays
 * faithful. Case is kept as authored. Empty tokens are dropped.
 */
export function tokenize(text: string): string[] {
  return text
    .split(/\s+/)
    .map((tok) => tok.replace(/^[\p{P}\p{S}]+|[\p{P}\p{S}]+$/gu, ""))
    .filter((tok) => tok.length > 0);
}

function baseLang(code: string): string {
  return code.toLowerCase().split(/[-_]/)[0];
}

function sameLang(a: string | undefined | null, b: string | undefined | null): boolean {
  return Boolean(a) && Boolean(b) && baseLang(a as string) === baseLang(b as string);
}

/** Target-language tokens contributed by one exercise (text blocks, options, word_bank). */
function targetTokens(ex: Exercise, target: string | null, includeBlocks = true): string[] {
  const out: string[] = [];
  if (includeBlocks) {
    for (const b of ex.prompt.text_blocks ?? []) {
      if (sameLang(b.language_code, target)) out.push(...tokenize(b.text));
    }
  }
  if (sameLang(ex.prompt.answer_language_code, target)) {
    for (const o of ex.prompt.options ?? []) if (typeof o === "string") out.push(...tokenize(o));
    for (const w of ex.prompt.word_bank ?? []) if (typeof w === "string") out.push(...tokenize(w));
  }
  return out;
}

function dedupeCI(tokens: string[], seen = new Set<string>()): string[] {
  const out: string[] = [];
  for (const t of tokens) {
    const k = t.toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(t);
  }
  return out;
}

export interface WordBank {
  tiles: string[];
  source: "prompt" | "answer" | "none";
}

const EMPTY: WordBank = { tiles: [], source: "none" };

export function buildWordBank(args: {
  exercise: Exercise;
  lessonExercises?: Exercise[];
  answerHint?: string;
  targetLanguage: string | null;
}): WordBank {
  const { exercise, lessonExercises = [], answerHint, targetLanguage } = args;

  // (a) Server-provided word_bank: already answer tokens + distractors. Not
  // stripped, deduped or extended -- only shuffled (display order).
  const provided = exercise.prompt.word_bank;
  if (
    Array.isArray(provided) &&
    provided.length >= 2 &&
    provided.every((w) => typeof w === "string" && w.length > 0)
  ) {
    return { tiles: seededShuffleNotOriginal(provided, exercise.id), source: "prompt" };
  }

  // (b) Retry after a miss: the correct answer is already on screen.
  if (answerHint && answerHint.trim()) {
    const own = exercise.prompt.answer_language_code;
    const target = typeof own === "string" && own ? own : targetLanguage;
    const answer = tokenize(answerHint);
    const inAnswer = new Set(answer.map((t) => t.toLowerCase()));
    const otherTokens = target
      ? lessonExercises.filter((e) => e.id !== exercise.id).flatMap((e) => targetTokens(e, target))
      : [];
    const pool = dedupeCI(otherTokens, new Set(inAnswer));
    const want = Math.min(4, Math.max(2, Math.ceil(answer.length / 2) + 1));
    const distractors = seededShuffle(pool, `${exercise.id}:distractors`).slice(0, want);
    const tiles = seededShuffleNotOriginal([...answer, ...distractors], exercise.id);
    return tiles.length < 2 ? EMPTY : { tiles, source: "answer" };
  }

  return EMPTY;
}
