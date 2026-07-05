import { test, expect } from "@playwright/test";
import { freshEmail, registerAndLand } from "./helpers";

// A brand-new user (zero completed lessons) must see the locked state,
// never a crash or an empty infinite-scroll -- verified manually per
// BUILD_LOG.md ("confirmed a genuinely brand-new user sees the locked
// state" during the Endless Practice verification pass).

test("fresh user sees the practice-locked state, not the feed", async ({ page }) => {
  await registerAndLand(page, freshEmail("e2e-practice-locked"));

  await page.getByRole("link", { name: "Practice" }).first().click();
  await page.waitForURL(/\/practice$/);

  await expect(
    page.getByText("Complete your first lesson to unlock practice"),
  ).toBeVisible();
});
