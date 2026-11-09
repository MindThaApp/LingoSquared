import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmphasizedText } from "./EmphasizedText";

describe("EmphasizedText", () => {
  it("renders each asterisk-delimited span as emphasized target-language text", () => {
    const { container } = render(<p><EmphasizedText text="Use *om te* with *leren*." /></p>);
    expect(screen.getByText("om te")).toHaveClass("target-language-span");
    expect(screen.getByText("leren")).toHaveClass("target-language-span");
    expect(container.querySelectorAll("em")).toHaveLength(2);
    expect(container.textContent).toBe("Use om te with leren.");
  });

  it("leaves plain and unmatched-asterisk text unchanged", () => {
    const { container } = render(<EmphasizedText text="Plain text with *one marker" />);
    expect(container.textContent).toBe("Plain text with *one marker");
    expect(container.querySelector("em")).toBeNull();
  });
});
