import { useState } from "react";
import { useTranslation } from "react-i18next";
import { SpeakButton } from "./SpeakButton";
import { VoiceCaptureControls } from "./VoiceCaptureControls";
import { VirtualKeyboard } from "./VirtualKeyboard";
import { useKeyboardFocus } from "../lib/useKeyboardFocus";
import { LANGUAGE_SCRIPT, scriptDirection, scriptNeedsVirtualKeyboard } from "@lingo/shared/lib/scripts";
import { PracticeApi } from "@lingo/shared/api/endpoints";
import { ApiError } from "@lingo/shared/api/client";

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

type Exchange = { app: string; learner: string; correct: boolean };

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
  const { showKeyboard, dismissKeyboard, inputProps } = useKeyboardFocus();

  const answerLang = node.answer_language_code;
  const script = LANGUAGE_SCRIPT[answerLang] ?? null;
  const dir = scriptDirection(script);

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
      setHistory((h) => [...h, { app: node.app_turn.text, learner: reply, correct: res.correct }]);
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
      setError(err instanceof ApiError && err.code === "practice_item_not_found" ? "dead" : "retry");
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
              <p className="conversation-line conversation-line-app">{h.app}</p>
              <p
                className={
                  h.correct
                    ? "conversation-line conversation-line-you"
                    : "conversation-line conversation-line-you conversation-line-missed"
                }
                dir={dir}
              >
                {h.learner}
              </p>
            </div>
          ))}
        </div>
      )}

      <div className="conversation-current">
        <p className="conversation-line conversation-line-app" dir={node.app_turn.direction ?? "ltr"}>
          {node.app_turn.text}
        </p>
        <SpeakButton text={node.app_turn.text} languageCode={node.app_turn.language_code} />
      </div>

      {finished ? (
        <p className="muted">{t("practice.conversation_finished")}</p>
      ) : (
        <>
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
              onKeyDown={(e) => {
                if (e.key === "Enter") submit();
              }}
              disabled={submitting}
              placeholder={t("practice.conversation_reply_placeholder")}
              dir={dir}
              {...inputProps}
            />
          </div>
          {script && scriptNeedsVirtualKeyboard(script) && showKeyboard && (
            <VirtualKeyboard
              script={script}
              onInsert={(char: string) => setValue((v) => v + char)}
              onBackspace={() => setValue((v) => v.slice(0, -1))}
              onDismiss={dismissKeyboard}
            />
          )}
          <button className="btn btn-block" onClick={submit} disabled={submitting || !value.trim()}>
            {t("practice.conversation_send")}
          </button>
        </>
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
