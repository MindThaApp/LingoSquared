import { defineConfig, devices } from "@playwright/test";

// Dedicated port. Must be one already listed in the backend's
// CORS_ORIGINS (checked: 5173-5176 are whitelisted) or every request
// gets silently CORS-blocked -- this exact failure mode is documented
// in CLAUDE.md as a "confusing CORS false-lead." 5173/5174 are the ones
// a human commonly has open for manual testing per CLAUDE.md, so this
// suite deliberately uses 5175 to avoid fighting an interactive session
// for the port while staying inside the allowlist.
const E2E_PORT = 5175;
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? `http://localhost:${E2E_PORT}`;
// Optional: run against an already-installed Chromium binary instead of the
// one matching this @playwright/test version (e.g. a sandbox with a
// preinstalled browser and no network for `playwright install`). Unset =
// Playwright's own managed browser, as before.
const CHROMIUM_PATH = process.env.PLAYWRIGHT_CHROMIUM_PATH;

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false, // tests register real users against a shared backend; keep serial
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  timeout: 30_000,
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    ...(CHROMIUM_PATH ? { launchOptions: { executablePath: CHROMIUM_PATH } } : {}),
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  // Only manages the frontend dev server. The backend (Docker stack,
  // seeded content) is a precondition -- see e2e/README.md -- because
  // provisioning it belongs to whichever session owns the Docker stack
  // per docs/SONNET_BUILD_PROMPT_UPGRADES.md's ownership map, not to
  // this test runner.
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : {
        command: `npm run dev -- --port ${E2E_PORT} --strictPort`,
        cwd: "../frontend",
        url: BASE_URL,
        reuseExistingServer: true,
        timeout: 30_000,
      },
});
