import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChoiceOptions } from "./ChoiceOptions";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe("ChoiceOptions", () => {
  it("exposes radio semantics, metadata, initial focus, and the selected value", () => {
    const onSelect = vi.fn();
    render(
      <ChoiceOptions
        options={["uno", "dos"]}
        selected="dos"
        onSelect={onSelect}
        disabled={false}
        correctOption={null}
        direction="rtl"
        lang="es"
      />,
    );
    const group = screen.getByRole("radiogroup", { name: "exercise.options_label" });
    expect(group).toHaveAttribute("dir", "rtl");
    expect(group).toHaveAttribute("lang", "es");
    expect(screen.getByRole("radio", { name: "uno" })).toHaveFocus();
    expect(screen.getByRole("radio", { name: "dos" })).toHaveAttribute("aria-checked", "true");
    fireEvent.click(screen.getByRole("radio", { name: "uno" }));
    expect(onSelect).toHaveBeenCalledWith("uno");
  });

  it("prevents selection when disabled", () => {
    const onSelect = vi.fn();
    render(<ChoiceOptions options={["a", "b"]} selected={null} onSelect={onSelect} disabled correctOption={null} />);
    fireEvent.click(screen.getByRole("radio", { name: "a" }));
    expect(onSelect).not.toHaveBeenCalled();
    expect(screen.getAllByRole("radio")).toEqual(expect.arrayContaining([
      expect.objectContaining({ disabled: true }),
    ]));
  });

  it("adds accessible correct and incorrect markers after grading", () => {
    render(
      <ChoiceOptions
        options={["right", "wrong", "other"]}
        selected="wrong"
        onSelect={() => {}}
        disabled
        gradedResult={{ correct: false, correctResponse: "right" }}
        correctOption="right"
      />,
    );
    expect(screen.getByRole("radio", { name: /right.*exercise\.option_correct/ })).toHaveClass("correct");
    expect(screen.getByRole("radio", { name: /wrong.*exercise\.option_incorrect/ })).toHaveClass("incorrect");
    expect(screen.getByRole("radio", { name: "other" })).not.toHaveClass("correct", "incorrect");
  });
});
