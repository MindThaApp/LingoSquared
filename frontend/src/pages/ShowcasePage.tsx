import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, Headphones, SlidersHorizontal } from "lucide-react";
import { CatalogApi, LessonApi } from "@lingo/shared/api/endpoints";
import { formatCorrectResponse } from "@lingo/shared/lib/formatAnswer";
import { resultStatus } from "@lingo/shared/lib/gradingResult";
import type {
  AnswerResponse,
  AnswerResult,
  Exercise,
  Lesson,
  TeachingCard,
} from "@lingo/shared/api/types";
import { ReadingPassageWithQuestions } from "../components/ReadingPassageWithQuestions";
import { ExerciseRenderer } from "../components/exercises/ExerciseRenderer";
import { EmphasizedText } from "../components/EmphasizedText";

// Convenience fallbacks: known dev lesson ids tried first, then real
// discovery if they don't contain what we expect (ids vary by DB).
const READING_CANDIDATE_ID = "d2fa0c7c-540e-4133-87d9-bde3f947993f";
const DICTATION_CANDIDATE_ID = "54467356-644e-4c29-84e4-1f809d2a95f0";

interface ReadingSample {
  passageCard: TeachingCard;
  questions: Exercise[];
}

interface ShowcaseSamples {
  reading: ReadingSample | null;
  dictation: Exercise | null;
}

function isGlossedReadingCard(card: TeachingCard): boolean {
  return (
    card.kind === "reading" &&
    Boolean(card.glosses) &&
    Object.keys(card.glosses ?? {}).length > 0
  );
}

// Fold a fetched lesson into whatever we still need. Mutates `found` and
// short-circuits: once both slots are filled the walk stops.
function absorbLesson(lesson: Lesson, found: ShowcaseSamples): void {
  if (!found.reading) {
    const passageCard = lesson.teaching.find(isGlossedReadingCard);
    const questions = lesson.exercises.filter((e) => e.type === "reading_comprehension");
    if (passageCard && questions.length > 0) {
      found.reading = { passageCard, questions };
    }
  }
  if (!found.dictation) {
    const dictation = lesson.exercises.find((e) => e.type === "dictation");
    if (dictation) found.dictation = dictation;
  }
}

async function discoverSamples(): Promise<ShowcaseSamples> {
  const found: ShowcaseSamples = { reading: null, dictation: null };

  // 1) Try the known dev candidates first (cheap, usually enough).
  for (const id of [READING_CANDIDATE_ID, DICTATION_CANDIDATE_ID]) {
    try {
      absorbLesson(await LessonApi.get(id), found);
    } catch {
      // Ignore — these ids vary by DB; fall through to discovery.
    }
    if (found.reading && found.dictation) return found;
  }

  // 2) Walk the Dutch (nl) B2 catalog until both samples are satisfied.
  let courses;
  try {
    courses = await CatalogApi.allCourses();
  } catch {
    return found;
  }
  const nl = courses.filter((c) => c.target_language === "nl");
  const b2 = nl.filter((c) => c.level === "B2");
  const candidates = b2.length > 0 ? b2 : nl;

  for (const course of candidates) {
    let units;
    try {
      units = await CatalogApi.units(course.id);
    } catch {
      continue;
    }
    for (const unit of units) {
      let lessons;
      try {
        lessons = await CatalogApi.lessons(unit.id);
      } catch {
        continue;
      }
      for (const lessonSummary of lessons) {
        try {
          absorbLesson(await LessonApi.get(lessonSummary.id), found);
        } catch {
          continue;
        }
        if (found.reading && found.dictation) return found;
      }
    }
  }
  return found;
}

