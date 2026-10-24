import csv
import hashlib
import io
import logging
import mimetypes
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4
from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy import Float, case, delete, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from app.core.config import get_settings
from app.core.rate_limit import DailyCharBudget, RateLimiter, register_limiter
from app.core.security import create_refresh_token, create_token, hash_password, open_successor_token, seal_successor_token, verify_password
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
    ExerciseType,
    FeedbackAttachment,
    GrammarProgress,
    Language,
    Lesson,
    LessonProgress,
    Lexeme,
    PracticeAttempt,
    PracticeItem,
    PracticeTemplate,
    PushSubscription,
    QuestCompletion,
    RefreshToken,
    ReviewItem,
    SkillProgress,
    Unit,
    UnitSection,
    User,
    UserAchievement,
    UserIdentity,
    SocialLoginNonce,
    UserLexemeSRS,
    UserStats,
    VocabularyProgress,
)
from app.schemas.api import (
    AnswerIn,
    AnswerOut,
    AdminPasswordResetOut,
    AdminUserAdminIn,
    AdminUserCreateIn,
    AdminUserCreateOut,
    AdminUserListOut,
    AdminUserOut,
    AdminUserUnlockIn,
    AdminUserUnlockOut,
    AuthOut,
    CheckpointIn,
    CheckpointResultOut,
    CompleteOut,
    ContentCoverageOut,
    ContentIssueCategory,
    ContentIssueCreatedOut,
    FeedbackAttachmentUploadOut,
    ContentIssueOut,
    ContentIssueReportIn,
    ContentIssueStatus,
    ContentIssueUpdateIn,
    CourseDetail,
    CourseOut,
    GeneralFeedbackIn,
    ImportOut,
    ImportRequest,
    DailyGoalIn,
    DailyGoalOut,
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
    PlacementAnswerIn,
    PlacementAnswerOut,
    PlacementResultIn,
    PlacementResultOut,
    PlacementSetOut,
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
    SocialLinkIn,
    SocialLoginIn,
    SocialNonceOut,
    SocialUnlinkIn,
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
from app.api.deps import current_user, optional_current_user, lenient_current_user, admin_user, is_admin_user
from app.services.progress import activity_day_bounds, effective_streak_days, record_activity, resolve_user_tz, stats_for, valid_timezone_or_none, award_xp
from app.services.quests import QUEST_DEFINITIONS, daily_quests_for
from app.review.sm2 import schedule
from app.review.grading import (
    decode_feedback,
    display_correct_response,
    exercise_type_value,
    grade,
    is_arabic_hamza_only_difference,
    select_feedback,
)
from app.review.placement import (
    PLACEMENT_BLOCK_SIZE,
    PLACEMENT_LEVELS,
    PLACEMENT_PASS_THRESHOLD,
    parse_cefr_level,
    recommend_from_answers,
)
from app.services import tts as tts_service
from app.services import stt as stt_service
from app.services import social_auth
from app.services import push as push_service
from app.services.push_scheduler import claim_notification, local_date_for
from app.services import feedback_attachments as feedback_attachment_service
from app.practice.service import (
    render_item_feedback,
    generate_batch,
    generate_checkpoint,
    generate_conversation_batch,
    generate_review_batch,
    generate_review_retry,
    generate_speaking_batch,
)
from app.content.service import (
    export_content,
    import_content,
    import_practice_templates,
    validation_errors,
)

logger = logging.getLogger(__name__)

router=APIRouter()

GENERATED_PRACTICE_TYPES = {"speak_repeat", "speak_response", "conversation"}


def practice_item_type(item: PracticeItem, template: PracticeTemplate) -> str:
    generated_type = (
        item.filled_slots.get("_generated_type")
        if isinstance(item.filled_slots, dict)
        else None
    )
    if generated_type in GENERATED_PRACTICE_TYPES:
        return generated_type
    return template.type


def conversation_public_node(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": node["id"],
        "app_turn": node["app_turn"],
        "accepted_variants": node["accepted_variants"],
        "answer_language_code": node["answer_language_code"],
        "terminal": node["terminal"],
    }


def conversation_nodes(prompt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        node["id"]: node
        for node in prompt.get("nodes") or []
        if isinstance(node, dict) and node.get("id")
    }


def conversation_reply_result(
    *,
    node: dict[str, Any],
    response: Any,
    script,
    language_code: str | None,
    input_mode: str = "typed",
) -> tuple[str, str | None]:
    best_result = "incorrect"
    best_variant = None
    for variant in node.get("accepted_variants") or []:
        result = grade(
            response,
            variant,
            "speak_response",
            script=script,
            language_code=language_code,
            input_mode=input_mode,
        )
        if result == "correct":
            return result, variant
        if result == "almost" and best_result == "incorrect":
            best_result = result
            best_variant = variant
    return best_result, best_variant


def conversation_next_node(
    *,
    node: dict[str, Any],
    matched_variant: str | None,
    nodes: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    if matched_variant is not None:
        for branch in node.get("branches") or []:
            if branch.get("variant") == matched_variant:
                return nodes.get(branch.get("next_node_id"))
        if node.get("terminal"):
            return None
    fallback_id = node.get("fallback_node_id")
    return nodes.get(fallback_id) if fallback_id else None

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
# 2026-07-10: /auth/refresh and /auth/logout shipped unrated. Both are
# unauthenticated and both funnel through find_refresh_token()'s
# bcrypt-verify-against-every-row scan, so an unrated caller gets a free
# token-probing surface AND a CPU sink. Shared limiter, per-IP, same
# convention as REPORT_RATE_LIMIT's shared coverage of its 3 endpoints.
REFRESH_RATE_LIMIT = register_limiter(RateLimiter(limit=_rate_limit_settings.refresh_rate_limit_max, window_seconds=60))
# POST /auth/social/nonce: each call stores a row, so it is capped like
# refresh rather than left open.
SOCIAL_NONCE_RATE_LIMIT = register_limiter(RateLimiter(limit=_rate_limit_settings.refresh_rate_limit_max, window_seconds=60))
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
# Screenshot uploads are unauthenticated for the same reason as /feedback
# itself, so they get their own per-IP limiter at the same ceiling/window.
FEEDBACK_ATTACHMENT_RATE_LIMIT = register_limiter(RateLimiter(limit=_rate_limit_settings.report_rate_limit_max, window_seconds=60))

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

def refresh_token_digest(raw_token:str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

def add_refresh_token(db:Session,user_id:str,now_value:datetime|None=None,raw_token:str|None=None) -> tuple[str,RefreshToken]:
    raw_token=raw_token or create_refresh_token()
    now_value=now_value or utc_now()
    row=RefreshToken(
        token_hash=hash_password(raw_token),
        token_sha256=refresh_token_digest(raw_token),
        user_id=user_id,
        issued_at=now_value,
        expires_at=now_value+timedelta(seconds=get_settings().refresh_token_expire_seconds),
    )
    db.add(row)
    db.flush()
    return raw_token,row

def add_proposed_refresh_token(db:Session,user_id:str,now_value:datetime,proposed:str) -> tuple[str,RefreshToken]|None:
    """Insert a client-proposed token, or return None if that value is taken.

    The existence check alone is not enough: another rotation (any user) may
    have inserted the same value without committing yet. The insert then
    waits on the unique index and fails once that transaction commits; the
    savepoint keeps that failure from aborting the surrounding rotation.
    """
    if db.scalar(select(RefreshToken.id).where(RefreshToken.token_sha256==refresh_token_digest(proposed))) is not None:
        return None
    savepoint=db.begin_nested()
    try:
        added=add_refresh_token(db,user_id,now_value,proposed)
    except IntegrityError:
        savepoint.rollback()
        return None
    savepoint.commit()
    return added

def issue_refresh_token(db:Session,user_id:str,now_value:datetime|None=None) -> str:
    return add_refresh_token(db,user_id,now_value)[0]

def find_refresh_token(db:Session,raw_token:str,for_update:bool=False):
    query=select(RefreshToken).where(RefreshToken.token_sha256==refresh_token_digest(raw_token))
    if for_update:
        # Serializes concurrent refreshes of the same token: the second
        # request waits for the first to commit and then sees the rotation
        # (and its recorded successor) instead of rotating a second time.
        query=query.with_for_update().execution_options(populate_existing=True)
    return db.scalar(query)

def prune_stale_refresh_tokens(db:Session,user_id:str,now_value:datetime):
    revoked_cutoff = now_value - timedelta(days=7)
    db.execute(delete(RefreshToken).where(
        RefreshToken.user_id==user_id,
        (RefreshToken.expires_at<=now_value)
        | (RefreshToken.revoked_at<=revoked_cutoff),
    ))

def lock_user_sessions(db:Session,user_id:str):
    """Serialize every refresh-token rotation and revoke-all of one user.

    Both paths take the user's row lock first (always before any token row
    lock, so the order cannot invert). Without it, a revoke-all could miss a
    successor that a concurrent rotation has inserted but not yet committed.
    """
    return db.scalar(select(User).where(User.id==user_id).with_for_update().execution_options(populate_existing=True))

def revoke_all_refresh_tokens(db:Session,user_id:str,now_value:datetime):
    lock_user_sessions(db,user_id)
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id==user_id,RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now_value)
        .execution_options(synchronize_session="fetch")
    )

def auth_response(db:Session,user):
    prune_stale_refresh_tokens(db,user.id,utc_now())
    refresh_token=issue_refresh_token(db,user.id)
    db.commit()
    return {"access_token":create_token(user.id),"refresh_token":refresh_token,"token_type":"bearer","expires_in":get_settings().access_token_expire_seconds,"user":{"id":user.id,"email":user.email,"display_name":user.display_name,"is_admin":is_admin_user(user)}}

def refresh_response(user_id:str,refresh_token:str):
    return {"access_token":create_token(user_id),"refresh_token":refresh_token,"token_type":"bearer","expires_in":get_settings().access_token_expire_seconds}

def rotate_refresh_token(db:Session,token:RefreshToken,presented_raw:str,proposed_next:str|None,now_value:datetime) -> str:
    # A client-proposed successor is honoured only if no token with that
    # value exists yet; otherwise the server picks one (the response is
    # always authoritative, the proposal is only a recovery aid).
    added=add_proposed_refresh_token(db,token.user_id,now_value,proposed_next) if proposed_next else None
    successor_raw,successor=added or add_refresh_token(db,token.user_id,now_value)
    token.revoked_at=now_value
    token.replaced_by_id=successor.id
    token.successor_sealed=seal_successor_token(presented_raw,token.token_sha256,successor_raw)
    # The token being rotated now has a successor of its own, so its
    # predecessor can no longer be answered from the grace path: drop that
    # sealed copy rather than keep it around until pruning.
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.replaced_by_id==token.id,RefreshToken.successor_sealed.is_not(None))
        .values(successor_sealed=None)
        .execution_options(synchronize_session=False)
    )
    return successor_raw

