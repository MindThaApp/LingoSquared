import { useMemo, useState } from "react";
import { useQueries, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { CatalogApi, LexemeApi, ProgressApi } from "@lingo/shared/api/endpoints";
import type { Lexeme, LexemeSort, MistakeLexeme } from "@lingo/shared/api/types";

const PAGE_SIZE = 50;

function MasteryBar({ mastery }: { mastery: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, mastery)) * 100);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div className="progress-track" style={{ flex: 1, minWidth: 60 }}>
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="muted" style={{ fontSize: "0.8rem", minWidth: 34, textAlign: "right" }}>
        {pct}%
      </span>
    </div>
  );
}

function DueBadge({ dueAt, suspended }: { dueAt: string; suspended: boolean }) {
  const { t } = useTranslation();
  if (suspended) {
    return (
      <span className="muted" style={{ fontSize: "0.8rem" }}>
        {t("vocabulary.suspended")}
      </span>
    );
  }
  const isDue = new Date(dueAt).getTime() <= Date.now();
  if (isDue) {
    return <span className="badge">{t("vocabulary.due_now")}</span>;
  }
  return (
    <span className="muted" style={{ fontSize: "0.8rem" }}>
      {t("vocabulary.due_on", { date: new Date(dueAt).toLocaleDateString() })}
    </span>
  );
}