// Local one-shot grading for the standalone dictation demo, mirroring the
// per-question flow in ReadingPassageWithQuestions.
function DictationDemo({ exercise }: { exercise: Exercise }) {
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleAnswer(response: AnswerResponse) {
    if (result || submitting) return;
    setSubmitting(true);
    try {
      setResult(await LessonApi.answer(exercise.id, response));
    } catch {
      // Allow another attempt on failure.
    } finally {
      setSubmitting(false);
    }
  }

  const status = result ? resultStatus(result) : null;
  return (
    <>
      <ExerciseRenderer
        exercise={exercise}
        onAnswer={handleAnswer}
        disabled={submitting || Boolean(result)}
        gradedResult={
          result ? { correct: result.correct, correctResponse: result.correct_response } : undefined
        }
      />
      {result && status && (
        <div className={`feedback-banner ${status}`} role="status">
          <p style={{ margin: "0 0 6px" }}>
            {status === "correct" && "Correct!"}
            {status === "almost" && "Almost — check your spelling."}
            {status === "incorrect" && "Not quite."}
          </p>
          {status !== "correct" && (
            <p style={{ margin: 0, fontWeight: 400 }}>
              Answer: {formatCorrectResponse(result.correct_response)}
            </p>
          )}
          {result.feedback && (
            <p style={{ margin: "6px 0 0", fontWeight: 400 }}>
              <EmphasizedText text={result.feedback} />
            </p>
          )}
        </div>
      )}
    </>
  );
}

function SectionHeader({
  icon,
  title,
  subtitle,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <div style={{ marginBottom: 8 }}>
      <h2 style={{ display: "flex", alignItems: "center", gap: 8, margin: "0 0 4px" }}>
        {icon}
        {title}
      </h2>
      <p className="muted" style={{ margin: 0 }}>
        {subtitle}
      </p>
    </div>
  );
}

// "Try the new features" showcase — surfaces the reading + comprehension
// combined view, the dictation exercise, and a pointer to skill-targeted
// practice, discovering live Dutch content to demo them honestly.
export default function ShowcasePage() {
  const samplesQuery = useQuery({
    queryKey: ["showcase-samples"],
    queryFn: discoverSamples,
    staleTime: 5 * 60 * 1000,
  });

  return (
    <div>
      <div className="home-hero">
        <h1>Try the new features</h1>
        <p className="muted" style={{ maxWidth: 560 }}>
          A quick tour of what's new: read a passage with tap-to-gloss and answer
          questions without losing your place, type what you hear, and jump into
          practice targeted at a specific skill.
        </p>
      </div>

      {samplesQuery.isLoading && (
        <div className="page-loading">Finding sample content…</div>
      )}

      {samplesQuery.isError && (
        <div className="feedback-banner error" role="alert" style={{ marginBottom: 16 }}>
          <p style={{ margin: "0 0 10px" }}>Couldn't load the showcase content.</p>
          <button className="btn btn-block" onClick={() => samplesQuery.refetch()}>
            Retry
          </button>
        </div>
      )}

      {samplesQuery.data && (
        <>
          <section className="card" style={{ marginBottom: 16 }}>
            <SectionHeader
              icon={<BookOpen size={22} style={{ color: "var(--accent)" }} />}
              title="Reading + comprehension"
              subtitle="The passage stays pinned above while you answer — tap any word for its gloss."
            />
            {samplesQuery.data.reading ? (
              <ReadingPassageWithQuestions
                passageCard={samplesQuery.data.reading.passageCard}
                questions={samplesQuery.data.reading.questions}
              />
            ) : (
              <p className="muted" style={{ margin: 0 }}>
                No reading sample found in the current content.
              </p>
            )}
          </section>

          <section className="card" style={{ marginBottom: 16 }}>
            <SectionHeader
              icon={<Headphones size={22} style={{ color: "var(--accent)" }} />}
              title="Dictation"
              subtitle="Listen, then type exactly what you hear."
            />
            {samplesQuery.data.dictation ? (
              <DictationDemo exercise={samplesQuery.data.dictation} />
            ) : (
              <p className="muted" style={{ margin: 0 }}>
                No dictation sample found in the current content.
              </p>
            )}
          </section>
        </>
      )}

      <section className="card continue-card">
        <div className="continue-info">
          <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <SlidersHorizontal size={20} style={{ color: "var(--accent)" }} />
            Skill-targeted practice
          </h3>
          <span className="muted">Head to practice and try filtering by exercise type.</span>
        </div>
        <Link className="btn" to="/practice">
          Practice
        </Link>
      </section>
    </div>
  );
}
