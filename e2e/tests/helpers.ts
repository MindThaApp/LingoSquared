import type { Page } from "@playwright/test";

/**
 * Unique, harmless test account per run -- @example.com per this
 * project's own convention (RFC-2606 reserved; .invalid was tried and
 * rejected by the email validator, see CLAUDE.md/BUILD_LOG.md).
 */
export function freshEmail(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}@example.com`;
}

export async function registerAndLand(page: Page, email: string, password = "e2e-test-pass-1"): Promise<void> {
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Register" }).click();
  await page.waitForURL("/");
}

/**
 * Navigates a freshly-registered user through the two-step picker into
 * a named seeded course and opens its unit path. Targets the course by
 * exact title text, not list position -- dev/local DBs commonly
 * accumulate test/debug courses from other sessions' verification runs
 * (e.g. "Multi-answer grading regression", "Pair en-fa", "Idempotent
 * course <uuid>") that would otherwise win on alphabetical sort or
 * list-position luck.
 */
export async function goToCourseUnits(
  page: Page,
  speakLanguageName: string | RegExp,
  learnLanguageName: string | RegExp,
  courseTitle: string,
): Promise<void> {
  // NavBar renders both a desktop topbar nav and a mobile tabbar nav, so
  // every nav link resolves to two DOM elements -- always .first().
  await page.getByRole("link", { name: "Learn" }).first().click();
  await page.waitForURL(/\/courses$/);
  await page.getByRole("button", { name: speakLanguageName }).first().click();
  await page.getByRole("button", { name: learnLanguageName }).first().click();
  // NOT exact:true -- the course card renders `{title} <span
  // class="badge">{level}</span>`, so the containing element's full text
  // is "Dari Foundations A1", not the title alone; a substring match on
  // the title text is what actually finds it, and stays unique against
  // sibling titles like "Dari Elementary" / "English Foundations for
  // Dari Speakers" (neither contains this title as a substring).
  await page.getByText(courseTitle).click();
  await page.waitForURL(/\/courses\/[^/]+(\/level)?$/);
  if (/\/level$/.test(page.url())) {
    // LevelCheckPage skips itself via an effect (renders null while
    // unitsQuery loads, then auto-navigates away) whenever a course has
    // <=1 reading/writing unit -- e.g. seeded single-unit courses. In
    // that case there is NEVER a button on this page. Multi-unit
    // courses DO render three real level-choice buttons, but only once
    // unitsQuery resolves -- there's a real gap between "URL says
    // /level" and "the choice buttons actually exist," and which of the
    // two eventual outcomes (buttons vs. auto-redirect) happens isn't
    // knowable in advance.
    //
    // IMPORTANT: `locator.isVisible({timeout})` does NOT poll/retry for
    // that duration -- it is a single immediate check, and `timeout`
    // barely affects it. Using it to "wait" for the heading returned
    // `false` within single-digit milliseconds, every time, regardless
    // of how large the timeout was set to, because the query hadn't
    // resolved yet at that exact instant. `locator.waitFor()` is the
    // one that actually polls. (Found live via explicit timestamped
    // logging after two other fixes -- for a stale-DOM race and for
    // `.continue-card` colliding with the previous page's class -- both
    // looked plausible and were real, but neither was the actual cause
    // of the multi-unit case hanging.)
    //
    // Race the two real outcomes instead of guessing which applies:
    const heading = page.getByText("What's your level?");
    const outcome = await Promise.race([
      heading.waitFor({ state: "visible", timeout: 8000 }).then(() => "buttons" as const),
      page.waitForURL(/\/courses\/[^/]+$/, { timeout: 8000 }).then(() => "skipped" as const),
    ]).catch(() => "neither" as const);
    if (outcome === "buttons") {
      // Since the placement test landed, the page leads with a placement-test
      // CTA card (itself a `.continue-card`, but not a level choice) and keeps
      // the three self-report level buttons behind a "Skip" toggle. Reveal
      // them and pick the beginner level, which navigates into the course.
      await page.getByRole("button", { name: "Skip — I'll pick myself" }).click({ timeout: 5000 });
      await page.getByRole("button", { name: /Complete beginner/ }).click({ timeout: 5000 });
    }
  }
  await page.waitForURL(/\/courses\/[^/]+$/, { timeout: 10000 });
}

/**
 * The three publish-gate launch pairs (en<->nl, en<->fa/prs) per the
 * 2026-07-05 scope decision in CLAUDE.md. Course titles must match a
 * REAL imported course, not a test artifact -- verify with
 * `curl "http://localhost:8000/courses?source=X&target=Y"` before
 * adding an entry here (en-nl has no real course yet as of this
 * writing, only test artifacts -- do not add it until one exists).
 */
export const LAUNCH_COURSES = {
  // The learn-step tile's accessible name is the UI-localized language name
  // (`language_names.<code>` in en.json), NOT the API's `Language.name` --
  // en.json now renders fa as "Persian" (`Farsi` no longer appears anywhere
  // in the step-2 button). The course TITLE below is unaffected: it's a
  // literal DB `Course.title` string, not a translated language name, and
  // "Farsi Foundations" is still the real seeded title (verified via
  // `curl "http://localhost:8020/courses?source=en&target=fa"`).
  farsiFoundations: { speak: /English/, learn: /Persian/, title: "Farsi Foundations" },
  dariFoundations: { speak: /English/, learn: /Dari/, title: "Dari Foundations" },
} as const;

/** Convenience wrapper kept for the existing en-fa specs. */
export async function goToFarsiFoundationsUnits(page: Page): Promise<void> {
  const c = LAUNCH_COURSES.farsiFoundations;
  await goToCourseUnits(page, c.speak, c.learn, c.title);
}
