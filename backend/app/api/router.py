import logging
import mimetypes
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy import Float, case, delete, func, select, text
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.rate_limit import DailyCharBudget, RateLimiter, register_limiter
from app.core.security import create_refresh_token, create_token, hash_password, verify_password
from app.core.errors import fail
from app.db.session import get_db
from app.models import (
    Achievement,
    CheckpointAttempt,
    ContentIssueReport,
    ContentItem,
    Course,
    Exercise,
    ExerciseAttempt,
    GrammarProgress,
    Language,
    Lesson,
    LessonProgress,
    Lexeme,
    PracticeAttempt,
    PracticeItem,
    PracticeTemplate,
    PushSubscription,
    RefreshToken,
    ReviewItem,
    SkillProgress,
    Unit,
    UnitSection,
    User,
    UserAchievement,
    UserLexemeSRS,
    UserStats,
    VocabularyProgress,
)
from app.schemas.api import (
    AnswerIn,
    AnswerOut,
    AuthOut,
    CheckpointIn,
    CheckpointResultOut,
    CompleteOut,
    ContentCoverageOut,
    ContentIssueCategory,
    ContentIssueCreatedOut,
    ContentIssueOut,
    ContentIssueReportIn,
    ContentIssueStatus,
    ContentIssueUpdateIn,
    CourseDetail,
    CourseOut,
    GeneralFeedbackIn,
    ImportOut,
    ImportRequest,
    LanguageOut,
    LanguagePairOut,
    LessonDetail,
    LessonOut,
    LexemeListOut,
    LexemeSort,
    LexemeSummaryOut,
    LoginIn,
    LogoutIn,
    MeOut,
    MistakeLexemeListOut,
    PracticeAnswerOut,
    PracticeArtifactImport,
    PracticeBatchIn,
    PracticeBatchOut,
    PracticeImportOut,
    PushNotifyOut,
    PushSubscribeIn,
    PushUnsubscribeIn,
    PushVapidKeyOut,
    QuestsOut,
    RefreshIn,
    RefreshOut,
    RegisterIn,
    ReviewAnswerOut,
    ReviewDueOut,
    ReviewItemsOut,
    ReviewSessionIn,
    STTOut,
    StartOut,
    StreakOut,
    TTSFallback,
    TTSIn,
    UnitOut,
    ValidateRequest,
    ValidationOut,
    XPOut,
)
from app.api.deps import current_user, optional_current_user, lenient_current_user, admin_user
from app.services.progress import activity_day_bounds, record_activity, resolve_user_tz, stats_for, valid_timezone_or_none
from app.services.quests import QUEST_DEFINITIONS, daily_quests_for
from app.review.sm2 import schedule
from app.review.grading import (
    decode_feedback,
    display_correct_response,
    grade,
    select_feedback,
)
from app.services import tts as tts_service
from app.services import stt as stt_service
from app.services import push as push_service
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

logger = logging.getLogger(__name__)

router=APIRouter()

# Rate limiting: per-IP for the unauthenticated auth endpoints (brute-force
# login protection, registration-abuse prevention), per-account for the
# answer endpoints (same resource-exhaustion-adjacent surface as the
# AnswerIn payload-size bound above — generous enough that no real lesson
# pace ever trips it). See app/core/rate_limit.py for why this is
# in-memory rather than Redis-backed. Limits are deliberately loose/simple
# per Ramin's ask, not tuned against real traffic yet.
_rate_limit_settings = get_settings()
LOGIN_RATE_LIMIT = register_limiter(RateLimiter(limit=_rate_limit_settings.login_rate_limit_max, window_seconds=60))
REGISTER_RATE_LIMIT = register_limiter(RateLimiter(limit=_rate_limit_settings.register_rate_limit_max, window_seconds=3600))
ANSWER_RATE_LIMIT = register_limiter(RateLimiter(limit=_rate_limit_settings.answer_rate_limit_max, window_seconds=60))
# Phase H2 (2026-07-07 integrity audit, docs/SONNET_BUILD_PROMPT_LAUNCH.md):
# /tts, /stt/transcribe, and the three generation endpoints were completely
# unrated. TTS additionally gets a per-account daily character budget,
# separate from TTSUsage's account-agnostic shared monthly budget.
TTS_RATE_LIMIT = register_limiter(RateLimiter(limit=_rate_limit_settings.tts_rate_limit_max, window_seconds=60))
TTS_DAILY_CHAR_BUDGET = register_limiter(DailyCharBudget(daily_limit=_rate_limit_settings.tts_daily_char_cap))
STT_RATE_LIMIT = register_limiter(RateLimiter(limit=_rate_limit_settings.stt_rate_limit_max, window_seconds=60))
GENERATION_RATE_LIMIT = register_limiter(RateLimiter(limit=_rate_limit_settings.generation_rate_limit_max, window_seconds=60))
# Phase H4: content-issue report endpoints never had any rate limit.
REPORT_RATE_LIMIT = register_limiter(RateLimiter(limit=_rate_limit_settings.report_rate_limit_max, window_seconds=60))

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

