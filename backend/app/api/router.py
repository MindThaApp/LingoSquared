import json
import mimetypes
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.rate_limit import RateLimiter, register_limiter
from app.core.security import create_token, hash_password, verify_password
from app.db.session import get_db
from app.models import *
from app.schemas.api import *
from app.api.deps import current_user, optional_current_user, admin_user
from app.services.progress import activity_day_bounds, record_activity, resolve_user_tz, stats_for, valid_timezone_or_none
from app.services.quests import daily_quests_for
from app.review.sm2 import schedule
from app.review.grading import grade_answer, FREE_TEXT_EXERCISE_TYPES
from app.services import tts as tts_service
from app.practice.service import (
    generate_batch,
    generate_checkpoint,
    generate_review_batch,
    generate_review_retry,
)
from app.content.service import (
    export_content,
    import_content,
    import_practice_templates,
    validation_errors,
)

router=APIRouter()
def fail(status,code,message,**details):
    raise HTTPException(
        status,
        detail={"code":code,"message":message,**details},
    )

# Rate limiting: per-IP for the unauthenticated auth endpoints (brute-force
# login protection, registration-abuse prevention), per-account for the
# answer endpoints (same resource-exhaustion-adjacent surface as the
# AnswerIn payload-size bound above — generous enough that no real lesson
# pace ever trips it). See app/core/rate_limit.py for why this is
# in-memory rather than Redis-backed. Limits are deliberately loose/simple
# per Ramin's ask, not tuned against real traffic yet.
LOGIN_RATE_LIMIT = register_limiter(RateLimiter(limit=10, window_seconds=60))
REGISTER_RATE_LIMIT = register_limiter(RateLimiter(limit=5, window_seconds=3600))
ANSWER_RATE_LIMIT = register_limiter(RateLimiter(limit=120, window_seconds=60))

def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"

def enforce_rate_limit(limiter: RateLimiter, key: str, code: str, message: str):
    retry_after = limiter.check(key)
    if retry_after is not None:
        fail(429, code, message, retry_after_seconds=max(1, int(retry_after) + 1))

MEDIA_ASSETS_DIR = Path(__file__).resolve().parents[2] / "media_assets"
MAX_AUDIO_SIZE_BYTES = 5 * 1024 * 1024
MEDIA_ASSET_KEY_RE = re.compile(
    r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,198}[A-Za-z0-9])?"
)
MEDIA_CACHE_CONTROL = "public, max-age=31536000, immutable"


def media_asset_path(key: str) -> Path:
    if ".." in key or MEDIA_ASSET_KEY_RE.fullmatch(key) is None:
        fail(
            422,
            "invalid_media_asset_key",
            "Media asset key must be 1-200 letters, numbers, dots, underscores, or hyphens and must not contain '..'",
        )
    return MEDIA_ASSETS_DIR / f"{key}.mp3"

def auth_response(user):
    return {"access_token":create_token(user.id),"token_type":"bearer","expires_in":get_settings().access_token_expire_seconds,"user":user}
def normalized(v):
    if isinstance(v,str): return " ".join(v.strip().casefold().split())
    if isinstance(v,list): return [normalized(x) for x in v]
    if isinstance(v,dict): return {str(k):normalized(x) for k,x in sorted(v.items())}
    return v
def is_multi_answer_response(correct):
    return (
        isinstance(correct,dict)
        and set(correct)=={"canonical","accepted"}
        and isinstance(correct["accepted"],list)
    )
def canonical_pairs(value):
    """Canonicalize a matching_pairs answer into an order-independent set of
    (left,right) tuples, regardless of representation. CONTRACT.md documents
    the submitted `response` as a flat {left: right} pair-mapping (what
    MatchingPairs.tsx sends and what the Endless Practice engine's
    derive_answer() produces), but hand-authored lesson content's
    accepted_answers/correct_response has historically been written as a
    list of {"left":...,"right":...} objects instead (matching the prompt's
    `pairs` display shape) - a real mismatch that made every compiled
    matching_pairs exercise ungradeable-correct regardless of what the
    learner picked. Accept either shape here so both compare equal."""
    if isinstance(value, dict):
        return frozenset((normalized(k), normalized(v)) for k, v in value.items())
    if isinstance(value, list) and all(
        isinstance(item, dict) and {"left", "right"} <= set(item) for item in value
    ):
        return frozenset((normalized(item["left"]), normalized(item["right"])) for item in value)
    return None
def display_correct_response(correct):
    if is_multi_answer_response(correct):
        return correct["canonical"]
    return correct
def decode_feedback(raw):
    """Decode Exercise.feedback. Phase C stores an optional JSON object
    ({"generic","feedback_by_option","orthography_strict"}) in the same
    Text column that historically held a bare feedback string - decode
    defensively so every pre-Phase-C row (plain string or None) keeps
    behaving exactly as before."""
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except (ValueError, TypeError):
        return {"generic": raw}
    if not isinstance(decoded, dict):
        return {"generic": raw}
    return decoded
def select_feedback(feedback_meta, response, result):
    if result != "correct":
        by_option = feedback_meta.get("feedback_by_option") or {}
        if isinstance(response, str) and response in by_option:
            return by_option[response]
    return feedback_meta.get("generic")
def resolve_script(db, language_code):
    if not language_code:
        return None
    language = db.get(Language, language_code)
    return language.script if language else None
def exercise_type_value(exercise_type):
    return exercise_type.value if hasattr(exercise_type, "value") else exercise_type
