import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const load = (loc: string) =>
  JSON.parse(readFileSync(resolve(__dirname, `../../../packages/shared/src/i18n/locales/${loc}.json`), "utf8"));
const en = load("en");
const nl = load("nl");
const fa = load("fa");
const prs = load("prs");

// Every quest code the backend can hand out must have title+description keys
// in every UI locale, else the quest renders in English under nl/fa/prs.
const src = readFileSync(resolve(__dirname, "../../../backend/app/services/quests.py"), "utf8");
const defs = src.slice(src.indexOf("QUEST_DEFINITIONS"), src.indexOf("def selected_quest_definitions"));
const codes = [...defs.matchAll(/"code"\s*:\s*"([a-z0-9_]+)"/g)].map((m) => m[1]);

describe("quest translations", () => {
  it("parses the backend quest codes", () => {
    expect(codes.length).toBeGreaterThanOrEqual(8);
  });
  for (const [name, locale] of Object.entries({ en, nl, fa, prs })) {
    it(`${name} has title and description for every backend quest code`, () => {
      const quests = (locale as unknown as { quests: Record<string, { title?: string; description?: string }> }).quests;
      for (const code of codes) {
        expect(quests[code]?.title, `${name}.quests.${code}.title`).toBeTruthy();
        expect(quests[code]?.description, `${name}.quests.${code}.description`).toBeTruthy();
      }
    });
  }
});