def utc_now():
    return datetime.now(timezone.utc)

def as_aware(value):
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

def issue_refresh_token(db:Session,user_id:str,now_value:datetime|None=None) -> str:
    raw_token=create_refresh_token()
    now_value=now_value or utc_now()
    db.add(
        RefreshToken(
            token_hash=hash_password(raw_token),
            user_id=user_id,
            issued_at=now_value,
            expires_at=now_value+timedelta(seconds=get_settings().refresh_token_expire_seconds),
        )
    )
    return raw_token

def find_refresh_token(db:Session,raw_token:str):
    for token in db.scalars(select(RefreshToken)):
        try:
            if verify_password(raw_token,token.token_hash):
                return token
        except Exception:
            continue
    return None

def revoke_all_refresh_tokens(db:Session,user_id:str,now_value:datetime):
    for token in db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id==user_id,
            RefreshToken.revoked_at.is_(None),
        )
    ):
        token.revoked_at=now_value

def auth_response(db:Session,user):
    refresh_token=issue_refresh_token(db,user.id)
    db.commit()
    return {"access_token":create_token(user.id),"refresh_token":refresh_token,"token_type":"bearer","expires_in":get_settings().access_token_expire_seconds,"user":user}

def refresh_response(db:Session,user_id:str):
    refresh_token=issue_refresh_token(db,user_id)
    return {"access_token":create_token(user_id),"refresh_token":refresh_token,"token_type":"bearer","expires_in":get_settings().access_token_expire_seconds}
def resolve_script(db, language_code):
    if not language_code:
        return None
    language = db.get(Language, language_code)
    return language.script if language else None
