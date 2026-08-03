import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import type { TextBlock } from "@lingo/shared/api/types";
import { GlossableText, tokenizeForGloss } from "./GlossableText";

const nlBlock: TextBlock = {
  text: "Kasia verandert van baan.",
  language_code: "nl",
  direction: "ltr",
};

const glosses = { verandert: "changes", baan: "job" };

describe("tokenizeForGloss", () => {
  it("keeps words and separators so the passage renders verbatim", () => {
    const segments = tokenizeForGloss("Kasia verandert van baan.");
    expect(segments.map((s) => s.text).join("")).toBe("Kasia verandert van baan.");
    // Words are flagged, whitespace/punctuation are not.
    expect(segments.filter((s) => s.isWord).map((s) => s.text)).toEqual([
      "Kasia",
      "verandert",
      "van",
      "baan",
    ]);
  });

  it("does not crash on whitespace-less scripts (treats a Han run as one word)", () => {
    const segments = tokenizeForGloss("我喜欢读书。");
    expect(segments.map((s) => s.text).join("")).toBe("我喜欢读书。");
    expect(segments.some((s) => s.isWord)).toBe(true);
  });
});

describe("GlossableText", () => {
  it("makes only glossed tokens tappable and shows the gloss on tap", () => {
    render(<GlossableText block={nlBlock} glosses={glosses} />);

    // Two glossed tokens -> two buttons; "Kasia"/"van" are plain text.
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(2);
    expect(buttons.map((b) => b.textContent)).toEqual(["verandert", "baan"]);
    expect(screen.getByText("Kasia")).toBeInTheDocument();

    // No popover until a word is tapped.
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();

    fireEvent.click(buttons[0]);
    expect(screen.getByRole("tooltip")).toHaveTextContent("changes");

    // Tapping the same word again dismisses the popover.
    fireEvent.click(buttons[0]);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();

    // Escape dismisses too.
    fireEvent.click(buttons[1]);
    expect(screen.getByRole("tooltip")).toHaveTextContent("job");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("honors the block direction for RTL passages", () => {
    const faBlock: TextBlock = {
      text: "کاسیا شغلش را عوض می‌کند",
      language_code: "fa",
      direction: "rtl",
    };
    const { container } = render(
      <GlossableText block={faBlock} glosses={{ عوض: "changes" }} />,
    );
    const root = container.querySelector(".glossable-text");
    expect(root).toHaveAttribute("dir", "rtl");
    expect(root).toHaveAttribute("lang", "fa");
    // The gloss key present in the passage is tappable.
    expect(screen.getByRole("button", { name: "عوض" })).toBeInTheDocument();
  });
});