def replayed_successor(db:Session,token:RefreshToken,presented_raw:str,proposed_next:str|None,now_value:datetime) -> str|None:
    """Return the successor for a retried rotation, or None for real reuse.

    A rotated-out token is accepted again only while its successor is still
    the live head of the chain (not itself rotated, revoked or expired), and
    only when either
      - the caller also presents that successor as next_refresh_token, which
        proves it already holds the successor (a retry of the very same
        request, e.g. after the page was closed mid-request), or
      - the rotation happened within refresh_reuse_grace_seconds (a reload
        that lost the response, or a second tab racing the first), and the
        window has answered fewer than refresh_reuse_grace_max_replays
        retries of this rotation so far.
    The SAME refresh successor is returned; no new refresh token is minted,
    so the chain never branches. Each answer does carry a fresh access
    token, which is why the time-window path is capped: past the cap a
    replay is treated as reuse. The proof-of-possession path is not capped,
    because a caller holding the successor could refresh with it anyway.
    Logout- and reuse-revoked tokens have no successor and never qualify.
    """
    if token.replaced_by_id is None or not token.successor_sealed or token.revoked_at is None:
        return None
    successor=db.get(RefreshToken,token.replaced_by_id,with_for_update=True,populate_existing=True)
    if successor is None or successor.revoked_at is not None or as_aware(successor.expires_at)<=now_value:
        return None
    if proposed_next and secrets.compare_digest(refresh_token_digest(proposed_next),successor.token_sha256 or ""):
        return proposed_next
    settings=get_settings()
    grace=settings.refresh_reuse_grace_seconds
    if grace<=0 or now_value-as_aware(token.revoked_at)>timedelta(seconds=grace):
        return None
    if (token.grace_replays or 0)>=settings.refresh_reuse_grace_max_replays:
        return None
    successor_raw=open_successor_token(presented_raw,token.token_sha256,token.successor_sealed)
    if successor_raw is not None:
        token.grace_replays=(token.grace_replays or 0)+1
    return successor_raw
def social_audiences(provider:str) -> set[str]:
    settings=get_settings()
    if not settings.social_sign_in_enabled:
        return set()
    return settings.google_oauth_client_id_set if provider=="google" else settings.apple_audience_id_set
def issue_social_nonce(db:Session) -> tuple[str,int]:
    ttl=get_settings().social_nonce_ttl_seconds
    now_value=utc_now()
    db.execute(delete(SocialLoginNonce).where(SocialLoginNonce.expires_at<=now_value))
    raw=secrets.token_urlsafe(32)
    db.add(SocialLoginNonce(nonce_sha256=social_auth.nonce_digest(raw),expires_at=now_value+timedelta(seconds=ttl)))
    db.commit()
    return raw,ttl
def consume_social_nonce(db:Session,raw_nonce:str) -> bool:
    """Atomically use up a nonce this server issued; False if it was never
    issued, has expired, or was already used. Committed at once, so a
    sign-in that fails later still cannot reuse it."""
    consumed=db.execute(
        delete(SocialLoginNonce)
        .where(SocialLoginNonce.nonce_sha256==social_auth.nonce_digest(raw_nonce),SocialLoginNonce.expires_at>utc_now())
        .returning(SocialLoginNonce.nonce_sha256)
    ).first()
    db.commit()
    return consumed is not None
def verified_social_claims(db:Session,body:SocialLoginIn) -> dict:
    audiences=social_audiences(body.provider)
    if not audiences:
        fail(503,"social_login_unavailable",f"{body.provider.title()} social login is not configured")
    try:
        claims=social_auth.verify_id_token(body.provider,body.id_token,audiences,body.nonce)
    except social_auth.ProviderUnavailable:
        fail(503,"social_provider_unavailable",f"{body.provider.title()} sign-in is temporarily unavailable. Please try again.")
    except social_auth.SocialTokenError:
        fail(401,"invalid_credentials","Invalid social sign-in token")
    # The token's nonce matched the raw nonce sent with it; it must also be
    # one this server issued and not yet used, or a captured request could
    # be replayed until the ID token expires.
    if not consume_social_nonce(db,body.nonce):
        fail(401,"invalid_credentials","Invalid social sign-in token")
    return claims
def social_email(claims:dict) -> str|None:
    raw_email=claims.get("email")
    return raw_email.strip().lower() if isinstance(raw_email,str) and raw_email.strip() else None
# Guest accounts are ordinary password accounts the web client registers
# with a generated address and password that are never shown to the user
# (frontend AuthContext.continueAsGuest / isGuestUser).
GUEST_EMAIL_RE=re.compile(r"^guest-[A-Za-z0-9-]+@example\.com$")
def is_guest_account(user:User) -> bool:
    return bool(user.email and GUEST_EMAIL_RE.fullmatch(user.email))
def user_provider_identity(db:Session,user_id:str,provider:str):
    return db.scalar(select(UserIdentity).where(UserIdentity.user_id==user_id,UserIdentity.provider==provider))
def social_display_name(body:SocialLoginIn,claims:dict,email:str|None) -> str:
    name=body.display_name or claims.get("name")
    if isinstance(name,str) and name.strip():
        return name.strip()[:100]
    if email and "@" in email:
        return email.split("@",1)[0][:100]
    return f"{body.provider.title()} user"
def synthetic_social_email(provider:str,subject:str) -> str:
    digest=hashlib.sha256(f"{provider}:{subject}".encode()).hexdigest()[:24]
    return f"{provider}-{digest}@social.lingosquared.example"
def resolve_social_user(db:Session,body:SocialLoginIn,claims:dict):
    provider=body.provider
    subject=claims["sub"]
    identity=db.get(UserIdentity,(provider,subject))
    if identity:
        user=db.get(User,identity.user_id)
        if user:
            return user
        fail(401,"invalid_credentials","Invalid social sign-in token")

    email=social_email(claims)
    email_trusted=bool(email) and social_auth.email_is_trusted_for_linking(provider,claims,email)
    existing_email_user=db.scalar(select(User).where(User.email==email)) if email else None
    if existing_email_user and email_trusted:
        # Registration never proves ownership of the address, so an account
        # with a password may have been created by someone else in the
        # provider user's name. Signing in to it here would hand that
        # person the provider user's account (pre-account hijacking). Such
        # an account is linked only from inside it: log in with the
        # password, then connect the provider (POST /auth/social/link).
        if existing_email_user.password_hash is not None:
            fail(409,"account_exists",f"An account with this email already exists. Log in with your password, then connect {provider.title()} from your profile.")
        # Never attach a second account of the same provider to one user.
        if user_provider_identity(db,existing_email_user.id,provider):
            fail(409,"provider_already_linked",f"This account is already linked to a different {provider.title()} sign-in")
        db.add(UserIdentity(user_id=existing_email_user.id,provider=provider,provider_subject=subject))
        return existing_email_user

    # An address the provider does not vouch for is never stored as the
    # account email: it would let that sign-in claim the address.
    user_email=email if email and email_trusted and not existing_email_user else synthetic_social_email(provider,subject)
    user=User(
        email=user_email,
        password_hash=None,
        display_name=social_display_name(body,claims,email),
        is_admin=False,
    )
    db.add(user)
    db.flush()
    db.add(UserStats(user_id=user.id,total_xp=0,streak_days=0,last_activity_date=None,daily_goal=20))
    db.add(UserIdentity(user_id=user.id,provider=provider,provider_subject=subject))
    return user
def delete_user_account(db:Session,user:User):
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
def resolve_script(db, language_code):
    if not language_code:
        return None
    language = db.get(Language, language_code)
    return language.script if language else None
def stored_exercise_answer(e,attempt):
    feedback_meta = decode_feedback(e.feedback)
    language_code = e.prompt.get("answer_language_code")
    result = attempt.outcome or ("correct" if attempt.correct else "incorrect")
    snapshot = attempt.feedback_snapshot or {}
    correct_response = snapshot.get("correct_response", display_correct_response(e.correct_response))
    feedback = snapshot.get("feedback")
    if "feedback" not in snapshot:
        feedback = (
            "Check the hamza spelling: أ, إ, and آ are written differently from ا."
            if result == "almost"
            and isinstance(attempt.response, str)
            and isinstance(e.correct_response, str)
            and is_arabic_hamza_only_difference(
                attempt.response,
                e.correct_response,
                language_code=language_code,
                exercise_type=exercise_type_value(e.type),
                case_sensitive=bool(feedback_meta.get("case_sensitive")),
                punctuation_strict=bool(feedback_meta.get("punctuation_strict")),
            )
            else select_feedback(feedback_meta, attempt.response, result)
        )
    return {
        "correct": attempt.correct,
        "result": result,
        "correct_response": correct_response,
        "xp_awarded": attempt.xp_awarded,
        "feedback": feedback,
    }