def grade(response,correct,exercise_type=None,*,script=None,orthography_strict=None):
    """Returns the 3-state result: 'correct' | 'almost' | 'incorrect'.
    'almost' (Phase C typo tolerance) is only ever returned for free-typed
    answers on eligible exercise types - flashcard, multi-answer, and
    choice-type grading below always resolve straight to correct/incorrect."""
    if exercise_type == ExerciseType.flashcard:
        report=normalized(response)
        if not isinstance(report,str) or report not in {"known","unknown"}:
            fail(422,"invalid_flashcard_response","Flashcard response must be 'known' or 'unknown'")
        return "correct" if report == "known" else "incorrect"
    if is_multi_answer_response(correct):
        normalized_response=normalized(response)
        is_ok = any(normalized_response==normalized(item) for item in correct["accepted"])
        return "correct" if is_ok else "incorrect"
    type_value = exercise_type_value(exercise_type)
    free_text_eligible = (
        type_value in FREE_TEXT_EXERCISE_TYPES
        or type_value in {"fill_in_blank", "listen_order"}
    )
    if free_text_eligible and isinstance(response, str) and isinstance(correct, str):
        return grade_answer(
            response,
            correct,
            exercise_type=type_value,
            script=script,
            orthography_strict=orthography_strict,
        )
    if type_value == "matching_pairs":
        correct_pairs = canonical_pairs(correct)
        if correct_pairs is not None:
            return "correct" if canonical_pairs(response) == correct_pairs else "incorrect"
    return "correct" if normalized(response)==normalized(correct) else "incorrect"
def exercise_answer(db, user, e, response):
    feedback_meta = decode_feedback(e.feedback)
    script = resolve_script(db, e.prompt.get("answer_language_code"))
    result = grade(
        response,
        e.correct_response,
        e.type,
        script=script,
        orthography_strict=feedback_meta.get("orthography_strict"),
    )
    correct = result != "incorrect"
    previously_correct = db.scalar(
        select(ExerciseAttempt.id)
        .where(
            ExerciseAttempt.user_id == user.id,
            ExerciseAttempt.exercise_id == e.id,
            ExerciseAttempt.correct.is_(True),
        )
        .limit(1)
    )
    xp = e.xp if correct and previously_correct is None else 1 if correct else 0

    db.add(
        ExerciseAttempt(
            user_id=user.id,
            exercise_id=e.id,
            response=response,
            correct=correct,
            outcome=result,
            xp_awarded=xp,
        )
    )
    lp = db.scalar(
        select(LessonProgress).where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id == e.lesson_id,
        )
    )
    if not lp:
        lp = LessonProgress(
            user_id=user.id,
            lesson_id=e.lesson_id,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            correct_count=0,
            answer_count=0,
            xp_earned=0,
        )
        db.add(lp)

    lp.answer_count += 1
    lp.correct_count += int(correct)
    lp.xp_earned += xp
    record_activity(db, user.id, xp, user.timezone)
    db.commit()
    return {
        "correct": correct,
        "result": result,
        "correct_response": display_correct_response(e.correct_response),
        "xp_awarded": xp,
        "feedback": select_feedback(feedback_meta, response, result),
    }

def speaking_unlocked(db:Session,course_id:str,user_id:str|None) -> bool:
    if not user_id: return False
    reading_units=list(db.scalars(select(Unit).where(Unit.course_id==course_id,Unit.section==UnitSection.reading_writing)))
    if not reading_units: return False
    for unit in reading_units:
        lesson_ids=list(db.scalars(select(Lesson.id).where(Lesson.unit_id==unit.id)))
        if not lesson_ids: return False
        completed=db.scalar(select(func.count(LessonProgress.id)).where(LessonProgress.user_id==user_id,LessonProgress.lesson_id.in_(lesson_ids),LessonProgress.completed_at.is_not(None)))
        if completed != len(lesson_ids): return False
    return True

@router.post("/auth/register",response_model=AuthOut,status_code=201)
def register(body:RegisterIn,request:Request,db:Session=Depends(get_db)):
    enforce_rate_limit(REGISTER_RATE_LIMIT,client_ip(request),"register_rate_limited","Too many registration attempts from this address. Please try again later.")
    email=body.email.lower()
    if db.scalar(select(User).where(User.email==email)): fail(409,"email_exists","An account with this email already exists")
    user=User(email=email,password_hash=hash_password(body.password),display_name=body.display_name or email.split("@")[0],is_admin=email in get_settings().admin_email_set,timezone=valid_timezone_or_none(body.timezone)); db.add(user); db.flush()
    db.add(UserStats(user_id=user.id,total_xp=0,streak_days=0,last_activity_date=None,daily_goal=20,hearts=5,gems=0))
    db.commit(); return auth_response(user)
@router.post("/auth/login",response_model=AuthOut)
def login(body:LoginIn,request:Request,db:Session=Depends(get_db)):
    enforce_rate_limit(LOGIN_RATE_LIMIT,client_ip(request),"login_rate_limited","Too many login attempts. Please wait before trying again.")
    user=db.scalar(select(User).where(User.email==body.email.lower()))
    if not user or not verify_password(body.password,user.password_hash): fail(401,"invalid_credentials","Invalid email or password")
    valid_tz=valid_timezone_or_none(body.timezone)
    if valid_tz and valid_tz!=user.timezone: user.timezone=valid_tz; db.commit()
    return auth_response(user)
@router.get("/auth/me",response_model=MeOut)
def me(user=Depends(current_user)): return user
@router.get("/languages",response_model=list[LanguageOut])
def languages(db:Session=Depends(get_db)): return list(db.scalars(select(Language).order_by(Language.code)))
@router.get("/language-pairs",response_model=list[LanguagePairOut])
def pairs(db:Session=Depends(get_db)):
    rows=db.execute(select(Course.source_language,Course.target_language,func.count(Course.id)).group_by(Course.source_language,Course.target_language)).all()
    return [{"source_language":a,"target_language":b,"course_count":n} for a,b,n in rows]
def course_shape(db,c): return {"id":c.id,"source_language":c.source_language,"target_language":c.target_language,"title":c.title,"level":c.level,"unit_count":db.scalar(select(func.count(Unit.id)).where(Unit.course_id==c.id))}
@router.get("/courses",response_model=list[CourseOut])
def courses(source:str|None=None,target:str|None=None,db:Session=Depends(get_db)):
    q=select(Course); q=q.where(Course.source_language==source) if source else q; q=q.where(Course.target_language==target) if target else q
    return [course_shape(db,c) for c in db.scalars(q.order_by(Course.level,Course.title))]
