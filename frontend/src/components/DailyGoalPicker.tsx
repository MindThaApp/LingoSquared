import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ProgressApi } from "@lingo/shared/api/endpoints";

export const DAILY_GOAL_OPTIONS = [10, 20, 30, 50] as const;
type Goal = (typeof DAILY_GOAL_OPTIONS)[number];

/** Daily XP goal editor (PUT /me/daily-goal accepts exactly these values). */
export function DailyGoalPicker() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const xpQuery = useQuery({ queryKey: ["xp"], queryFn: ProgressApi.xp });
  const [status, setStatus] = useState<"idle" | "saved" | "error">("idle");
  const mutation = useMutation({
    mutationFn: (goal: Goal) => ProgressApi.setDailyGoal(goal),
    onSuccess: () => {
      setStatus("saved");
      void queryClient.invalidateQueries({ queryKey: ["xp"] });
      void queryClient.invalidateQueries({ queryKey: ["quests"] });
    },
    onError: () => setStatus("error"),
  });
  const current = xpQuery.data?.daily_goal;

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <h3 id="daily-goal-title" style={{ marginTop: 0 }}>{t("profile.goal_title")}</h3>
      <p className="muted" style={{ marginTop: 4 }}>{t("profile.goal_hint")}</p>
      <div className="goal-picker" role="radiogroup" aria-labelledby="daily-goal-title">
        {DAILY_GOAL_OPTIONS.map((goal) => (
          <button
            key={goal}
            type="button"
            role="radio"
            aria-checked={current === goal}
            className="goal-option"
            disabled={mutation.isPending || current === undefined}
            onClick={() => {
              setStatus("idle");
              mutation.mutate(goal);
            }}
          >
            <strong>{t(`profile.goal_${goal}`)}</strong>
            <span className="goal-option-xp">{t("profile.goal_xp", { xp: goal })}</span>
          </button>
        ))}
      </div>
      <p className="muted" role="status" style={{ margin: "8px 0 0", minHeight: "1.2em" }}>
        {status === "saved" ? t("profile.goal_saved") : ""}
      </p>
      {status === "error" && (
        <p className="form-error" role="alert">{t("profile.goal_error")}</p>
      )}
    </div>
  );
}
