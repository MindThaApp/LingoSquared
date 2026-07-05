import { test, expect } from "@playwright/test";
import { freshEmail, registerAndLand } from "./helpers";

// Covers the flow CLAUDE.md/BUILD_LOG.md records as manually verified
// multiple times this project (register -> home dashboard; logout
// button was once accidentally deleted and only caught by a live
// click-through) -- turning that manual check into a repeatable one.

test("register -> lands on home dashboard with nav visible", async ({ page }) => {
  const email = freshEmail("e2e-register");
  await registerAndLand(page, email);

  // NavBar renders both a desktop topbar nav and a mobile tabbar nav, so
  // every nav link resolves to two DOM elements -- always .first().
  await expect(page.getByRole("link", { name: "Lingo²" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Home" }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Learn" }).first()).toBeVisible();
});

test("logout returns to login page and blocks protected routes", async ({ page }) => {
  const email = freshEmail("e2e-logout");
  await registerAndLand(page, email);

  await page.getByRole("link", { name: "Profile" }).first().click();
  await page.getByRole("button", { name: /log out/i }).click();
  await page.waitForURL(/\/login/);

  // Protected route should bounce back to login once logged out.
  await page.goto("/");
  await page.waitForURL(/\/login/);
});

test("login with wrong password shows a real error, not a stale-session message", async ({ page }) => {
  const email = freshEmail("e2e-badpw");
  await registerAndLand(page, email);
  await page.getByRole("link", { name: "Profile" }).first().click();
  await page.getByRole("button", { name: /log out/i }).click();
  await page.waitForURL(/\/login/);

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("definitely-wrong");
  await page.getByRole("button", { name: "Log in" }).click();

  // Regression guard for the documented bug: the global 401 handler
  // once showed "Session expired" for a failed /auth/login instead of
  // the server's real "Invalid email or password".
  await expect(page.getByText(/invalid email or password/i)).toBeVisible();
  await expect(page.getByText(/session expired/i)).toHaveCount(0);
});

test("guest login creates a working session", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "Continue as guest" }).click();
  await page.getByLabel("Pick a name").fill("E2E Guest");
  await page.getByRole("button", { name: "Start guest session" }).click();
  await page.waitForURL("/");
  await expect(page.getByRole("link", { name: "Home" }).first()).toBeVisible();
});
