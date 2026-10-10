import { test, expect } from "@playwright/test";
import { enBlock, mockedApp, openLessonViaCourseMap, unit, type LessonFixture } from "./mocks";

// Amber "almost" verdict (AnswerResult.result === "almost": accepted, XP
// awarded, but not an exact match). The runner must show the amber banner
// with the correct form AND treat it as a pass: Continue works, the item is
// NOT recycled to the back of the queue, and the lesson can finish.
// Fully route-mocked -- see tests/mocks.ts.

const lesson: LessonFixture = {
  id: "lesson-almost",
  unit_id: "unit-1",
  title: "Drinks",
  teaching: [],
  exercises: [
    // No word_bank on either item, so both render the plain typed input
    // even on this A1 course.
    { id: "ex-1", type: "translation", order: 1, prompt: { text_blocks: [enBlock("I drink water")], answer_language_code: "nl" } },
    { id: "ex-2", type: "translation", order: 2, prompt: { text_blocks: [enBlock("Good morning")], answer_language_code: "nl" } },
  ],
};

test("almost verdict shows the amber banner and does not block progress", async ({ page, baseURL }) => {
  const api = await mockedApp(page, baseURL, {
    units: [unit({ id: "unit-1", title: "Basics 1", order: 1, track: "core" })],
    lessons: [lesson],
  });
  const answered: string[] = [];
  api.on("POST", "/exercises/:id/answer", ({ params }) => {
    answered.push(params.id);
    return params.id === "ex-1"
      ? { correct: true, result: "almost", correct_response: "Ik drink water", xp_awarded: 10 }
      : { correct: true, result: "correct", correct_response: "Goedemorgen", xp_awarded: 10 };
  });

  await openLessonViaCourseMap(page, "Basics 1", "Drinks");

  // Item 1: a one-letter slip -> "almost".
  await expect(page.getByText("I drink water")).toBeVisible();
  await page.getByPlaceholder("Type your translation").fill("Ik drinck water");
  await page.getByRole("button", { name: "Check", exact: true }).click();

  const banner = page.locator(".feedback-banner.almost");
  await expect(banner).toBeVisible();
  // Announced through the runner's persistent polite live region that wraps
  // the banner (a live region has to exist before its content changes), not
  // a role on the banner itself.
  await expect(page.locator('[role="status"][aria-live="polite"]').filter({ has: banner })).toHaveCount(1);
  await expect(banner).toContainText("Almost correct. Correct answer: Ik drink water");
  await expect(banner).toContainText("Almost!");
  await expect(banner).toContainText("Correct answer: Ik drink water");
  await expect(banner).toContainText("You wrote: Ik drinck water");
  // Amber, not the red "incorrect" styling.
  await expect(page.locator(".feedback-banner.incorrect")).toHaveCount(0);
  const [bg, amberSoft] = await banner.evaluate((el) => [
    getComputedStyle(el).backgroundColor,
    (() => {
      const probe = document.createElement("div");
      probe.style.background = "var(--almost-soft)";
      document.body.appendChild(probe);
      const c = getComputedStyle(probe).backgroundColor;
      probe.remove();
      return c;
    })(),
  ]);
  expect(bg).toBe(amberSoft);

  const cont = banner.getByRole("button", { name: "Continue" });
  await expect(cont).toBeEnabled();
  await cont.click();

  // Advances to item 2 (not a recycled item 1).
  await expect(page.getByText("Good morning")).toBeVisible();
  await expect(banner).toHaveCount(0);
  await page.getByPlaceholder("Type your translation").fill("Goedemorgen");
  await page.getByRole("button", { name: "Check", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Correct!" })).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();

  // Queue empty after two answers -> the almost item was never re-queued.
  await page.waitForURL(`**/lessons/${lesson.id}/done`);
  await expect(page.getByRole("heading", { name: "Lesson complete!" })).toBeVisible();
  expect(answered).toEqual(["ex-1", "ex-2"]);
  expect(api.calls.filter((c) => c.method === "POST" && c.path === `/lessons/${lesson.id}/complete`)).toHaveLength(1);
  expect(api.crashReports).toEqual([]);
});
