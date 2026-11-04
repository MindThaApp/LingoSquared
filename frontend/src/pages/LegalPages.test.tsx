import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import en from "../../../packages/shared/src/i18n/locales/en.json";
import { PrivacyPolicyPage } from "./PrivacyPolicyPage";
import { TermsOfServicePage } from "./TermsOfServicePage";

let language = "en";
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (k: string) => k, i18n: { language } }),
}));

afterEach(cleanup);

describe.each([
  ["Privacy", PrivacyPolicyPage],
  ["Terms", TermsOfServicePage],
])("%s page", (_n, Page) => {
  const view = () => render(<MemoryRouter><Page /></MemoryRouter>);

  it("shows no notice in English", () => {
    language = "en";
    view();
    expect(screen.queryByTestId("legal-english-only-notice")).toBeNull();
  });

  it.each(["fa", "ar", "nl", "pt-BR"])("shows the notice for %s", (l) => {
    language = l;
    view();
    expect(screen.getByTestId("legal-english-only-notice")).toHaveTextContent("legal.english_only_notice");
  });

  it("marks the body lang=en dir=ltr", () => {
    language = "fa";
    view();
    const body = screen.getByTestId("legal-body");
    expect(body).toHaveAttribute("lang", "en");
    expect(body).toHaveAttribute("dir", "ltr");
  });
});

it("en locale defines the notice", () => {
  expect(en.legal.english_only_notice).toMatch(/English only/);
});
