import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { X } from "lucide-react";
import { PlacementApi } from "@lingo/shared/api/endpoints";
import { ApiError } from "@lingo/shared/api/client";
import { ExerciseRenderer } from "../components/exercises/ExerciseRenderer";
import { QuitConfirm } from "../components/QuitConfirm";
import { formatCorrectResponse } from "@lingo/shared/lib/formatAnswer";
import { resultStatus } from "@lingo/shared/lib/gradingResult";
import { answerDirectionForExercise } from "@lingo/shared/lib/scripts";
import { resultPassed } from "../lib/answerOutcome";
import { AlmostFeedback } from "../components/AlmostFeedback";
import { setPlacementRecommendation } from "../lib/placementPreferences";
import { setLevelPreference, type SelfReportedLevel } from "../lib/levelPreferences";
import type {
  AnswerResponse,
  PlacementAnswerIn,
  PlacementAnswerResult,
  PlacementProbe,
  PlacementRecommendation,
  PlacementSet,
} from "@lingo/shared/api/types";

type Phase = "loading" | "unavailable" | "in_progress" | "scoring" | "scoring_error" | "done";

// Best-effort backward-compat bridge into the pre-existing self-report
// preference (levelPreferences.ts), which CourseUnitsPage still falls back
// to when no placement recommendation exists (e.g. a different course the
// learner hasn't placement-tested into). Coarse by design -- the placement
// recommendation itself (a specific unit) is always the authoritative
// value once set; see placementPreferences.ts.
function toSelfReportedLevel(level: string): SelfReportedLevel {
  if (level === "A1") return "beginner";
  if (level === "A2" || level === "B1") return "some_basics";
  return "conversational";
}

