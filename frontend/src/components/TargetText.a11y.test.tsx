import "@testing-library/jest-dom/vitest";
import { describe, it, vi } from "vitest";
import { render } from "@testing-library/react";
import { expectNoSeriousA11yViolations } from "../test/axe";
import { TeachingCardView } from "./TeachingCardView";
import { ChoiceOptions } from "./exercises/ChoiceOptions";
import { TranslitStateProvider } from "./translitContext";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, o?: { text?: string }) => (o?.text ? `Pronunciation: ${o.text}` : key),
    i18n: { language: "en" },
  }),
}));
vi.mock("../api/tts", () => ({ speak: vi.fn() }));

describe("pronunciation line accessibility", () => {
  it("teaching card with RTL text + romanization has no serious violations", async () => {
    const { container } = render(
      <TranslitStateProvider value={{ show: true, available: true, setShow: () => {} }}>
        <TeachingCardView
          card={{
            kind: "vocabulary",
            title: "Hello",
            text_blocks: [
              { text: "سلام", language_code: "fa", direction: "rtl", translit: "salâm" },
              { text: "hello", language_code: "en", direction: "ltr" },
            ],
          }}
        />
      </TranslitStateProvider>,
    );
    await expectNoSeriousA11yViolations(container);
  });

  it("choice options with romanization have no serious violations", async () => {
    const { container } = render(
      <TranslitStateProvider value={{ show: true, available: true, setShow: () => {} }}>
        <ChoiceOptions
          options={["سلام", "خداحافظ"]}
          selected={null}
          onSelect={() => {}}
          disabled={false}
          correctOption={null}
          direction="rtl"
          lang="fa"
          translitMap={{ سلام: "salâm", خداحافظ: "khodâ hâfez" }}
        />
      </TranslitStateProvider>,
    );
    await expectNoSeriousA11yViolations(container);
  });
});
