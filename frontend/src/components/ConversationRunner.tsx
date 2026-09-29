import { useState } from "react";
import { useTranslation } from "react-i18next";
import { SpeakButton } from "./SpeakButton";
import { VoiceCaptureControls } from "./VoiceCaptureControls";
import { VirtualKeyboard } from "./VirtualKeyboard";
import { useKeyboardFocus } from "../lib/useKeyboardFocus";
import { LANGUAGE_SCRIPT, scriptDirection, scriptNeedsVirtualKeyboard } from "@lingo/shared/lib/scripts";
import { PracticeApi } from "@lingo/shared/api/endpoints";
import { ApiError } from "@lingo/shared/api/client";
import { PERMANENT_ANSWER_ERROR_CODES } from "../lib/practiceAnswerErrors";
import { resultStatus } from "@lingo/shared/lib/gradingResult";
import type { GradingStatus } from "@lingo/shared/api/types";
import { AlmostFeedback } from "./AlmostFeedback";

// Endless conversation practice (backend `mode=conversation`). Unlike every
// other exercise this is MULTI-TURN: one practice item carries a node graph,
// and each learner reply selects the next node. So it cannot go through
// ExerciseRenderer (which is one-shot) — PracticeCard branches to this
// component on item.type === "conversation".
//
// The graph rides on the item (there is no server-side conversation state),
// so advancing is purely: submit {node_id, response} -> read `next_node` off
// the answer response -> render it. A reply the backend can't match returns
// the fallback node, which re-prompts; a conversation NEVER dead-ends.

export type ConversationTurn = {
  text: string;
  language_code: string;
  direction?: string;
};

export type ConversationNode = {
  id: string;
  app_turn: ConversationTurn;
  accepted_variants: string[];
  answer_language_code: string;
  terminal: boolean;
};

export type ConversationPrompt = {
  start_node_id: string;
  current_node: ConversationNode;
  nodes: ConversationNode[];
};

type Exchange = {
  app: string;
  appLang: string;
  appDir: string;
  learner: string;
  correct: boolean;
  status: GradingStatus;
  correction?: string;
};

export function ConversationRunner({
  itemId,
  prompt,
  onAnswered,
}: {
  itemId: string;
  prompt: ConversationPrompt;
  onAnswered: (correct: boolean, xp: number) => void;
}) {
  const { t } = useTranslation();
  const [node, setNode] = useState<ConversationNode>(prompt.current_node);
  const [value, setValue] = useState("");
  const [history, setHistory] = useState<Exchange[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [finished, setFinished] = useState(prompt.current_node.terminal);
  const [error, setError] = useState<"retry" | "dead" | null>(null);
  const answerLang = node.answer_language_code;
  const script = LANGUAGE_SCRIPT[answerLang] ?? null;
  const dir = scriptDirection(script);
  const { showKeyboard, inputProps, keyboardProps } = useKeyboardFocus({
    value,
    setValue,
    script,
    disabled: submitting || finished,
  });

  async function submit() {
    const reply = value.trim();
    if (!reply || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await PracticeApi.answer(itemId, {
        node_id: node.id,
        response: reply,
      } as never);
      const next = (res as unknown as { next_node?: ConversationNode }).next_node;
      setHistory((h) => [
        ...h,
        {
          app: node.app_turn.text,
          appLang: node.app_turn.language_code,
          appDir: node.app_turn.direction ?? "ltr",
          learner: reply,
          correct: res.correct,
          status: resultStatus(res),
          // Only a plain-string answer key can be shown/diffed; never invent one.
          correction: typeof res.correct_response === "string" ? res.correct_response : undefined,
        },
      ]);
      onAnswered(res.correct, res.xp_awarded);
      setValue("");
      if (next) {
        setNode(next);
        // A terminal node still gets rendered — it's the app's closing line.
        if (next.terminal) setFinished(true);
      } else {
        setFinished(true);
      }
    } catch (err) {
      // Same split as PracticeCard: a permanently-dead item can't be retried,
      // anything else keeps the learner's text so they can try again.
      if (err instanceof ApiError && PERMANENT_ANSWER_ERROR_CODES.has(err.code)) {
        setError("dead");
        setFinished(true); // hides the input + send button
      } else {
        setError("retry");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="conversation-runner">
      {history.length > 0 && (
        <div className="conversation-history">
          {history.map((h, i) => (
            <div key={i} className="conversation-exchange">
              <p
                className="conversation-line conversation-line-app"
                lang={h.appLang}
                dir={h.appDir}
              >
                {h.app}
              </p>
              <p
                className={
                  h.correct
                    ? "conversation-line conversation-line-you"
                    : "conversation-line conversation-line-you conversation-line-missed"
                }
                dir={dir}
                lang={answerLang}
              >
                {h.learner}
              </p>
              {h.status === "almost" && (
                // Amber pass: the reply was accepted; conversation continues as after a correct one.
                <div className="feedback-banner almost" role="status">
                  <AlmostFeedback learner={h.learner} correct={h.correction} dir={dir} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="conversation-current" aria-live="polite">
        <p
          className="conversation-line conversation-line-app"
          dir={node.app_turn.direction ?? "ltr"}
          lang={node.app_turn.language_code}
        >
          {node.app_turn.text}
        </p>
        <SpeakButton text={node.app_turn.text} languageCode={node.app_turn.language_code} />
      </div>

      {finished ? (
        // Dead item: show only the "unavailable" banner below — "conversation
        // finished" would be misleading since the conversation was cut off.
        error === "dead" ? null : <p className="muted">{t("practice.conversation_finished")}</p>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          <p className="muted" style={{ fontSize: "0.9rem" }}>
            {t("practice.conversation_your_turn")}
          </p>
          <VoiceCaptureControls
            languageCode={answerLang}
            onTranscript={setValue}
            disabled={submitting}
          />
          <div className="form-field">
            <input
              type="text"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              disabled={submitting}
              placeholder={t("practice.conversation_reply_placeholder")}
              aria-label={t("practice.conversation_reply_placeholder")}
              lang={answerLang}
              dir={dir}
              {...inputProps}
            />
          </div>
          {script && scriptNeedsVirtualKeyboard(script) && showKeyboard && (
            <VirtualKeyboard
              script={script}
              {...keyboardProps}
            />
          )}
          <button
            type="submit"
            className="btn btn-block"
            disabled={submitting || !value.trim()}
            onMouseDown={(e) => e.preventDefault()}
          >
            {t("practice.conversation_send")}
          </button>
        </form>
      )}

      {error === "retry" && (
        <div className="feedback-banner error" role="alert">
          <p style={{ margin: 0 }}>{t("practice.submit_error")}</p>
        </div>
      )}
      {error === "dead" && (
        <div className="feedback-banner error" role="alert">
          <p style={{ margin: 0 }}>{t("practice.item_unavailable")}</p>
        </div>
      )}
    </div>
  );
}