@router.get("/courses/{course_id}",response_model=CourseDetail)
def course(course_id:str,db:Session=Depends(get_db)):
    c=db.get(Course,course_id)
    if not c: fail(404,"course_not_found","Course not found")
    return {**course_shape(db,c),"description":c.description}
@router.get("/courses/{course_id}/units",response_model=list[UnitOut])
def units(course_id:str,user=Depends(optional_current_user),db:Session=Depends(get_db)):
    if not db.get(Course,course_id):
        fail(404,"course_not_found","Course not found")
    unlocked=(user and user.is_admin) or speaking_unlocked(
        db,
        course_id,
        user.id if user else None,
    )
    result=[]
    for unit in db.scalars(
        select(Unit)
        .where(Unit.course_id==course_id)
        .order_by(Unit.order)
    ):
        checkpoint_passed=bool(
            user
            and db.scalar(
                select(CheckpointAttempt.id)
                .where(
                    CheckpointAttempt.user_id==user.id,
                    CheckpointAttempt.unit_id==unit.id,
                    CheckpointAttempt.passed.is_(True),
                )
                .limit(1)
            )
        )
        result.append(
            {
                "id":unit.id,
                "title":unit.title,
                "order":unit.order,
                "lesson_count":db.scalar(
                    select(func.count(Lesson.id))
                    .where(Lesson.unit_id==unit.id)
                ),
                "section":unit.section,
                "locked":unit.section==UnitSection.speaking and not unlocked,
                "checkpoint_passed":checkpoint_passed,
            }
        )
    return result
@router.get("/units/{unit_id}/lessons",response_model=list[LessonOut])
def lessons(unit_id:str,db:Session=Depends(get_db)):
    if not db.get(Unit,unit_id): fail(404,"unit_not_found","Unit not found")
    return [{"id":l.id,"title":l.title,"order":l.order,"exercise_count":db.scalar(select(func.count(Exercise.id)).where(Exercise.lesson_id==l.id))} for l in db.scalars(select(Lesson).where(Lesson.unit_id==unit_id).order_by(Lesson.order))]
@router.get("/lessons/{lesson_id}",response_model=LessonDetail)
def lesson(lesson_id:str,db:Session=Depends(get_db)):
    l=db.get(Lesson,lesson_id)
    if not l: fail(404,"lesson_not_found","Lesson not found")
    teaching=[{"kind":item.kind,"title":item.title or None,"text_blocks":item.content.get("text_blocks",[]),"note":item.content.get("note")} for item in l.teaching_items]
    return {"id":l.id,"unit_id":l.unit_id,"title":l.title,"teaching":teaching,"exercises":[{"id":e.id,"type":e.type,"order":e.order,"prompt":e.prompt} for e in l.exercises]}
