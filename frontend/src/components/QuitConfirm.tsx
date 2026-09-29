import { useId } from "react";
import { useTranslation } from "react-i18next";

interface QuitConfirmProps {
  message: string;
  onKeepGoing: () => void;
  onQuit: () => void;
}

// Shared in-app confirm overlay used by LessonRunnerPage/CheckpointPage/
// ReviewPage's exit affordance. Plain conditional div, no modal library --
// see CLAUDE.md's standing "no new dependency" instruction for this task.
export function QuitConfirm({ message, onKeepGoing, onQuit }: QuitConfirmProps) {
  const { t } = useTranslation();
  const messageId = useId();
  return (
    <div className="confirm-overlay" role="dialog" aria-modal="true" aria-labelledby={messageId}>
      <div className="confirm-overlay-card">
        <p id={messageId} style={{ margin: "0 0 16px" }}>{message}</p>
        <div className="confirm-overlay-actions">
          <button type="button" className="btn btn-secondary" onClick={onKeepGoing}>
            {t("common.keep_going")}
          </button>
          <button type="button" className="btn" onClick={onQuit}>
            {t("common.quit")}
          </button>
        </div>
      </div>
    </div>
  );
}