export function PlacementTestPage() {
  const { t } = useTranslation();
  const { courseId = "" } = useParams();
  const navigate = useNavigate();

  const [phase, setPhase] = useState<Phase>("loading");
  const [placementSet, setPlacementSet] = useState<PlacementSet | null>(null);
  const [index, setIndex] = useState(0);
  const [blockCorrect, setBlockCorrect] = useState(0);
  const [result, setResult] = useState<PlacementAnswerResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [lastResponse, setLastResponse] = useState<AnswerResponse | undefined>();
  const [submitError, setSubmitError] = useState(false);
  const [finalResult, setFinalResult] = useState<PlacementRecommendation | null>(null);
  const [showQuitConfirm, setShowQuitConfirm] = useState(false);

  // The answers accumulated so far, kept in a ref alongside state so the
  // scoring retry button (rendered after an async failure) always resends
  // the exact same list rather than a stale closure's copy.
  const answersRef = useRef<PlacementAnswerIn[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function start() {
      try {
        const res = await PlacementApi.start(courseId);
        if (cancelled) return;
        if (res.items.length === 0) {
          setPhase("unavailable");
        } else {
          setPlacementSet(res);
          setPhase("in_progress");
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && (err.code === "placement_unavailable" || err.code === "course_not_found")) {
          setPhase("unavailable");
        } else {
          setPhase("unavailable");
        }
      }
    }
    start();
    return () => {
      cancelled = true;
    };
  }, [courseId]);

  const items: PlacementProbe[] = placementSet?.items ?? [];
  const blockSize = placementSet?.block_size ?? 4;
  const passThreshold = placementSet?.pass_threshold ?? 3;
  const current = items[index];

  async function handleAnswer(response: AnswerResponse) {
    if (!current) return;
    setSubmitting(true);
    setLastResponse(response);
    setSubmitError(false);
    try {
      const res = await PlacementApi.answer(courseId, current.id, response);
      setResult(res);
    } catch {
      setSubmitError(true);
    } finally {
      setSubmitting(false);
    }
  }

  function handleRetryAnswer() {
    if (lastResponse) handleAnswer(lastResponse);
  }

  async function finish(answers: PlacementAnswerIn[]) {
    answersRef.current = answers;
    setPhase("scoring");
    try {
      const rec = await PlacementApi.result(courseId, answers);
      setFinalResult(rec);
      setPlacementRecommendation(courseId, { unitId: rec.recommended_unit_id, level: rec.recommended_level });
      setLevelPreference(courseId, toSelfReportedLevel(rec.recommended_level));
      setPhase("done");
    } catch {
      setPhase("scoring_error");
    }
  }

  function retryFinish() {
    finish(answersRef.current);
  }

  // Block-of-4 flow with early-exit (docs/PLACEMENT_TEST_SPEC.md §2.1):
  // administer levels in ascending order, 4 items per level; a level block
  // is passed at >= pass_threshold correct. Stop at the first FAILED block,
  // or after the highest available block passes.
  async function handleContinue() {
    if (!current || !lastResponse) return;
    // "almost" counts toward the block pass, same as correct.
    const wasCorrect = result ? resultPassed(result) : false;
    const newAnswers = [...answersRef.current, { exercise_id: current.id, response: lastResponse }];
    const newBlockCorrect = blockCorrect + (wasCorrect ? 1 : 0);
    const posInBlock = index % blockSize;
    const isLastOfBlock = posInBlock === blockSize - 1 || index === items.length - 1;

    answersRef.current = newAnswers;
    setResult(null);
    setLastResponse(undefined);

    if (isLastOfBlock) {
      const passedBlock = newBlockCorrect >= passThreshold;
      const isLastItemOverall = index === items.length - 1;
      if (!passedBlock || isLastItemOverall) {
        await finish(newAnswers);
        return;
      }
      setBlockCorrect(0);
      setIndex(index + 1);
      return;
    }
    setBlockCorrect(newBlockCorrect);
    setIndex(index + 1);
  }

  function handleQuit() {
    navigate(-1);
  }

  if (phase === "loading" || phase === "scoring") {
    return <div className="page-loading">{t("placement.loading")}</div>;
  }

  if (phase === "scoring_error") {
    return (
      <div className="card" style={{ textAlign: "center" }}>
        <p className="muted">{t("placement.scoring_error")}</p>
        <button className="btn" onClick={retryFinish}>
          {t("common.retry")}
        </button>
      </div>
    );
  }

  if (phase === "unavailable") {
    return (
      <div className="card" style={{ textAlign: "center" }}>
        <div style={{ fontSize: "3rem" }}>🤔</div>
        <h2>{t("placement.unavailable_title")}</h2>
        <p className="muted">{t("placement.unavailable_body")}</p>
        <button className="btn" onClick={() => navigate(-1)}>
          {t("placement.go_back")}
        </button>
      </div>
    );
  }

  if (phase === "done" && finalResult) {
    return (
      <div style={{ textAlign: "center", paddingTop: 20 }}>
        <div style={{ fontSize: "4rem", marginBottom: 8 }}>🎯</div>
        <h1>{t("placement.result_title")}</h1>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, margin: "8px 0" }}>
          <span className="badge">{finalResult.recommended_level}</span>
          <span className="muted">{t(`cefr.${finalResult.recommended_level}`)}</span>
        </div>
        <p className="muted">{t("placement.result_rationale")}</p>
        <div className="card" style={{ marginTop: 16, textAlign: "start", maxWidth: 420, marginInline: "auto" }}>
          <h3 style={{ marginTop: 0 }}>{t("placement.result_per_level_title")}</h3>
          <ul style={{ margin: 0, paddingInlineStart: 20 }}>
            {Object.entries(finalResult.per_level).map(([level, stat]) => (
              <li key={level}>
                {t("placement.result_per_level_score", { level, correct: stat.correct, total: stat.total })}
              </li>
            ))}
          </ul>
        </div>
        <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 24, flexWrap: "wrap" }}>
          <Link
            className="btn"
            to={`/units/${finalResult.recommended_unit_id}`}
            state={{ courseId }}
          >
            {t("placement.result_cta", { unit: finalResult.recommended_unit_title })}
          </Link>
          <Link className="btn btn-secondary" to="/courses">
            {t("placement.result_back_to_courses")}
          </Link>
        </div>
      </div>
    );
  }

  if (!current) return null;

  const pct = (index / items.length) * 100;

  return (
    <div>
      <div className="card" style={{ marginBottom: 16, textAlign: "center", background: "var(--surface-2)" }}>
        <strong>{t("placement.header")}</strong>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <div className="progress-track" style={{ flex: 1 }}>
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <span className="muted" style={{ whiteSpace: "nowrap" }}>
          {t("placement.level_progress", {
            level: current.level,
            current: (index % blockSize) + 1,
            total: blockSize,
          })}
        </span>
        <button
          type="button"
          className="btn-icon-toggle"
          aria-label={t("placement.exit_label")}
          onClick={() => setShowQuitConfirm(true)}
        >
          <X size={18} />
        </button>
      </div>
      <ExerciseRenderer
        key={current.id}
        exercise={{ id: current.id, type: current.type, order: current.order, prompt: current.prompt }}
        onAnswer={handleAnswer}
        disabled={submitting || Boolean(result) || submitError}
        gradedResult={
          result ? { correct: result.correct, correctResponse: result.correct_response } : undefined
        }
      />
      {submitError && !result && (
        <div className="feedback-banner error" role="alert">
          <p style={{ margin: "0 0 10px" }}>{t("placement.submit_error")}</p>
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
                correct={formatCorrectResponse(result.correct_response)}
                dir={answerDirectionForExercise({ id: current.id, type: current.type, order: current.order, prompt: current.prompt })}
              />
              <button className="btn btn-block" onClick={handleContinue}>
                {t("placement.continue")}
              </button>
            </div>
          );
        }
        return (
          // role="status" (implicit aria-live="polite") - announces the grading
          // result to screen readers when the banner mounts.
          <div className={`feedback-banner ${status}`} role="status">
            <p style={{ margin: "0 0 6px" }}>
              {status === "correct" && t("placement.correct")}
              {status === "incorrect" && t("placement.incorrect")}
            </p>
            {status !== "correct" && (
              <p style={{ margin: "0 0 10px", fontWeight: 400 }}>
                {t("placement.correct_answer", { answer: formatCorrectResponse(result.correct_response) })}
              </p>
            )}
            <button className="btn btn-block" onClick={handleContinue}>
              {t("placement.continue")}
            </button>
          </div>
        );
      })()}
      {showQuitConfirm && (
        <QuitConfirm
          message={t("placement.quit_confirm_message")}
          onKeepGoing={() => setShowQuitConfirm(false)}
          onQuit={handleQuit}
        />
      )}
    </div>
  );
}
