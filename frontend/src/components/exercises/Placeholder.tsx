import { useTranslation } from "react-i18next";
import type { ExerciseComponentProps } from "./types";

// listening_placeholder / speaking_placeholder — no audio/mic pipeline yet
// (matches backend, which only defines the schema for now). Renders a
// disabled "coming soon" card with a way to move on.
export function Placeholder({ exercise, onAnswer, disabled }: ExerciseComponentProps) {
  const { t } = useTranslation();
  const label =
    exercise.type === "listening_placeholder"
      ? t("exercise.placeholder_listening")
      : t("exercise.placeholder_speaking");
  const icon = exercise.type === "listening_placeholder" ? "🎧" : "🎙️";

  return (
    <div className="card" style={{ textAlign: "center" }} aria-disabled>
      <div style={{ fontSize: "2.5rem", marginBottom: 8 }}>{icon}</div>
      <p className="muted">{t("exercise.placeholder_coming_soon", { label })}</p>
      <button className="btn btn-block" disabled={disabled} onClick={() => onAnswer("")}>
        {t("exercise.skip_for_now")}
      </button>
    </div>
  );
}
