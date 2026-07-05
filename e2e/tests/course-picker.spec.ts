import { test, expect } from "@playwright/test";
import { freshEmail, registerAndLand, goToFarsiFoundationsUnits } from "./helpers";

// Covers the two-step language picker -> course list -> unit path flow,
// verified manually in BUILD_LOG.md ("register -> home dashboard ->
// two-step language picker -> skill path -> a full lesson"). Assumes the
// en-fa "Farsi Foundations" A1 course is seeded.

test("two-step picker reaches a real seeded course and its unit path", async ({ page }) => {
  await registerAndLand(page, freshEmail("e2e-picker"));
  await goToFarsiFoundationsUnits(page);

  await expect(page.locator(".path-node").first()).toBeVisible();
});
