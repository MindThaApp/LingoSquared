import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Exercise } from "@lingo/shared/api/types";

const getPreference = vi.fn<() => "bank" | "type" | null>();
const setPreference = vi.fn();
let bankTiles = ["hola", "mundo"];

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (key: string) => key }) }));
vi.mock("../../auth/AuthContext", () => ({ useAuth: () => ({ user: { id: "user-1" } }) }));
vi.mock("../targetLanguageContext", () => ({ useTargetLanguage: () => "es" }));
vi.mock("../../lib/wordBankTiles", () => ({
  buildWordBank: () => ({ tiles: bankTiles }),
}));
vi.mock("../../lib/wordBankPreference", () => ({
  defaultAnswerMode: (level: string) => level === "A1" || level === "A2" ? "bank" : "type",
  getWordBankPreference: () => getPreference(),
  setWordBankPreference: (...args: unknown[]) => setPreference(...args),
}));
vi.mock("@lingo/shared/lib/scripts", () => ({ answerDirectionForExercise: () => "ltr" }));
vi.mock("./WordBankInput", () => ({
  WordBankInput: ({ onSubmit, disabled }: { onSubmit: (answer: string) => void; disabled: boolean }) => (
    <button type="button" disabled={disabled} onClick={() => onSubmit("hola mundo")}>mock word bank</button>
  ),
}));

import { AnswerModeSwitch } from "./AnswerModeSwitch";

const exercise: Exercise = {
  id: "e1",
  type: "translation",
  order: 1,
  prompt: { text_blocks: [], answer_language_code: "es" },
};

function renderSwitch(overrides: Partial<React.ComponentProps<typeof AnswerModeSwitch>> = {}) {
  const onAnswer = vi.fn();
  render(
    <AnswerModeSwitch
      exercise={exercise}
      courseLevel="A1"
      disabled={false}
      onAnswer={onAnswer}
      renderTyping={(toggle) => <div>typing input{toggle}</div>}
      {...overrides}
    />,
  );
  return onAnswer;
}

beforeEach(() => {
  getPreference.mockReset().mockReturnValue(null);
  setPreference.mockReset();
  bankTiles = ["hola", "mundo"];
});

describe("AnswerModeSwitch", () => {
  it("bypasses bank behavior when disabled by configuration or missing a course level", () => {
    const first = renderSwitch({ enabled: false });
    expect(screen.getByText("typing input")).toBeInTheDocument();
    expect(screen.queryByText("mock word bank")).toBeNull();
    first.mockClear();
  });

  it("uses the A1 bank by default and forwards its submitted answer", () => {
    const onAnswer = renderSwitch();
    fireEvent.click(screen.getByRole("button", { name: "mock word bank" }));
    expect(onAnswer).toHaveBeenCalledWith("hola mundo");
  });

  it("switches modes and persists the choice for the signed-in user", () => {
    getPreference.mockReturnValue("type");
    renderSwitch();
    fireEvent.click(screen.getByRole("button", { name: "exercise.use_word_bank" }));
    expect(screen.getByText("mock word bank")).toBeInTheDocument();
    expect(setPreference).toHaveBeenCalledWith("user-1", "bank");

    fireEvent.click(screen.getByRole("button", { name: "exercise.type_instead" }));
    expect(screen.getByText("typing input")).toBeInTheDocument();
    expect(setPreference).toHaveBeenLastCalledWith("user-1", "type");
  });

  it("falls back to typing without a toggle when fewer than two bank tiles exist", () => {
    bankTiles = ["hola"];
    renderSwitch();
    expect(screen.getByText("typing input")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /word_bank/ })).toBeNull();
  });
});
