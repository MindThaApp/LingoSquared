import { test, expect } from "@playwright/test";
import { freshEmail, registerAndLand, goToFarsiFoundationsUnits } from "./helpers";

// Covers "open a unit -> open a lesson -> teaching cards -> exercise
// phase begins", the structural part of the flow BUILD_LOG.md records
// as manually verified end-to-end. Deliberately stops at the first
// exercise rendering rather than answering it: grading is real
// server-side truth (see CONTRACT.md / router.py grade()), so a
// generic bot can't know the correct answer for arbitrary content
// without either hardcoding it per-unit or the backend exposing a
// test-only reveal endpoint -- neither exists today. Full
// answer-through-completion coverage is a known gap, not an oversight;
// flag it to whoever owns Docker/backend if it becomes worth building.

test("first unit's first lesson: teaching cards advance into the exercise phase", async ({ page }) => {
  await registerAndLand(page, freshEmail("e2e-lesson"));
  await goToFarsiFoundationsUnits(page);

  await page.locator(".path-bubble").first().click();
  await page.waitForURL(/\/units\/[^/]+$/);

  await page.locator(".continue-card").first().click();
  await page.waitForURL(/\/lessons\/[^/]+$/);

  // Walk through teaching cards (count varies by unit) until practice starts.
  let guard = 0;
  while (guard < 20) {
    const startPractice = page.getByRole("button", { name: "Start practice" });
    if (await startPractice.isVisible().catch(() => false)) {
      await startPractice.click();
      break;
    }
    await page.getByRole("button", { name: "Next" }).click();
    guard += 1;
  }
  expect(guard).toBeLessThan(20);

  // Exercise phase: ExerciseRenderer should now show a real exercise,
  // not the "no exercises" empty state.
  await expect(page.getByText("No exercises in this lesson.")).toHaveCount(0);
  await expect(page.locator(".progress-track")).toBeVisible();
});
