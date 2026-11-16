import { test, expect } from "@playwright/test";
import { freshEmail } from "./helpers";
import { stubExternals } from "./journeys.helpers";

const PASSWORD = "e2e-launch-pass-1";
async function noHorizontalOverflow(page: import("@playwright/test").Page) {
  const over = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(over).toBeLessThanOrEqual(1);
}

test("forgot password: request form confirms generically, bogus reset link is rejected", async ({ page }) => {
  await stubExternals(page);
  await page.goto("/login");
  await page.getByRole("link", { name: "Forgot password?" }).click();
  await page.waitForURL(/\/forgot-password/);
  // Same answer for an address that has no account (no account enumeration).
  await page.getByLabel("Email").fill(freshEmail("e2e-nobody"));
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByText(/reset link is on its way/)).toBeVisible();

  await page.goto("/reset-password?token=not-a-real-token");
  await page.getByLabel("New password (at least 8 characters)").fill("e2e-launch-new-pass-2");
  await page.getByLabel("Repeat new password").fill("e2e-launch-new-pass-2");
  await page.getByRole("button", { name: "Set new password" }).click();
  await expect(page.getByText("This reset link is invalid or has expired.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Request a new link" })).toBeVisible();
});

test.describe("mobile viewport (400px)", () => {
  test.use({ viewport: { width: 400, height: 800 }, isMobile: true, hasTouch: true });

  test("login, register, course picker and legal pages do not overflow; PWA manifest is served", async ({ page, request }) => {
    await stubExternals(page);
    for (const path of ["/login", "/register", "/privacy", "/terms"]) {
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await noHorizontalOverflow(page);
    }
    await page.goto("/register");
    await page.getByLabel("Email").fill(freshEmail("e2e-mobile"));
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Register" }).click();
    await page.waitForURL(/\/welcome/);
    await noHorizontalOverflow(page);
    await page.getByRole("button", { name: /English/ }).first().click();
    // Farsi/Dari tiles carry the beta label, and the explanation shows on the target step.
    await expect(page.getByRole("button", { name: /Persian/ }).first().getByTestId("beta-badge")).toBeVisible();
    await expect(page.getByTestId("beta-note")).toBeVisible();
    await noHorizontalOverflow(page);

    const manifest = await request.get("/manifest.webmanifest");
    expect(manifest.ok()).toBe(true);
    const json = await manifest.json();
    expect(json.display).toMatch(/standalone|fullscreen|minimal-ui/);
    expect((await request.get("/sw.js")).ok()).toBe(true);
  });
});
