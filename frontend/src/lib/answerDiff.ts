// Pure diff helper for the "Almost right" feedback banner. Compares what the
// learner typed with the accepted answer and marks which parts differ.
// Single-word answers are diffed per code point (Array.from, so surrogate
// pairs are never split); multi-word answers are diffed per word. Simple LCS.

export interface DiffSegment {
  text: string;
  /** true when this segment differs (extra/wrong in learner, missing/right form in correct). */
  changed: boolean;
}

export interface AnswerDiff {
  mode: "char" | "word";
  /** The learner's answer; changed segments are the wrong/extra parts. */
  learner: DiffSegment[];
  /** The correct answer; changed segments are the parts the learner missed or got wrong. */
  correct: DiffSegment[];
}

function lcsKeepMasks(a: string[], b: string[], eq: (x: string, y: string) => boolean) {
  const n = a.length;
  const m = b.length;
  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = eq(a[i], b[j]) ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const keepA = new Array<boolean>(n).fill(false);
  const keepB = new Array<boolean>(m).fill(false);
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (eq(a[i], b[j])) {
      keepA[i] = true;
      keepB[j] = true;
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      i++;
    } else {
      j++;
    }
  }
  return { keepA, keepB };
}

function toSegments(tokens: string[], keep: boolean[]): DiffSegment[] {
  const out: DiffSegment[] = [];
  tokens.forEach((text, idx) => {
    const changed = !keep[idx];
    const last = out[out.length - 1];
    if (last && last.changed === changed) last.text += text;
    else out.push({ text, changed });
  });
  return out;
}

// A word plus its trailing whitespace, so re-joining tokens reproduces the input.
function wordTokens(s: string): string[] {
  return s.match(/\S+\s*|\s+/g) ?? [];
}

export function diffAnswers(learnerRaw: string, correctRaw: string): AnswerDiff {
  const learner = learnerRaw.trim();
  const correct = correctRaw.trim();
  const multiWord = /\s/.test(learner) || /\s/.test(correct);
  if (multiWord) {
    const a = wordTokens(learner);
    const b = wordTokens(correct);
    const { keepA, keepB } = lcsKeepMasks(a, b, (x, y) => x.trim() === y.trim());
    return { mode: "word", learner: toSegments(a, keepA), correct: toSegments(b, keepB) };
  }
  const a = Array.from(learner);
  const b = Array.from(correct);
  const { keepA, keepB } = lcsKeepMasks(a, b, (x, y) => x === y);
  return { mode: "char", learner: toSegments(a, keepA), correct: toSegments(b, keepB) };
}
