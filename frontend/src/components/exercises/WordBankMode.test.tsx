import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { Translation } from "./Translation";
import type { Exercise } from "@lingo/shared/api/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

let mockUserId: string | null = "user-a";
vi.mock("../../auth/AuthContext", () => ({
  useAuth: () => ({ user: mockUserId ? { id: mockUserId } : null }),
}));

function ex(id: string, text: string, lang: string, extra: Record<string, unknown> = {}): Exercise {
  return {
    id,
    type: "translation",
    order: 1,
    prompt: { text_blocks: [{ text, language_code: lang, direction: "ltr" }], answer_language_code: "nl", ...extra },
  };
}

// A server-provided word_bank (answer tokens + a distractor) makes the bank available.
const current = ex("cur", "the man and the woman", "en", { word_bank: ["de", "man", "en", "de", "vrouw", "kat"] });
const noBank = ex("nb", "the man and the woman", "en");
const siblings = [ex("s1", "de man", "nl"), ex("s2", "en de vrouw", "nl")];
const lessonExercises = [current, ...siblings];

function renderTr(level: "A1" | "B1" | null, onAnswer = vi.fn(), exercise = current, lex = lessonExercises) {
  render(
    <Translation exercise={exercise} onAnswer={onAnswer} disabled={false} courseLevel={level} lessonExercises={lex} />,
  );
  return onAnswer;
}

function tileButtons() {
  const bank = screen.getByTestId("word-bank-tiles");
  return within(bank).getAllByRole("button", { hidden: true });
}

beforeEach(() => {
  localStorage.clear();
  mockUserId = "user-a";
});

describe("word bank mode", () => {
  it("A1 defaults to the bank; B1 and unknown level default to typing", () => {
    renderTr("A1");
    expect(screen.getByTestId("word-bank-tiles")).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  it("B1 defaults to typing (with a Use word bank toggle)", () => {
    renderTr("B1");
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "exercise.use_word_bank" })).toBeInTheDocument();
  });

  it("prompt WITHOUT word_bank and no answerHint at A1 -> typing, no toggle", () => {
    renderTr("A1", vi.fn(), noBank);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "exercise.use_word_bank" })).toBeNull();
    expect(screen.queryByTestId("word-bank-tiles")).toBeNull();
  });

  it("word_bank present but no course level (review/practice) -> typing", () => {
    renderTr(null);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("no level -> plain typing, no toggle", () => {
    renderTr(null);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "exercise.use_word_bank" })).toBeNull();
  });

  it("submits the space-joined tapped tiles as one string", () => {
    const onAnswer = renderTr("A1");
    const check = screen.getByRole("button", { name: "common.check" });
    expect(check).toBeDisabled();
    for (const word of ["de", "man"]) {
      fireEvent.click(within(screen.getByTestId("word-bank-tiles")).getAllByRole("button", { name: word })[0]);
    }
    fireEvent.click(check);
    expect(onAnswer).toHaveBeenCalledTimes(1);
    const arg = onAnswer.mock.calls[0][0];
    expect(typeof arg).toBe("string");
    expect(arg).toBe("de man");
  });

  it("a removed tile returns to its original slot; positions never shift", () => {
    renderTr("A1");
    const before = tileButtons().map((b) => b.textContent);
    const answerRow = screen.getByTestId("word-bank-answer");
    fireEvent.click(screen.getByTestId("word-bank-slot-1"));
    expect(within(answerRow).getAllByRole("button")).toHaveLength(1);
    expect(tileButtons().map((b) => b.textContent)).toEqual(before); // placeholder keeps width/position
    expect(screen.getByTestId("word-bank-slot-1")).toBeDisabled();
    fireEvent.click(within(answerRow).getAllByRole("button")[0]);
    expect(within(answerRow).queryAllByRole("button")).toHaveLength(0);
    expect(screen.getByTestId("word-bank-slot-1")).toBeEnabled();
    expect(tileButtons().map((b) => b.textContent)).toEqual(before);
  });

  it("duplicate-text tiles are tracked by index (bank hint path with two 'de')", () => {
    const onAnswer = vi.fn();
    render(
      <Translation
        exercise={noBank}
        onAnswer={onAnswer}
        disabled={false}
        courseLevel="A1"
        lessonExercises={lessonExercises}
        answerHint="de man de vrouw"
      />,
    );
    const de = within(screen.getByTestId("word-bank-tiles")).getAllByRole("button", { name: "de" });
    expect(de).toHaveLength(2);
    fireEvent.click(de[0]);
    // The other "de" tile must still be tappable.
    const remaining = within(screen.getByTestId("word-bank-tiles")).getAllByRole("button", { name: "de" });
    expect(remaining).toHaveLength(1);
    expect(remaining[0]).toBeEnabled();
    fireEvent.click(remaining[0]);
    fireEvent.click(screen.getByRole("button", { name: "common.check" }));
    expect(onAnswer).toHaveBeenCalledWith("de de");
  });

  it("toggle persists per user id", () => {
    mockUserId = "user-a";
    const { unmount } = render(
      <Translation exercise={current} onAnswer={vi.fn()} disabled={false} courseLevel="A1" lessonExercises={lessonExercises} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "exercise.type_instead" }));
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    unmount();

    render(
      <Translation exercise={current} onAnswer={vi.fn()} disabled={false} courseLevel="A1" lessonExercises={lessonExercises} />,
    );
    expect(screen.getByRole("textbox")).toBeInTheDocument(); // user A remembered "type"
  });

  it("user A's 'type' does not affect user B", () => {
    localStorage.setItem("word-bank-mode:user-a", "type");
    mockUserId = "user-b";
    renderTr("A1");
    expect(screen.getByTestId("word-bank-tiles")).toBeInTheDocument();
  });

  it("RTL: a Farsi exercise gets dir=rtl on both bank containers", () => {
    const fa = ex("fa1", "the book", "en", { answer_language_code: "fa", word_bank: ["این", "کتاب", "است", "من"] });
    renderTr("A1", vi.fn(), fa, [fa]);
    expect(screen.getByTestId("word-bank-tiles")).toHaveAttribute("dir", "rtl");
    expect(screen.getByTestId("word-bank-answer")).toHaveAttribute("dir", "rtl");
  });

  it("reverse_translation stays typed-only even at A1", () => {
    const rev = { ...current, type: "reverse_translation" as const };
    renderTr("A1", vi.fn(), rev);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
    expect(screen.queryByTestId("word-bank-tiles")).toBeNull();
  });
});
