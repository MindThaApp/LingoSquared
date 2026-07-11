import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Translation } from "./Translation";
import type { Exercise } from "@lingo/shared/api/types";

// Regression test for the ar (true Modern Standard Arabic) virtual-keyboard
// blocker fix (packages/shared/src/lib/scripts.ts, 2026-07-12): the shared
// "arabic" script id/keyboard is Perso-Arabic (fa/prs) and was wrongly used
// for `ar` too -- keheh ک/farsi-yeh ی instead of real Arabic kaf ك/yeh ي,
// making Arabic-typing exercises untypeable/ungradeable. Added because a
// live end-to-end check against a real ar course wasn't possible on the
// shared dev backend this worktree points at (no `ar` Language row or
// content imported -- confirmed via GET /courses, 37 courses, none ar;
// importing one requires admin auth this worker is correctly blocked from
// self-granting). This test drives the REAL component/grading-shape chain
// (no mocking of scripts.ts/VirtualKeyboard) with the exact exercise shape
// and expected answer copied from the real, reviewed content at
// docs/content/realizations/ar/a1_unit01_greetings.yaml lesson02 (the
// shukran/شكرا vocabulary item + exercise07's translation shape,
// answer_language_code: ar) -- grading the real corpus's actual shape, not
// an invented one. Live fa/prs regression + real ar keyboard/direction
// screenshots for this fix are documented in the fix's commit message.
vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

// Verbatim from docs/content/realizations/ar/a1_unit01_greetings.yaml
// lesson02.exercise07.produce_evening: tested_text differs (produce_evening
// is مساء الخير), but exercise07's shape (translation, answer_language_code:
// ar) and lesson02's own teach.shukran vocabulary item (target: شكرا) are
// both real. Constructing the equivalent "translate thank you" exercise
// using the real taught word شكرا (kaf U+0643, not Persian keheh U+06A9).
const arabicTranslation: Exercise = {
  id: "ex-ar-shukran",
  type: "translation",
  order: 7,
  prompt: {
    text_blocks: [{ text: "Translate into Arabic: Thank you.", language_code: "en", direction: "ltr" }],
    answer_language_code: "ar",
  },
};

describe("ar (true MSA) virtual keyboard -- untypeable-Arabic blocker fix", () => {
  it("renders a keyboard with real Arabic-range letters (kaf U+0643, yeh U+064A), not Perso-Arabic", () => {
    const onAnswer = vi.fn();
    render(<Translation exercise={arabicTranslation} onAnswer={onAnswer} disabled={false} />);

    fireEvent.focus(screen.getByRole("textbox"));

    // Real Arabic kaf (U+0643) must be present as its own key.
    const kaf = screen.getByRole("button", { name: "ك" });
    expect(kaf).toBeInTheDocument();
    // Real Arabic yeh (U+064A) must be present as its own key.
    const yeh = screen.getByRole("button", { name: "ي" });
    expect(yeh).toBeInTheDocument();
    // Ta marbuta and alif maqsura -- real MSA letters absent from Perso-Arabic.
    expect(screen.getByRole("button", { name: "ة" })).toBeInTheDocument(); // ة
    expect(screen.getByRole("button", { name: "ى" })).toBeInTheDocument(); // ى

    // The Perso-Arabic-ONLY letters (keheh U+06A9, farsi-yeh U+06CC, pe/che/zhe/gaf)
    // must NOT appear on this keyboard -- confirms it's genuinely the new
    // arabic_msa layout, not a relabeled Perso-Arabic one.
    expect(screen.queryByRole("button", { name: "ک" })).not.toBeInTheDocument(); // ک keheh
    expect(screen.queryByRole("button", { name: "ی" })).not.toBeInTheDocument(); // ی farsi-yeh
    expect(screen.queryByRole("button", { name: "پ" })).not.toBeInTheDocument(); // پ pe
    expect(screen.queryByRole("button", { name: "چ" })).not.toBeInTheDocument(); // چ che
    expect(screen.queryByRole("button", { name: "ژ" })).not.toBeInTheDocument(); // ژ zhe
    expect(screen.queryByRole("button", { name: "گ" })).not.toBeInTheDocument(); // گ gaf

    // RTL direction on the keyboard root.
    const keyboard = kaf.closest(".virtual-keyboard");
    expect(keyboard).toHaveAttribute("dir", "rtl");
  });

  it("typing via the on-screen keys assembles the exact codepoints real ar content expects, and grades correct", () => {
    const onAnswer = vi.fn();
    render(<Translation exercise={arabicTranslation} onAnswer={onAnswer} disabled={false} />);

    fireEvent.focus(screen.getByRole("textbox"));

    // Real word from ar.a1.unit01.lesson02.teach.shukran: شكرا
    // (shin U+0634, kaf U+0643, ra U+0631, alif U+0627) -- exact codepoints
    // from docs/content/realizations/ar/a1_unit01_greetings.yaml line 196.
    const chars = ["ش", "ك", "ر", "ا"]; // ش ك ر ا
    for (const ch of chars) {
      fireEvent.mouseDown(screen.getByRole("button", { name: ch }));
    }

    const input = screen.getByRole("textbox") as HTMLInputElement;
    expect(input.value).toBe("شكرا"); // شكرا, exact codepoint match

    const check = screen.getByRole("button", { name: "common.check" });
    expect(check).toBeEnabled();
    fireEvent.click(check);
    expect(onAnswer).toHaveBeenCalledWith("شكرا");
  });
});
