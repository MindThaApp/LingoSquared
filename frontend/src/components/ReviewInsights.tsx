import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ReviewApi } from "@lingo/shared/api/endpoints";

// Quiet by design: both blocks render nothing while loading, on error, or when
// there is nothing to show, so a failed forecast never blocks the review screen.
export function ReviewInsights() {
  const { t } = useTranslation();
  const forecast = useQuery({
    queryKey: ["reviews-forecast"],
    queryFn: () => ReviewApi.forecast(),
    retry: false,
  });
  const leeches = useQuery({
    queryKey: ["reviews-leeches"],
    queryFn: () => ReviewApi.leeches(),
    retry: false,
  });

  const f = forecast.data;
  const cells = f
    ? [
        { key: "today", label: t("review.forecast_today"), n: f.today },
        { key: "tomorrow", label: t("review.forecast_tomorrow"), n: f.tomorrow },
        { key: "week", label: t("review.forecast_week"), n: f.this_week },
      ]
    : [];
  const showForecast = cells.some((c) => c.n > 0);
  const leechItems = leeches.data?.items ?? [];

  return (
    <>
      {showForecast && (
        <section className="card" aria-label={t("review.forecast_title")} style={{ marginTop: 14 }}>
          <h3 style={{ margin: "0 0 10px" }}>{t("review.forecast_title")}</h3>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {cells.map((c) => (
              <div key={c.key} style={{ flex: "1 1 80px", textAlign: "center" }}>
                <div style={{ fontSize: "1.5rem", fontWeight: 700 }}>{c.n}</div>
                <div className="muted">{c.label}</div>
              </div>
            ))}
          </div>
        </section>
      )}
      {leechItems.length > 0 && (
        <section className="card" aria-label={t("review.leech_title")} style={{ marginTop: 14 }}>
          <h3 style={{ margin: "0 0 6px" }}>{t("review.leech_title")}</h3>
          <p className="muted" style={{ margin: "0 0 10px" }}>{t("review.leech_body")}</p>
          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
            {leechItems.map((l) => (
              <li
                key={l.lexeme_id}
                style={{ display: "flex", justifyContent: "space-between", gap: 12, padding: "4px 0" }}
              >
                <span dir="auto">
                  <strong>{l.token}</strong> <span className="muted">{l.english_gloss}</span>
                </span>
                <span className="muted" style={{ whiteSpace: "nowrap" }}>
                  {t("review.leech_missed", { count: l.lapses })}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

// "Next review in X" from the interval the server just scheduled.
export function nextReviewLabel(t: (key: string, opts?: Record<string, unknown>) => string, days: number): string {
  if (days <= 1) return t("review.next_review_tomorrow");
  if (days < 14) return t("review.next_review_days", { count: days });
  if (days < 60) return t("review.next_review_weeks", { count: Math.round(days / 7) });
  return t("review.next_review_months", { count: Math.max(2, Math.round(days / 30)) });
}
