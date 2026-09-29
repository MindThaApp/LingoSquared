import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { CatalogApi, PracticeApi, ProgressApi } from "@lingo/shared/api/endpoints";
import { CourseTargetLanguage } from "../components/CourseTargetLanguage";
import { ExerciseRenderer } from "../components/exercises/ExerciseRenderer";
import { ConversationRunner, type ConversationPrompt } from "../components/ConversationRunner";
import { ReportIssueButton } from "../components/ReportIssueButton";
import { invalidateProgressQueries } from "../lib/invalidateProgress";
import { ApiError } from "@lingo/shared/api/client";
import { formatCorrectResponse } from "@lingo/shared/lib/formatAnswer";
import { resultStatus } from "@lingo/shared/lib/gradingResult";
import { answerDirectionForExercise } from "@lingo/shared/lib/scripts";
import { AlmostFeedback } from "../components/AlmostFeedback";
import type {
  AnswerResponse,
  CourseDetail,
  PracticeAnswerResult,
  PracticeBatchMode,
  PracticeItem,
} from "@lingo/shared/api/types";
import {
  getPracticeModePreference,
  setPracticeModePreference,
} from "../lib/practiceModePreference";

const PRACTICE_MODES: PracticeBatchMode[] = ["mixed", "speaking", "conversation"];

// The six drillable exercise types a learner can filter the feed down to.
// An empty selection means "no filter" (all types), so this is purely
// additive on top of the mode selector. Kept as plain strings — the batch
// endpoint accepts this subset (see docs/CONTRACT.md, POST
// /practice/{course_id}/batch's `types`).
const PRACTICE_TYPES = [
  "multiple_choice",
  "fill_in_blank",
  "word_order",
  "translation",
  "matching_pairs",
  "listen_select",
] as const;

const BATCH_SIZE = 10;
const PREFETCH_THRESHOLD = 3;
// Rendered-card cap: an endless feed would otherwise keep every card (and its
// exercise DOM) mounted forever. When a batch pushes the list past this, the
// OLDEST already-answered cards are dropped; unanswered/active cards and
// multi-turn conversation cards (whose completion isn't observable here) are
// never dropped, so the list can exceed the cap if the learner isn't answering.
const MAX_RENDERED_CARDS = 30;

function trimAnswered(
  list: PracticeItem[],
  answered: ReadonlySet<string>,
): PracticeItem[] {
  let excess = list.length - MAX_RENDERED_CARDS;
  if (excess <= 0) return list;
  return list.filter((item) => {
    if (excess > 0 && item.type !== "conversation" && answered.has(item.id)) {
      excess -= 1;
      return false;
    }
    return true;
  });
}

// Old budget-Android WebViews (a real slice of the fa/prs audience) can
// lack IntersectionObserver entirely -- constructing it unguarded would
// hard-crash the whole feed at first render. When it's missing, fall back
// to a manual "Load more" button instead of auto-loading infinite scroll.
const SUPPORTS_INTERSECTION_OBSERVER = typeof IntersectionObserver !== "undefined";

// These codes mean the item itself can never be answered again (already
// answered elsewhere, expired mid-scroll, or not this user's) -- distinct
// from a transient network/server failure, which IS retryable with the
// same stored response. See backend/app/api/router.py's practice_answer().
const PERMANENT_ANSWER_ERROR_CODES = new Set([
  "practice_item_not_found",
  "practice_item_answered",
  "practice_item_expired",
]);

interface EligibleCourse extends CourseDetail {
  completed_lessons: number;
}

