import { createRef } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { VirtualKeyboard } from "./VirtualKeyboard";

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));

function renderKeyboard(script: "arabic" | "devanagari" | "latin" = "arabic") {
  const callbacks = { onInsert: vi.fn(), onBackspace: vi.fn(), onDismiss: vi.fn(), onContainerBlur: vi.fn() };
  const containerRef = createRef<HTMLDivElement>();
  const view = render(<VirtualKeyboard script={script} containerRef={containerRef} {...callbacks} />);
  return { ...callbacks, containerRef, ...view };
}

describe("VirtualKeyboard", () => {
  it("invokes character, space, backspace, and dismiss callbacks", () => {
    const callbacks = renderKeyboard();
    fireEvent.click(screen.getByRole("button", { name: "ا" }));
    fireEvent.click(screen.getByRole("button", { name: "keyboard.space" }));
    fireEvent.click(screen.getByRole("button", { name: "keyboard.backspace" }));
    fireEvent.click(screen.getByRole("button", { name: "keyboard.use_device_keyboard" }));
    expect(callbacks.onInsert.mock.calls.map(([value]) => value)).toEqual(["ا", " "]);
    expect(callbacks.onBackspace).toHaveBeenCalledOnce();
    expect(callbacks.onDismiss).toHaveBeenCalledOnce();
  });

  it("toggles the Arabic symbols layer and preserves its left-to-right direction", () => {
    const { container } = renderKeyboard();
    fireEvent.click(screen.getByRole("button", { name: "۱۲۳" }));
    expect(screen.getByRole("button", { name: "۱" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "ا" })).not.toBeInTheDocument();
    expect(container.querySelector(".virtual-keyboard-row[dir='ltr']")).not.toBeNull();
    expect(screen.getByRole("button", { name: "الف‌ب" })).toHaveAttribute("title", "keyboard.show_letters");
  });

  it("forwards the container ref and blur event, and returns null for Latin", () => {
    const callbacks = renderKeyboard("devanagari");
    expect(callbacks.containerRef.current).toHaveClass("virtual-keyboard");
    fireEvent.blur(callbacks.containerRef.current!, { relatedTarget: document.body });
    expect(callbacks.onContainerBlur).toHaveBeenCalledOnce();
    callbacks.unmount();
    const { container } = renderKeyboard("latin");
    expect(container).toBeEmptyDOMElement();
  });
});