def exercise_answer(db, user, e, response, client_operation_id=None, input_mode="typed"):
    # A stable operation id makes network retries return the original result.
    if client_operation_id:
        previous = db.scalar(select(ExerciseAttempt).where(
            ExerciseAttempt.user_id == user.id,
            ExerciseAttempt.client_operation_id == client_operation_id,
        ))
        if previous:
            return stored_exercise_answer(db.get(Exercise, previous.exercise_id) or e, previous)

    # This per-user lock also serializes first-correct grading decisions, so
    # two different simultaneous submits cannot both receive full first-try XP.
    stats_for(db, user.id, for_update=True)
    if client_operation_id:
        previous = db.scalar(select(ExerciseAttempt).where(
            ExerciseAttempt.user_id == user.id,
            ExerciseAttempt.client_operation_id == client_operation_id,
        ))
        if previous:
            return stored_exercise_answer(db.get(Exercise, previous.exercise_id) or e, previous)

    feedback_meta = decode_feedback(e.feedback)
    language_code = e.prompt.get("answer_language_code")
    script = resolve_script(db, language_code)
    result = grade(
        response,
        e.correct_response,
        e.type,
        script=script,
        language_code=language_code,
        input_mode=input_mode,
        orthography_strict=feedback_meta.get("orthography_strict"),
        case_sensitive=bool(feedback_meta.get("case_sensitive")),
        punctuation_strict=bool(feedback_meta.get("punctuation_strict")),
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
    replay = previously_correct is not None
    xp = e.xp if correct and not replay else 0
    if correct and replay:
        day_start, day_end = activity_day_bounds(user.timezone)
        correct_today = db.scalar(
            select(func.count(ExerciseAttempt.id)).where(
                ExerciseAttempt.user_id == user.id,
                ExerciseAttempt.correct.is_(True),
                ExerciseAttempt.created_at >= day_start,
                ExerciseAttempt.created_at < day_end,
            )
        ) or 0
        # Replay XP is deliberately bounded to the first 20 correct lesson
        # answers in the user's local day.
        xp = 1 if correct_today < 20 else 0

    attempt = ExerciseAttempt(
            user_id=user.id,
            exercise_id=e.id,
            response=response,
            correct=correct,
            outcome=result,
            xp_awarded=xp,
            client_operation_id=client_operation_id,
        )
    response_snapshot = stored_exercise_answer(e, attempt)
    attempt.feedback_snapshot = {
        "correct_response": response_snapshot["correct_response"],
        "feedback": response_snapshot["feedback"],
    }
    try:
        with db.begin_nested():
            db.add(attempt)
            db.flush()
    except IntegrityError:
        # The unique operation constraint is the final arbiter if two retry
        # requests pass the lookup together. The savepoint keeps the session
        # usable so we can return the already persisted answer.
        if client_operation_id:
            previous = db.scalar(select(ExerciseAttempt).where(
                ExerciseAttempt.user_id == user.id,
                ExerciseAttempt.client_operation_id == client_operation_id,
            ))
            if previous:
                return stored_exercise_answer(db.get(Exercise, previous.exercise_id) or e, previous)
        raise
    if result != "correct" and not replay:
        existing_review = db.scalar(
            select(ReviewItem.id).where(
                ReviewItem.user_id == user.id,
                ReviewItem.exercise_id == e.id,
            )
        )
        if existing_review is None:
            review = ReviewItem(
                user_id=user.id,
                exercise_id=e.id,
                interval_days=0,
                ease_factor=2.3,
                repetitions=0,
                due_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
            try:
                with db.begin_nested():
                    db.add(review)
                    db.flush()
            except IntegrityError:
                # A simultaneous miss may have inserted this user's review
                # row after the lookup. Preserve it without resetting state.
                pass
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
            # If an answer arrives before the explicit /start call, the
            # auto-created session begins with this persisted attempt.
            started_at=attempt.created_at or datetime.now(timezone.utc),
            completed_at=None,
            correct_count=0,
            answer_count=0,
            xp_earned=0,
        )
        db.add(lp)

    lp.answer_count += 1
    lp.correct_count += int(correct)
    lp.xp_earned += xp
    if replay:
        award_xp(db, user.id, xp)
    else:
        record_activity(db, user.id, xp, user.timezone)
    db.commit()
    return stored_exercise_answer(e, attempt)

PLACEMENT_RATE_LIMIT_MESSAGE = "Too many answers submitted too quickly. Please slow down."


def build_placement_set(db, course):
    """Assemble the laddered probe set for a course (no answers withheld
    here -- the caller serializes only {id, level, type, order, prompt}).

    Groups the course's reading/writing multiple_choice / matching_pairs
    exercises by the CEFR level of their owning unit, and for each level
    A1->A2->B1->B2 that can fill a full block of PLACEMENT_BLOCK_SIZE,
    deterministically takes the first block ordered by
    (unit.order, lesson.order, exercise.order, exercise.id). Levels that
    can't fill a block are dropped from the ladder. Returns
    ``(levels, items)`` -- ``levels`` empty means placement is unavailable.
    """
    rows = db.execute(
        select(
            Unit.content_key,
            Unit.order,
            Lesson.order,
            Exercise.order,
            Exercise.id,
            Exercise.type,
            Exercise.prompt,
        )
        .join(Lesson, Lesson.unit_id == Unit.id)
        .join(Exercise, Exercise.lesson_id == Lesson.id)
        .where(
            Unit.course_id == course.id,
            Unit.section == UnitSection.reading_writing,
            Unit.track == "core",
            Exercise.retired_at.is_(None),
            Exercise.type.in_(
                [ExerciseType.multiple_choice, ExerciseType.matching_pairs]
            ),
        )
        .order_by(Unit.order, Lesson.order, Exercise.order, Exercise.id)
    ).all()

    by_level: dict[str, list] = {}
    for content_key, _u_order, _l_order, ex_order, ex_id, ex_type, prompt in rows:
        level = parse_cefr_level(content_key)
        if level not in PLACEMENT_LEVELS:
            continue
        by_level.setdefault(level, []).append(
            {
                "id": ex_id,
                "level": level,
                "type": exercise_type_value(ex_type),
                "order": ex_order,
                "prompt": prompt,
            }
        )

    levels: list[str] = []
    items: list[dict] = []
    for level in PLACEMENT_LEVELS:
        block = by_level.get(level, [])
        if len(block) < PLACEMENT_BLOCK_SIZE:
            continue
        levels.append(level)
        items.extend(block[:PLACEMENT_BLOCK_SIZE])
    return levels, items


def placement_probe(db, exercise_id, course_id):
    """Return the Exercise iff it exists, belongs to ``course_id``, is in a
    reading/writing unit, and is a placement probe type -- else None. Used
    to validate /answer and /result submissions (a non-match is a 400
    exercise_not_in_placement)."""
    e = db.get(Exercise, exercise_id)
    if not e or e.retired_at is not None:
        return None
    if exercise_type_value(e.type) not in ("multiple_choice", "matching_pairs"):
        return None
    lesson = db.get(Lesson, e.lesson_id)
    if not lesson:
        return None
    unit = db.get(Unit, lesson.unit_id)
    if not unit or unit.course_id != course_id or unit.section != UnitSection.reading_writing:
        return None
    return e


def placement_grade(db, e, response):
    """Pure grade of one probe -- NO rows written. Choice types resolve
    straight to correct/incorrect, but we still pass the exercise's own
    strictness inputs for parity with exercise_answer()."""
    feedback_meta = decode_feedback(e.feedback)
    language_code = e.prompt.get("answer_language_code")
    return grade(
        response,
        e.correct_response,
        e.type,
        script=resolve_script(db, language_code),
        language_code=language_code,
        orthography_strict=feedback_meta.get("orthography_strict"),
        case_sensitive=bool(feedback_meta.get("case_sensitive")),
        punctuation_strict=bool(feedback_meta.get("punctuation_strict")),
    )


def first_placement_unit(db, course_id, level):
    """First reading/writing unit (lowest order) whose parsed CEFR ==
    ``level``. If ``level`` is None or no unit matches, returns the course's
    first reading/writing unit (the course start). None only if the course
    has no reading/writing units at all."""
    units = list(
        db.scalars(
            select(Unit)
            .where(
                Unit.course_id == course_id,
                Unit.section == UnitSection.reading_writing,
                Unit.track == "core",
            )
            .order_by(Unit.order)
        )
    )
    if not units:
        return None
    if level is not None:
        for unit in units:
            if parse_cefr_level(unit.content_key) == level:
                return unit
    return units[0]


def speaking_unlocked(db:Session,course_id:str,user_id:str|None,unit_order:int) -> bool:
    if not user_id: return False
    reading_units=list(db.scalars(select(Unit).where(Unit.course_id==course_id,Unit.section==UnitSection.reading_writing,Unit.track=="core",Unit.order < unit_order).order_by(Unit.order)))
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
    if unit.track=="core" and unit.section==UnitSection.speaking and not is_admin_user(user) and not speaking_unlocked(db,unit.course_id,user.id,unit.order):
        fail(409,"speaking_locked","Complete the earlier reading and writing units before starting speaking lessons")

@router.post("/auth/register",response_model=AuthOut,status_code=201)
def register(body:RegisterIn,request:Request,db:Session=Depends(get_db)):
    enforce_rate_limit(REGISTER_RATE_LIMIT,client_ip(request),"register_rate_limited","Too many registration attempts from this address. Please try again later.")
    email=body.email.lower()
    if db.scalar(select(User).where(User.email==email)): fail(409,"email_exists","An account with this email already exists")
    user=User(email=email,password_hash=hash_password(body.password),display_name=body.display_name or email.split("@")[0],is_admin=False,timezone=valid_timezone_or_none(body.timezone)); db.add(user); db.flush()
    db.add(UserStats(user_id=user.id,total_xp=0,streak_days=0,last_activity_date=None,daily_goal=20))
    return auth_response(db,user)
@router.post("/auth/login",response_model=AuthOut)
def login(body:LoginIn,request:Request,db:Session=Depends(get_db)):
    enforce_rate_limit(LOGIN_RATE_LIMIT,client_ip(request),"login_rate_limited","Too many login attempts. Please wait before trying again.")
    user=db.scalar(select(User).where(User.email==body.email.lower()))
    if not user or not user.password_hash or not verify_password(body.password,user.password_hash): fail(401,"invalid_credentials","Invalid email or password")
    if not user.is_active: fail(401,"inactive_user","This account is inactive")
    valid_tz=valid_timezone_or_none(body.timezone)
    if valid_tz and valid_tz!=user.timezone: user.timezone=valid_tz
    return auth_response(db,user)
@router.post("/auth/social",response_model=AuthOut)
def social_login(body:SocialLoginIn,request:Request,db:Session=Depends(get_db)):
    enforce_rate_limit(LOGIN_RATE_LIMIT,client_ip(request),"login_rate_limited","Too many login attempts. Please wait before trying again.")
    claims=verified_social_claims(db,body)
    try:
        user=resolve_social_user(db,body,claims)
        db.flush()
    except IntegrityError:
        # A concurrent first sign-in with the same identity created the
        # account first (our insert waited on it, then hit the unique key).
        db.rollback()
        identity=db.get(UserIdentity,(body.provider,claims["sub"]))
        user=db.get(User,identity.user_id) if identity else None
        if user is None:
            fail(409,"social_sign_in_conflict","This sign-in is being set up by another request. Please try again.")
    if not user.is_active: fail(401,"inactive_user","This account is inactive")
    return auth_response(db,user)
def require_recent_proof(user:User,current_password:str|None):
    """A bare access token is not enough to change how an account signs in.

    Guests have no usable password and nothing to protect beyond the
    session itself, so they pass. An account with a password must send it.
    An account that signs in only through a provider has no password to
    check, so it cannot add or remove sign-ins this way.
    """
    if is_guest_account(user):
        return
    if user.password_hash is None:
        fail(403,"reauthentication_required","Sign in again with your current sign-in method to change linked sign-ins.")
    if not current_password or not verify_password(current_password,user.password_hash):
        fail(403,"reauthentication_required","Enter your current password to change linked sign-ins.")
@router.post("/auth/social/nonce",response_model=SocialNonceOut)
def social_nonce(request:Request,db:Session=Depends(get_db)):
    """A single-use nonce for the next Google/Apple sign-in or link.

    The client passes SHA-256(nonce) to the provider and the raw nonce back
    with the ID token; /auth/social and /auth/social/link accept it once,
    within social_nonce_ttl_seconds.
    """
    enforce_rate_limit(SOCIAL_NONCE_RATE_LIMIT,client_ip(request),"login_rate_limited","Too many login attempts. Please wait before trying again.")
    if not get_settings().social_sign_in_enabled:
        fail(503,"social_login_unavailable","Social login is not configured")
    raw,ttl=issue_social_nonce(db)
    return {"nonce":raw,"expires_in":ttl}
@router.post("/auth/social/link",response_model=MeOut)
def link_social(body:SocialLinkIn,request:Request,user=Depends(current_user),db:Session=Depends(get_db)):
    """Attach a Google/Apple sign-in to the signed-in account.

    For a guest account this is the upgrade path: the account keeps its id,
    and with it every bit of progress, while its generated email and
    never-shown password are replaced by the provider identity (and the
    provider's email when the provider vouches for it and no other account
    uses it). Any other account must confirm its current password (see
    require_recent_proof). Accounts are never merged: an identity or email
    that already belongs to another account is a 409.
    """
    enforce_rate_limit(LOGIN_RATE_LIMIT,client_ip(request),"login_rate_limited","Too many login attempts. Please wait before trying again.")
    claims=verified_social_claims(db,body)
    provider=body.provider
    subject=claims["sub"]
    identity=db.get(UserIdentity,(provider,subject))
    if identity and identity.user_id!=user.id:
        fail(409,"identity_in_use",f"This {provider.title()} sign-in already belongs to another account")
    if not identity:
        require_recent_proof(user,body.current_password)
        if user_provider_identity(db,user.id,provider):
            fail(409,"provider_already_linked",f"This account is already linked to a different {provider.title()} sign-in")
        if is_guest_account(user):
            email=social_email(claims)
            email_trusted=bool(email) and social_auth.email_is_trusted_for_linking(provider,claims,email)
            if email and email_trusted:
                owner=db.scalar(select(User).where(User.email==email))
                if owner and owner.id!=user.id:
                    fail(409,"email_exists","An account with this email already exists. Sign in to that account instead.")
                user.email=email
            else:
                user.email=synthetic_social_email(provider,subject)
            user.password_hash=None
            if body.display_name and body.display_name.strip():
                user.display_name=body.display_name.strip()[:100]
        db.add(UserIdentity(user_id=user.id,provider=provider,provider_subject=subject))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            fail(409,"identity_in_use",f"This {provider.title()} sign-in already belongs to another account")
        db.refresh(user)
    return me_payload(db,user)
@router.post("/auth/social/unlink",response_model=MeOut)
def unlink_social(body:SocialUnlinkIn,request:Request,user=Depends(current_user),db:Session=Depends(get_db)):
    """Remove a linked Google/Apple sign-in from the signed-in account.

    Never removes the last way to sign in: an account without a password
    keeps at least one identity. An account with a password must confirm
    it; one without (two providers linked) needs no password to drop one.
    """
    enforce_rate_limit(LOGIN_RATE_LIMIT,client_ip(request),"login_rate_limited","Too many login attempts. Please wait before trying again.")
    identity=user_provider_identity(db,user.id,body.provider)
    if identity is None:
        fail(404,"identity_not_found",f"No {body.provider.title()} sign-in is linked to this account")
    if user.password_hash is not None and not is_guest_account(user):
        require_recent_proof(user,body.current_password)
    other_identities=db.scalar(
        select(func.count()).select_from(UserIdentity).where(UserIdentity.user_id==user.id,UserIdentity.provider!=body.provider)
    ) or 0
    has_password=user.password_hash is not None and not is_guest_account(user)
    if not has_password and other_identities==0:
        fail(409,"last_login_method","This is the only way to sign in to this account, so it cannot be removed.")
    db.delete(identity)
    db.commit()
    return me_payload(db,user)
@router.post("/auth/refresh",response_model=RefreshOut)
def refresh(body:RefreshIn,request:Request,db:Session=Depends(get_db)):
    # Rate-limit before lookup, and count invalid-token probes too (same
    # principle as login counting failed password attempts).
    enforce_rate_limit(REFRESH_RATE_LIMIT,client_ip(request),"refresh_rate_limited","Too many token refresh attempts from this address. Please wait before trying again.")
    now_value=utc_now()
    refresh_token=find_refresh_token(db,body.refresh_token)
    if not refresh_token:
        fail(401,"invalid_refresh_token","Invalid or expired refresh token")
    user_id=refresh_token.user_id
    prune_stale_refresh_tokens(db,user_id,now_value)
    db.commit()
    # Re-read under the user's session lock, then the token's row lock, for
    # the rotation decision itself. The user lock makes a rotation and a
    # concurrent revoke-all (reuse detection elsewhere in the family) run
    # one after the other, so the rotation sees the revocation and the
    # revoke-all sees the successor.
    lock_user_sessions(db,user_id)
    refresh_token=find_refresh_token(db,body.refresh_token,for_update=True)
    now_value=utc_now()
    if not refresh_token:
        fail(401,"invalid_refresh_token","Invalid or expired refresh token")
    if refresh_token.revoked_at is not None:
        user=db.get(User,refresh_token.user_id)
        successor_raw=replayed_successor(db,refresh_token,body.refresh_token,body.next_refresh_token,now_value) if user and user.is_active else None
        if successor_raw is not None:
            db.commit()
            return refresh_response(user.id,successor_raw)
        revoke_all_refresh_tokens(db,refresh_token.user_id,now_value)
        db.commit()
        fail(401,"refresh_token_reused","Refresh token was already used or revoked")
    if as_aware(refresh_token.expires_at)<=now_value:
        fail(401,"invalid_refresh_token","Invalid or expired refresh token")
    user=db.get(User,refresh_token.user_id)
    if not user or not user.is_active:
        fail(401,"invalid_refresh_token","Invalid or expired refresh token")
    successor_raw=rotate_refresh_token(db,refresh_token,body.refresh_token,body.next_refresh_token,now_value)
    db.commit()
    return refresh_response(user.id,successor_raw)
@router.post("/auth/logout",status_code=204)
def logout(body:LogoutIn,request:Request,db:Session=Depends(get_db)):
    # Shares the refresh endpoint's limiter and error code.
    enforce_rate_limit(REFRESH_RATE_LIMIT,client_ip(request),"refresh_rate_limited","Too many token refresh attempts from this address. Please wait before trying again.")
    refresh_token=find_refresh_token(db,body.refresh_token)
    if refresh_token and refresh_token.revoked_at is None:
        refresh_token.revoked_at=utc_now()
        db.commit()
    return Response(status_code=204)
@router.get("/auth/me",response_model=MeOut)
def me(user=Depends(current_user),db:Session=Depends(get_db)):
    return me_payload(db,user)
def me_payload(db:Session,user:User):
    identities=list(db.scalars(select(UserIdentity).where(UserIdentity.user_id==user.id).order_by(UserIdentity.created_at)))
    return {
        "id":user.id,
        "email":user.email,
        "display_name":user.display_name,
        "is_admin":is_admin_user(user),
        "created_at":user.created_at,
        "identities":[{"provider":identity.provider,"created_at":identity.created_at} for identity in identities],
    }
@router.get("/me/export")
def export_me(response:Response,user=Depends(current_user),db:Session=Depends(get_db)):
    # GDPR-style data-portability export: everything reasonably tied to this
    # account in one JSON document, so a user can download their data before
    # the irreversible DELETE /me below. Shape documented in docs/CONTRACT.md
    # (update it FIRST if this changes). Deliberately excluded: refresh_tokens
    # rows (session material, not personal data -- also revoked wholesale by
    # DELETE /me regardless) and push-subscription p256dh/auth values
    # (channel crypto keys, not personal data).
    stats=db.get(UserStats,user.id)
    lexeme_rows=db.execute(select(UserLexemeSRS,Lexeme).join(Lexeme,Lexeme.id==UserLexemeSRS.lexeme_id).where(UserLexemeSRS.user_id==user.id)).all()
    practice_rows=db.execute(select(PracticeAttempt,PracticeItem).join(PracticeItem,PracticeItem.id==PracticeAttempt.practice_item_id).where(PracticeAttempt.user_id==user.id).order_by(PracticeAttempt.created_at)).all()
    earned=db.execute(select(UserAchievement,Achievement).join(Achievement,Achievement.id==UserAchievement.achievement_id).where(UserAchievement.user_id==user.id)).all()
    response.headers["Content-Disposition"]=f'attachment; filename="auvel-export-{datetime.now(timezone.utc).date().isoformat()}.json"'
    return {
        "format_version":1,
        "exported_at":datetime.now(timezone.utc),
        "profile":{"id":user.id,"email":user.email,"display_name":user.display_name,"created_at":user.created_at,"timezone":user.timezone},
        "stats":{"total_xp":stats.total_xp,"streak_days":stats.streak_days,"last_activity_date":stats.last_activity_date,"daily_goal":stats.daily_goal,"streak_freezes_available":stats.streak_freezes_available,"last_freeze_used_date":stats.last_freeze_used_date} if stats else None,
        "skill_progress":[{"course_id":x.course_id,"completed_lessons":x.completed_lessons,"mastery":x.mastery} for x in db.scalars(select(SkillProgress).where(SkillProgress.user_id==user.id))],
        "lesson_progress":[{"lesson_id":x.lesson_id,"started_at":x.started_at,"completed_at":x.completed_at,"correct_count":x.correct_count,"answer_count":x.answer_count,"xp_earned":x.xp_earned} for x in db.scalars(select(LessonProgress).where(LessonProgress.user_id==user.id))],
        "exercise_attempts":[{"exercise_id":x.exercise_id,"response":x.response,"correct":x.correct,"outcome":x.outcome,"xp_awarded":x.xp_awarded,"created_at":x.created_at} for x in db.scalars(select(ExerciseAttempt).where(ExerciseAttempt.user_id==user.id).order_by(ExerciseAttempt.created_at))],
        "practice_attempts":[{"practice_item_id":a.practice_item_id,"course_id":i.course_id,"prompt":i.prompt,"response":a.response,"correct":a.correct,"xp_awarded":a.xp_awarded,"created_at":a.created_at} for a,i in practice_rows],
        "checkpoint_attempts":[{"unit_id":x.unit_id,"total_items":x.total_items,"passed":x.passed,"score":x.score,"weak_outcomes":x.weak_outcomes,"created_at":x.created_at,"scored_at":x.scored_at} for x in db.scalars(select(CheckpointAttempt).where(CheckpointAttempt.user_id==user.id).order_by(CheckpointAttempt.created_at))],
        "lexeme_srs":[{"lexeme_id":s.lexeme_id,"token":lx.token,"english_gloss":lx.english_gloss,"language_code":lx.language_code,"course_id":s.course_id,"mastery":s.mastery,"ease_factor":s.ease_factor,"interval_days":s.interval_days,"repetitions":s.repetitions,"due_at":s.due_at,"last_reviewed_at":s.last_reviewed_at,"introduced_at":s.introduced_at,"suspended":s.suspended} for s,lx in lexeme_rows],
        "review_items":[{"exercise_id":x.exercise_id,"ease_factor":x.ease_factor,"interval_days":x.interval_days,"repetitions":x.repetitions,"mastery":x.mastery,"due_at":x.due_at} for x in db.scalars(select(ReviewItem).where(ReviewItem.user_id==user.id))],
        "achievements":[{"code":ach.code,"title":ach.title,"earned_at":ua.earned_at} for ua,ach in earned],
        "quest_completions":[{"quest_code":x.quest_code,"date":x.date,"awarded_at":x.awarded_at} for x in db.scalars(select(QuestCompletion).where(QuestCompletion.user_id==user.id))],
        "vocabulary_progress":[{"content_item_id":x.content_item_id,"mastery":x.mastery,"last_reviewed_at":x.last_reviewed_at} for x in db.scalars(select(VocabularyProgress).where(VocabularyProgress.user_id==user.id))],
        "grammar_progress":[{"content_item_id":x.content_item_id,"mastery":x.mastery,"last_reviewed_at":x.last_reviewed_at} for x in db.scalars(select(GrammarProgress).where(GrammarProgress.user_id==user.id))],
        "push_subscriptions":[{"endpoint":x.endpoint,"created_at":x.created_at} for x in db.scalars(select(PushSubscription).where(PushSubscription.user_id==user.id))],
        "content_issue_reports":[{"id":x.id,"exercise_id":x.exercise_id,"practice_item_id":x.practice_item_id,"page_path":x.page_path,"category":x.category,"description":x.description,"status":x.status,"created_at":x.created_at} for x in db.scalars(select(ContentIssueReport).where(ContentIssueReport.reporter_user_id==user.id))],
    }
@router.delete("/me",status_code=204)
def delete_me(user=Depends(current_user),db:Session=Depends(get_db)):
    delete_user_account(db,user)
    db.commit()
    return Response(status_code=204)
@router.get("/languages",response_model=list[LanguageOut])
def languages(db:Session=Depends(get_db)): return list(db.scalars(select(Language).order_by(Language.code)))
@router.get("/language-pairs",response_model=list[LanguagePairOut])
def pairs(db:Session=Depends(get_db)):
    rows=db.execute(select(Course.source_language,Course.target_language,func.count(Course.id)).group_by(Course.source_language,Course.target_language)).all()
    return [{"source_language":a,"target_language":b,"course_count":n} for a,b,n in rows]
def course_shape(db,c): return {"id":c.id,"source_language":c.source_language,"target_language":c.target_language,"title":c.title,"level":c.level,"unit_count":db.scalar(select(func.count(Unit.id)).where(Unit.course_id==c.id,Unit.track=="core")),"recommended":c.recommended}
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
                "locked":unit.track=="core" and unit.section==UnitSection.speaking and not (
                    (user and is_admin_user(user))
                    or speaking_unlocked(db,course_id,user.id if user else None,unit.order)
                ),
                "checkpoint_passed":checkpoint_passed,
                "content_key":unit.content_key,
                "track":unit.track,
            }
        )
    return result
