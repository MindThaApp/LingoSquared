// Shared Vitest setup (referenced from vitest.config.ts's setupFiles).
//
// React Testing Library only auto-registers its per-test cleanup when a
// global `afterEach` exists at import time (i.e. vitest's `globals: true`,
// which this harness deliberately doesn't use). Without this hook, every
// render() in a multi-test file accumulates in the same jsdom document and
// role/name queries start matching stale elements from earlier tests —
// found the moment the first multi-test component file was added
// (2026-07-10); the two original single-test files just never tripped it.
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

afterEach(() => {
  cleanup();
});
