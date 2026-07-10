import { test, expect } from "@playwright/test";
import { freshEmail, registerAndLand } from "./helpers";

// Covers the account-deletion flow (DELETE /me + ProfilePage's
// "Delete account" section with DeleteAccountConfirm's typed-email
// gate), which landed 2026-07-10 and was verified manually but not by
// this suite.
//
// SAFETY: this test is genuinely destructive within its own scope -- it
// deletes the account it operates on. The account is therefore ALWAYS a
// brand-new throwaway registered inside this very test (freshEmail's
// unique-per-run @example.com convention), never a shared fixture, a
// long-lived test account, or anything another spec might reuse. Do not
// refactor it to reuse an account from another spec, and do not point it
// at any account you care about.
//
// Everything runs as ONE test rather than several: the steps are
// strictly sequential states of the same account's lifecycle (exists ->
// dialog gating -> deleted -> login must fail), and splitting them would
// force one registration per step -- which both multiplies throwaway
// accounts and burns the REGISTER_RATE_LIMIT budget (5/hour/IP on
// default settings) this suite already presses against (see
// e2e/README.md).

const PASSWORD = "e2e-test-pass-1";

test("delete account: typed-email gate, redirect with notice, dead credentials", async ({ page }) => {
  const email = freshEmail("e2e-delete");
  await registerAndLand(page, email, PASSWORD);

  // NavBar renders both a desktop topbar nav and a mobile tabbar nav, so
  // every nav link resolves to two DOM elements -- always .first().
  await page.getByRole("link", { name: "Profile" }).first().click();
  await page.waitForURL(/\/profile/);

  // The danger-zone card's opener. exact:true matters: the dialog's
  // commit button is "Permanently delete my account", which CONTAINS
  // this button's name, and Playwright's default role-name matching is
  // substring -- without exact:true this locator would go ambiguous the
  // moment the dialog opens (e.g. on a retry after a slow first click).
  await page.getByRole("button", { name: "Delete my account", exact: true }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog.getByText("Delete this account forever?")).toBeVisible();

  const confirmButton = dialog.getByRole("button", {
    name: "Permanently delete my account",
  });
  // Label text is "To confirm, type your email address exactly as it
  // appears here: {email}" -- match on the stable prefix, not the
  // per-run email.
  const emailInput = dialog.getByLabel(/to confirm, type your email/i);

  // Gate check 1: empty input -> commit button disabled.
  await expect(confirmButton).toBeDisabled();

  // Gate check 2: a WRONG email -> still disabled. (A prefixed variant
  // of the real address, so it also proves the match isn't a substring
  // check.)
  await emailInput.fill(`wrong-${email}`);
  await expect(confirmButton).toBeDisabled();

  // Gate check 3: the correct email -> enabled.
  await emailInput.fill(email);
  await expect(confirmButton).toBeEnabled();

  // The deletion itself: DELETE /me, then the frontend clears the local
  // session and lands on /login with the one-time sessionStorage-carried
  // notice (see frontend/src/lib/accountDeletedNotice.ts for why it's
  // not route state).
  await confirmButton.click();
  await page.waitForURL(/\/login/);
  await expect(page.getByText(/your account has been deleted/i)).toBeVisible();

  // The deleted account's credentials must now fail with the same
  // honest auth error as any bad login ("Invalid email or password" --
  // the backend treats a deleted user identically to a never-existed
  // one), not a crash, a redirect into the app, or the stale-session
  // message auth.spec.ts guards against.
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.getByText(/invalid email or password/i)).toBeVisible();
  await expect(page.getByText(/session expired/i)).toHaveCount(0);
  await expect(page).toHaveURL(/\/login/);
});
