import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LanguageSwitcher } from "./LanguageSwitcher";

const changeLanguage = vi.fn();
let language = "en";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language, changeLanguage },
  }),
}));

beforeEach(() => {
  language = "en";
  changeLanguage.mockReset();
});

describe("LanguageSwitcher", () => {
  it("shows native language names and reflects the current UI language", () => {
    language = "fa";
    render(<LanguageSwitcher />);
    const select = screen.getByRole("combobox", { name: "language_switcher.aria_label" });
    expect(select).toHaveValue("fa");
    expect(screen.getByRole("option", { name: "فارسی" })).toHaveAttribute("lang", "fa");
    expect(screen.getByRole("option", { name: "English" })).toHaveAttribute("lang", "en");
    expect(screen.getAllByRole("option")).toHaveLength(15);
  });

  it("requests a language change with the selected code", () => {
    render(<LanguageSwitcher />);
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "ja" } });
    expect(changeLanguage).toHaveBeenCalledOnce();
    expect(changeLanguage).toHaveBeenCalledWith("ja");
  });
});
