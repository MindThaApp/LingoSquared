import { defineConfig } from "vitest/config";

// Minimal Vitest harness (first-ever frontend unit tests, 2026-07-10).
// Deliberately no @vitejs/plugin-react here: Vitest's own esbuild pass
// already compiles .tsx via tsconfig's `jsx: "react-jsx"`, and the plugin
// only adds fast-refresh, which tests don't need — keeping it out also
// avoids tying the test runner to the app's exact Vite major version.
export default defineConfig({
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    // Registers React Testing Library's afterEach cleanup (and jest-dom's
    // matchers) once for every test file — without it, renders from
    // earlier tests in the same file leak into later ones' queries. See
    // src/test/setup.ts for the full why.
    setupFiles: ["src/test/setup.ts"],
  },
});
