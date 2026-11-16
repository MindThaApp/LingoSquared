import "@testing-library/jest-dom/vitest";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ConversationRunner, type ConversationPrompt } from "./ConversationRunner";
import { PracticeApi } from "@lingo/shared/api/endpoints";
import { ApiError } from "@lingo/shared/api/client";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

vi.mock("@lingo/shared/api/endpoints", () => ({
  PracticeApi: { answer: vi.fn() },
}));

vi.mock("./SpeakButton", () => ({ SpeakButton: () => null }));
vi.mock("./VoiceCaptureControls", () => ({ VoiceCaptureControls: () => null }));

const answer = PracticeApi.answer as unknown as ReturnType<typeof vi.fn>;

function makePrompt(direction: string): ConversationPrompt {
  const start = {
    id: "n1",
    app_turn: { text: "Hallo, hoe gaat het?", language_code: "nl", direction },
    accepted_variants: ["goed"],
    answer_language_code: "en",
    terminal: false,
  };
  return { start_node_id: "n1", current_node: start, nodes: [start] };
}

function renderRunner(direction = "ltr") {
  return render(
    <ConversationRunner itemId="item-1" prompt={makePrompt(direction)} onAnswered={vi.fn()} />,
  );
}

async function sendReply(text: string) {
  const input = screen.getByPlaceholderText("practice.conversation_reply_placeholder");
  fireEvent.change(input, { target: { value: text } });
  fireEvent.click(screen.getByRole("button", { name: "practice.conversation_send" }));
}

describe("ConversationRunner", () => {
  beforeEach(() => {
    answer.mockReset();
  });

  it.each(["practice_item_answered", "practice_item_expired", "practice_item_not_found"])(
    "permanent error %s shows the unavailable banner and removes the input",
    async (code) => {
      answer.mockRejectedValue(new ApiError(409, code, "gone"));
      renderRunner();
      await sendReply("goed");
      expect(await screen.findByRole("alert")).toHaveTextContent("practice.item_unavailable");
      expect(screen.queryByPlaceholderText("practice.conversation_reply_placeholder")).toBeNull();
      expect(screen.queryByRole("button", { name: "practice.conversation_send" })).toBeNull();
      expect(screen.queryByText("practice.conversation_finished")).toBeNull();
    },
  );

  it("a generic error shows the retry banner and keeps the text and input enabled", async () => {
    answer.mockRejectedValue(new ApiError(500, "internal_error", "boom"));
    renderRunner();
    await sendReply("goed");
    expect(await screen.findByRole("alert")).toHaveTextContent("practice.submit_error");
    const input = screen.getByPlaceholderText("practice.conversation_reply_placeholder");
    expect(input).toBeEnabled();
    expect(input).toHaveValue("goed");
  });

  it("gives history app lines the app turn's direction", async () => {
    const next = {
      id: "n2",
      app_turn: { text: "بسیار خوب", language_code: "fa", direction: "rtl" },
      accepted_variants: [],
      answer_language_code: "en",
      terminal: true,
    };
    answer.mockResolvedValue({ correct: true, xp_awarded: 1, next_node: next });
    renderRunner("rtl");
    await sendReply("goed");
    await waitFor(() => expect(document.querySelector(".conversation-history")).not.toBeNull());
    const line = document.querySelector(".conversation-history .conversation-line-app");
    expect(line).toHaveTextContent("Hallo, hoe gaat het?");
    expect(line).toHaveAttribute("dir", "rtl");
  });

  it("romanized reply shows the script nudge, stays on the same turn, and a script retry is accepted", async () => {
    const node = makePrompt("ltr").current_node;
    answer
      .mockResolvedValueOnce({
        correct: false,
        result: "almost",
        correct_response: ["goed"],
        xp_awarded: 0,
        feedback_code: "romanized_input",
        next_node: node,
      })
      .mockResolvedValueOnce({ correct: true, result: "correct", correct_response: ["goed"], xp_awarded: 5, next_node: null });
    const onAnswered = vi.fn();
    render(<ConversationRunner itemId="item-1" prompt={makePrompt("ltr")} onAnswered={onAnswered} />);
    await sendReply("goed");
    expect(await screen.findByText(/almost_feedback.title_romanized/, { selector: ".almost-title" })).toBeInTheDocument();
    // Input is still open for the retry; the reply was not counted correct.
    expect(screen.getByPlaceholderText("practice.conversation_reply_placeholder")).toBeInTheDocument();
    expect(onAnswered).toHaveBeenLastCalledWith(false, 0);
    await sendReply("goed");
    await waitFor(() => expect(onAnswered).toHaveBeenLastCalledWith(true, 5));
  });
});