def exercise_answer(db, user, e, response):
    feedback_meta = decode_feedback(e.feedback)
    script = resolve_script(db, e.prompt.get("answer_language_code"))
    result = grade(
        response,
        e.correct_response,
        e.type,
        script=script,
        orthography_strict=feedback_meta.get("orthography_strict"),
        case_sensitive=bool(feedback_meta.get("case_sensitive")),
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

def require_speaking_unlocked(db:Session, unit:"Unit", user) -> None:
    # Phase H1 (2026-07-07 integrity audit): start() already ran this check;
    # exercise_answer()/complete() didn't, letting a user enumerate a locked
    # unit's lessons, answer every exercise by id (earning XP), and complete
    # each lesson without ever unlocking speaking. Shared helper, 3 call
    # sites (start, answer, complete), same check each time.
    if unit.section==UnitSection.speaking and not user.is_admin and not speaking_unlocked(db,unit.course_id,user.id):
        fail(409,"speaking_locked","Complete all reading and writing units before starting speaking lessons")

@router.post("/auth/register",response_model=AuthOut,status_code=201)
def register(body:RegisterIn,request:Request,db:Session=Depends(get_db)):
    enforce_rate_limit(REGISTER_RATE_LIMIT,client_ip(request),"register_rate_limited","Too many registration attempts from this address. Please try again later.")
    email=body.email.lower()
    if db.scalar(select(User).where(User.email==email)): fail(409,"email_exists","An account with this email already exists")
    user=User(email=email,password_hash=hash_password(body.password),display_name=body.display_name or email.split("@")[0],is_admin=email in get_settings().admin_email_set,timezone=valid_timezone_or_none(body.timezone)); db.add(user); db.flush()
    db.add(UserStats(user_id=user.id,total_xp=0,streak_days=0,last_activity_date=None,daily_goal=20))
    return auth_response(db,user)
@router.post("/auth/login",response_model=AuthOut)
def login(body:LoginIn,request:Request,db:Session=Depends(get_db)):
    enforce_rate_limit(LOGIN_RATE_LIMIT,client_ip(request),"login_rate_limited","Too many login attempts. Please wait before trying again.")
    user=db.scalar(select(User).where(User.email==body.email.lower()))
    if not user or not verify_password(body.password,user.password_hash): fail(401,"invalid_credentials","Invalid email or password")
    valid_tz=valid_timezone_or_none(body.timezone)
    if valid_tz and valid_tz!=user.timezone: user.timezone=valid_tz
    return auth_response(db,user)
@router.post("/auth/refresh",response_model=RefreshOut)
def refresh(body:RefreshIn,db:Session=Depends(get_db)):
    refresh_token=find_refresh_token(db,body.refresh_token)
    now_value=utc_now()
    if not refresh_token:
        fail(401,"invalid_refresh_token","Invalid or expired refresh token")
    if refresh_token.revoked_at is not None:
        revoke_all_refresh_tokens(db,refresh_token.user_id,now_value)
        db.commit()
        fail(401,"refresh_token_reused","Refresh token was already used or revoked")
    if as_aware(refresh_token.expires_at)<=now_value:
        fail(401,"invalid_refresh_token","Invalid or expired refresh token")
    user=db.get(User,refresh_token.user_id)
    if not user:
        fail(401,"invalid_refresh_token","Invalid or expired refresh token")
    refresh_token.revoked_at=now_value
    response=refresh_response(db,user.id)
    db.commit()
    return response
@router.post("/auth/logout",status_code=204)
def logout(body:LogoutIn,db:Session=Depends(get_db)):
    refresh_token=find_refresh_token(db,body.refresh_token)
    if refresh_token and refresh_token.revoked_at is None:
        refresh_token.revoked_at=utc_now()
        db.commit()
    return Response(status_code=204)
@router.get("/auth/me",response_model=MeOut)
def me(user=Depends(current_user)): return user
@router.delete("/me",status_code=204)
def delete_me(user=Depends(current_user),db:Session=Depends(get_db)):
    user_practice_item_ids = select(PracticeItem.id).where(PracticeItem.user_id == user.id)
    db.execute(
        delete(ContentIssueReport).where(
            ContentIssueReport.practice_item_id.in_(user_practice_item_ids)
        )
    )
    db.execute(
        delete(PracticeAttempt).where(
            (PracticeAttempt.user_id == user.id)
            | (PracticeAttempt.practice_item_id.in_(user_practice_item_ids))
        )
    )
    db.delete(user)
    db.commit()
    return Response(status_code=204)
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
                "completed_lesson_count":(
                    db.scalar(
                        select(func.count(LessonProgress.id))
                        .join(Lesson,Lesson.id==LessonProgress.lesson_id)
                        .where(
                            LessonProgress.user_id==user.id,
                            Lesson.unit_id==unit.id,
                            LessonProgress.completed_at.is_not(None),
                        )
                    )
                    if user
                    else 0
                ),
                "section":unit.section,
                "locked":unit.section==UnitSection.speaking and not unlocked,
                "checkpoint_passed":checkpoint_passed,
                "content_key":unit.content_key,
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
    teaching=[{"kind":item.kind,"title":item.title or None,"text_blocks":item.content.get("text_blocks",[]),"note":item.content.get("note"),"examples":item.content.get("examples")} for item in l.teaching_items]
    return {"id":l.id,"unit_id":l.unit_id,"title":l.title,"teaching":teaching,"exercises":[{"id":e.id,"type":e.type,"order":e.order,"prompt":e.prompt} for e in l.exercises]}
@router.post("/lessons/{lesson_id}/start",response_model=StartOut)
def start(lesson_id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    lesson_row=db.get(Lesson,lesson_id)
    if not lesson_row: fail(404,"lesson_not_found","Lesson not found")
    unit=db.get(Unit,lesson_row.unit_id)
    require_speaking_unlocked(db,unit,user)
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
    lesson_row=db.get(Lesson,e.lesson_id)
    unit=db.get(Unit,lesson_row.unit_id)
    require_speaking_unlocked(db,unit,user)
    return exercise_answer(db,user,e,body.response)
@router.post("/exercises/{exercise_id}/report",response_model=ContentIssueCreatedOut,status_code=201)
def report_content_issue(exercise_id:str,body:ContentIssueReportIn,request:Request,user=Depends(current_user),db:Session=Depends(get_db)):
    enforce_rate_limit(REPORT_RATE_LIMIT,user.id,"report_rate_limited","Too many reports submitted too quickly. Please slow down.")
    if not db.get(Exercise,exercise_id): fail(404,"exercise_not_found","Exercise not found")
    issue=ContentIssueReport(reporter_user_id=user.id,exercise_id=exercise_id,category=body.category,description=body.description,learner_response=body.learner_response,client_context={"user_agent":request.headers.get("user-agent",""),"accept_language":request.headers.get("accept-language","")})
    db.add(issue); db.commit(); db.refresh(issue)
    return issue
@router.post("/practice/items/{item_id}/report",response_model=ContentIssueCreatedOut,status_code=201)
def report_practice_item_issue(item_id:str,body:ContentIssueReportIn,request:Request,user=Depends(current_user),db:Session=Depends(get_db)):
    enforce_rate_limit(REPORT_RATE_LIMIT,user.id,"report_rate_limited","Too many reports submitted too quickly. Please slow down.")
    # PracticeItem-backed content (review sessions, unit checkpoints, and
    # the Endless Practice feed all generate PracticeItem rows, never
    # Exercise rows) has no report path through the endpoint above.
    # Ownership-checked the same way /practice/items/{id}/answer is:
    # a foreign item 404s rather than leaking whether the id exists.
    item=db.get(PracticeItem,item_id)
    if not item or item.user_id!=user.id: fail(404,"practice_item_not_found","Practice item not found")
    issue=ContentIssueReport(reporter_user_id=user.id,practice_item_id=item_id,category=body.category,description=body.description,learner_response=body.learner_response,client_context={"user_agent":request.headers.get("user-agent",""),"accept_language":request.headers.get("accept-language","")})
    db.add(issue); db.commit(); db.refresh(issue)
    return issue
@router.post("/feedback",response_model=ContentIssueCreatedOut,status_code=201)
def report_general_feedback(body:GeneralFeedbackIn,request:Request,user=Depends(lenient_current_user),db:Session=Depends(get_db)):
    rate_key=user.id if user else client_ip(request)
    enforce_rate_limit(REPORT_RATE_LIMIT,rate_key,"report_rate_limited","Too many reports submitted too quickly. Please slow down.")
    issue=ContentIssueReport(reporter_user_id=user.id if user else None,exercise_id=None,practice_item_id=None,page_path=body.page_path,category=body.category,description=body.description,client_context=body.client_context)
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
    require_speaking_unlocked(db, unit, user)
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
    result=grade(body.response,e.correct_response,e.type,script=script,orthography_strict=feedback_meta.get("orthography_strict"),case_sensitive=bool(feedback_meta.get("case_sensitive")))
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


@router.get("/me/lexemes", response_model=LexemeListOut)
def lexemes(
    course_id: str,
    sort: LexemeSort = "due_soonest",
    part_of_speech: str | None = None,
    search: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    if not db.get(Course, course_id):
        fail(404, "course_not_found", "Course not found")

    conditions = [
        UserLexemeSRS.user_id == user.id,
        UserLexemeSRS.course_id == course_id,
        Lexeme.course_id == course_id,
    ]
    if part_of_speech:
        conditions.append(Lexeme.part_of_speech == part_of_speech)
    if search:
        pattern = f"%{search}%"
        conditions.append(
            Lexeme.token.ilike(pattern)
            | Lexeme.english_gloss.ilike(pattern)
        )

    total_count = db.scalar(
        select(func.count(UserLexemeSRS.id))
        .join(Lexeme, Lexeme.id == UserLexemeSRS.lexeme_id)
        .where(*conditions)
    ) or 0

    orderings = {
        "due_soonest": (
            UserLexemeSRS.suspended.asc(),
            UserLexemeSRS.due_at.asc(),
            Lexeme.token.asc(),
        ),
        "mastery_asc": (UserLexemeSRS.mastery.asc(), Lexeme.token.asc()),
        "mastery_desc": (UserLexemeSRS.mastery.desc(), Lexeme.token.asc()),
        "alphabetical": (Lexeme.token.asc(), Lexeme.english_gloss.asc()),
        "recently_introduced": (
            UserLexemeSRS.introduced_at.desc(),
            Lexeme.token.asc(),
        ),
    }
    rows = db.execute(
        select(Lexeme, UserLexemeSRS)
        .join(UserLexemeSRS, UserLexemeSRS.lexeme_id == Lexeme.id)
        .where(*conditions)
        .order_by(*orderings[sort])
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "items": [
            {
                "token": lexeme.token,
                "english_gloss": lexeme.english_gloss,
                "part_of_speech": lexeme.part_of_speech,
                "mastery": srs.mastery,
                "interval_days": srs.interval_days,
                "repetitions": srs.repetitions,
                "due_at": srs.due_at,
                "introduced_at": srs.introduced_at,
                "suspended": srs.suspended,
                "last_reviewed_at": srs.last_reviewed_at,
            }
            for lexeme, srs in rows
        ],
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/me/lexemes/summary", response_model=LexemeSummaryOut)
def lexeme_summary(
    course_id: str,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    if not db.get(Course, course_id):
        fail(404, "course_not_found", "Course not found")

    conditions = (
        UserLexemeSRS.user_id == user.id,
        UserLexemeSRS.course_id == course_id,
    )
    _, day_end = activity_day_bounds(user.timezone)
    row = db.execute(
        select(
            func.count(UserLexemeSRS.id),
            # Rough learner-facing bands over the 0.0-1.0 mastery score:
            # <0.33 just introduced, <0.75 still learning, >=0.75 strong.
            func.sum(case((UserLexemeSRS.mastery < 0.33, 1), else_=0)),
            func.sum(
                case(
                    (
                        (UserLexemeSRS.mastery >= 0.33)
                        & (UserLexemeSRS.mastery < 0.75),
                        1,
                    ),
                    else_=0,
                )
            ),
            func.sum(case((UserLexemeSRS.mastery >= 0.75, 1), else_=0)),
            func.sum(
                case(
                    (
                        (UserLexemeSRS.due_at <= day_end)
                        & (UserLexemeSRS.suspended.is_(False)),
                        1,
                    ),
                    else_=0,
                )
            ),
            func.sum(case((UserLexemeSRS.suspended.is_(True), 1), else_=0)),
        ).where(*conditions)
    ).one()
    return {
        "total_tracked": row[0] or 0,
        "mastery_bands": {
            "new": row[1] or 0,
            "learning": row[2] or 0,
            "strong": row[3] or 0,
        },
        "due_today": row[4] or 0,
        "suspended": row[5] or 0,
    }


@router.get("/me/mistakes", response_model=MistakeLexemeListOut)
def mistakes(
    course_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    if not db.get(Course, course_id):
        fail(404, "course_not_found", "Course not found")

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    correct_count = func.sum(
        case((PracticeAttempt.correct.is_(True), 1), else_=0)
    ).label("correct_count")
    wrong_count = func.sum(
        case((PracticeAttempt.correct.is_(False), 1), else_=0)
    ).label("wrong_attempt_count")
    total_attempts = func.count(PracticeAttempt.id).label("total_attempt_count")
    accuracy = (
        correct_count.cast(Float) / func.nullif(total_attempts, 0)
    ).label("recent_accuracy")

    # Real per-lexeme attempt history exists only for generated
    # PracticeItem-backed flows (practice, review, checkpoint), where
    # PracticeItem.target_lexeme_id identifies the word being tested.
    # Legacy ExerciseAttempt rows for hand-authored lesson exercises do not
    # carry a lexeme id, so they cannot honestly power a per-word mistakes
    # hub without a new persistence model.
    grouped = (
        select(
            Lexeme.token.label("token"),
            Lexeme.english_gloss.label("english_gloss"),
            Lexeme.part_of_speech.label("part_of_speech"),
            UserLexemeSRS.mastery.label("mastery"),
            UserLexemeSRS.repetitions.label("repetitions"),
            accuracy,
            wrong_count,
            total_attempts,
        )
        .join(PracticeItem, PracticeItem.target_lexeme_id == Lexeme.id)
        .join(
            PracticeAttempt,
            PracticeAttempt.practice_item_id == PracticeItem.id,
        )
        .join(
            UserLexemeSRS,
            (UserLexemeSRS.lexeme_id == Lexeme.id)
            & (UserLexemeSRS.user_id == user.id),
        )
        .where(
            PracticeAttempt.user_id == user.id,
            PracticeAttempt.created_at >= cutoff,
            PracticeItem.course_id == course_id,
            PracticeItem.target_lexeme_id.is_not(None),
            Lexeme.course_id == course_id,
            UserLexemeSRS.course_id == course_id,
        )
        .group_by(
            Lexeme.id,
            Lexeme.token,
            Lexeme.english_gloss,
            Lexeme.part_of_speech,
            UserLexemeSRS.mastery,
            UserLexemeSRS.repetitions,
        )
        .having(wrong_count > 0)
    ).subquery()

    total_count = db.scalar(select(func.count()).select_from(grouped)) or 0
    rows = db.execute(
        select(grouped)
        .order_by(
            grouped.c.wrong_attempt_count.desc(),
            grouped.c.recent_accuracy.asc(),
            grouped.c.mastery.asc(),
            grouped.c.token.asc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "items": [dict(row._mapping) for row in rows],
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.get("/push/vapid-public-key", response_model=PushVapidKeyOut)
def push_vapid_public_key():
    settings = get_settings()
    configured = push_service.push_configured()
    return {
        "public_key": settings.vapid_public_key if configured else None,
        "configured": configured,
    }
@router.post("/push/subscribe")
def push_subscribe(
    body: PushSubscribeIn,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    if not push_service.push_configured():
        fail(503, "push_not_configured", "Web push is not configured on this server")
    existing = db.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    )
    if existing:
        existing.user_id = user.id
        existing.p256dh = body.keys.p256dh
        existing.auth = body.keys.auth
    else:
        db.add(
            PushSubscription(
                user_id=user.id,
                endpoint=body.endpoint,
                p256dh=body.keys.p256dh,
                auth=body.keys.auth,
            )
        )
    db.commit()
    return {"subscribed": True}
@router.post("/push/unsubscribe")
def push_unsubscribe(
    body: PushUnsubscribeIn,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    sub = db.scalar(
        select(PushSubscription).where(
            PushSubscription.endpoint == body.endpoint,
            PushSubscription.user_id == user.id,
        )
    )
    if sub:
        db.delete(sub)
        db.commit()
    return {"subscribed": False}
@router.post("/admin/push/notify-due-reviews", response_model=PushNotifyOut)
def admin_push_notify_due_reviews(
    user=Depends(admin_user),
    db: Session = Depends(get_db),
):
    """Manual trigger for the one real E4 notification case ("you have
    due reviews"). NOT on a schedule — this project has no background
    scheduler/cron infrastructure (no Celery/APScheduler/worker service
    in docker-compose.yml), so autonomous periodic firing is explicitly
    out of scope for this pass rather than inventing new infrastructure
    to support it; see docs/BUILD_LOG.md's E4 entry. An external caller
    (a real cron, a manually-triggered admin action, etc.) hits this
    endpoint whenever a "reviews due" push should go out.
    """
    if not push_service.push_configured():
        fail(503, "push_not_configured", "Web push is not configured on this server")
    now = datetime.now(timezone.utc)
    user_ids = db.scalars(
        select(UserLexemeSRS.user_id)
        .where(
            UserLexemeSRS.due_at <= now,
            UserLexemeSRS.suspended.is_(False),
        )
        .distinct()
    ).all()
    notified_users = 0
    notifications_sent = 0
    for uid_ in user_ids:
        sent = push_service.send_push_to_user(
            db,
            uid_,
            title="Reviews are waiting",
            body="You have words due for review — keep your streak going.",
            url="/review",
        )
        if sent:
            notified_users += 1
            notifications_sent += sent
    return {"notified_users": notified_users, "notifications_sent": notifications_sent}


@router.post("/admin/push/notify-streaks-at-risk", response_model=PushNotifyOut)
def admin_push_notify_streaks_at_risk(
    user=Depends(admin_user),
    db: Session = Depends(get_db),
):
    """Manual trigger for the evening "your streak ends tonight" push.
    Same design as /admin/push/notify-due-reviews above: NOT on a
    schedule — this project deliberately has no background scheduler/
    cron infrastructure, so an external cron (see
    scripts/trigger_streak_notifications.sh) hits this endpoint in the
    evening. A user's streak is "at risk" when they have a streak worth
    protecting (streak_days > 0) and haven't been active yet TODAY in
    their OWN timezone — the same per-user day boundary
    record_activity() uses (activity_day_bounds(), E2), so this never
    disagrees with the actual streak bookkeeping about whether today
    still counts.

    No per-day send dedup exists: every call re-notifies every
    still-inactive user, so the external cron should fire this once per
    evening, not repeatedly (documented in the trigger script).
    """
    if not push_service.push_configured():
        fail(503, "push_not_configured", "Web push is not configured on this server")
    rows = db.execute(
        select(UserStats.user_id, UserStats.streak_days, UserStats.last_activity_date, User.timezone)
        .join(User, User.id == UserStats.user_id)
        .where(UserStats.streak_days > 0)
    ).all()
    notified_users = 0
    notifications_sent = 0
    for uid_, streak_days, last_activity_date, user_tz in rows:
        day_start, _ = activity_day_bounds(user_tz)
        if last_activity_date == day_start.date():
            # Already active today in their own timezone — streak is safe.
            continue
        sent = push_service.send_push_to_user(
            db,
            uid_,
            title="Your streak is at risk",
            body=f"Your {streak_days}-day streak ends tonight — come back before midnight!",
            url="/",
        )
        if sent:
            notified_users += 1
            notifications_sent += sent
    return {"notified_users": notified_users, "notifications_sent": notifications_sent}


@router.post("/reviews/session", response_model=ReviewItemsOut)
def review_session(
    body: ReviewSessionIn,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    enforce_rate_limit(GENERATION_RATE_LIMIT,user.id,"generation_rate_limited","Too many generation requests too quickly. Please slow down.")
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
    enforce_rate_limit(GENERATION_RATE_LIMIT,user.id,"generation_rate_limited","Too many generation requests too quickly. Please slow down.")
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
        all_unit_lexeme_ids = set(
            db.scalars(
                select(Lexeme.id)
                .join(Lesson, Lesson.id == Lexeme.provenance_lesson_id)
                .where(Lesson.unit_id == unit_id)
                .distinct()
            )
        )
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
                    UserLexemeSRS.lexeme_id.in_(all_unit_lexeme_ids),
                )
                .with_for_update()
            )
        ) if all_unit_lexeme_ids else set()
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
        for lexeme_id in (
            all_unit_lexeme_ids - covered_lexeme_ids - existing_lexeme_ids
        ):
            db.add(
                UserLexemeSRS(
                    user_id=user.id,
                    lexeme_id=lexeme_id,
                    course_id=unit.course_id,
                    ease_factor=2.5,
                    interval_days=1,
                    repetitions=0,
                    # The checkpoint passed the unit but did not directly
                    # sample this lexeme, so seed it as known-enough to enter
                    # SRS while still due soon for an actual recall check.
                    mastery=0.3,
                    due_at=scored_at + timedelta(days=1),
                    last_reviewed_at=None,
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
def xp(user=Depends(current_user),db:Session=Depends(get_db)):
    s=stats_for(db,user.id)
    # xp_today = XP earned within the user's own local day (the same
    # activity_day_bounds() window streaks/quests/practice caps already
    # use), summed live from the persisted per-answer rows rather than a
    # new counter column: ExerciseAttempt covers lesson answers,
    # PracticeAttempt covers practice/review-session/checkpoint answers,
    # and today's QuestCompletion rows cover quest rewards (completions
    # don't persist the reward amount, so it's joined back to the
    # hardcoded QUEST_DEFINITIONS by code). LessonProgress.xp_earned is
    # deliberately NOT added — it is a running sum of the same
    # ExerciseAttempt rows, so adding it would double-count every lesson
    # answer. Known gap (documented in CONTRACT.md): the legacy
    # /reviews/{id}/answer flow bumps total_xp without persisting any
    # per-answer XP row, so its XP can't be attributed to a day — the
    # frontend stopped using that flow with Phase A/E1.
    day_start,day_end=activity_day_bounds(user.timezone)
    exercise_xp=db.scalar(
        select(func.coalesce(func.sum(ExerciseAttempt.xp_awarded),0)).where(
            ExerciseAttempt.user_id==user.id,
            ExerciseAttempt.created_at>=day_start,
            ExerciseAttempt.created_at<day_end,
        )
    ) or 0
    practice_xp=db.scalar(
        select(func.coalesce(func.sum(PracticeAttempt.xp_awarded),0)).where(
            PracticeAttempt.user_id==user.id,
            PracticeAttempt.created_at>=day_start,
            PracticeAttempt.created_at<day_end,
        )
    ) or 0
    quest_rewards={q["code"]:q["xp_reward"] for q in QUEST_DEFINITIONS}
    quest_xp=sum(
        quest_rewards.get(code,0)
        for code in db.scalars(
            select(QuestCompletion.quest_code).where(
                QuestCompletion.user_id==user.id,
                QuestCompletion.date==day_start.date(),
            )
        )
    )
    return {"total_xp":s.total_xp,"daily_goal":s.daily_goal,"xp_today":exercise_xp+practice_xp+quest_xp}
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
    enforce_rate_limit(GENERATION_RATE_LIMIT,user.id,"generation_rate_limited","Too many generation requests too quickly. Please slow down.")
    course=db.get(Course,course_id)
    if not course: fail(404,"course_not_found","Course not found")
    locked,items=generate_batch(
        db,
        user.id,
        course,
        body.size if body else 10,
        is_admin=user.is_admin,
    )
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
def tts(request:Request,body:TTSIn,user=Depends(current_user),db:Session=Depends(get_db)):
    enforce_rate_limit(TTS_RATE_LIMIT,user.id,"tts_rate_limited","Too many TTS requests too quickly. Please slow down.")
    if not db.get(Language,body.language_code): fail(422,"unsupported_language_code","Language code is not supported")
    if body.language_code not in tts_service.TTS_SUPPORTED_LANGUAGES:
        return JSONResponse({"use_browser_tts":True,"reason":"unsupported_language"})
    # Per-account daily character budget (Phase H2), separate from the
    # account-agnostic shared monthly budget just below -- without this, one
    # account alone could burn the entire month's quota in ~800 requests.
    # Same graceful-degradation shape as the shared-budget check: fall back
    # to browser TTS rather than hard-failing, since from the frontend's
    # perspective "out of quota" reads identically either way.
    if not TTS_DAILY_CHAR_BUDGET.reserve(user.id,len(body.text)):
        return JSONResponse({"use_browser_tts":True,"reason":"quota_exceeded"})
    if not tts_service.reserve_characters(db,len(body.text)):
        return JSONResponse({"use_browser_tts":True,"reason":"quota_exceeded"})
    try: audio=tts_service.synthesize(body.text,body.language_code,body.speaking_rate or 1.0)
    except Exception:
        # Previously swallowed silently — a dead/corrupted Google or Azure
        # credential looked identical to normal operation server-side (the
        # client just quietly used browser TTS). Log the real provider
        # exception with the request id before degrading.
        logger.exception(
            "tts synthesis failed, falling back to browser TTS request_id=%s user_id=%s language=%s",
            getattr(request.state, "request_id", None), user.id, body.language_code,
        )
        tts_service.refund_characters(db,len(body.text))
        return JSONResponse({"use_browser_tts":True,"reason":"provider_error"})
    return Response(content=audio,media_type="audio/mpeg")

@router.post("/stt/transcribe",response_model=STTOut)
async def stt_transcribe(
    language_code: str = Form(...),
    audio: UploadFile = File(...),
    user=Depends(current_user),
):
    enforce_rate_limit(STT_RATE_LIMIT,user.id,"stt_rate_limited","Too many transcription requests too quickly. Please slow down.")
    # Fallback STT only — the frontend only calls this when client-side WASM
    # Whisper isn't available (no WebAssembly threads, model failed to load,
    # etc). Self-hosted faster-whisper, never a cloud API. Same size cap as
    # recorded media assets — a spoken answer is a few seconds of audio, not
    # minutes, so 5 MB is generous headroom while still bounding worst case.
    total_bytes = 0
    chunks: list[bytes] = []
    while chunk := await audio.read(64 * 1024):
        total_bytes += len(chunk)
        if total_bytes > MAX_AUDIO_SIZE_BYTES:
            fail(413, "audio_too_large", "Recording must not exceed 5 MB")
        chunks.append(chunk)
    if total_bytes == 0:
        fail(422, "empty_audio", "Recording must not be empty")
    audio_bytes = b"".join(chunks)
    try:
        transcript = await run_in_threadpool(
            stt_service.transcribe_audio,
            audio_bytes,
            language_code,
        )
    except Exception:
        fail(500, "transcription_failed", "Speech-to-text transcription failed")
    finally:
        # Privacy default: discard raw audio immediately after transcription
        # — never written to disk, never logged, not retained beyond this
        # request's stack frame.
        del audio_bytes, chunks
    return {"transcript": transcript}
