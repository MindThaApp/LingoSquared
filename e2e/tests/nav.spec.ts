import { test, expect } from "@playwright/test";
import { freshEmail, registerAndLand } from "./helpers";

// Smoke test: every bottom-tab route renders without crashing. Cheap
// regression guard for the class of bug this project has hit before --
// a whole page silently left unstyled/unwired after a redesign (e.g.
// the deleted logout button, unstyled LessonCompletePage/ReviewPage/
// ProfilePage) is at least caught here as "the route didn't 500 or
// throw", even though full visual/UX correctness still needs a human.

const TABS: Array<{ name: string; urlPattern: RegExp }> = [
  { name: "Home", urlPattern: /\/$/ },
  { name: "Practice", urlPattern: /\/practice$/ },
  { name: "Review", urlPattern: /\/review$/ },
  { name: "Profile", urlPattern: /\/profile$/ },
];

test("every bottom-tab route renders without a crash", async ({ page }) => {
  await registerAndLand(page, freshEmail("e2e-nav"));

  for (const tab of TABS) {
    await page.getByRole("link", { name: tab.name }).first().click();
    await page.waitForURL(tab.urlPattern);
    // A React error boundary / thrown render error would leave the
    // app shell (nav) gone; confirm it's still there after navigating.
    await expect(page.getByRole("link", { name: "Lingo²" })).toBeVisible();
  }
});