function LexemeRow({ lexeme }: { lexeme: Lexeme }) {
  return (
    <div className="card" style={{ marginBottom: 8, padding: "12px 14px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
        <div>
          <strong>{lexeme.token}</strong>
          <span className="muted" style={{ marginLeft: 8 }}>
            {lexeme.english_gloss}
          </span>
        </div>
        <span className="muted" style={{ fontSize: "0.75rem" }}>
          {lexeme.part_of_speech}
        </span>
      </div>
      <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <MasteryBar mastery={lexeme.mastery} />
        <DueBadge dueAt={lexeme.due_at} suspended={lexeme.suspended} />
      </div>
    </div>
  );
}

function MistakeRow({ mistake }: { mistake: MistakeLexeme }) {
  const { t } = useTranslation();
  return (
    <div className="card" style={{ marginBottom: 8, padding: "12px 14px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
        <div>
          <strong>{mistake.token}</strong>
          <span className="muted" style={{ marginLeft: 8 }}>
            {mistake.english_gloss}
          </span>
        </div>
        <span className="muted" style={{ fontSize: "0.75rem" }}>
          {mistake.part_of_speech}
        </span>
      </div>
      <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
        <MasteryBar mastery={mistake.mastery} />
        <span className="muted" style={{ fontSize: "0.8rem" }}>
          {t("vocabulary.wrong_count", { count: mistake.wrong_attempt_count })}
        </span>
      </div>
    </div>
  );
}

export function VocabularyPage() {
  const { t } = useTranslation();
  const [courseId, setCourseId] = useState<string | null>(null);
  const [tab, setTab] = useState<"words" | "mistakes">("words");
  const [sort, setSort] = useState<LexemeSort>("due_soonest");
  const [search, setSearch] = useState("");
  const [limit, setLimit] = useState(PAGE_SIZE);

  const progressQuery = useQuery({ queryKey: ["progress"], queryFn: ProgressApi.progress });
  const courseIds = useMemo(
    () => [...new Set((progressQuery.data?.skill_progress ?? []).map((s) => s.course_id))],
    [progressQuery.data],
  );
  const courseQueries = useQueries({
    queries: courseIds.map((id) => ({
      queryKey: ["course", id],
      queryFn: () => CatalogApi.course(id),
      enabled: !!id,
    })),
  });
  const courseOptions = courseIds
    .map((id, i) => ({ id, title: courseQueries[i]?.data?.title }))
    .filter((c): c is { id: string; title: string } => !!c.title);

  const activeCourseId = courseId ?? (courseOptions.length === 1 ? courseOptions[0].id : null);

  const summaryQuery = useQuery({
    queryKey: ["lexeme-summary", activeCourseId],
    queryFn: () => LexemeApi.summary(activeCourseId!),
    enabled: !!activeCourseId,
  });

  const wordsQuery = useQuery({
    queryKey: ["lexemes", activeCourseId, sort, search, limit],
    queryFn: () => LexemeApi.list(activeCourseId!, { sort, search: search || undefined, limit }),
    enabled: !!activeCourseId && tab === "words",
  });

  const mistakesQuery = useQuery({
    queryKey: ["mistakes", activeCourseId, limit],
    queryFn: () => LexemeApi.mistakes(activeCourseId!, { limit }),
    enabled: !!activeCourseId && tab === "mistakes",
  });

  if (progressQuery.isLoading) return <p className="muted">{t("vocabulary.loading")}</p>;

  if (courseOptions.length === 0) {
    return (
      <div className="card" style={{ textAlign: "center" }}>
        <div style={{ fontSize: "3rem" }}>📖</div>
        <h2>{t("vocabulary.empty_title")}</h2>
        <p className="muted">{t("vocabulary.empty_body")}</p>
      </div>
    );
  }

  if (!activeCourseId) {
    return (
      <div>
        <h1>{t("vocabulary.pick_course_title")}</h1>
        {courseOptions.map((c) => (
          <button
            key={c.id}
            className="card continue-card"
            style={{ width: "100%", textAlign: "start", marginBottom: 12, cursor: "pointer" }}
            onClick={() => setCourseId(c.id)}
          >
            <div className="continue-info">
              <h3 style={{ margin: 0 }}>{c.title}</h3>
            </div>
          </button>
        ))}
      </div>
    );
  }

  const activeQuery = tab === "words" ? wordsQuery : mistakesQuery;
  const items = tab === "words" ? wordsQuery.data?.items : mistakesQuery.data?.items;
  const totalCount = tab === "words" ? wordsQuery.data?.total_count : mistakesQuery.data?.total_count;

  return (
    <div>
      <h1 style={{ marginBottom: 4 }}>{t("vocabulary.title")}</h1>
      {courseOptions.length > 1 && (
        <button className="btn-icon-toggle" style={{ marginBottom: 12 }} onClick={() => setCourseId(null)}>
          {t("vocabulary.change_course")}
        </button>
      )}

      {summaryQuery.data && (
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 16 }}>
          <div className="card" style={{ padding: "10px 16px", textAlign: "center" }}>
            <strong style={{ fontSize: "1.3rem" }}>{summaryQuery.data.total_tracked}</strong>
            <div className="muted" style={{ fontSize: "0.75rem" }}>{t("vocabulary.stat_tracked")}</div>
          </div>
          <div className="card" style={{ padding: "10px 16px", textAlign: "center" }}>
            <strong style={{ fontSize: "1.3rem" }}>{summaryQuery.data.due_today}</strong>
            <div className="muted" style={{ fontSize: "0.75rem" }}>{t("vocabulary.stat_due_today")}</div>
          </div>
          <div className="card" style={{ padding: "10px 16px", textAlign: "center" }}>
            <strong style={{ fontSize: "1.3rem" }}>{summaryQuery.data.mastery_bands.strong}</strong>
            <div className="muted" style={{ fontSize: "0.75rem" }}>{t("vocabulary.stat_strong")}</div>
          </div>
          <div className="card" style={{ padding: "10px 16px", textAlign: "center" }}>
            <strong style={{ fontSize: "1.3rem" }}>{summaryQuery.data.suspended}</strong>
            <div className="muted" style={{ fontSize: "0.75rem" }}>{t("vocabulary.stat_suspended")}</div>
          </div>
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button
          className={`btn ${tab === "words" ? "" : "btn-secondary"}`}
          onClick={() => {
            setTab("words");
            setLimit(PAGE_SIZE);
          }}
        >
          {t("vocabulary.tab_words")}
        </button>
        <button
          className={`btn ${tab === "mistakes" ? "" : "btn-secondary"}`}
          onClick={() => {
            setTab("mistakes");
            setLimit(PAGE_SIZE);
          }}
        >
          {t("vocabulary.tab_mistakes")}
        </button>
      </div>

      {tab === "words" && (
        <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
          <input
            type="text"
            placeholder={t("vocabulary.search_placeholder") ?? undefined}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setLimit(PAGE_SIZE);
            }}
            style={{ flex: 1, minWidth: 160 }}
          />
          <select
            value={sort}
            onChange={(e) => {
              setSort(e.target.value as LexemeSort);
              setLimit(PAGE_SIZE);
            }}
          >
            <option value="due_soonest">{t("vocabulary.sort_due_soonest")}</option>
            <option value="mastery_asc">{t("vocabulary.sort_mastery_asc")}</option>
            <option value="mastery_desc">{t("vocabulary.sort_mastery_desc")}</option>
            <option value="alphabetical">{t("vocabulary.sort_alphabetical")}</option>
            <option value="recently_introduced">{t("vocabulary.sort_recent")}</option>
          </select>
        </div>
      )}

      {activeQuery.isLoading && <p className="muted">{t("vocabulary.loading")}</p>}

      {!activeQuery.isLoading && items?.length === 0 && (
        <p className="muted">
          {tab === "words" ? t("vocabulary.no_words") : t("vocabulary.no_mistakes")}
        </p>
      )}

      {tab === "words" &&
        (items as Lexeme[] | undefined)?.map((lexeme) => (
          <LexemeRow key={lexeme.token} lexeme={lexeme} />
        ))}
      {tab === "mistakes" &&
        (items as MistakeLexeme[] | undefined)?.map((mistake) => (
          <MistakeRow key={mistake.token} mistake={mistake} />
        ))}

      {items && totalCount !== undefined && items.length < totalCount && (
        <button
          className="btn btn-secondary btn-block"
          style={{ marginTop: 8 }}
          onClick={() => setLimit((n) => n + PAGE_SIZE)}
        >
          {t("vocabulary.load_more")}
        </button>
      )}
    </div>
  );
}
