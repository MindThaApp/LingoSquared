import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { LessonApi, ReviewApi } from "@lingo/shared/api/endpoints";
import { CourseTargetLanguage } from "../components/CourseTargetLanguage";
import { ExerciseRenderer } from "../components/exercises/ExerciseRenderer";
import { TeachingCardView } from "../components/TeachingCardView";
import { EmphasizedText } from "../components/EmphasizedText";
import { ReportIssueButton } from "../components/ReportIssueButton";
import { SpeakButton } from "../components/SpeakButton";
import { QuitConfirm } from "../components/QuitConfirm";
import { ApiError } from "@lingo/shared/api/client";
import { formatCorrectResponse } from "@lingo/shared/lib/formatAnswer";
import { resultStatus } from "@lingo/shared/lib/gradingResult";
import type {
  AnswerResponse,
  AnswerResult,
  Exercise,
  PracticeAnswerResult,
  PracticeItem,
  TeachingCard,
} from "@lingo/shared/api/types";
import { asExerciseType } from "@lingo/shared/api/types";
import { buildLessonBlocks, flattenBlocks } from "../lib/interleave";
import { useCourseLevel } from "../lib/useCourseLevel";

interface QueueItem {
  exercise: Exercise;
  missCount: number;
  isConfirmation: boolean;
  correctAnswerHint?: string;
  // Teaching cards (cumulative) that must have been shown before this
  // exercise - see lib/interleave. Recycled misses keep their original value,
  // which is always already satisfied by the time they come around again.
  cardsBefore: number;
}

interface MissedWord {
  text: string;
  languageCode?: string;
}

// Read-only back/forward review (Ramin UX request, 2026-07-09): every
// teaching card the learner has advanced past, and every exercise attempt
// they've submitted (including recycled misses), gets appended here as it's
// left behind. `reviewCursor` (an index into this array, or `null` for
// "live") drives a purely-additive read-only replay mode - it never
// mutates `teachingIndex`/`queue`/`result` and can never let the learner
// resubmit an already-graded exercise or skip past the live item.
type HistoryEntry =
  | { kind: "teaching"; card: TeachingCard }
  | { kind: "exercise"; exercise: Exercise; response: AnswerResponse | undefined; result: AnswerResult };

const MISS_LIMIT = 2;

// LessonApi.start retry backoff (ms): one initial attempt + 3 retries.
const START_RETRY_DELAYS_MS = [500, 1000, 2000];

// Private-use marker substituted for the interpolated answer so the answer
// value can be wrapped in <bdi dir="auto"> without touching the shared
// locale strings (they live in packages/shared and stay plain
// "Label: {{answer}}"). Without the isolation an RTL answer inside an LTR
// label (or vice versa) reorders the surrounding punctuation.
const ANSWER_MARK = "\uE000";

// Where "back" goes: navigate(-1) only when there is in-app history to go
// back to; a deep-linked / refreshed runner has history.state.idx === 0.
function canGoBackInApp(): boolean {
  const idx = (window.history.state as { idx?: unknown } | null)?.idx;
  return typeof idx === "number" && idx > 0;
}

function sleep(ms: number) {
  return new Promise<void>((resolve) => setTimeout(resolve, ms));
}

function missedWordFromResult(exercise: Exercise, result: AnswerResult): MissedWord {
  return {
    text: formatCorrectResponse(result.correct_response),
    languageCode: exercise.prompt.answer_language_code,
  };
}

