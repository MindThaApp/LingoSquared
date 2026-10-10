import { test, expect } from "@playwright/test";
import { freshEmail, registerAndLand } from "./helpers";

// Smoke test: every bottom-tab route renders without crashing. Cheap
// regression guard for the class of bug this project has hit before --
// a whole page silently left unstyled/unwired after a redesign (e.g.
// the deleted logout button, unstyled LessonCompletePage/ReviewPage/
// ProfilePage) is at least caught here as "the route didn't 500 or
// throw", even though full visual/UX correctness still needs a human.

// `runner: true` marks the full-screen runner routes (App.tsx
// RUNNER_PATTERNS), which deliberately hide the NavBar, so the shell
// check differs there and the test steps back to the tabbed shell after.
const TABS: Array<{ name: string; urlPattern: RegExp; runner?: boolean }> = [
  { name: "Home", urlPattern: /\/$/ },
  { name: "Practice", urlPattern: /\/practice$/ },
  { name: "Review", urlPattern: /\/review$/, runner: true },
  { name: "Profile", urlPattern: /\/profile$/ },
];

test("every bottom-tab route renders without a crash", async ({ page }) => {
  await registerAndLand(page, freshEmail("e2e-nav"));

  for (const tab of TABS) {
    await page.getByRole("link", { name: tab.name }).first().click();
    await page.waitForURL(tab.urlPattern);
    // A thrown render error lands on the ErrorBoundary card; the page
    // itself must have rendered something into <main>.
    await expect(page.getByRole("main")).not.toBeEmpty();
    await expect(page.getByText("Something went wrong")).toHaveCount(0);
    if (tab.runner) {
      await expect(page.getByRole("link", { name: "Auvel" })).toHaveCount(0);
      await page.goBack();
    }
    // Confirm the app shell (nav) is there on the tabbed routes.
    await expect(page.getByRole("link", { name: "Auvel" })).toBeVisible();
  }
});
