import { test, expect, type Page } from "@playwright/test";
import { freshEmail } from "./helpers";
import { makeReviewsDue, runLesson, stubExternals, type Step } from "./journeys.helpers";

const PASSWORD = "e2e-journey-pass-1";

const FARSI_L1: Step[] = [
  { prompt: /Choose the Farsi word for hello/, kind: "choice", right: "سلام", wrong: "خداحافظ" },
  { prompt: /Thank you/, kind: "type", right: "ممنون", wrong: "wrong" },
  { prompt: /Arrange: I am Sara/, kind: "order", right: "من سارا هستم", wrong: "هستم سارا من" },
];

async function register(page: Page, email: string, password = PASSWORD): Promise<void> {
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Register" }).click();
  await page.waitForURL(/\/welcome/);
}

/** Guided first start (English UI): pick the pair + course, default goal, start from the beginning. */
async function onboard(page: Page, speak: RegExp, learn: RegExp, title: string): Promise<void> {
  await page.getByRole("button", { name: speak }).first().click();
  await page.getByRole("button", { name: learn }).first().click();
  await page.getByText(title).click();
  await expect(page.getByText("Step 2 of 3")).toBeVisible();
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByText("Step 3 of 3")).toBeVisible();
  await page.getByText("Start from the beginning").click();
  await page.waitForURL(/\/courses\/[^/]+$/);
}

/** From the course map: first unit, first lesson. */
async function openFirstLesson(page: Page): Promise<void> {
  await page.locator(".path-bubble").first().click();
  await page.waitForURL(/\/units\/[^/]+$/);
  await page.locator(".continue-card").first().click();
  await page.waitForURL(/\/lessons\/[^/]+$/);
}

test("sign up, onboarding, first lesson (wrong then right), completion, XP and review", async ({ page }) => {
  await stubExternals(page);
  const email = freshEmail("e2e-journey");
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByRole("button", { name: "Register" }).click();
  await page.waitForURL(/\/welcome/);

  // Onboarding: learner language, target language, course, daily goal, start from the beginning.
  await onboard(page, /English/, /Persian/, "Farsi Foundations");
  await openFirstLesson(page);
  const { wrongAnswers } = await runLesson(page, FARSI_L1, { wrongFirst: true });
  expect(wrongAnswers).toBe(1);

  await expect(page.getByRole("heading", { name: "Lesson complete!" })).toBeVisible();
  // XP counts up with an animation; the final value is 3 exercises x 10 XP (the missed one is retried).
  await expect(page.getByTestId("lesson-xp-earned")).toContainText("30");

  await page.getByRole("link", { name: "Profile" }).first().click();
  await expect(page.getByTestId("profile-total-xp")).toContainText("30");

  await makeReviewsDue(email);
  await page.getByRole("link", { name: "Review" }).first().click();
  await page.getByRole("button", { name: "Start" }).click();
  // Review mode: "Fix your mistakes" replays the exercise missed in the lesson.
  await expect(page.getByText("Mistake 1 / 1")).toBeVisible();
  await page.getByRole("radio", { name: "سلام", exact: true }).click();
  await page.getByRole("button", { name: "Check", exact: true }).click();
  await expect(page.locator(".feedback-banner")).toHaveClass(/correct/);
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByText("1 fixed of 1")).toBeVisible();
});

test("password change, logout, login with the new password", async ({ page }) => {
  await stubExternals(page);
  const email = freshEmail("e2e-pw");
  const NEW_PASSWORD = "e2e-journey-new-pass-2";
  await register(page, email);
  await page.getByRole("button", { name: "Skip for now" }).click();
  await page.getByRole("link", { name: "Profile" }).first().click();

  await page.getByLabel("Current password").fill(PASSWORD);
  await page.getByLabel("New password (at least 8 characters)").fill(NEW_PASSWORD);
  await page.getByLabel("Repeat new password").fill(NEW_PASSWORD);
  await page.getByRole("button", { name: "Change password", exact: true }).click();
  await expect(page.getByText(/Password changed/)).toBeVisible();

  await page.getByRole("button", { name: "Log out" }).click();
  await page.waitForURL(/\/login/);

  // The old password no longer works...
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByText(/invalid email or password/i)).toBeVisible();

  // ...the new one does.
  await page.getByLabel("Password").fill(NEW_PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL((url) => !/\/login/.test(url.pathname));
  await expect(page.getByRole("link", { name: "Home" }).first()).toBeVisible();
});

