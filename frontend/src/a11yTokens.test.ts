import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

// jsdom cannot compute rendered colours, so axe's color-contrast rule is off in
// unit tests (see test/axe.ts). These checks pin the index.css text tokens
// against the backgrounds they render on; the real-browser rule runs in
// scripts/a11y_check.sh.
const css = readFileSync(resolve(__dirname, "index.css"), "utf8");

function tokens(block: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const m of block.matchAll(/(--[a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)) out[m[1]] = m[2];
  return out;
}
const lightBlock = css.slice(css.indexOf(":root {"), css.indexOf("@media (prefers-color-scheme: dark)"));
const darkStart = css.indexOf("@media (prefers-color-scheme: dark)");
const darkBlock = css.slice(darkStart, css.indexOf("\n}\n", darkStart));
const light = tokens(lightBlock);
const dark = { ...light, ...tokens(darkBlock) };

function lum(hex: string) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function ratio(a: string, b: string) {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

describe.each([
  ["light", light],
  ["dark", dark],
])("%s theme text tokens", (_name, t) => {
  for (const bg of ["--bg", "--surface", "--surface-2", "--accent-soft"]) {
    it(`--text-soft on ${bg} >= 4.5:1`, () => {
      expect(ratio(t["--text-soft"], t[bg])).toBeGreaterThanOrEqual(4.5);
    });
    it(`--accent on ${bg} >= 4.5:1`, () => {
      expect(ratio(t["--accent"], t[bg])).toBeGreaterThanOrEqual(4.5);
    });
  }
});
