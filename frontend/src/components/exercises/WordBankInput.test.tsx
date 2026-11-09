import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WordBankInput } from "./WordBankInput";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));

describe("WordBankInput", () => {
  it("tracks duplicate tiles independently and submits them in tap order", () => {
    const onSubmit = vi.fn();
    render(<WordBankInput tiles={["de", "kat", "de"]} direction="ltr" disabled={false} onSubmit={onSubmit} />);
    const bank = screen.getByTestId("word-bank-tiles");

    fireEvent.click(within(bank).getAllByRole("button", { name: "de" })[1]);
    fireEvent.click(within(bank).getByRole("button", { name: "kat" }));
    expect(within(screen.getByTestId("word-bank-answer")).getAllByRole("button").map((tile) => tile.textContent)).toEqual([
      "de",
      "kat",
    ]);
    fireEvent.click(screen.getByRole("button", { name: "common.check" }));
    expect(onSubmit).toHaveBeenCalledWith("de kat");
  });

  it("restores an unplaced tile to its original slot", () => {
    render(<WordBankInput tiles={["one", "two"]} direction="rtl" disabled={false} onSubmit={vi.fn()} />);
    fireEvent.click(screen.getByTestId("word-bank-slot-1"));
    expect(screen.getByTestId("word-bank-slot-1")).toHaveStyle({ visibility: "hidden" });
    fireEvent.click(within(screen.getByTestId("word-bank-answer")).getByRole("button", { name: "two" }));
    expect(screen.getByTestId("word-bank-slot-1")).toBeVisible();
    expect(screen.getByTestId("word-bank-tiles")).toHaveAttribute("dir", "rtl");
  });

  it("disables all interaction when the exercise is locked", () => {
    const onSubmit = vi.fn();
    render(<WordBankInput tiles={["locked"]} direction={undefined} disabled onSubmit={onSubmit} />);
    expect(screen.getByTestId("word-bank-slot-0")).toBeDisabled();
    expect(screen.getByRole("button", { name: "common.check" })).toBeDisabled();
    fireEvent.click(screen.getByTestId("word-bank-slot-0"));
    expect(screen.getByTestId("word-bank-answer")).toBeEmptyDOMElement();
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