@router.get("/units/{unit_id}/lessons",response_model=list[LessonOut])
def lessons(unit_id:str,db:Session=Depends(get_db)):
    if not db.get(Unit,unit_id): fail(404,"unit_not_found","Unit not found")
    return [{"id":l.id,"title":l.title,"order":l.order,"exercise_count":db.scalar(select(func.count(Exercise.id)).where(Exercise.lesson_id==l.id,Exercise.retired_at.is_(None)))} for l in db.scalars(select(Lesson).where(Lesson.unit_id==unit_id).order_by(Lesson.order))]
@router.get("/lessons/{lesson_id}",response_model=LessonDetail)
def lesson(lesson_id:str,db:Session=Depends(get_db)):
    l=db.get(Lesson,lesson_id)
    if not l: fail(404,"lesson_not_found","Lesson not found")
    teaching=[{"kind":item.kind,"title":item.title or None,"text_blocks":item.content.get("text_blocks",[]),"note":item.content.get("note"),"examples":item.content.get("examples"),**({"glosses":item.content["glosses"]} if "glosses" in item.content else {})} for item in l.teaching_items]
    return {"id":l.id,"unit_id":l.unit_id,"title":l.title,"teaching":teaching,"exercises":[{"id":e.id,"type":e.type,"order":e.order,"prompt":e.prompt} for e in l.exercises if e.retired_at is None]}