export function LessonRunnerPage() {
  const { t } = useTranslation();
  const { lessonId = "" } = useParams();
  const location = useLocation();
  const courseId = (location.state as { courseId?: string } | null)?.courseId;
  const courseLevel = useCourseLevel(courseId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const finishingRef = useRef(false);
  const continueButtonRef = useRef<HTMLButtonElement>(null);

  // Phase B2: review warm-up, shown before teaching cards. `null` means
  // "not checked yet" so the teaching-card phase never flashes before the
  // (silent, best-effort) due-review check resolves.
  const [reviewItems, setReviewItems] = useState<PracticeItem[] | null>(null);
  const [reviewIndex, setReviewIndex] = useState(0);
  const [reviewResult, setReviewResult] = useState<PracticeAnswerResult | null>(null);
  const [reviewSubmitting, setReviewSubmitting] = useState(false);

  const [teachingIndex, setTeachingIndex] = useState(0);

  // Phase B1: exercise queue with error recycling, replacing the old plain
  // index-through-array approach.
  const [queue, setQueue] = useState<QueueItem[] | null>(null);
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [lastResponse, setLastResponse] = useState<AnswerResponse | undefined>();
  const [totalXp, setTotalXp] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [lockedError, setLockedError] = useState<string | null>(null);
  const [missedWords, setMissedWords] = useState<MissedWord[]>([]);
  const [completedCount, setCompletedCount] = useState(0);
  const missedExerciseIds = useState(() => new Set<string>())[0];
  const [submitError, setSubmitError] = useState(false);
  const [finishError, setFinishError] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const [showQuitConfirm, setShowQuitConfirm] = useState(false);

  // Read-only back/forward review state - see the HistoryEntry comment above.
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [reviewCursor, setReviewCursor] = useState<number | null>(null);

  const lessonQuery = useQuery({
    queryKey: ["lesson", lessonId],
    queryFn: () => LessonApi.get(lessonId),
  });

  // Start the lesson, retrying transient failures with backoff. A failed
  // start used to be swallowed, so /complete later 409'd lesson_not_started.
  // speaking_locked is a definitive answer, never retried.
  useEffect(() => {
    if (!lessonId) return;
    let cancelled = false;
    (async () => {
      for (let attempt = 0; ; attempt++) {
        try {
          await LessonApi.start(lessonId);
          return;
        } catch (err) {
          if (err instanceof ApiError && err.code === "speaking_locked") {
            if (!cancelled) setLockedError(t("lesson_runner.speaking_locked"));
            return;
          }
          if (attempt >= START_RETRY_DELAYS_MS.length) return;
          await sleep(START_RETRY_DELAYS_MS[attempt]);
          if (cancelled) return;
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [lessonId, t]);

  // Move focus to Continue when the result banner mounts so Enter continues.
  useEffect(() => {
    if (result) continueButtonRef.current?.focus();
  }, [result]);

  // Best-effort due-review check. Never blocks the lesson: any failure
  // (no courseId available, network error, nothing due) just resolves to
  // an empty list so the warm-up phase is skipped silently.
  useEffect(() => {
    let cancelled = false;
    async function loadReviewWarmup() {
      if (!courseId) {
        if (!cancelled) setReviewItems([]);
        return;
      }
      try {
        const due = await ReviewApi.due();
        const dueHere = due.by_course.find((c) => c.course_id === courseId);
        if (!dueHere || dueHere.due_count === 0) {
          if (!cancelled) setReviewItems([]);
          return;
        }
        const session = await ReviewApi.session(courseId, 2);
        if (!cancelled) setReviewItems(session.items);
      } catch {
        if (!cancelled) setReviewItems([]);
      }
    }
    loadReviewWarmup();
    return () => {
      cancelled = true;
    };
  }, [courseId]);

  useEffect(() => {
    if (lessonQuery.data && queue === null) {
      // Cards and exercises are interleaved (a few cards, then the exercises
      // testing them) instead of all cards up front; teachingIndex still walks
      // the original card order, the queue just gates how far it must go.
      const { blocks } = buildLessonBlocks(lessonQuery.data.teaching, lessonQuery.data.exercises);
      setQueue(
        flattenBlocks(blocks).map(({ exercise, cardsBefore }) => ({
          exercise,
          missCount: 0,
          isConfirmation: false,
          cardsBefore,
        })),
      );
    }
  }, [lessonQuery.data, queue]);

  const teaching = lessonQuery.data?.teaching ?? [];
  const current = queue?.[0];

  async function handleReviewAnswer(response: AnswerResponse) {
    const item = reviewItems?.[reviewIndex];
    if (!item) return;
    setReviewSubmitting(true);
    try {
      const res = await ReviewApi.answer(item.id, response);
      setReviewResult(res);
    } catch {
      // Item may have expired between fetch and answer - skip it rather
      // than blocking the lesson on the review system.
      setReviewIndex((i) => i + 1);
    } finally {
      setReviewSubmitting(false);
    }
  }

  function handleReviewSkip() {
    setReviewResult(null);
    setReviewIndex(reviewItems?.length ?? 0);
  }

  function handleReviewContinue() {
    setReviewResult(null);
    setReviewIndex((i) => i + 1);
  }

  async function handleAnswer(response: AnswerResponse) {
    if (!current) return;
    setSubmitting(true);
    setLastResponse(response);
    setSubmitError(false);
    try {
      const res = await LessonApi.answer(current.exercise.id, response);
      setResult(res);
      setTotalXp((xp) => xp + res.xp_awarded);
    } catch {
      // Network failure or unexpected server error mid-lesson: don't let it
      // become an unhandled rejection that leaves the UI just sitting there.
      // The learner's chosen answer (lastResponse) is preserved so Retry can
      // resubmit it without making them re-answer.
      setSubmitError(true);
    } finally {
      setSubmitting(false);
    }
  }

  function handleRetryAnswer() {
    if (lastResponse) handleAnswer(lastResponse);
  }

  async function finishLesson() {
    // Re-entry guard: the ref flips synchronously, unlike state, so a double
    // click / stray second call can never POST /complete twice.
    if (finishingRef.current) return;
    finishingRef.current = true;
    setFinishing(true);
    setFinishError(false);
    try {
      let completion;
      try {
        completion = await LessonApi.complete(lessonId);
      } catch (err) {
        if (err instanceof ApiError && err.code === "lesson_not_started") {
          // The initial start never landed: start now, retry complete once.
          await LessonApi.start(lessonId);
          completion = await LessonApi.complete(lessonId);
        } else {
          throw err;
        }
      }
      for (const key of ["progress", "xp", "streak", "quests", "reviews-due", "units"]) {
        queryClient.invalidateQueries({ queryKey: [key] });
      }
      navigate(`/lessons/${lessonId}/done`, {
        state: { completion, totalXp, missedWords },
      });
    } catch {
      // Don't lose the just-finished lesson's completion silently -- offer
      // a retry rather than leaving the learner on a dead-end screen.
      finishingRef.current = false;
      setFinishing(false);
      setFinishError(true);
    }
  }

  function handleQuit() {
    // courseId only exists in route state, not the URL, so there's no
    // reliable unit-lesson-list path to construct directly here. A
    // deep-linked runner has no in-app history, so fall back to home.
    if (canGoBackInApp()) navigate(-1);
    else navigate("/");
  }

  function renderAnswerLine(key: "lesson_runner.your_answer" | "lesson_runner.correct_answer", answer: string) {
    const parts = t(key, { answer: ANSWER_MARK }).split(ANSWER_MARK);
    return parts.map((part, i) => (
      <Fragment key={i}>
        {i > 0 && <bdi dir="auto">{answer}</bdi>}
        {part}
      </Fragment>
    ));
  }

  function handleReviewBack() {
    setReviewCursor((c) => (c === null ? history.length - 1 : Math.max(0, c - 1)));
  }

  function handleReviewForward() {
    setReviewCursor((c) => {
      if (c === null) return c;
      return c >= history.length - 1 ? null : c + 1;
    });
  }

  // Shared with the live exercise-queue banner below - review mode reuses
  // the exact same tri-state styling/copy rather than a second banner
  // system, just without a Continue button and with the learner's original
  // response line included.
  function renderResultBanner(
    bannerResult: AnswerResult,
    options?: { response?: AnswerResponse; footer?: ReactNode },
  ) {
    const status = resultStatus(bannerResult);
    return (
      // role="status" (implicit aria-live="polite") so screen readers announce
      // the grading result the moment the banner mounts - without it this
      // banner is completely silent to non-sighted users.
      <div className={`feedback-banner ${status}`} role="status">
        <p style={{ margin: "0 0 6px" }}>
          {status === "correct" && t("lesson_runner.correct")}
          {status === "almost" && t("lesson_runner.almost")}
          {status === "incorrect" && t("lesson_runner.incorrect")}
        </p>
        {options?.response !== undefined && (
          <p style={{ margin: "0 0 6px", fontWeight: 400 }}>
            {renderAnswerLine("lesson_runner.your_answer", formatCorrectResponse(options.response))}
          </p>
        )}
        {status !== "correct" && (
          <p style={{ margin: "0 0 6px", fontWeight: 400 }}>
            {renderAnswerLine("lesson_runner.correct_answer", formatCorrectResponse(bannerResult.correct_response))}
          </p>
        )}
        {bannerResult.feedback && (
          <p style={{ margin: "0 0 10px", fontWeight: 400 }}>
            <EmphasizedText text={bannerResult.feedback} />
          </p>
        )}
        {options?.footer}
      </div>
    );
  }

  function handleContinue() {
    if (!result || !queue || !current) return;
    const rest = queue.slice(1);
    setHistory((h) => [...h, { kind: "exercise", exercise: current.exercise, response: lastResponse, result }]);
    setResult(null);
    setLastResponse(undefined);

    const resolved = result.correct || current.isConfirmation;

    if (!result.correct && !missedExerciseIds.has(current.exercise.id)) {
      missedExerciseIds.add(current.exercise.id);
      setMissedWords((prev) => [...prev, missedWordFromResult(current.exercise, result)]);
    }

    let nextQueue: QueueItem[];
    if (resolved) {
      nextQueue = rest;
      setCompletedCount((n) => n + 1);
    } else {
      const newMissCount = current.missCount + 1;
      nextQueue = [
        ...rest,
        {
          exercise: current.exercise,
          cardsBefore: current.cardsBefore,
          missCount: newMissCount,
          isConfirmation: newMissCount >= MISS_LIMIT,
          correctAnswerHint:
            newMissCount >= MISS_LIMIT ? formatCorrectResponse(result.correct_response) : undefined,
        },
      ];
    }

    if (nextQueue.length === 0) {
      finishLesson();
    } else {
      setQueue(nextQueue);
    }
  }

  if (lockedError) {
    return (
      <div className="lesson-runner-page">
        <p className="error-text">{lockedError}</p>
        <button onClick={handleQuit}>{t("lesson_runner.go_back")}</button>
      </div>
    );
  }

  if (finishError) {
    return (
      <div className="card" style={{ textAlign: "center" }}>
        <p className="muted">{t("lesson_runner.finish_error")}</p>
        <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
          <button className="btn" onClick={finishLesson}>
            {t("common.retry")}
          </button>
          <button className="btn btn-secondary" onClick={handleQuit}>
            {t("lesson_runner.go_back")}
          </button>
        </div>
      </div>
    );
  }

  // Replaces the exercise while /complete is in flight so the last answer
  // can't be re-submitted (handleContinue clears `result` before this).
  if (finishing) {
    return (
      <div className="page-loading" role="status">
        {t("lesson_runner.saving", { defaultValue: "Saving…" })}
      </div>
    );
  }

  // Must be checked BEFORE the loading branch (isLoading goes false on error)
  // and before the phase branches below: without it a failed GET /lessons/{id}
  // fell all the way through to "No exercises in this lesson." — a dead end
  // with neither an explanation, a retry, nor a way back out.
  if (lessonQuery.isError) {
    return (
      <div className="card" style={{ textAlign: "center" }}>
        <p className="muted">{t("lesson_runner.load_error")}</p>
        <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
          <button className="btn" onClick={() => lessonQuery.refetch()}>
            {t("common.retry")}
          </button>
          <button className="btn btn-secondary" onClick={handleQuit}>
            {t("lesson_runner.go_back")}
          </button>
        </div>
      </div>
    );
  }

  if (lessonQuery.isLoading || reviewItems === null) {
    return <div className="page-loading">{t("lesson_runner.loading")}</div>;
  }

  // Review warm-up phase (B2) — up to 2 items, before teaching cards.
  if (reviewIndex < reviewItems.length) {
    const item = reviewItems[reviewIndex];
    return (
      <div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <span className="badge" style={{ display: "inline-block" }}>
            {t("lesson_runner.review_warmup_label")}
          </span>
          <button
            type="button"
            className="btn-icon-toggle"
            aria-label={t("lesson_runner.exit_label")}
            onClick={() => setShowQuitConfirm(true)}
          >
            <X size={18} />
          </button>
        </div>
        <p className="muted" style={{ margin: "0 0 12px" }}>
          {t("lesson_runner.review_warmup_hint", { count: reviewItems.length })}
        </p>
        <CourseTargetLanguage courseId={courseId}><ExerciseRenderer
          key={item.id}
          exercise={{ id: item.id, type: asExerciseType(item.type), order: 0, prompt: item.prompt }}
          onAnswer={handleReviewAnswer}
          disabled={reviewSubmitting || Boolean(reviewResult)}
          gradedResult={
            reviewResult
              ? { correct: reviewResult.correct, correctResponse: reviewResult.correct_response }
              : undefined
          }
        /></CourseTargetLanguage>
        {reviewResult && (() => {
          const status = resultStatus(reviewResult);
          return (
            <div className={`feedback-banner ${status}`} role="status">
              <p style={{ margin: "0 0 6px" }}>
                {status === "correct" && t("lesson_runner.correct")}
                {status === "almost" && t("lesson_runner.almost")}
                {status === "incorrect" && t("lesson_runner.incorrect")}
              </p>
              {status !== "correct" && (
                <p style={{ margin: "0 0 6px", fontWeight: 400 }}>
                  {renderAnswerLine(
                    "lesson_runner.correct_answer",
                    formatCorrectResponse(reviewResult.correct_response),
                  )}
                </p>
              )}
              <button className="btn btn-block" onClick={handleReviewContinue}>
                {t("lesson_runner.continue")}
              </button>
            </div>
          );
        })()}
        <div style={{ marginTop: 12, textAlign: "center" }}>
          <button type="button" className="btn btn-secondary" onClick={handleReviewSkip}>
            {t("lesson_runner.review_warmup_skip")}
          </button>
        </div>
        {showQuitConfirm && (
          <QuitConfirm
            message={t("lesson_runner.quit_confirm_message")}
            onKeepGoing={() => setShowQuitConfirm(false)}
            onQuit={handleQuit}
          />
        )}
      </div>
    );
  }

  // Read-only review of a previously-shown teaching card or exercise
  // attempt (Ramin UX request, 2026-07-09). Takes priority over the live
  // teaching/exercise phases below whenever the learner has stepped back;
  // never touches teachingIndex/queue/result, so the live phase resumes
  // exactly where it left off once reviewCursor returns to null.
  if (reviewCursor !== null) {
    const entry = history[reviewCursor];
    const canGoBack = reviewCursor > 0;
    return (
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
          <button
            type="button"
            className="btn-icon-toggle"
            aria-label={t("lesson_runner.review_back_label")}
            onClick={handleReviewBack}
            disabled={!canGoBack}
          >
            <ChevronLeft size={18} />
          </button>
          <span className="badge" style={{ flex: 1, textAlign: "center" }}>
            {t("lesson_runner.review_mode_label")}
          </span>
          <button
            type="button"
            className="btn-icon-toggle"
            aria-label={t("lesson_runner.review_forward_label")}
            onClick={handleReviewForward}
          >
            <ChevronRight size={18} />
          </button>
          <button
            type="button"
            className="btn-icon-toggle"
            aria-label={t("lesson_runner.exit_label")}
            onClick={() => setShowQuitConfirm(true)}
          >
            <X size={18} />
          </button>
        </div>
        {entry.kind === "teaching" ? (
          <TeachingCardView card={entry.card} />
        ) : (
          <>
            <CourseTargetLanguage courseId={courseId}><ExerciseRenderer
              key={`review-${reviewCursor}`}
              exercise={entry.exercise}
              onAnswer={() => {}}
              disabled
              gradedResult={{ correct: entry.result.correct, correctResponse: entry.result.correct_response }}
            /></CourseTargetLanguage>
            {renderResultBanner(entry.result, { response: entry.response })}
          </>
        )}
        {showQuitConfirm && (
          <QuitConfirm
            message={t("lesson_runner.quit_confirm_message")}
            onKeepGoing={() => setShowQuitConfirm(false)}
            onQuit={handleQuit}
          />
        )}
      </div>
    );
  }

  // Show cards up to the next exercise's `cardsBefore` (all remaining cards
  // when there is no exercise to gate on, e.g. a cards-only lesson).
  const cardsToShow = current ? Math.min(current.cardsBefore, teaching.length) : teaching.length;
  if (teachingIndex < cardsToShow) {
    const card = teaching[teachingIndex];
    // "Start practice" only when the next thing after this card is an exercise.
    const isLast = current !== undefined && teachingIndex === cardsToShow - 1;
    const pct = ((teachingIndex + 1) / teaching.length) * 100;
    return (
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
          {history.length > 0 && (
            <button
              type="button"
              className="btn-icon-toggle"
              aria-label={t("lesson_runner.review_back_label")}
              onClick={handleReviewBack}
            >
              <ChevronLeft size={18} />
            </button>
          )}
          <div className="progress-track" style={{ flex: 1 }}>
            <div className="progress-fill" style={{ width: `${pct}%` }} />
          </div>
          <button
            type="button"
            className="btn-icon-toggle"
            aria-label={t("lesson_runner.exit_label")}
            onClick={() => setShowQuitConfirm(true)}
          >
            <X size={18} />
          </button>
        </div>
        <span className="muted">
          {t("lesson_runner.learn_progress", { current: teachingIndex + 1, total: teaching.length })}
        </span>
        <TeachingCardView card={card} />
        <button
          className="btn btn-block"
          onClick={() => {
            setHistory((h) => [...h, { kind: "teaching", card }]);
            setTeachingIndex((i) => i + 1);
          }}
        >
          {isLast ? t("lesson_runner.start_practice") : t("lesson_runner.next")}
        </button>
        {showQuitConfirm && (
          <QuitConfirm
            message={t("lesson_runner.quit_confirm_message")}
            onKeepGoing={() => setShowQuitConfirm(false)}
            onQuit={handleQuit}
          />
        )}
      </div>
    );
  }

  if (!current) return <p>{t("lesson_runner.no_exercises")}</p>;

  // Progress reflects the growing queue honestly: completed exercises out
  // of (completed + still-queued), so a recycled miss visibly grows the
  // denominator instead of the bar silently jumping backward or lying
  // about how much work is actually left.
  const totalSoFar = completedCount + queue!.length;
  const pct = totalSoFar > 0 ? (completedCount / totalSoFar) * 100 : 0;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        {history.length > 0 && (
          <button
            type="button"
            className="btn-icon-toggle"
            aria-label={t("lesson_runner.review_back_label")}
            onClick={handleReviewBack}
          >
            <ChevronLeft size={18} />
          </button>
        )}
        <div className="progress-track" style={{ flex: 1 }}>
          <div className="progress-fill" style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
        </div>
        <span className="stat-xp" style={{ fontWeight: 700, whiteSpace: "nowrap" }}>
          ⭐ {totalXp}
        </span>
        <button
          type="button"
          className="btn-icon-toggle"
          aria-label={t("lesson_runner.exit_label")}
          onClick={() => setShowQuitConfirm(true)}
        >
          <X size={18} />
        </button>
      </div>
      {current.isConfirmation && result === null && (
        <div className="feedback-banner incorrect" role="status" style={{ marginBottom: 12 }}>
          <p style={{ margin: 0 }}>
            {t("lesson_runner.confirmation_hint", {
              answer: current.correctAnswerHint ?? "",
            })}
          </p>
        </div>
      )}
      <CourseTargetLanguage courseId={courseId}><ExerciseRenderer
        key={`${current.exercise.id}-${current.missCount}`}
        exercise={current.exercise}
        onAnswer={handleAnswer}
        courseLevel={courseLevel}
        lessonExercises={lessonQuery.data?.exercises}
        answerHint={current.correctAnswerHint}
        disabled={submitting || Boolean(result) || submitError}
        gradedResult={
          result ? { correct: result.correct, correctResponse: result.correct_response } : undefined
        }
      /></CourseTargetLanguage>
      {submitError && !result && (
        <div className="feedback-banner error" role="alert">
          <p style={{ margin: "0 0 10px" }}>{t("lesson_runner.submit_error")}</p>
          <button className="btn btn-block" onClick={handleRetryAnswer} disabled={submitting}>
            {t("common.retry")}
          </button>
        </div>
      )}
      {result &&
        renderResultBanner(result, {
          footer: (
            <button ref={continueButtonRef} className="btn btn-block" onClick={handleContinue}>
              {t("lesson_runner.continue")}
            </button>
          ),
        })}
      <div style={{ marginTop: 12, textAlign: "center" }}>
        <ReportIssueButton
          lastResponse={lastResponse}
          onSubmit={(category, description, response) =>
            LessonApi.reportIssue(current.exercise.id, category, description, response)
          }
        />
      </div>
      {showQuitConfirm && (
        <QuitConfirm
          message={t("lesson_runner.quit_confirm_message")}
          onKeepGoing={() => setShowQuitConfirm(false)}
          onQuit={handleQuit}
        />
      )}
    </div>
  );
}

export function MissedWordsSummary({ words }: { words: MissedWord[] }) {
  const { t } = useTranslation();
  if (words.length === 0) return null;
  return (
    <div className="card" style={{ marginTop: 16, textAlign: "start" }}>
      <h3 style={{ marginTop: 0 }}>{t("lesson_complete.missed_words_title")}</h3>
      <p className="muted" style={{ marginTop: 0 }}>
        {t("lesson_complete.missed_words_subtitle")}
      </p>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {words.map((word, i) => (
          <li
            key={i}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 0",
              borderTop: i > 0 ? "1px solid var(--border)" : undefined,
            }}
          >
            <span>{word.text}</span>
            {word.languageCode && <SpeakButton text={word.text} languageCode={word.languageCode} />}
          </li>
        ))}
      </ul>
    </div>
  );
}
