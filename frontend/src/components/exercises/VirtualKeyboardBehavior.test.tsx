import "@testing-library/jest-dom/vitest";
import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Translation } from "./Translation";
import { FillInBlank } from "./FillInBlank";
import { WritingPrompt } from "./WritingPrompt";
import type { Exercise } from "@lingo/shared/api/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const arabic: Exercise = {
  id: "ex-ar",
  type: "translation",
  order: 1,
  prompt: {
    text_blocks: [{ text: "Translate into Arabic: Thank you.", language_code: "en", direction: "ltr" }],
    answer_language_code: "ar",
  },
};

const dutch: Exercise = {
  id: "ex-nl",
  type: "fill_in_blank",
  order: 1,
  prompt: {
    text_blocks: [{ text: "Ik kom ___ België.", language_code: "nl", direction: "ltr" }],
    answer_language_code: "nl",
  },
};

function typeInto(input: HTMLInputElement, value: string, caret: number, end = caret) {
  fireEvent.change(input, { target: { value } });
  input.setSelectionRange(caret, end);
}

describe("virtual keyboard: caret-aware editing", () => {
  it("inserts mid-string at the caret and replaces a selection", () => {
    render(<Translation exercise={arabic} onAnswer={vi.fn()} disabled={false} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.focus(input);
    typeInto(input, "شر", 1);
    fireEvent.click(screen.getByRole("button", { name: "ك" }));
    expect(input.value).toBe("شكر");
    expect(input.selectionStart).toBe(2);

    typeInto(input, "شكر", 0, 3);
    fireEvent.click(screen.getByRole("button", { name: "ا" }));
    expect(input.value).toBe("ا");
  });

  it("backspace deletes the char before the caret, not the last char", () => {
    render(<Translation exercise={arabic} onAnswer={vi.fn()} disabled={false} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.focus(input);
    typeInto(input, "شكرا", 2);
    fireEvent.click(screen.getByRole("button", { name: "⌫" }));
    expect(input.value).toBe("شرا");
    expect(input.selectionStart).toBe(1);
  });

  it("a mousedown on a key only prevents default; the action fires on click once", () => {
    render(<Translation exercise={arabic} onAnswer={vi.fn()} disabled={false} />);
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.focus(input);
    const key = screen.getByRole("button", { name: "ك" });
    expect(fireEvent.mouseDown(key)).toBe(false); // default prevented
    expect(input.value).toBe("");
    fireEvent.click(key);
    expect(input.value).toBe("ك");
  });
});

describe("virtual keyboard: focus / inputMode / submit", () => {
  it("keeps the keyboard mounted when focus moves onto a key, closes when it leaves", () => {
    render(<Translation exercise={arabic} onAnswer={vi.fn()} disabled={false} />);
    const input = screen.getByRole("textbox");
    fireEvent.focus(input);
    const key = screen.getByRole("button", { name: "ك" });
    fireEvent.blur(input, { relatedTarget: key });
    expect(screen.getByRole("button", { name: "ك" })).toBeInTheDocument();
    fireEvent.blur(key, { relatedTarget: document.body });
    expect(screen.queryByRole("button", { name: "ك" })).not.toBeInTheDocument();
  });

  it("sets inputMode=none while the keyboard is in use and restores it on dismiss", () => {
    render(<Translation exercise={arabic} onAnswer={vi.fn()} disabled={false} />);
    const input = screen.getByRole("textbox");
    fireEvent.focus(input);
    expect(input).toHaveAttribute("inputmode", "none");
    fireEvent.click(screen.getByRole("button", { name: "keyboard.use_device_keyboard" }));
    expect(input).not.toHaveAttribute("inputmode", "none");
  });

  it("does not set inputMode for latin scripts", () => {
    render(<FillInBlank exercise={dutch} onAnswer={vi.fn()} disabled={false} />);
    expect(screen.getByRole("textbox")).not.toHaveAttribute("inputmode");
  });

  it("one click on Check with the keyboard open submits", () => {
    const onAnswer = vi.fn();
    render(<Translation exercise={arabic} onAnswer={onAnswer} disabled={false} />);
    const input = screen.getByRole("textbox");
    fireEvent.focus(input);
    fireEvent.click(screen.getByRole("button", { name: "ك" }));
    const check = screen.getByRole("button", { name: "common.check" });
    expect(fireEvent.mouseDown(check)).toBe(false); // input keeps focus, no layout shift
    expect(screen.getByRole("button", { name: "ك" })).toBeInTheDocument();
    fireEvent.click(check);
    expect(onAnswer).toHaveBeenCalledTimes(1);
    expect(onAnswer).toHaveBeenCalledWith("ك");
  });
});

describe("free-text exercises: form submit and autofocus", () => {
  it("auto-focuses the input on mount, but not when disabled", () => {
    const { unmount } = render(<FillInBlank exercise={dutch} onAnswer={vi.fn()} disabled={false} />);
    expect(screen.getByRole("textbox")).toHaveFocus();
    unmount();
    render(<FillInBlank exercise={dutch} onAnswer={vi.fn()} disabled />);
    expect(screen.getByRole("textbox")).not.toHaveFocus();
  });

  it("submitting the form (Enter) sends the trimmed answer; empty/disabled do not", () => {
    const onAnswer = vi.fn();
    render(<FillInBlank exercise={dutch} onAnswer={onAnswer} disabled={false} />);
    const input = screen.getByRole("textbox");
    fireEvent.submit(input);
    expect(onAnswer).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { value: " uit " } });
    fireEvent.submit(input);
    expect(onAnswer).toHaveBeenCalledWith("uit");
  });

  it("WritingPrompt uses a form with a submit button and a textarea", () => {
    const onAnswer = vi.fn();
    render(
      <WritingPrompt
        exercise={{ ...dutch, type: "writing_prompt" } as Exercise}
        onAnswer={onAnswer}
        disabled={false}
      />,
    );
    const ta = screen.getByRole("textbox");
    expect(ta.tagName).toBe("TEXTAREA");
    fireEvent.change(ta, { target: { value: "hallo\nwereld" } });
    fireEvent.submit(ta);
    expect(onAnswer).toHaveBeenCalledWith("hallo\nwereld");
  });
});
