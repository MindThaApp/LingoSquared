import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// Emoji icons/flags render inconsistently (flags show as bare letters on Windows).
const EMOJI = /[\u{1F300}-\u{1FAFF}⭐]/u;
const FILES = ["src/components/layout/NavBar.tsx", "src/pages/CoursePickerPage.tsx"];
describe("no emoji icons in nav and course picker", () => {
  for (const f of FILES) {
    it(f, () => {
      expect(readFileSync(f, "utf8")).not.toMatch(EMOJI);
    });
  }
});
