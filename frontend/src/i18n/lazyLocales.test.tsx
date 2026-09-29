import { Suspense, lazy } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import { I18nextProvider, useTranslation } from "react-i18next";
import { describe, expect, it, vi } from "vitest";

// initI18n() drives i18next's global singleton, so each test gets a fresh
// module graph (and therefore a fresh singleton).
async function freshI18n(language: string, cb?: (l: string) => void) {
  vi.resetModules();
  const mod = await import("@lingo/shared/i18n");
  const inst = mod.initI18n({ language, onLanguageChanged: cb });
  return { inst, en: (await import("../../../packages/shared/src/i18n/locales/en.json")).default };
}

describe("lazy locale loading", () => {
  it("changeLanguage loads nl, updates language and fires the callback", async () => {
    const cb = vi.fn();
    const { inst } = await freshI18n("en", cb);
    await new Promise((r) => setTimeout(r, 0));
    const nl = (await import("../../../packages/shared/src/i18n/locales/nl.json")).default as Record<string, unknown>;
    expect(inst.hasResourceBundle("nl", "translation")).toBe(false);
    await inst.changeLanguage("nl");
    expect(inst.language).toBe("nl");
    expect(cb).toHaveBeenCalledWith("nl");
    const key = "common.loading";
    const expected = (nl.common as Record<string, string>).loading;
    expect(inst.t(key)).toBe(expected);
    expect(expected).not.toBe(key);
  });

  it("loads fa and keeps RTL callback semantics", async () => {
    const cb = vi.fn();
    const { inst } = await freshI18n("en", cb);
    await inst.changeLanguage("fa");
    expect(cb).toHaveBeenLastCalledWith("fa");
    const fa = (await import("../../../packages/shared/src/i18n/locales/fa.json")).default as Record<string, unknown>;
    expect(inst.t("common.loading")).toBe((fa.common as Record<string, string>).loading);
  });

  it("unknown language falls back to en without crashing", async () => {
    const { inst, en } = await freshI18n("en");
    await inst.changeLanguage("xx");
    expect(inst.t("common.loading")).toBe((en as { common: { loading: string } }).common.loading);
  });

  it("non-en initial language never renders raw keys", async () => {
    const { inst } = await freshI18n("nl");
    const nl = (await import("../../../packages/shared/src/i18n/locales/nl.json")).default as Record<string, unknown>;
    const expected = (nl.common as Record<string, string>).loading;
    const seen: string[] = [];
    function Probe() {
      const { t } = useTranslation();
      const v = t("common.loading");
      seen.push(v);
      return <p>{v}</p>;
    }
    render(
      <I18nextProvider i18n={inst}>
        <Suspense fallback={<span>fallback</span>}>
          <Probe />
        </Suspense>
      </I18nextProvider>,
    );
    expect(await screen.findByText(expected)).toBeTruthy();
    expect(seen).not.toContain("common.loading");
  });
});

describe("lazy route", () => {
  it("shows the Suspense fallback, then the lazy page", async () => {
    const Page = lazy(async () => {
      await new Promise((r) => setTimeout(r, 20));
      return { default: () => <h1>lazy page content</h1> };
    });
    render(
      <MemoryRouter initialEntries={["/x"]}>
        <Suspense fallback={<div role="status">Loading…</div>}>
          <Routes>
            <Route path="/x" element={<Page />} />
          </Routes>
        </Suspense>
      </MemoryRouter>,
    );
    expect(screen.getByRole("status")).toBeTruthy();
    expect(await screen.findByText("lazy page content")).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
  });
});