function PracticeCard({
  item,
  courseId,
  onAnswered,
}: {
  item: PracticeItem;
  courseId: string | null;
  onAnswered: (correct: boolean, xp: number) => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [result, setResult] = useState<PracticeAnswerResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const [submitError, setSubmitError] = useState(false);
  const [lastResponse, setLastResponse] = useState<AnswerResponse | undefined>();
  const [lastSpoken, setLastSpoken] = useState(false);

  async function handleAnswer(response: AnswerResponse, meta?: { inputMode?: "spoken" }) {
    setSubmitting(true);
    setLastResponse(response);
    setLastSpoken(meta?.inputMode === "spoken");
    setSubmitError(false);
    try {
      const res = await PracticeApi.answer(item.id, response, meta);
      setResult(res);
      invalidateProgressQueries(queryClient);
      onAnswered(res.correct, res.xp_awarded);
    } catch (err) {
      if (err instanceof ApiError && PERMANENT_ANSWER_ERROR_CODES.has(err.code)) {
        // Item may have expired mid-scroll (or already been answered/is
        // foreign to this user) — the card can't be retried, so resolve it
        // visibly instead of silently re-enabling a dead exercise.
        setUnavailable(true);
      } else {
        // Network failure or unexpected server error: retryable with the
        // same stored response, don't clear the learner's selection.
        setSubmitError(true);
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handleRetryAnswer() {
    if (lastResponse) handleAnswer(lastResponse, lastSpoken ? { inputMode: "spoken" } : undefined);
  }

  // Conversation items are multi-turn: the runner owns its own submit loop and
  // node advancement, so it bypasses the one-shot ExerciseRenderer/result path.
  if (item.type === "conversation") {
    return (
      <div className="card practice-card">
        <ConversationRunner
          itemId={item.id}
          prompt={item.prompt as unknown as ConversationPrompt}
          onAnswered={onAnswered}
        />
        <ReportIssueButton
          onSubmit={(category, description, response) =>
            PracticeApi.reportIssue(item.id, category, description, response)
          }
        />
      </div>
    );
  }

  return (
    <div className="card practice-card">
      <CourseTargetLanguage courseId={courseId}><ExerciseRenderer
        exercise={{ id: item.id, type: item.type, order: 0, prompt: item.prompt }}
        onAnswer={handleAnswer}
        disabled={submitting || Boolean(result) || unavailable || submitError}
        gradedResult={
          result ? { correct: result.correct, correctResponse: result.correct_response } : undefined
        }
      /></CourseTargetLanguage>
      {submitError && !result && (
        <div className="feedback-banner error" role="alert">
          <p style={{ margin: "0 0 10px" }}>{t("practice.submit_error")}</p>
          <button className="btn btn-block" onClick={handleRetryAnswer} disabled={submitting}>
            {t("common.retry")}
          </button>
        </div>
      )}
      {result && (() => {
        const status = resultStatus(result);
        if (status === "almost") {
          return (
            <div className="feedback-banner almost" role="status">
              <AlmostFeedback
                learner={typeof lastResponse === "string" ? lastResponse : undefined}
                spoken={lastSpoken}
                correct={formatCorrectResponse(result.correct_response)}
                dir={answerDirectionForExercise({ id: item.id, type: item.type, order: 0, prompt: item.prompt })}
              />
            </div>
          );
        }
        return (
          // role="status" (implicit aria-live="polite") - announces the grading
          // result to screen readers when the banner mounts.
          <div className={`feedback-banner ${status}`} role="status">
            <p style={{ margin: 0 }}>
              {status === "correct" && t("practice.correct", { xp: result.xp_awarded })}
              {status === "incorrect" &&
                t("lesson_runner.correct_answer", {
                  answer: formatCorrectResponse(result.correct_response),
                })}
            </p>
          </div>
        );
      })()}
      {unavailable && (
        <div className="feedback-banner" role="status">
          <p style={{ margin: 0 }}>{t("practice.item_unavailable")}</p>
        </div>
      )}
      <div style={{ marginTop: 12, textAlign: "center" }}>
        {/* item.id is a PracticeItem id, same table review/checkpoint
            items use - reported through the shared practice-item report
            endpoint, not /exercises/{id}/report. */}
        <ReportIssueButton
          lastResponse={lastResponse}
          onSubmit={(category, description, response) =>
            PracticeApi.reportIssue(item.id, category, description, response)
          }
        />
      </div>
    </div>
  );
}

export function PracticeFeedPage() {
  const { t } = useTranslation();
  const location = useLocation();
  // Course pre-selection via route state (e.g. VocabularyPage's "Practice
  // these words"), same threading pattern as CourseUnitsPage -> UnitLessonsPage.
  const routeState = location.state as
    | { courseId?: string; targetLexemeIds?: string[] }
    | null;
  const requestedCourseId = routeState?.courseId;
  // A "drill weak outcomes" entry (e.g. from a failed checkpoint) seeds the
  // feed with just these lexeme UUIDs. Read once at mount, like courseId.
  const requestedTargetLexemeIds = routeState?.targetLexemeIds;
  const [loadingEligibility, setLoadingEligibility] = useState(true);
  const [eligibilityError, setEligibilityError] = useState(false);
  const [eligibleCourses, setEligibleCourses] = useState<EligibleCourse[]>([]);
  const [courseId, setCourseId] = useState<string | null>(null);
  const [mode, setMode] = useState<PracticeBatchMode>(() => getPracticeModePreference());
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [items, setItems] = useState<PracticeItem[]>([]);
  const [locked, setLocked] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [feedError, setFeedError] = useState(false);
  const [exhausted, setExhausted] = useState(false);
  const [combo, setCombo] = useState(0);
  const [xpToast, setXpToast] = useState<number | null>(null);
  // Keyed by item id (not list index) so trimming old cards can't shift refs.
  const cardRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  // Ids of cards answered this session. Independent of the (trimmed) render
  // list; only used to decide which cards are safe to drop.
  const answeredIdsRef = useRef<Set<string>>(new Set());
  const loadingMoreRef = useRef(false);
  // Bumped whenever mode/type filter changes (the feed restarts). A batch
  // request captures the value at start and drops its result -- items,
  // exhausted, error -- if it changed while in flight, so an old mode's
  // response can't leak into the new feed.
  const feedGenRef = useRef(0);

  // MUST stay caught: the inner Promise.all means a single failing
  // CatalogApi.course() rejects the whole chain, leaving eligibleCourses
  // empty — which the render below is otherwise unable to tell apart from
  // "this learner has completed no lessons", so it told learners who HAVE
  // completed lessons that practice is locked (and rejected unhandled).
  const loadEligibility = useCallback(() => {
    setLoadingEligibility(true);
    setEligibilityError(false);
    ProgressApi.progress()
      .then(async (progress) => {
        const withProgress = progress.skill_progress.filter(
          (sp) => sp.completed_lessons > 0,
        );
        const courses = await Promise.all(
          withProgress.map((sp) =>
            CatalogApi.course(sp.course_id).then((course) => ({
              ...course,
              completed_lessons: sp.completed_lessons,
            })),
          ),
        );
        setEligibleCourses(courses);
        // A requested course that isn't actually eligible (no completed
        // lessons) falls through to the normal picker/locked states rather
        // than starting a feed the backend would refuse to fill.
        if (requestedCourseId && courses.some((c) => c.id === requestedCourseId)) {
          setCourseId(requestedCourseId);
        } else if (courses.length === 1) {
          setCourseId(courses[0].id);
        }
      })
      .catch(() => setEligibilityError(true))
      .finally(() => setLoadingEligibility(false));
  }, [requestedCourseId]);

  useEffect(() => {
    loadEligibility();
    // Mount-only on purpose: route state is read once when the page is
    // entered; re-running on in-place state changes would re-append a new
    // course's items onto an already-populated feed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadMore = useCallback(async () => {
    if (!courseId || loadingMoreRef.current || exhausted) return;
    const gen = feedGenRef.current;
    loadingMoreRef.current = true;
    setLoadingMore(true);
    setFeedError(false);
    try {
      const res = await PracticeApi.batch(courseId, BATCH_SIZE, mode, {
        types: selectedTypes,
        targetLexemeIds: requestedTargetLexemeIds,
      });
      if (gen !== feedGenRef.current) return;
      setLocked(res.locked);
      if (res.items.length === 0) {
        setExhausted(true);
      } else {
        setItems((prev) => trimAnswered([...prev, ...res.items], answeredIdsRef.current));
      }
    } catch {
      if (gen !== feedGenRef.current) return;
      // Without this the failure left items=[], exhausted=false,
      // loadingMore=false — a completely blank feed with no message and no
      // way to retry. `exhausted` deliberately stays false so the "you've
      // practiced everything" copy can never stand in for a network error.
      setFeedError(true);
    } finally {
      // A stale request must not clear the in-flight flag the NEW request
      // owns (restartFeed already reset it for the new generation).
      if (gen === feedGenRef.current) {
        loadingMoreRef.current = false;
        setLoadingMore(false);
      }
    }
  }, [courseId, exhausted, mode, selectedTypes, requestedTargetLexemeIds]);

  useEffect(() => {
    if (courseId) loadMore();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId, mode, selectedTypes]);

  // Invalidates any in-flight batch and frees the in-flight guard so the
  // effect above can issue the new mode/filter's load immediately.
  function restartFeed() {
    feedGenRef.current += 1;
    loadingMoreRef.current = false;
    setLoadingMore(false);
    setItems([]);
    setExhausted(false);
    setLocked(false);
    setFeedError(false);
    cardRefs.current.clear();
    answeredIdsRef.current.clear();
  }

  // Switching mode restarts the feed: already-loaded items belong to the
  // previous mode, and "exhausted" in one mode says nothing about another.
  function handleModeChange(next: PracticeBatchMode) {
    if (next === mode) return;
    setPracticeModePreference(next);
    restartFeed();
    setMode(next);
  }

  // Toggling a type filter restarts the feed for the same reason mode does:
  // already-loaded items may not match the new filter, and "exhausted"
  // under one filter says nothing about another. Empty set = all types.
  function toggleType(type: string) {
    restartFeed();
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    );
  }

  useEffect(() => {
    if (!SUPPORTS_INTERSECTION_OBSERVER) return;
    // Never auto-retry a failed batch on scroll — that would hammer a down
    // backend and hide the error banner behind a permanent spinner. The
    // learner's explicit Retry button is the only way back in.
    if (feedError) return;
    const targetIndex = items.length - PREFETCH_THRESHOLD;
    const targetItem = targetIndex >= 0 ? items[targetIndex] : undefined;
    const target = targetItem ? cardRefs.current.get(targetItem.id) : null;
    if (!target) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) loadMore();
      },
      { rootMargin: "200px" },
    );
    observer.observe(target);
    return () => observer.disconnect();
  }, [items, loadMore, feedError]);

  function handleAnswered(correct: boolean, xp: number) {
    setCombo((c) => (correct ? c + 1 : 0));
    if (xp > 0) {
      setXpToast(xp);
      window.setTimeout(() => setXpToast(null), 1500);
    }
  }

  if (loadingEligibility) {
    return <div className="page-loading">{t("common.loading")}</div>;
  }

  // Must come BEFORE the locked/empty branch: an unknown eligibility list is
  // not an empty one, and "complete a lesson first" would be a flat lie to a
  // learner who has completed several.
  if (eligibilityError) {
    return (
      <div className="feedback-banner error" role="alert">
        <p style={{ margin: "0 0 10px" }}>{t("practice.eligibility_fetch_error")}</p>
        <button className="btn btn-block" onClick={loadEligibility}>
          {t("common.retry")}
        </button>
      </div>
    );
  }

  if (eligibleCourses.length === 0) {
    return (
      <div className="card" style={{ textAlign: "center" }}>
        <h3>{t("practice.locked_title")}</h3>
        <p className="muted">{t("practice.locked_body")}</p>
        <Link className="btn" to="/courses">
          {t("home.learn")}
        </Link>
      </div>
    );
  }

  if (!courseId) {
    return (
      <div>
        <h2>{t("practice.choose_course")}</h2>
        {eligibleCourses.map((course) => (
          <button
            key={course.id}
            className="card practice-card"
            style={{ width: "100%", textAlign: "start", cursor: "pointer" }}
            onClick={() => setCourseId(course.id)}
          >
            <strong>{course.title}</strong>
          </button>
        ))}
      </div>
    );
  }

  return (
    <div>
      <div className="practice-header">
        {combo > 1 && (
          <span className="badge practice-combo">{t("practice.combo", { count: combo })}</span>
        )}
      </div>

      <div
        role="group"
        aria-label={t("practice.mode_label")}
        style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}
      >
        {PRACTICE_MODES.map((m) => (
          <button
            key={m}
            className={`btn ${m === mode ? "" : "btn-secondary"}`}
            aria-pressed={m === mode}
            onClick={() => handleModeChange(m)}
          >
            {t(`practice.mode_${m}`)}
          </button>
        ))}
      </div>

      <div
        role="group"
        aria-label={t("practice.type_filter_label")}
        style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}
      >
        {PRACTICE_TYPES.map((type) => {
          const active = selectedTypes.includes(type);
          return (
            <button
              key={type}
              className={`btn ${active ? "" : "btn-secondary"}`}
              aria-pressed={active}
              onClick={() => toggleType(type)}
            >
              {t(`practice.type_${type}`)}
            </button>
          );
        })}
      </div>

      {locked && items.length === 0 && (
        <div className="card" style={{ textAlign: "center" }}>
          <h3>{t("practice.locked_title")}</h3>
          <p className="muted">{t("practice.locked_body")}</p>
          <Link className="btn" to="/courses">
            {t("home.learn")}
          </Link>
        </div>
      )}

      {items.map((item) => (
        <div
          key={item.id}
          ref={(el) => {
            if (el) cardRefs.current.set(item.id, el);
            else cardRefs.current.delete(item.id);
          }}
        >
          <PracticeCard
            courseId={courseId}
            item={item}
            onAnswered={(correct, xp) => {
              answeredIdsRef.current.add(item.id);
              handleAnswered(correct, xp);
            }}
          />
        </div>
      ))}

      {loadingMore && <div className="page-loading">{t("common.loading")}</div>}

      {feedError && !loadingMore && (
        <div className="feedback-banner error" role="alert">
          <p style={{ margin: "0 0 10px" }}>
            {items.length > 0
              ? t("practice.load_more_error")
              : t("practice.feed_fetch_error")}
          </p>
          <button className="btn btn-block" onClick={() => loadMore()}>
            {t("common.retry")}
          </button>
        </div>
      )}

      {!SUPPORTS_INTERSECTION_OBSERVER && !exhausted && !feedError && !loadingMore && items.length > 0 && (
        <button className="btn btn-block" onClick={() => loadMore()}>
          {t("practice.load_more")}
        </button>
      )}

      {exhausted && !loadingMore && (
        <p className="muted" style={{ textAlign: "center" }}>
          {items.length > 0 ? t("practice.exhausted") : t("practice.none_yet")}
        </p>
      )}

      {xpToast !== null && (
        <div className="practice-xp-toast stat-xp" role="status">+{xpToast} XP</div>
      )}
    </div>
  );
}
