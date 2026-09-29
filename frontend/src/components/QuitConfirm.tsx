import { useEffect, useId, useRef } from "react";
import { useTranslation } from "react-i18next";

interface QuitConfirmProps {
  message: string;
  onKeepGoing: () => void;
  onQuit: () => void;
}

// Shared in-app confirm overlay used by LessonRunnerPage/CheckpointPage/
// ReviewPage's exit affordance. Plain conditional div, no modal library --
// see CLAUDE.md's standing "no new dependency" instruction for this task.
// Accessible modal: initial focus on the safe "keep going" action, Tab
// trapped inside, Escape cancels, focus restored to the opener on close.
export function QuitConfirm({ message, onKeepGoing, onQuit }: QuitConfirmProps) {
  const { t } = useTranslation();
  const titleId = useId();
  const cardRef = useRef<HTMLDivElement>(null);
  const keepGoingRef = useRef<HTMLButtonElement>(null);
  const onKeepGoingRef = useRef(onKeepGoing);
  onKeepGoingRef.current = onKeepGoing;

  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    keepGoingRef.current?.focus();
    return () => {
      if (previouslyFocused && document.contains(previouslyFocused)) {
        previouslyFocused.focus();
      }
    };
  }, []);

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.stopPropagation();
      event.preventDefault();
      onKeepGoingRef.current();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = cardRef.current?.querySelectorAll<HTMLElement>(
      "button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])",
    );
    if (!focusable || focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const active = document.activeElement;
    if (event.shiftKey && (active === first || !cardRef.current?.contains(active))) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && (active === last || !cardRef.current?.contains(active))) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div
      className="confirm-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onKeyDown={handleKeyDown}
    >
      <div className="confirm-overlay-card" ref={cardRef}>
        <p id={titleId} style={{ margin: "0 0 16px" }}>{message}</p>
        <div className="confirm-overlay-actions">
          <button
            type="button"
            className="btn btn-secondary"
            ref={keepGoingRef}
            onClick={onKeepGoing}
          >
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
