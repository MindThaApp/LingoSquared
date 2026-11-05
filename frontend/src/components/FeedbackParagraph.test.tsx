import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { FeedbackParagraph } from "./FeedbackParagraph";

const blocks = (...codes: string[]) => codes.map((language_code) => ({ language_code, text: "x", direction: "ltr" as const }));

describe("FeedbackParagraph", () => {
  it("is rtl when the prompt's source-language block is Persian/Arabic/Dari", () => {
    for (const code of ["fa", "ar", "prs"]) {
      const { unmount } = render(<FeedbackParagraph text={`note ${code}`} prompt={{ text_blocks: blocks("nl", code), answer_language_code: "nl" }} />);
      expect(screen.getByText(`note ${code}`).closest("p")).toHaveAttribute("dir", "rtl");
      unmount();
    }
  });

  it("is ltr for an LTR source language and auto without a gloss block or prompt", () => {
    const { unmount } = render(<FeedbackParagraph text="a" prompt={{ text_blocks: blocks("fa", "en"), answer_language_code: "fa" }} />);
    expect(screen.getByText("a").closest("p")).toHaveAttribute("dir", "ltr");
    unmount();
    const r2 = render(<FeedbackParagraph text="b" prompt={{ text_blocks: blocks("nl"), answer_language_code: "nl" }} />);
    expect(screen.getByText("b").closest("p")).toHaveAttribute("dir", "auto");
    r2.unmount();
    render(<FeedbackParagraph text="c" />);
    expect(screen.getByText("c").closest("p")).toHaveAttribute("dir", "auto");
  });

  it("keeps emphasis markup and caller style", () => {
    render(<FeedbackParagraph text="use *huis* here" style={{ margin: 3 }} />);
    expect(screen.getByText("huis").tagName).toBe("EM");
    expect(screen.getByText("huis").closest("p")).toHaveStyle({ margin: "3px", fontWeight: "400" });
  });
});
