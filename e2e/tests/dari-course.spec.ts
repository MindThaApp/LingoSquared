import { test, expect } from "@playwright/test";
import { freshEmail, registerAndLand, goToCourseUnits, LAUNCH_COURSES } from "./helpers";

// Dari (prs) is one of the three publish-gate launch pairs per the
// 2026-07-05 scope decision in CLAUDE.md ("publish-gate language set:
// en<->nl and en<->fa/prs only... need to hit essentially no functional
// breakage"). This mirrors course-picker.spec.ts/lesson-teaching.spec.ts's
// en-fa coverage for the en-prs "Dari Foundations" course, since fa and
// prs get separate content/RTL/script/keyboard code paths -- fa passing
// doesn't prove prs works.

test("two-step picker reaches Dari Foundations and its unit path", async ({ page }) => {
  await registerAndLand(page, freshEmail("e2e-dari-picker"));
  const c = LAUNCH_COURSES.dariFoundations;
  await goToCourseUnits(page, c.speak, c.learn, c.title);

  await expect(page.locator(".path-node").first()).toBeVisible();
});

test("Dari Foundations: teaching cards advance into the exercise phase", async ({ page }) => {
  await registerAndLand(page, freshEmail("e2e-dari-lesson"));
  const c = LAUNCH_COURSES.dariFoundations;
  await goToCourseUnits(page, c.speak, c.learn, c.title);

  await page.locator(".path-bubble").first().click();
  await page.waitForURL(/\/units\/[^/]+$/);
  await page.locator(".continue-card").first().click();
  await page.waitForURL(/\/lessons\/[^/]+$/);

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

  await expect(page.getByText("No exercises in this lesson.")).toHaveCount(0);
  await expect(page.locator(".progress-track")).toBeVisible();
});