@router.post("/lessons/{lesson_id}/start",response_model=StartOut)
def start(lesson_id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    lesson_row=db.get(Lesson,lesson_id)
    if not lesson_row: fail(404,"lesson_not_found","Lesson not found")
    unit=db.get(Unit,lesson_row.unit_id)
    require_speaking_unlocked(db,unit,user)
    p=db.scalar(select(LessonProgress).where(LessonProgress.user_id==user.id,LessonProgress.lesson_id==lesson_id)); now=datetime.now(timezone.utc)
    if not p:
        candidate=LessonProgress(
            user_id=user.id,
            lesson_id=lesson_id,
            started_at=now,
            completed_at=None,
            correct_count=0,
            answer_count=0,
            xp_earned=0,
        )
        try:
            with db.begin_nested():
                db.add(candidate)
                db.flush()
            p=candidate
        except IntegrityError:
            # Another request created the row after our initial lookup.
            # Keep the outer transaction usable and return that row.
            p=db.scalar(select(LessonProgress).where(LessonProgress.user_id==user.id,LessonProgress.lesson_id==lesson_id))
            if p is None:
                raise
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
    return exercise_answer(db,user,e,body.response,body.client_operation_id,body.input_mode)
# --- Placement test (course-level), 2026-08-05 -------------------------
# Recognition-only, side-effect-free (MVP): assembled from the course's own
# existing multiple_choice/matching_pairs exercises, graded by grade(), and
# writes NOTHING (no ExerciseAttempt/LessonProgress/XP/streak/SRS). It only
# recommends a starting unit; persistence is client-side (localStorage).
# Full design: docs/PLACEMENT_TEST_SPEC.md; contract: docs/CONTRACT.md.
@router.get("/courses/{course_id}/placement",response_model=PlacementSetOut)
def placement_set(course_id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    enforce_rate_limit(ANSWER_RATE_LIMIT,user.id,"answer_rate_limited",PLACEMENT_RATE_LIMIT_MESSAGE)
    course=db.get(Course,course_id)
    if not course: fail(404,"course_not_found","Course not found")
    levels,items=build_placement_set(db,course)
    # Contract: 409 when the course can't fill even one A1 block (< 4 usable
    # A1 probes). Higher tiers may be dropped from the ladder silently; A1
    # is the floor (spec 4).
    if "A1" not in levels:
        fail(409,"placement_unavailable","This course does not have enough recognition exercises to build a placement test")
    return {
        "course_id":course_id,
        "levels":levels,
        "block_size":PLACEMENT_BLOCK_SIZE,
        "pass_threshold":PLACEMENT_PASS_THRESHOLD,
        "items":items,
    }
@router.post("/courses/{course_id}/placement/answer",response_model=PlacementAnswerOut)
def placement_answer(course_id:str,body:PlacementAnswerIn,user=Depends(current_user),db:Session=Depends(get_db)):
    enforce_rate_limit(ANSWER_RATE_LIMIT,user.id,"answer_rate_limited",PLACEMENT_RATE_LIMIT_MESSAGE)
    course=db.get(Course,course_id)
    if not course: fail(404,"course_not_found","Course not found")
    e=placement_probe(db,body.exercise_id,course_id)
    if e is None:
        fail(400,"exercise_not_in_placement","Exercise does not belong to this course's placement set")
    result=placement_grade(db,e,body.response)
    # No persistence: pure grade() call, distinct from POST /exercises/{id}/answer.
    return {
        "correct":result!="incorrect",
        "result":result,
        "correct_response":display_correct_response(e.correct_response),
    }
@router.post("/courses/{course_id}/placement/result",response_model=PlacementResultOut)
def placement_result(course_id:str,body:PlacementResultIn,user=Depends(current_user),db:Session=Depends(get_db)):
    enforce_rate_limit(ANSWER_RATE_LIMIT,user.id,"answer_rate_limited",PLACEMENT_RATE_LIMIT_MESSAGE)
    course=db.get(Course,course_id)
    if not course: fail(404,"course_not_found","Course not found")
    # Re-grade every submitted answer server-side (thresholds live only
    # here, un-gameable). Answers that aren't valid probes for this course
    # are silently ignored. No rows written.
    graded=[]
    for ans in body.answers:
        e=placement_probe(db,ans.exercise_id,course_id)
        if e is None: continue
        lesson=db.get(Lesson,e.lesson_id)
        unit=db.get(Unit,lesson.unit_id)
        level=parse_cefr_level(unit.content_key)
        if level is None: continue
        result=placement_grade(db,e,ans.response)
        graded.append((level,result!="incorrect"))
    recommended_level,per_level=recommend_from_answers(graded)
    unit=first_placement_unit(db,course_id,recommended_level)
    # Empty/short answers -> recommend the course start; report that unit's
    # own level as the recommendation rather than null.
    if recommended_level is None and unit is not None:
        recommended_level=parse_cefr_level(unit.content_key)
    return {
        "recommended_level":recommended_level,
        "recommended_unit_id":unit.id if unit else None,
        "recommended_unit_content_key":unit.content_key if unit else None,
        "recommended_unit_title":unit.title if unit else None,
        "per_level":per_level,
    }
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
@router.post("/feedback/attachments",response_model=FeedbackAttachmentUploadOut,status_code=201)
def upload_feedback_attachment(request:Request,file:UploadFile=File(...),db:Session=Depends(get_db)):
    enforce_rate_limit(FEEDBACK_ATTACHMENT_RATE_LIMIT,client_ip(request),"report_rate_limited","Too many reports submitted too quickly. Please slow down.")
    attachment=feedback_attachment_service.store_feedback_attachment(db,file)
    return {
        "attachment_key":attachment.key,
        "expires_in_seconds":feedback_attachment_service.FEEDBACK_ATTACHMENT_EXPIRES_SECONDS,
    }
@router.post("/feedback",response_model=ContentIssueCreatedOut,status_code=201)
def report_general_feedback(body:GeneralFeedbackIn,request:Request,user=Depends(lenient_current_user),db:Session=Depends(get_db)):
    rate_key=user.id if user else client_ip(request)
    enforce_rate_limit(REPORT_RATE_LIMIT,rate_key,"report_rate_limited","Too many reports submitted too quickly. Please slow down.")
    issue=ContentIssueReport(reporter_user_id=user.id if user else None,exercise_id=None,practice_item_id=None,page_path=body.page_path,category=body.category,description=body.description,client_context=body.client_context)
    db.add(issue); db.flush()
    feedback_attachment_service.claim_feedback_attachments(db,issue,body.attachment_keys)
    db.commit(); db.refresh(issue)
    return issue
def seed_params_for_lesson(db: Session, user_id: str, lesson_id: str, since: datetime | None, now: datetime) -> dict[str, Any]:
    """Choose initial SRS values from each active exercise's first session answer."""
    exercises = list(db.scalars(select(Exercise).where(
        Exercise.lesson_id == lesson_id,
        Exercise.retired_at.is_(None),
    )))
    scores = []
    found_attempt = False
    if since is not None:
        for exercise in exercises:
            attempt = db.scalar(
                select(ExerciseAttempt)
                .where(
                    ExerciseAttempt.user_id == user_id,
                    ExerciseAttempt.exercise_id == exercise.id,
                    ExerciseAttempt.created_at >= since,
                )
                .order_by(ExerciseAttempt.created_at, ExerciseAttempt.id)
                .limit(1)
            )
            if attempt is None:
                scores.append(0.0)
            else:
                found_attempt = True
                outcome = attempt.outcome or ("correct" if attempt.correct else "incorrect")
                scores.append(1.0 if outcome == "correct" else 0.5 if outcome == "almost" else 0.0)
    score = sum(scores) / len(exercises) if exercises and scores and found_attempt else None
    if score is None or 0.6 <= score < 0.9:
        return {"ease_factor": 2.5, "interval_days": 0, "repetitions": 0, "mastery": 0.0, "due_at": now + timedelta(days=1), "last_reviewed_at": None}
    if score >= 0.9:
        return {"ease_factor": 2.5, "interval_days": 3, "repetitions": 1, "mastery": 0.5, "due_at": now + timedelta(days=3), "last_reviewed_at": now}
    return {"ease_factor": 2.3, "interval_days": 0, "repetitions": 0, "mastery": 0.0, "due_at": now + timedelta(hours=4), "last_reviewed_at": None}


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

    if first_completion:
        exercise_count = db.scalar(
            select(func.count(Exercise.id)).where(
                Exercise.lesson_id == lesson_id,
                Exercise.retired_at.is_(None),
            )
        ) or 0
        answered_in_session = db.scalar(
            select(func.count(ExerciseAttempt.id))
            .join(Exercise, Exercise.id == ExerciseAttempt.exercise_id)
            .where(
                ExerciseAttempt.user_id == user.id,
                Exercise.lesson_id == lesson_id,
                ExerciseAttempt.created_at >= session_started_at,
                ExerciseAttempt.created_at < now,
            )
        ) or 0
        if exercise_count > 0 and answered_in_session == 0:
            fail(409, "lesson_not_attempted", "Answer at least one lesson exercise before completing it")

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
        seed_params = seed_params_for_lesson(db, user.id, lesson_id, session_started_at, now)
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
                        **seed_params,
                        introduced_at=now,
                        suspended=False,
                        last_session_id=None,
                    )
                )

    total = db.scalar(
        select(func.count(Lesson.id))
        .join(Unit)
        .where(Unit.course_id == unit.course_id, Unit.track == "core")
    ) or 1
    skill.mastery = skill.completed_lessons / total

    if first_completion:
        record_activity(db, user.id, 0, user.timezone)

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
    limit: int = Query(50, ge=1, le=200),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    q = (
        select(ReviewItem)
        .join(Exercise, Exercise.id == ReviewItem.exercise_id)
        .where(
            ReviewItem.user_id == user.id,
            ReviewItem.due_at <= datetime.now(timezone.utc),
            Exercise.retired_at.is_(None),
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
    language_code=e.prompt.get("answer_language_code")
    script=resolve_script(db,language_code)
    result=grade(body.response,e.correct_response,e.type,script=script,language_code=language_code,orthography_strict=feedback_meta.get("orthography_strict"),case_sensitive=bool(feedback_meta.get("case_sensitive")),punctuation_strict=bool(feedback_meta.get("punctuation_strict")),input_mode=body.input_mode)
    correct=result!="incorrect"
    xp=e.xp if correct else 0
    schedule(r,result); record_activity(db,user.id,xp,user.timezone); db.commit()
    feedback = select_feedback(feedback_meta,body.response,result)
    if result == "almost" and isinstance(body.response,str) and isinstance(e.correct_response,str) and is_arabic_hamza_only_difference(body.response,e.correct_response,language_code=language_code,exercise_type=exercise_type_value(e.type),case_sensitive=bool(feedback_meta.get("case_sensitive")),punctuation_strict=bool(feedback_meta.get("punctuation_strict"))):
        feedback = "Check the hamza spelling: أ, إ, and آ are written differently from ا."
    return {"correct":correct,"result":result,"correct_response":display_correct_response(e.correct_response),"xp_awarded":xp,"feedback":feedback,"next_due_at":r.due_at}
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


def tracked_lexeme_conditions(
    user_id,
    course_id: str,
    part_of_speech: str | None = None,
    search: str | None = None,
):
    """Shared WHERE clause for the user's tracked vocabulary in a course
    (the /me/lexemes browser and the /courses/{id}/lexemes/export download
    must agree on the population: UserLexemeSRS-tracked lexemes only, never
    the full course-wide pool)."""
    conditions = [
        UserLexemeSRS.user_id == user_id,
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
    return conditions


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

    conditions = tracked_lexeme_conditions(user.id, course_id, part_of_speech, search)

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


@router.get("/courses/{course_id}/lexemes/export")
def lexemes_export(
    course_id: str,
    format: Literal["csv", "anki"] = "csv",
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    """Download the user's tracked vocabulary for a course as a file for
    external tools (spreadsheet CSV, or Anki's 2-column tab-separated
    text-import format). See docs/CONTRACT.md "Vocabulary export".

    A plain in-memory Response (not StreamingResponse) is deliberate: the
    population is one user's tracked lexemes in one course — bounded by how
    much vocabulary a human can actually study (hundreds to low thousands
    of short rows), nowhere near a size that needs chunked streaming.
    """
    if not db.get(Course, course_id):
        fail(404, "course_not_found", "Course not found")

    rows = db.execute(
        select(Lexeme, UserLexemeSRS)
        .join(UserLexemeSRS, UserLexemeSRS.lexeme_id == Lexeme.id)
        .where(*tracked_lexeme_conditions(user.id, course_id))
        .order_by(Lexeme.token.asc(), Lexeme.english_gloss.asc())
    ).all()

    buffer = io.StringIO()
    if format == "anki":
        # Standard Anki text import: front TAB back, one note per line, no
        # header row. The two #-directives are honored by Anki >=2.1.55 and
        # ignored as comments by older versions, so the file imports
        # cleanly either way. csv.writer (not "\t".join) so a token/gloss
        # containing a tab or newline can't silently corrupt the column
        # structure.
        buffer.write("#separator:tab\n#html:false\n")
        writer = csv.writer(buffer, delimiter="\t", lineterminator="\n")
        for lexeme, _srs in rows:
            writer.writerow([lexeme.token, lexeme.english_gloss])
        media_type = "text/tab-separated-values"
        # Anki's import picker expects .txt for text files, not .tsv.
        filename = f"vocabulary-{course_id}.txt"
    else:
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["token", "gloss", "part_of_speech", "mastery", "due_at"])
        for lexeme, srs in rows:
            writer.writerow(
                [
                    lexeme.token,
                    lexeme.english_gloss,
                    lexeme.part_of_speech,
                    srs.mastery,
                    srs.due_at.isoformat() if srs.due_at else "",
                ]
            )
        media_type = "text/csv"
        filename = f"vocabulary-{course_id}.csv"

    return Response(
        content=buffer.getvalue(),
        media_type=f"{media_type}; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
    due_users = db.execute(
        select(UserLexemeSRS.user_id, User.timezone)
        .where(
            UserLexemeSRS.due_at <= now,
            UserLexemeSRS.suspended.is_(False),
        )
        .join(User, User.id == UserLexemeSRS.user_id)
        .distinct()
    ).all()
    notified_users = 0
    notifications_sent = 0
    for uid_, user_tz in due_users:
        if not claim_notification(db, uid_, "daily_reminder", local_date_for(user_tz, now)):
            continue
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
        select(UserStats.user_id, UserStats.streak_days, UserStats.last_activity_date, User.timezone, UserStats.streak_freezes_available)
        .join(User, User.id == UserStats.user_id)
        .where(UserStats.streak_days > 0)
    ).all()
    notified_users = 0
    notifications_sent = 0
    for uid_, streak_days, last_activity_date, user_tz, freezes_available in rows:
        day_start, _ = activity_day_bounds(user_tz)
        effective_days = effective_streak_days(
            streak_days,
            last_activity_date,
            user_tz,
            today=day_start.date(),
            freezes_available=freezes_available,
        )
        if effective_days == 0 or last_activity_date == day_start.date():
            # Already active today in their own timezone — streak is safe.
            continue
        if not claim_notification(db, uid_, "streak_at_risk", day_start.date()):
            continue
        sent = push_service.send_push_to_user(
            db,
            uid_,
            title="Your streak is at risk",
            body=f"Your {effective_days}-day streak ends tonight — come back before midnight!",
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
        weak_lexeme_ids = [
            str(lexeme_id)
            for lexeme_id in db.scalars(
                select(PracticeItem.target_lexeme_id)
                .join(
                    PracticeAttempt,
                    PracticeAttempt.practice_item_id == PracticeItem.id,
                )
                .where(
                    PracticeAttempt.user_id == user.id,
                    PracticeItem.session_id == checkpoint.id,
                    PracticeItem.source == "checkpoint",
                    PracticeAttempt.correct.is_(False),
                    PracticeItem.target_lexeme_id.is_not(None),
                )
                .distinct()
                .order_by(PracticeItem.target_lexeme_id)
            )
        ]
        return {
            "status": "complete",
            "answered_items": checkpoint.total_items,
            "total_items": checkpoint.total_items,
            "passed": checkpoint.passed,
            "score": checkpoint.score,
            "weak_outcomes": checkpoint.weak_outcomes,
            "weak_lexeme_ids": weak_lexeme_ids,
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
            "weak_lexeme_ids": [],
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
    weak_lexeme_ids = [
        str(lexeme_id)
        for lexeme_id in db.scalars(
            select(PracticeItem.target_lexeme_id)
            .join(
                PracticeAttempt,
                PracticeAttempt.practice_item_id == PracticeItem.id,
            )
            .where(
                PracticeAttempt.user_id == user.id,
                PracticeItem.session_id == checkpoint.id,
                PracticeItem.source == "checkpoint",
                PracticeAttempt.correct.is_(False),
                PracticeItem.target_lexeme_id.is_not(None),
            )
            .distinct()
            .order_by(PracticeItem.target_lexeme_id)
        )
    ]

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
    if hasattr(checkpoint, "weak_lexeme_ids"):
        checkpoint.weak_lexeme_ids = weak_lexeme_ids
    checkpoint.scored_at = scored_at
    db.commit()

    return {
        "status": "complete",
        "answered_items": checkpoint.total_items,
        "total_items": checkpoint.total_items,
        "passed": passed,
        "score": score,
        "weak_outcomes": weak_outcomes,
        "weak_lexeme_ids": weak_lexeme_ids,
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
    today=datetime.now(resolve_user_tz(user.timezone)).date()
    s=db.get(UserStats,user.id)
    if not s:
        return {
            "streak_days":0,
            "last_activity_date":None,
            "streak_freezes_available":0,
            "freeze_used_today":False,
            "active_today":False,
        }
    return {
        "streak_days":effective_streak_days(s.streak_days,s.last_activity_date,user.timezone,today=today,freezes_available=s.streak_freezes_available),
        "last_activity_date":s.last_activity_date,
        "streak_freezes_available":s.streak_freezes_available,
        "freeze_used_today":s.last_freeze_used_date==today,
        # Computed server-side (not left to the client) because "today" is the
        # user's own timezone day boundary (User.timezone), the same boundary
        # streak accounting itself uses — a device-clock derivation could
        # disagree with it. Consumed by the HomePage streak-at-risk banner.
        "active_today":s.last_activity_date==today,
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
@router.get("/me/daily-goal",response_model=DailyGoalOut)
def get_daily_goal(user=Depends(current_user),db:Session=Depends(get_db)):
    return {"daily_goal_xp":stats_for(db,user.id).daily_goal}
@router.put("/me/daily-goal",response_model=DailyGoalOut)
def update_daily_goal(body:DailyGoalIn,user=Depends(current_user),db:Session=Depends(get_db)):
    stats=stats_for(db,user.id)
    stats.daily_goal=body.daily_goal_xp
    db.commit()
    return {"daily_goal_xp":stats.daily_goal}
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
    if body and body.mode == "speaking":
        generator = generate_speaking_batch
    elif body and body.mode == "conversation":
        generator = generate_conversation_batch
    else:
        generator = generate_batch
    locked,items=generator(
        db,
        user.id,
        course,
        body.size if body else 10,
        is_admin=is_admin_user(user),
        types=body.types if body else None,
        **(
            {"target_lexeme_ids": body.target_lexeme_ids}
            if generator is generate_batch and body
            else {}
        ),
    )
    db.commit()
    return {
        "locked":locked,
        "items":[
            {
                "id":item.id,
                "type":practice_item_type(
                    item,
                    db.get(PracticeTemplate,item.template_id),
                ),
                "prompt":item.prompt,
            }
            for item in items
        ],
    }
@router.post(
    "/practice/items/{item_id}/answer",
    response_model=PracticeAnswerOut,
    response_model_exclude_none=True,
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
    now = datetime.now(timezone.utc)
    if item.expires_at <= now:
        fail(
            410,
            "practice_item_expired",
            "Practice item has expired",
        )

    template = db.get(PracticeTemplate, item.template_id)
    item_type = practice_item_type(item, template)
    if item.answered_at is not None:
        fail(
            409,
            "practice_item_answered",
            "Practice item was already answered",
        )

    if item_type == "conversation":
        if not isinstance(body.response, dict):
            fail(
                422,
                "invalid_conversation_response",
                "Conversation response must include node_id and response",
            )
        node_id = body.response.get("node_id")
        learner_response = body.response.get("response")
        if not isinstance(node_id, str) or learner_response is None:
            fail(
                422,
                "invalid_conversation_response",
                "Conversation response must include node_id and response",
            )
        nodes = conversation_nodes(item.prompt)
        node = nodes.get(node_id)
        if node is None:
            fail(
                422,
                "invalid_conversation_node",
                "Conversation node not found",
            )
        script = resolve_script(db, node.get("answer_language_code"))
        result, matched_variant = conversation_reply_result(
            node=node,
            response=learner_response,
            script=script,
            language_code=node.get("answer_language_code"),
            input_mode=body.input_mode,
        )
        correct = result != "incorrect"
        next_node = conversation_next_node(
            node=node,
            matched_variant=matched_variant,
            nodes=nodes,
        )
        xp_awarded = 0
        if not correct or next_node is not None:
            db.commit()
            return {
                "correct": correct,
                "result": result,
                "correct_response": node.get("accepted_variants") or [],
                "xp_awarded": 0,
                "next_node": (
                    conversation_public_node(next_node)
                    if next_node is not None
                    else None
                ),
            }

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
        if item.target_lexeme_id:
            srs = db.scalar(
                select(UserLexemeSRS)
                .where(
                    UserLexemeSRS.user_id == user.id,
                    UserLexemeSRS.lexeme_id == item.target_lexeme_id,
                )
                .with_for_update()
            )
        if srs is not None:
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
                correct=True,
                xp_awarded=xp_awarded,
            )
        )
        item.answered_at = now
        record_activity(db, user.id, xp_awarded, user.timezone)
        db.commit()
        return {
            "correct": True,
            "result": result,
            "correct_response": node.get("accepted_variants") or [],
            "xp_awarded": xp_awarded,
        }

    script = resolve_script(db, item.prompt.get("answer_language_code"))
    language_code = item.prompt.get("answer_language_code")
    result = grade(
        body.response,
        item.correct_response,
        item_type,
        script=script,
        language_code=language_code,
        input_mode=body.input_mode,
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
        "feedback": render_item_feedback(
            db, template, item.course_id, item.filled_slots,
            item.target_lexeme_id,
        ),
    }

def temporary_password() -> str:
    return secrets.token_urlsafe(18)

def admin_user_summary(db:Session,target:User) -> dict:
    stats=db.get(UserStats,target.id)
    direct_courses=set(db.scalars(select(SkillProgress.course_id).where(SkillProgress.user_id==target.id)))
    lesson_courses=set(
        db.scalars(
            select(Unit.course_id)
            .join(Lesson,Lesson.unit_id==Unit.id)
            .join(LessonProgress,LessonProgress.lesson_id==Lesson.id)
            .where(LessonProgress.user_id==target.id)
            .distinct()
        )
    )
    course_ids=direct_courses|lesson_courses
    enrolled=[
        {"id":course.id,"title":course.title}
        for course in db.scalars(select(Course).where(Course.id.in_(course_ids)).order_by(Course.title)) if course
    ] if course_ids else []
    return {
        "id":target.id,
        "email":target.email,
        "display_name":target.display_name,
        "created_at":target.created_at,
        "xp":stats.total_xp if stats else 0,
        "streak":effective_streak_days(stats.streak_days,stats.last_activity_date,target.timezone,freezes_available=stats.streak_freezes_available) if stats else 0,
        "last_activity":stats.last_activity_date if stats else None,
        "enrolled_courses":enrolled,
        "is_admin":is_admin_user(target),
        "is_active":target.is_active,
    }

def get_admin_target_user(db:Session,user_id:str) -> User:
    target=db.get(User,user_id)
    if not target: fail(404,"user_not_found","User not found")
    return target

def active_admin_count(db:Session) -> int:
    return db.scalar(
        select(func.count(User.id)).where(
            User.is_active.is_(True),
            User.is_admin.is_(True),
        )
    ) or 0

def complete_lesson_for_user(db:Session,target:User,lesson_row:Lesson,now:datetime) -> tuple[bool,int]:
    progress=db.scalar(
        select(LessonProgress)
        .where(
            LessonProgress.user_id==target.id,
            LessonProgress.lesson_id==lesson_row.id,
        )
        .with_for_update()
    )
    created_or_completed=False
    if not progress:
        progress=LessonProgress(
            user_id=target.id,
            lesson_id=lesson_row.id,
            started_at=now,
            completed_at=now,
            correct_count=0,
            answer_count=0,
            xp_earned=0,
        )
        db.add(progress)
        created_or_completed=True
    elif progress.completed_at is None:
        if progress.started_at is None:
            progress.started_at=now
        progress.completed_at=now
        created_or_completed=True

    introduced=0
    seed_params = seed_params_for_lesson(db, target.id, lesson_row.id, progress.started_at if progress else now, now) if created_or_completed else None
    lexemes=list(db.scalars(select(Lexeme).where(Lexeme.provenance_lesson_id==lesson_row.id)))
    existing=set(
        db.scalars(
            select(UserLexemeSRS.lexeme_id)
            .where(
                UserLexemeSRS.user_id==target.id,
                UserLexemeSRS.lexeme_id.in_([lexeme.id for lexeme in lexemes]),
            )
            .with_for_update()
        )
    ) if lexemes else set()
    for lexeme in lexemes if created_or_completed else []:
        if lexeme.id in existing:
            continue
        db.add(
            UserLexemeSRS(
                user_id=target.id,
                lexeme_id=lexeme.id,
                course_id=lexeme.course_id,
                **seed_params,
                introduced_at=now,
                suspended=False,
                last_session_id=None,
            )
        )
        introduced+=1
    return created_or_completed,introduced

def refresh_skill_progress(db:Session,target:User,course_id:str):
    completed=db.scalar(
        select(func.count(LessonProgress.id))
        .join(Lesson,Lesson.id==LessonProgress.lesson_id)
        .join(Unit,Unit.id==Lesson.unit_id)
        .where(
            LessonProgress.user_id==target.id,
            Unit.course_id==course_id,
            Unit.track=="core",
            LessonProgress.completed_at.is_not(None),
        )
    ) or 0
    total=db.scalar(select(func.count(Lesson.id)).join(Unit).where(Unit.course_id==course_id,Unit.track=="core")) or 1
    skill=db.scalar(select(SkillProgress).where(SkillProgress.user_id==target.id,SkillProgress.course_id==course_id))
    if not skill:
        skill=SkillProgress(user_id=target.id,course_id=course_id,completed_lessons=0,mastery=0.0)
        db.add(skill)
    skill.completed_lessons=completed
    skill.mastery=completed/total

def mark_unit_checkpoint_passed(db:Session,target:User,unit_id:str,now:datetime) -> bool:
    existing=checkpoint_passed_for_unit(db,target.id,unit_id)
    if existing:
        return False
    db.add(
        CheckpointAttempt(
            user_id=target.id,
            unit_id=unit_id,
            total_items=12,
            passed=True,
            score=1.0,
            weak_outcomes=[],
            created_at=now,
            scored_at=now,
        )
    )
    return True

@router.post("/admin/users",response_model=AdminUserCreateOut,status_code=201)
def admin_create_user(body:AdminUserCreateIn,user=Depends(admin_user),db:Session=Depends(get_db)):
    email=body.email.lower()
    if db.scalar(select(User).where(User.email==email)): fail(409,"email_exists","An account with this email already exists")
    password=temporary_password()
    target=User(email=email,password_hash=hash_password(password),display_name=body.display_name,is_admin=False,is_active=True)
    db.add(target); db.flush()
    db.add(UserStats(user_id=target.id,total_xp=0,streak_days=0,last_activity_date=None,daily_goal=20))
    db.commit(); db.refresh(target)
    return {"user":admin_user_summary(db,target),"temporary_password":password}

@router.get("/admin/users",response_model=AdminUserListOut)
def admin_list_users(q:str|None=Query(None,max_length=200),limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),user=Depends(admin_user),db:Session=Depends(get_db)):
    query=select(User)
    if q and q.strip():
        pattern=f"%{q.strip()}%"
        query=query.where(or_(User.email.ilike(pattern),User.display_name.ilike(pattern)))
    total=db.scalar(select(func.count()).select_from(query.subquery())) or 0
    users=list(db.scalars(query.order_by(User.created_at.desc(),User.email).offset(offset).limit(limit)))
    return {"items":[admin_user_summary(db,target) for target in users],"total":total,"limit":limit,"offset":offset}

@router.post("/admin/users/{user_id}/reset-password",response_model=AdminPasswordResetOut)
def admin_reset_password(user_id:str,user=Depends(admin_user),db:Session=Depends(get_db)):
    target=get_admin_target_user(db,user_id)
    password=temporary_password()
    target.password_hash=hash_password(password)
    revoke_all_refresh_tokens(db,target.id,utc_now())
    db.commit()
    return {"temporary_password":password}

@router.post("/admin/users/{user_id}/deactivate",response_model=AdminUserOut)
def admin_deactivate_user(user_id:str,user=Depends(admin_user),db:Session=Depends(get_db)):
    target=get_admin_target_user(db,user_id)
    if target.is_active and is_admin_user(target) and active_admin_count(db)<=1:
        fail(409,"last_admin","Cannot deactivate the last remaining admin")
    target.is_active=False
    revoke_all_refresh_tokens(db,target.id,utc_now())
    db.commit(); db.refresh(target)
    return admin_user_summary(db,target)

@router.post("/admin/users/{user_id}/activate",response_model=AdminUserOut)
def admin_activate_user(user_id:str,user=Depends(admin_user),db:Session=Depends(get_db)):
    target=get_admin_target_user(db,user_id)
    target.is_active=True
    db.commit(); db.refresh(target)
    return admin_user_summary(db,target)

@router.delete("/admin/users/{user_id}",status_code=204)
def admin_delete_user(user_id:str,user=Depends(admin_user),db:Session=Depends(get_db)):
    target=get_admin_target_user(db,user_id)
    if target.is_active and is_admin_user(target) and active_admin_count(db)<=1:
        fail(409,"last_admin","Cannot delete the last remaining admin")
    delete_user_account(db,target)
    db.commit()
    return Response(status_code=204)

@router.post("/admin/users/{user_id}/admin",response_model=AdminUserOut)
def admin_set_admin(user_id:str,body:AdminUserAdminIn,user=Depends(admin_user),db:Session=Depends(get_db)):
    target=get_admin_target_user(db,user_id)
    if not body.is_admin and target.is_active and is_admin_user(target):
        if active_admin_count(db)<=1:
            fail(409,"last_admin","Cannot demote the last remaining admin")
    target.is_admin=body.is_admin
    db.commit(); db.refresh(target)
    return admin_user_summary(db,target)

@router.post("/admin/users/{user_id}/unlock",response_model=AdminUserUnlockOut)
def admin_unlock_user(user_id:str,body:AdminUserUnlockIn,user=Depends(admin_user),db:Session=Depends(get_db)):
    target=get_admin_target_user(db,user_id)
    now=datetime.now(timezone.utc)
    lessons_to_complete:list[Lesson]=[]
    unit_ids:set[str]=set()
    course_ids:set[str]=set()
    if body.lesson_id:
        lesson_row=db.get(Lesson,body.lesson_id)
        if not lesson_row: fail(404,"lesson_not_found","Lesson not found")
        unit=db.get(Unit,lesson_row.unit_id)
        lessons_to_complete=[lesson_row]
        unit_ids.add(unit.id)
        course_ids.add(unit.course_id)
    elif body.unit_id:
        unit=db.get(Unit,body.unit_id)
        if not unit: fail(404,"unit_not_found","Unit not found")
        lessons_to_complete=list(db.scalars(select(Lesson).where(Lesson.unit_id==unit.id).order_by(Lesson.order)))
        unit_ids.add(unit.id)
        course_ids.add(unit.course_id)
    else:
        course=db.get(Course,body.course_id)
        if not course: fail(404,"course_not_found","Course not found")
        lessons_to_complete=list(
            db.scalars(
                select(Lesson)
                .join(Unit,Unit.id==Lesson.unit_id)
                .where(Unit.course_id==course.id,Unit.track=="core")
                .order_by(Unit.order,Lesson.order)
            )
        )
        unit_ids=set(db.scalars(select(Unit.id).where(Unit.course_id==course.id,Unit.track=="core")))
        course_ids.add(course.id)

    completed_lessons=0
    introduced_lexemes=0
    for lesson_row in lessons_to_complete:
        completed,introduced=complete_lesson_for_user(db,target,lesson_row,now)
        completed_lessons+=int(completed)
        introduced_lexemes+=introduced
    for course_id in course_ids:
        refresh_skill_progress(db,target,course_id)
    passed_checkpoints=sum(1 for unit_id in unit_ids if mark_unit_checkpoint_passed(db,target,unit_id,now))
    db.commit()
    return {"completed_lessons":completed_lessons,"passed_checkpoints":passed_checkpoints,"introduced_lexemes":introduced_lexemes}

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
    q=select(ContentIssueReport).options(selectinload(ContentIssueReport.attachments)); q=q.where(ContentIssueReport.status==status) if status else q; q=q.where(ContentIssueReport.category==category) if category else q
    issues=list(db.scalars(q.order_by(ContentIssueReport.created_at.desc(),ContentIssueReport.id.desc()).offset(offset).limit(limit)))
    # Triage enrichment (see ContentIssueOut / docs/CONTRACT.md): resolve
    # each referenced exercise/practice item's prompt (+ the exercise's
    # answer key) in ONE batched query per table, not per issue, plus a
    # per-exercise open-report count for duplicate spotting. The count is
    # over ALL open reports for that exercise in the whole table, not just
    # this filtered/paginated page. A dangling id (content since deleted)
    # simply leaves the enrichment fields null — never an error.
    ex_ids={i.exercise_id for i in issues if i.exercise_id}; pi_ids={i.practice_item_id for i in issues if i.practice_item_id}
    ex_map={row.id:row for row in db.execute(select(Exercise.id,Exercise.prompt,Exercise.correct_response).where(Exercise.id.in_(ex_ids)))} if ex_ids else {}
    pi_map={row_id:prompt for row_id,prompt in db.execute(select(PracticeItem.id,PracticeItem.prompt).where(PracticeItem.id.in_(pi_ids)))} if pi_ids else {}
    open_counts={eid:n for eid,n in db.execute(select(ContentIssueReport.exercise_id,func.count()).where(ContentIssueReport.exercise_id.in_(ex_ids),ContentIssueReport.status=="open").group_by(ContentIssueReport.exercise_id))} if ex_ids else {}
    out=[]
    for issue in issues:
        item=ContentIssueOut.model_validate(issue)
        ex=ex_map.get(issue.exercise_id) if issue.exercise_id else None
        if ex is not None: item.exercise_prompt=ex.prompt; item.exercise_correct_response=ex.correct_response; item.open_report_count=open_counts.get(issue.exercise_id,0)
        if issue.practice_item_id and issue.practice_item_id in pi_map: item.practice_item_prompt=pi_map[issue.practice_item_id]
        out.append(item)
    return out
@router.patch("/admin/content/issues/{issue_id}",response_model=ContentIssueOut)
def update_content_issue(issue_id:str,body:ContentIssueUpdateIn,user=Depends(admin_user),db:Session=Depends(get_db)):
    issue=db.scalar(select(ContentIssueReport).options(selectinload(ContentIssueReport.attachments)).where(ContentIssueReport.id==issue_id))
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
@router.get("/admin/content/issues/{issue_id}/attachments/{attachment_id}")
def content_issue_attachment(issue_id:str,attachment_id:str,user=Depends(admin_user),db:Session=Depends(get_db)):
    attachment=db.get(FeedbackAttachment,attachment_id)
    if not attachment or attachment.report_id!=issue_id:
        fail(404,"feedback_attachment_not_found","Feedback attachment not found")
    path=feedback_attachment_service.feedback_attachment_path(attachment.key)
    if not path.is_file():
        fail(404,"feedback_attachment_file_missing","Feedback attachment file is missing")
    return FileResponse(path,media_type=attachment.content_type)
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

@router.post("/stt/transcribe",response_model=STTOut,response_model_exclude_none=True)
async def stt_transcribe(
    language_code: str = Form(...),
    detail: str | None = Form(default=None),
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
        if detail == "words":
            result = await run_in_threadpool(
                stt_service.transcribe_audio_with_words,
                audio_bytes,
                language_code,
            )
        else:
            result = {
                "transcript": await run_in_threadpool(
                    stt_service.transcribe_audio,
                    audio_bytes,
                    language_code,
                )
            }
    except Exception:
        fail(500, "transcription_failed", "Speech-to-text transcription failed")
    finally:
        # Privacy default: discard raw audio immediately after transcription
        # — never written to disk, never logged, not retained beyond this
        # request's stack frame.
        del audio_bytes, chunks
    return result
