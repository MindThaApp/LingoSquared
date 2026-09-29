import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QuitConfirm } from "./QuitConfirm";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe("QuitConfirm", () => {
  it("moves initial focus to the keep-going button and labels the dialog", () => {
    render(<QuitConfirm message="Really quit?" onKeepGoing={() => {}} onQuit={() => {}} />);
    expect(screen.getByText("common.keep_going")).toHaveFocus();
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleName("Really quit?");
  });

  it("Escape calls the cancel handler", () => {
    const onKeepGoing = vi.fn();
    const onQuit = vi.fn();
    render(<QuitConfirm message="Really quit?" onKeepGoing={onKeepGoing} onQuit={onQuit} />);
    fireEvent.keyDown(screen.getByText("common.keep_going"), { key: "Escape" });
    expect(onKeepGoing).toHaveBeenCalledTimes(1);
    expect(onQuit).not.toHaveBeenCalled();
  });

  it("traps Tab within the dialog", () => {
    render(<QuitConfirm message="Really quit?" onKeepGoing={() => {}} onQuit={() => {}} />);
    const quit = screen.getByText("common.quit");
    quit.focus();
    fireEvent.keyDown(quit, { key: "Tab" });
    expect(screen.getByText("common.keep_going")).toHaveFocus();
  });
});