test("RTL: Farsi UI and Farsi course render the page and lesson text right-to-left", async ({ page }) => {
  await stubExternals(page);
  await register(page, freshEmail("e2e-rtl"));
  await onboard(page, /English/, /Persian/, "Farsi Foundations");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await page.getByLabel("Interface language").selectOption("fa");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.locator("html")).toHaveAttribute("lang", "fa");

  await openFirstLesson(page);
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");

  // Teaching card: the Farsi text block is rtl, its English gloss stays ltr.
  const farsi = page.locator('.text-block[lang="fa"]').first();
  await expect(farsi).toBeVisible();
  await expect(farsi).toHaveAttribute("dir", "rtl");
  await expect(page.locator('.text-block[lang="en"]').first()).toHaveAttribute("dir", "ltr");

  // First exercise (the order varies): whichever answer control shows is rtl, and the app chrome is Persian.
  const next = page.getByTestId("teaching-next");
  const control = page.getByRole("radiogroup").or(page.getByRole("textbox")).or(page.locator(".word-bank"));
  for (let i = 0; i < 10 && !(await control.isVisible()); i++) {
    if (await next.isVisible()) await next.click();
    await expect(next.or(control)).toBeVisible();
  }
  await expect(control).toHaveAttribute("dir", "rtl");
  await expect(page.locator(".exercise-shell").getByRole("button", { name: "بررسی" })).toBeVisible();
});

const DE_AR_L1: Step[] = [
  { prompt: /Wähle das arabische Wort für „Danke“/, kind: "choice", right: "شكرا", wrong: "مرحبا" },
  { prompt: /Hallo/, kind: "type", right: "مرحبا", wrong: "falsch" },
];

test("cross pair de-ar: German learner sees German instructions and an RTL Arabic answer area", async ({ page }) => {
  await stubExternals(page);
  await register(page, freshEmail("e2e-dear"));
  await onboard(page, /German|Deutsch/, /Arabic|العربية/, "Arabisch Grundlagen");
  await openFirstLesson(page);

  // Teaching card: German gloss is ltr, Arabic is rtl.
  await expect(page.locator('.text-block[lang="de"]').first()).toHaveAttribute("dir", "ltr");
  await expect(page.locator('.text-block[lang="ar"]').first()).toHaveAttribute("dir", "rtl");

  const { prompts, wrongAnswers } = await runLesson(page, DE_AR_L1, { wrongFirst: true });
  expect(wrongAnswers).toBe(1);
  // Instructions are in the learner's language (German), not English.
  expect(prompts.some((p) => p.includes("Wähle das arabische Wort für „Danke“"))).toBe(true);
  expect(prompts.every((p) => !/Choose|Translate/.test(p))).toBe(true);
  await expect(page.getByTestId("lesson-xp-earned")).toContainText("20");
});

test("account data export, then account deletion", async ({ page }) => {
  await stubExternals(page);
  const email = freshEmail("e2e-account");
  await register(page, email);
  await page.getByRole("button", { name: "Skip for now" }).click();
  await page.getByRole("link", { name: "Profile" }).first().click();

  // Export: the browser downloads a JSON file that contains this account's data.
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download my data" }).click();
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/^auvel-export-\d{4}-\d{2}-\d{2}\.json$/);
  const path = await file.path();
  const { readFile } = await import("node:fs/promises");
  const exported = await readFile(path, "utf8");
  expect(exported).toContain(email);
  expect(JSON.parse(exported)).toBeTruthy();

  // Deletion: typed-email confirmation, then the credentials stop working.
  await page.getByRole("button", { name: "Delete my account", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel(/to confirm, type your email/i).fill(email);
  await dialog.getByRole("button", { name: "Permanently delete my account" }).click();
  await page.waitForURL(/\/login/);
  await expect(page.getByText(/your account has been deleted/i)).toBeVisible();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByText(/invalid email or password/i)).toBeVisible();
});
