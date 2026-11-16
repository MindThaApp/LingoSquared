import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type { TextBlock } from "@lingo/shared/api/types";
import { TextBlockView } from "./TextBlock";
import { TargetText } from "./TargetText";
import { TranslitToggle } from "./TranslitToggle";
import { TranslitStateProvider } from "./translitContext";
import { ChoiceOptions } from "./exercises/ChoiceOptions";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, o?: { text?: string }) => (o?.text ? `${key}:${o.text}` : key),
    i18n: { language: "en" },
  }),
}));
vi.mock("../api/tts", () => ({ speak: vi.fn() }));

const on = { show: true, available: true, setShow: () => {} };
const off = { show: false, available: true, setShow: () => {} };

const fa: TextBlock = { text: "سلام", language_code: "fa", direction: "rtl", translit: "salâm" };
const ru: TextBlock = { text: "Привет", language_code: "ru", direction: "ltr", translit: "Privet" };

describe("TargetText / pronunciation line", () => {
  it("renders an LTR, labelled romanization line under RTL text when on", () => {
    const { container } = render(
      <TranslitStateProvider value={on}>
        <TextBlockView block={fa} />
      </TranslitStateProvider>,
    );
    const native = container.querySelector('.text-block[lang="fa"]')!;
    expect(native.getAttribute("dir")).toBe("rtl");
    expect(native.textContent).toBe("سلام");
    const line = container.querySelector(".translit")!;
    expect(line.getAttribute("dir")).toBe("ltr");
    expect(line.getAttribute("aria-label")).toBe("translit.aria:salâm");
    expect(line.textContent).toContain("salâm");
    // the romanization is never nested inside the RTL run
    expect(native.contains(line)).toBe(false);
  });

  it("renders nothing extra when off or when the block has no translit", () => {
    const { container, rerender } = render(
      <TranslitStateProvider value={off}>
        <TextBlockView block={ru} />
      </TranslitStateProvider>,
    );
    expect(container.querySelector(".translit")).toBeNull();
    rerender(
      <TranslitStateProvider value={on}>
        <TextBlockView block={{ ...ru, translit: undefined }} />
      </TranslitStateProvider>,
    );
    expect(container.querySelector(".translit")).toBeNull();
    expect(container.querySelector(".target-text")).toBeNull();
  });

  it("marks machine-drafted languages (fa/prs/ar) with a beta marker but not ru/hi", () => {
    const { container, rerender } = render(
      <TranslitStateProvider value={on}>
        <TextBlockView block={fa} />
      </TranslitStateProvider>,
    );
    expect(container.querySelector(".translit-beta")).not.toBeNull();
    rerender(
      <TranslitStateProvider value={on}>
        <TextBlockView block={ru} />
      </TranslitStateProvider>,
    );
    expect(container.querySelector(".translit-beta")).toBeNull();
    expect(screen.getByText("Privet")).toBeTruthy();
  });

  it("a reviewed romanization carries no beta marker even for fa/prs/ar", () => {
    const { container } = render(
      <TranslitStateProvider value={on}>
        <TextBlockView block={{ ...fa, translit_reviewed: true }} />
      </TranslitStateProvider>,
    );
    expect(container.querySelector(".translit")).not.toBeNull();
    expect(container.querySelector(".translit-beta")).toBeNull();
  });

  it("bare mode keeps option text unwrapped when nothing extra shows", () => {
    const { container } = render(
      <TranslitStateProvider value={off}>
        <TargetText text="Привет" lang="ru" bare translit="Privet" />
      </TranslitStateProvider>,
    );
    expect(container.innerHTML).toBe("Привет");
  });

  it("choice options show their romanization from translit_map", () => {
    const { container } = render(
      <TranslitStateProvider value={on}>
        <ChoiceOptions
          options={["Привет", "Пока"]}
          selected={null}
          onSelect={() => {}}
          disabled={false}
          correctOption={null}
          direction="ltr"
          lang="ru"
          translitMap={{ Привет: "Privet" }}
        />
      </TranslitStateProvider>,
    );
    const lines = container.querySelectorAll(".translit");
    expect(lines).toHaveLength(1);
    expect(lines[0].textContent).toContain("Privet");
  });
});

describe("TranslitToggle", () => {
  it("toggles through the context and hides for unsupported languages", () => {
    const setShow = vi.fn();
    const { container, rerender } = render(
      <TranslitStateProvider value={{ show: false, available: true, setShow }}>
        <TranslitToggle />
      </TranslitStateProvider>,
    );
    const btn = screen.getByRole("button");
    expect(btn.getAttribute("aria-pressed")).toBe("false");
    fireEvent.click(btn);
    expect(setShow).toHaveBeenCalledWith(true);
    rerender(
      <TranslitStateProvider value={{ show: false, available: false, setShow }}>
        <TranslitToggle />
      </TranslitStateProvider>,
    );
    expect(container.querySelector("button")).toBeNull();
  });
});