@router.post("/lessons/{lesson_id}/start",response_model=StartOut)
def start(lesson_id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    lesson_row=db.get(Lesson,lesson_id)
    if not lesson_row: fail(404,"lesson_not_found","Lesson not found")
    unit=db.get(Unit,lesson_row.unit_id)
    if unit.section==UnitSection.speaking and not user.is_admin and not speaking_unlocked(db,unit.course_id,user.id):
        fail(409,"speaking_locked","Complete all reading and writing units before starting speaking lessons")
    p=db.scalar(select(LessonProgress).where(LessonProgress.user_id==user.id,LessonProgress.lesson_id==lesson_id)); now=datetime.now(timezone.utc)
    if not p:
        p=LessonProgress(
            user_id=user.id,
            lesson_id=lesson_id,
            started_at=now,
            completed_at=None,
            correct_count=0,
            answer_count=0,
            xp_earned=0,
        )
        db.add(p)
    elif not p.started_at: p.started_at=now
    db.commit(); return {"started_at":p.started_at}
@router.post("/exercises/{exercise_id}/answer",response_model=AnswerOut)
def answer(exercise_id:str,body:AnswerIn,user=Depends(current_user),db:Session=Depends(get_db)):
    enforce_rate_limit(ANSWER_RATE_LIMIT,user.id,"answer_rate_limited","Too many answers submitted too quickly. Please slow down.")
    e=db.get(Exercise,exercise_id)
    if not e: fail(404,"exercise_not_found","Exercise not found")
    return exercise_answer(db,user,e,body.response)
@router.post("/exercises/{exercise_id}/report",response_model=ContentIssueCreatedOut,status_code=201)
def report_content_issue(exercise_id:str,body:ContentIssueReportIn,request:Request,user=Depends(current_user),db:Session=Depends(get_db)):
    if not db.get(Exercise,exercise_id): fail(404,"exercise_not_found","Exercise not found")
    issue=ContentIssueReport(reporter_user_id=user.id,exercise_id=exercise_id,category=body.category,description=body.description,learner_response=body.learner_response,client_context={"user_agent":request.headers.get("user-agent",""),"accept_language":request.headers.get("accept-language","")})
    db.add(issue); db.commit(); db.refresh(issue)
    return issue
@router.post("/lessons/{lesson_id}/complete", response_model=CompleteOut)
def complete(
    lesson_id: str,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    p = db.scalar(
        select(LessonProgress)
        .where(
            LessonProgress.user_id == user.id,
            LessonProgress.lesson_id == lesson_id,
        )
        .with_for_update()
    )
    if not p:
        fail(
            409,
            "lesson_not_started",
            "Start the lesson before completing it",
        )

    lesson_row = db.get(Lesson, lesson_id)
    unit = db.get(Unit, lesson_row.unit_id)
    now = datetime.now(timezone.utc)
    first_completion = p.completed_at is None
    session_started_at = p.completed_at or p.started_at

    completion_xp = db.scalar(
        select(func.coalesce(func.sum(ExerciseAttempt.xp_awarded), 0))
        .join(Exercise, Exercise.id == ExerciseAttempt.exercise_id)
        .where(
            ExerciseAttempt.user_id == user.id,
            Exercise.lesson_id == lesson_id,
            ExerciseAttempt.created_at >= session_started_at,
            ExerciseAttempt.created_at < now,
        )
    ) or 0

    p.completed_at = now
    skill = db.scalar(
        select(SkillProgress).where(
            SkillProgress.user_id == user.id,
            SkillProgress.course_id == unit.course_id,
        )
    )
    if not skill:
        skill = SkillProgress(
            user_id=user.id,
            course_id=unit.course_id,
            completed_lessons=0,
            mastery=0.0,
        )
        db.add(skill)

    if first_completion:
        skill.completed_lessons += 1
        lexemes = list(
            db.scalars(
                select(Lexeme).where(
                    Lexeme.provenance_lesson_id == lesson_id
                )
            )
        )
        existing = set(
            db.scalars(
                select(UserLexemeSRS.lexeme_id).where(
                    UserLexemeSRS.user_id == user.id,
                    UserLexemeSRS.lexeme_id.in_(
                        [lexeme.id for lexeme in lexemes]
                    ),
                )
            )
        ) if lexemes else set()

        for lexeme in lexemes:
            if lexeme.id not in existing:
                db.add(
                    UserLexemeSRS(
                        user_id=user.id,
                        lexeme_id=lexeme.id,
                        course_id=lexeme.course_id,
                        ease_factor=2.5,
                        interval_days=0,
                        repetitions=0,
                        mastery=0.0,
                        due_at=now + timedelta(days=1),
                        last_reviewed_at=None,
                        introduced_at=now,
                        suspended=False,
                        last_session_id=None,
                    )
                )

    total = db.scalar(
        select(func.count(Lesson.id))
        .join(Unit)
        .where(Unit.course_id == unit.course_id)
    ) or 1
    skill.mastery = skill.completed_lessons / total

    db.commit()
    return {
        "completed_at": p.completed_at,
        "xp_awarded": completion_xp,
        "accuracy": (
            p.correct_count / p.answer_count if p.answer_count else 0
        ),
    }
@router.get("/me/progress")
def progress(user=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(LessonProgress).where(LessonProgress.user_id==user.id)).all()
    skills=db.scalars(select(SkillProgress).where(SkillProgress.user_id==user.id)).all(); vocabulary=db.scalars(select(VocabularyProgress).where(VocabularyProgress.user_id==user.id)).all(); grammar=db.scalars(select(GrammarProgress).where(GrammarProgress.user_id==user.id)).all()
    return {"lessons_started":len(rows),"lessons_completed":sum(x.completed_at is not None for x in rows),"lesson_progress":[{"lesson_id":x.lesson_id,"started_at":x.started_at,"completed_at":x.completed_at,"accuracy":x.correct_count/x.answer_count if x.answer_count else 0,"xp_earned":x.xp_earned} for x in rows],"skill_progress":[{"course_id":x.course_id,"completed_lessons":x.completed_lessons,"mastery":x.mastery} for x in skills],"vocabulary_progress":[{"content_item_id":x.content_item_id,"mastery":x.mastery} for x in vocabulary],"grammar_progress":[{"content_item_id":x.content_item_id,"mastery":x.mastery} for x in grammar]}
@router.get("/me/reviews")
def reviews(
    cursor: str | None = None,
    limit: int = Query(100, ge=1, le=200),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    q = (
        select(ReviewItem)
        .where(
            ReviewItem.user_id == user.id,
            ReviewItem.due_at <= datetime.now(timezone.utc),
        )
        .order_by(ReviewItem.due_at, ReviewItem.id)
    )
    if cursor:
        try:
            due, id_ = cursor.split("|", 1)
            cursor_due = datetime.fromisoformat(due)
            q = q.where(
                (ReviewItem.due_at > cursor_due)
                | (
                    (ReviewItem.due_at == cursor_due)
                    & (ReviewItem.id > id_)
                )
            )
        except ValueError:
            fail(400, "invalid_cursor", "Review cursor is invalid")

    items = list(db.scalars(q.limit(limit + 1)))
    more = len(items) > limit
    items = items[:limit]
    result = []
    for review in items:
        exercise = db.get(Exercise, review.exercise_id)
        result.append(
            {
                "id": review.id,
                "exercise_id": review.exercise_id,
                "due_at": review.due_at,
                "mastery": review.mastery,
                "exercise": {
                    "id": exercise.id,
                    "type": exercise.type,
                    "prompt": exercise.prompt,
                },
            }
        )
    return {
        "items": result,
        "next_cursor": (
            f"{items[-1].due_at.isoformat()}|{items[-1].id}"
            if more
            else None
        ),
    }
@router.post("/reviews/{review_item_id}/answer",response_model=ReviewAnswerOut)
def review_answer(review_item_id:str,body:AnswerIn,user=Depends(current_user),db:Session=Depends(get_db)):
    enforce_rate_limit(ANSWER_RATE_LIMIT,user.id,"answer_rate_limited","Too many answers submitted too quickly. Please slow down.")
    r=db.get(ReviewItem,review_item_id)
    if not r or r.user_id!=user.id: fail(404,"review_not_found","Review item not found")
    e=db.get(Exercise,r.exercise_id)
    feedback_meta=decode_feedback(e.feedback)
    script=resolve_script(db,e.prompt.get("answer_language_code"))
    result=grade(body.response,e.correct_response,e.type,script=script,orthography_strict=feedback_meta.get("orthography_strict"))
    correct=result!="incorrect"
    xp=e.xp if correct else 0
    schedule(r,result); record_activity(db,user.id,xp,user.timezone); db.commit()
    return {"correct":correct,"result":result,"correct_response":display_correct_response(e.correct_response),"xp_awarded":xp,"feedback":select_feedback(feedback_meta,body.response,result),"next_due_at":r.due_at}
@router.get("/me/reviews/due", response_model=ReviewDueOut)
def lexeme_reviews_due(
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    conditions = (
        UserLexemeSRS.user_id == user.id,
        UserLexemeSRS.due_at <= now,
        UserLexemeSRS.suspended.is_(False),
    )
    due_count = db.scalar(
        select(func.count(UserLexemeSRS.id)).where(*conditions)
    ) or 0
    grouped = db.execute(
        select(
            UserLexemeSRS.course_id,
            func.count(UserLexemeSRS.id),
        )
        .where(*conditions)
        .group_by(UserLexemeSRS.course_id)
        .order_by(UserLexemeSRS.course_id)
    ).all()
    return {
        "due_count": due_count,
        "by_course": [
            {"course_id": course_id, "due_count": count}
            for course_id, count in grouped
        ],
    }


@router.post("/reviews/session", response_model=ReviewItemsOut)
def review_session(
    body: ReviewSessionIn,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    course = db.get(Course, body.course_id)
    if not course:
        fail(404, "course_not_found", "Course not found")

    session_id = str(uuid4())
    items = generate_review_batch(
        db,
        user.id,
        course,
        body.size,
        session_id,
    )
    db.commit()
    return {
        "items": [
            {
                "id": item.id,
                "type": db.get(
                    PracticeTemplate, item.template_id
                ).type,
                "prompt": item.prompt,
            }
            for item in items
        ]
    }


@router.post(
    "/units/{unit_id}/checkpoint",
    response_model=ReviewItemsOut,
)
def checkpoint_session(
    unit_id: str,
    body: CheckpointIn | None = None,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    unit = db.get(Unit, unit_id)
    if not unit:
        fail(404, "unit_not_found", "Unit not found")
    course = db.get(Course, unit.course_id)

    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": f"checkpoint:{user.id}:{unit_id}"},
    )
    latest = db.scalar(
        select(CheckpointAttempt)
        .where(
            CheckpointAttempt.user_id == user.id,
            CheckpointAttempt.unit_id == unit_id,
        )
        .order_by(
            CheckpointAttempt.created_at.desc(),
            CheckpointAttempt.id.desc(),
        )
        .limit(1)
        .with_for_update()
    )
    now = datetime.now(timezone.utc)
    if latest is not None and latest.scored_at is not None:
        retry_at = latest.created_at + timedelta(hours=1)
        if retry_at > now:
            retry_after_seconds = max(
                1,
                int((retry_at - now).total_seconds()) + 1,
            )
            fail(
                429,
                "checkpoint_retake_delayed",
                "This unit checkpoint can be attempted again in one hour",
                retry_after_seconds=retry_after_seconds,
            )

    session_id = str(uuid4())
    items = generate_checkpoint(
        db,
        user.id,
        course,
        unit_id,
        body.size if body else 15,
        session_id,
    )
    if len(items) < 12:
        db.rollback()
        fail(
            409,
            "checkpoint_unavailable",
            "This unit does not have enough practice material for a checkpoint",
        )

    db.add(
        CheckpointAttempt(
            id=session_id,
            user_id=user.id,
            unit_id=unit_id,
            total_items=len(items),
        )
    )
    db.commit()
    return {
        "items": [
            {
                "id": item.id,
                "type": db.get(
                    PracticeTemplate,
                    item.template_id,
                ).type,
                "prompt": item.prompt,
            }
            for item in items
        ]
    }


def checkpoint_passed_for_unit(
    db: Session,
    user_id: str,
    unit_id: str,
) -> bool:
    return bool(
        db.scalar(
            select(CheckpointAttempt.id)
            .where(
                CheckpointAttempt.user_id == user_id,
                CheckpointAttempt.unit_id == unit_id,
                CheckpointAttempt.passed.is_(True),
            )
            .limit(1)
        )
    )


@router.get(
    "/units/{unit_id}/checkpoint/result",
    response_model=CheckpointResultOut,
)
def checkpoint_result(
    unit_id: str,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    if not db.get(Unit, unit_id):
        fail(404, "unit_not_found", "Unit not found")

    checkpoint = db.scalar(
        select(CheckpointAttempt)
        .where(
            CheckpointAttempt.user_id == user.id,
            CheckpointAttempt.unit_id == unit_id,
        )
        .order_by(
            CheckpointAttempt.created_at.desc(),
            CheckpointAttempt.id.desc(),
        )
        .limit(1)
        .with_for_update()
    )
    if checkpoint is None:
        fail(
            404,
            "checkpoint_not_found",
            "No checkpoint attempt exists for this unit",
        )

    answered_items = db.scalar(
        select(func.count(PracticeAttempt.id))
        .join(
            PracticeItem,
            PracticeItem.id == PracticeAttempt.practice_item_id,
        )
        .where(
            PracticeAttempt.user_id == user.id,
            PracticeItem.session_id == checkpoint.id,
            PracticeItem.source == "checkpoint",
        )
    ) or 0

    if checkpoint.scored_at is not None:
        return {
            "status": "complete",
            "answered_items": checkpoint.total_items,
            "total_items": checkpoint.total_items,
            "passed": checkpoint.passed,
            "score": checkpoint.score,
            "weak_outcomes": checkpoint.weak_outcomes,
            "checkpoint_passed": checkpoint_passed_for_unit(
                db,
                user.id,
                unit_id,
            ),
        }

    if answered_items < checkpoint.total_items:
        return {
            "status": "in_progress",
            "answered_items": answered_items,
            "total_items": checkpoint.total_items,
            "passed": None,
            "score": None,
            "weak_outcomes": [],
            "checkpoint_passed": checkpoint_passed_for_unit(
                db,
                user.id,
                unit_id,
            ),
        }

    correct_items = db.scalar(
        select(func.count(PracticeAttempt.id))
        .join(
            PracticeItem,
            PracticeItem.id == PracticeAttempt.practice_item_id,
        )
        .where(
            PracticeAttempt.user_id == user.id,
            PracticeItem.session_id == checkpoint.id,
            PracticeItem.source == "checkpoint",
            PracticeAttempt.correct.is_(True),
        )
    ) or 0
    score = correct_items / checkpoint.total_items
    passed = score >= 0.8

    weak_outcomes = list(
        db.scalars(
            select(Lexeme.english_gloss)
            .join(
                PracticeItem,
                PracticeItem.target_lexeme_id == Lexeme.id,
            )
            .join(
                PracticeAttempt,
                PracticeAttempt.practice_item_id == PracticeItem.id,
            )
            .where(
                PracticeAttempt.user_id == user.id,
                PracticeItem.session_id == checkpoint.id,
                PracticeItem.source == "checkpoint",
                PracticeAttempt.correct.is_(False),
            )
            .distinct()
            .order_by(Lexeme.english_gloss)
        )
    )

    scored_at = datetime.now(timezone.utc)
    if passed:
        unit = db.get(Unit, unit_id)
        covered_lexeme_ids = set(
            db.scalars(
                select(PracticeItem.target_lexeme_id)
                .where(
                    PracticeItem.session_id == checkpoint.id,
                    PracticeItem.source == "checkpoint",
                    PracticeItem.target_lexeme_id.is_not(None),
                )
                .distinct()
            )
        )
        existing_lexeme_ids = set(
            db.scalars(
                select(UserLexemeSRS.lexeme_id)
                .where(
                    UserLexemeSRS.user_id == user.id,
                    UserLexemeSRS.lexeme_id.in_(covered_lexeme_ids),
                )
                .with_for_update()
            )
        )
        for lexeme_id in covered_lexeme_ids - existing_lexeme_ids:
            db.add(
                UserLexemeSRS(
                    user_id=user.id,
                    lexeme_id=lexeme_id,
                    course_id=unit.course_id,
                    ease_factor=2.5,
                    interval_days=3,
                    repetitions=1,
                    mastery=0.5,
                    due_at=scored_at + timedelta(days=3),
                    last_reviewed_at=scored_at,
                    introduced_at=scored_at,
                    suspended=False,
                    last_session_id=None,
                )
            )

    checkpoint.passed = passed
    checkpoint.score = score
    checkpoint.weak_outcomes = weak_outcomes
    checkpoint.scored_at = scored_at
    db.commit()

    return {
        "status": "complete",
        "answered_items": checkpoint.total_items,
        "total_items": checkpoint.total_items,
        "passed": passed,
        "score": score,
        "weak_outcomes": weak_outcomes,
        "checkpoint_passed": checkpoint_passed_for_unit(
            db,
            user.id,
            unit_id,
        ),
    }


@router.post(
    "/reviews/items/{item_id}/retry",
    response_model=ReviewItemsOut,
)
def review_retry(
    item_id: str,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    original = db.scalar(
        select(PracticeItem)
        .where(PracticeItem.id == item_id)
        .with_for_update()
    )
    if (
        not original
        or original.user_id != user.id
        or original.source != "review"
    ):
        fail(404, "review_item_not_found", "Review item not found")
    if original.answered_at is None:
        fail(
            409,
            "review_item_unanswered",
            "Answer the review item before requesting a retry",
        )
    if not original.target_lexeme_id or not original.session_id:
        fail(
            409,
            "review_item_invalid",
            "Review item has no retry context",
        )

    srs = db.scalar(
        select(UserLexemeSRS)
        .where(
            UserLexemeSRS.user_id == user.id,
            UserLexemeSRS.lexeme_id == original.target_lexeme_id,
        )
        .with_for_update()
    )
    if not srs:
        fail(409, "lexeme_srs_missing", "Lexeme review state is missing")

    course = db.get(Course, original.course_id)
    retry = generate_review_retry(
        db,
        user.id,
        course,
        srs,
        original.session_id,
    )
    if retry is None:
        fail(
            409,
            "review_retry_unavailable",
            "No valid review template is available for this lexeme",
        )

    db.commit()
    template = db.get(PracticeTemplate, retry.template_id)
    return {
        "items": [
            {
                "id": retry.id,
                "type": template.type,
                "prompt": retry.prompt,
            }
        ]
    }


@router.get("/me/streak",response_model=StreakOut)
def streak(user=Depends(current_user),db:Session=Depends(get_db)):
    s=stats_for(db,user.id)
    today=datetime.now(resolve_user_tz(user.timezone)).date()
    return {
        "streak_days":s.streak_days,
        "last_activity_date":s.last_activity_date,
        "streak_freezes_available":s.streak_freezes_available,
        "freeze_used_today":s.last_freeze_used_date==today,
    }
@router.get("/me/xp",response_model=XPOut)
def xp(user=Depends(current_user),db:Session=Depends(get_db)): s=stats_for(db,user.id); return {"total_xp":s.total_xp,"daily_goal":s.daily_goal}
@router.get("/me/achievements")
def achievements(user=Depends(current_user),db:Session=Depends(get_db)):
    earned=set(db.scalars(select(UserAchievement.achievement_id).where(UserAchievement.user_id==user.id)))
    return [{"id":a.id,"code":a.code,"title":a.title,"description":a.description,"earned":a.id in earned} for a in db.scalars(select(Achievement).order_by(Achievement.threshold))]
@router.get("/me/quests",response_model=QuestsOut)
def quests(user=Depends(current_user),db:Session=Depends(get_db)):
    result=daily_quests_for(db,user.id,user.timezone)
    db.commit()
    return {"quests":result}
@router.post("/practice/{course_id}/batch",response_model=PracticeBatchOut)
def practice_batch(
    course_id:str,
    body:PracticeBatchIn|None=None,
    user=Depends(current_user),
    db:Session=Depends(get_db),
):
    course=db.get(Course,course_id)
    if not course: fail(404,"course_not_found","Course not found")
    locked,items=generate_batch(db,user.id,course,body.size if body else 10)
    db.commit()
    return {
        "locked":locked,
        "items":[
            {"id":item.id,"type":db.get(PracticeTemplate,item.template_id).type,"prompt":item.prompt}
            for item in items
        ],
    }
@router.post(
    "/practice/items/{item_id}/answer",
    response_model=PracticeAnswerOut,
)
def practice_answer(
    item_id: str,
    body: AnswerIn,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(ANSWER_RATE_LIMIT,user.id,"answer_rate_limited","Too many answers submitted too quickly. Please slow down.")
    item = db.scalar(
        select(PracticeItem)
        .where(PracticeItem.id == item_id)
        .with_for_update()
    )
    if not item or item.user_id != user.id:
        fail(404, "practice_item_not_found", "Practice item not found")
    if item.answered_at is not None:
        fail(
            409,
            "practice_item_answered",
            "Practice item was already answered",
        )

    now = datetime.now(timezone.utc)
    if item.expires_at <= now:
        fail(
            410,
            "practice_item_expired",
            "Practice item has expired",
        )

    template = db.get(PracticeTemplate, item.template_id)
    script = resolve_script(db, item.prompt.get("answer_language_code"))
    result = grade(
        body.response,
        item.correct_response,
        template.type,
        script=script,
        orthography_strict=(
            True if item.source == "checkpoint" else None
        ),
    )
    correct = result != "incorrect"

    xp_awarded = 0
    if correct:
        day_start, day_end = activity_day_bounds(user.timezone)
        correct_today = db.scalar(
            select(func.count(PracticeAttempt.id)).where(
                PracticeAttempt.user_id == user.id,
                PracticeAttempt.correct.is_(True),
                PracticeAttempt.created_at >= day_start,
                PracticeAttempt.created_at < day_end,
            )
        ) or 0
        xp_awarded = item.xp_value if correct_today < 20 else 1

    srs = None
    if item.source == "checkpoint":
        pass
    elif item.target_lexeme_id:
        srs = db.scalar(
            select(UserLexemeSRS)
            .where(
                UserLexemeSRS.user_id == user.id,
                UserLexemeSRS.lexeme_id == item.target_lexeme_id,
            )
            .with_for_update()
        )

    if srs is not None:
        if item.source == "review":
            if srs.last_session_id != item.session_id:
                schedule(srs, result)
                srs.last_session_id = item.session_id
            srs.last_reviewed_at = now
        elif item.source == "practice":
            day_start, day_end = activity_day_bounds(user.timezone)
            attempts_today = db.scalar(
                select(func.count(PracticeAttempt.id))
                .join(
                    PracticeItem,
                    PracticeItem.id
                    == PracticeAttempt.practice_item_id,
                )
                .where(
                    PracticeAttempt.user_id == user.id,
                    PracticeItem.source == "practice",
                    PracticeItem.target_lexeme_id
                    == item.target_lexeme_id,
                    PracticeAttempt.created_at >= day_start,
                    PracticeAttempt.created_at < day_end,
                )
            ) or 0
            if attempts_today == 0:
                schedule(srs, result)
            srs.last_reviewed_at = now

    db.add(
        PracticeAttempt(
            user_id=user.id,
            practice_item_id=item.id,
            response=body.response,
            correct=correct,
            xp_awarded=xp_awarded,
        )
    )
    item.answered_at = now
    record_activity(db, user.id, xp_awarded, user.timezone)
    db.commit()
    return {
        "correct": correct,
        "result": result,
        "correct_response": display_correct_response(
            item.correct_response
        ),
        "xp_awarded": xp_awarded,
    }
@router.post("/admin/media/upload")
async def upload_media_asset(
    request: Request,
    key: str = Form(...),
    file: UploadFile = File(...),
    user=Depends(admin_user),
):
    path = media_asset_path(key)

    if file.content_type not in {"audio/mpeg", "audio/mp3"}:
        fail(
            415,
            "unsupported_media_type",
            "Recorded media assets must be MP3 audio",
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        fail(
            409,
            "media_asset_exists",
            "A recording already exists for this media asset key",
        )

    temporary_path = path.with_name(
        f".{path.name}.{uuid4().hex}.upload"
    )
    total_bytes = 0

    try:
        with temporary_path.open("xb") as destination:
            while chunk := await file.read(64 * 1024):
                total_bytes += len(chunk)
                if total_bytes > MAX_AUDIO_SIZE_BYTES:
                    fail(
                        413,
                        "media_asset_too_large",
                        "Recorded media assets must not exceed 5 MB",
                    )
                destination.write(chunk)

        if total_bytes == 0:
            fail(
                422,
                "empty_media_asset",
                "Recorded media asset must not be empty",
            )

        try:
            os.link(temporary_path, path)
        except FileExistsError:
            fail(
                409,
                "media_asset_exists",
                "A recording already exists for this media asset key",
            )
    finally:
        temporary_path.unlink(missing_ok=True)
        await file.close()

    return {
        "key": key,
        "url": str(request.url_for("get_media_asset", key=key)),
    }


@router.get("/media/{key}", name="get_media_asset")
def get_media_asset(key: str):
    path = media_asset_path(key)
    if not path.is_file():
        fail(
            404,
            "media_asset_not_found",
            "No recording exists for this media asset key",
        )

    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Cache-Control": MEDIA_CACHE_CONTROL},
    )
@router.post("/admin/content/import",response_model=ImportOut)
def content_import(body:ImportRequest,user=Depends(admin_user),db:Session=Depends(get_db)):
    count,messages,counters=import_content(db,body)
    # An empty `counters` dict means import_content returned before
    # writing anything (upfront structural validation failure) - still
    # hard-blocking, unchanged. Once past that point, `messages` are
    # non-fatal per-item content_key-reconciliation conflicts, surfaced
    # as `warnings` on a successful response instead of failing the
    # whole request (the rest of the payload already committed).
    if messages and not counters: fail(422,"content_invalid","; ".join(messages))
    return {"imported_courses":count,"warnings":messages,**counters}
@router.post(
    "/admin/courses/{course_id}/practice/import",
    response_model=PracticeImportOut,
)
def practice_content_import(
    course_id:str,
    body:PracticeArtifactImport,
    user=Depends(admin_user),
    db:Session=Depends(get_db),
):
    course=db.get(Course,course_id)
    if not course: fail(404,"course_not_found","Course not found")
    created,updated,errors=import_practice_templates(db,course,body)
    if errors: fail(422,"practice_content_invalid","; ".join(errors))
    return {"imported_templates":created,"updated_templates":updated}
@router.get("/admin/content/export")
def content_export(user=Depends(admin_user),db:Session=Depends(get_db)): return export_content(db)
@router.post("/admin/content/validate",response_model=ValidationOut)
def content_validate(body:ValidateRequest,user=Depends(admin_user),db:Session=Depends(get_db)):
    errors=validation_errors(db,body.content); return {"valid":not errors,"errors":errors}
@router.get("/admin/content/missing-report")
def missing(user=Depends(admin_user),db:Session=Depends(get_db)):
    kinds={k for (k,) in db.execute(select(ContentItem.kind).distinct())}; present={(a,b) for a,b in db.execute(select(Course.source_language,Course.target_language))}; codes=list(db.scalars(select(Language.code)))
    return {"missing_language_pairs":[{"source_language":a,"target_language":b} for a in codes for b in codes if a!=b and (a,b) not in present],"missing_content_kinds":sorted({"vocabulary","phrase","grammar_note","dialogue","pronunciation_note","cultural_note","reading"}-kinds)}
@router.get("/admin/content/issues",response_model=list[ContentIssueOut])
def content_issues(status:ContentIssueStatus|None=None,category:ContentIssueCategory|None=None,limit:int=Query(100,ge=1,le=200),offset:int=Query(0,ge=0),user=Depends(admin_user),db:Session=Depends(get_db)):
    q=select(ContentIssueReport); q=q.where(ContentIssueReport.status==status) if status else q; q=q.where(ContentIssueReport.category==category) if category else q
    return list(db.scalars(q.order_by(ContentIssueReport.created_at.desc(),ContentIssueReport.id.desc()).offset(offset).limit(limit)))
@router.patch("/admin/content/issues/{issue_id}",response_model=ContentIssueOut)
def update_content_issue(issue_id:str,body:ContentIssueUpdateIn,user=Depends(admin_user),db:Session=Depends(get_db)):
    issue=db.get(ContentIssueReport,issue_id)
    if not issue: fail(404,"content_issue_not_found","Content issue report not found")
    if body.duplicate_of_id:
        if body.duplicate_of_id==issue.id: fail(422,"invalid_duplicate_target","An issue cannot duplicate itself")
        if not db.get(ContentIssueReport,body.duplicate_of_id): fail(422,"duplicate_target_not_found","Duplicate target was not found")
    if "duplicate_of_id" in body.model_fields_set: issue.duplicate_of_id=body.duplicate_of_id
    if "triage_notes" in body.model_fields_set: issue.triage_notes=body.triage_notes
    if body.status=="duplicate" and not issue.duplicate_of_id: fail(422,"duplicate_target_required","duplicate_of_id is required when marking an issue duplicate")
    if body.status and body.status!=issue.status:
        now=datetime.now(timezone.utc)
        if body.status in {"triaged","resolved","wontfix","duplicate"} and not issue.triaged_at: issue.triaged_at=now
        if body.status in {"resolved","wontfix","duplicate"} and not issue.resolved_at: issue.resolved_at=now
        issue.status=body.status
    db.commit(); db.refresh(issue)
    return issue
@router.get("/admin/content/coverage",response_model=list[ContentCoverageOut])
def content_coverage(user=Depends(admin_user),db:Session=Depends(get_db)):
    rows=db.execute(
        select(
            Course.source_language,
            Course.target_language,
            func.count(func.distinct(Course.id)),
            func.count(func.distinct(Unit.id)),
            func.count(func.distinct(Lesson.id)),
            func.count(func.distinct(ContentIssueReport.id)).filter(ContentIssueReport.status=="open"),
        )
        .select_from(Course)
        .outerjoin(Unit,Unit.course_id==Course.id)
        .outerjoin(Lesson,Lesson.unit_id==Unit.id)
        .outerjoin(Exercise,Exercise.lesson_id==Lesson.id)
        .outerjoin(ContentIssueReport,ContentIssueReport.exercise_id==Exercise.id)
        .group_by(Course.source_language,Course.target_language)
        .order_by(Course.source_language,Course.target_language)
    ).all()
    return [{"source_language":source,"target_language":target,"course_count":courses,"total_unit_count":units,"total_lesson_count":lessons,"open_issue_count":issues} for source,target,courses,units,lessons,issues in rows]

@router.post("/tts",responses={200:{"content":{"audio/mpeg":{},"application/json":{"schema":TTSFallback.model_json_schema()}}}})
def tts(body:TTSIn,user=Depends(current_user),db:Session=Depends(get_db)):
    if not db.get(Language,body.language_code): fail(422,"unsupported_language_code","Language code is not supported")
    if body.language_code not in tts_service.GOOGLE_TTS_SUPPORTED_LANGUAGES:
        return JSONResponse({"use_browser_tts":True,"reason":"unsupported_language"})
    if not tts_service.reserve_characters(db,len(body.text)):
        return JSONResponse({"use_browser_tts":True,"reason":"quota_exceeded"})
    try: audio=tts_service.synthesize(body.text,body.language_code)
    except Exception:
        db.rollback()
        return JSONResponse({"use_browser_tts":True,"reason":"provider_error"})
    db.commit()
    return Response(content=audio,media_type="audio/mpeg")
