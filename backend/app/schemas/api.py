import json
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from app.models.entities import CEFRLevel, ExerciseType, UnitSection

ContentIssueCategory=Literal["wrong_answer_key","mistranslation","untaught_vocabulary","audio_issue","unclear_instruction","app_bug","general_feedback","other"]
ContentIssueStatus=Literal["open","triaged","resolved","wontfix","duplicate"]

# Security: bounds a user-supplied free-form payload's serialized size,
# regardless of whether it's a string/list/dict, so a single request can't
# force an unbounded-cost operation server-side (e.g. grade_answer()'s
# Damerau-Levenshtein comparison against exercise/practice/review answers
# allocates an O(len(response) * len(correct)) table with no length check
# of its own - a multi-megabyte `response` string was otherwise a trivial,
# unauthenticated-admin-not-required DoS). No legitimate answer (a word,
# phrase, or short sentence; matching_pairs/word_order's handful of
# tokens) comes close to this bound.
_MAX_PAYLOAD_JSON_CHARS = 5000


def _bounded_payload_size(value):
    try:
        size = len(json.dumps(value, default=str))
    except (TypeError, ValueError):
        size = len(str(value))
    if size > _MAX_PAYLOAD_JSON_CHARS:
        raise ValueError(f"payload too large (max {_MAX_PAYLOAD_JSON_CHARS} serialized characters)")
    return value

class ORM(BaseModel): model_config=ConfigDict(from_attributes=True)
# is_admin: additive (2026-07-10 security pass). The backend's admin_user
# dependency remains the real security boundary for every /admin/* route --
# exposing the flag here only lets the frontend gate admin UI
# (AdminContentPage) on the real value instead of firing admin API calls
# and reacting to the 403 after the fact.
class UserOut(ORM): id:str; email:EmailStr; display_name:str; is_admin:bool=False
class UserIdentityOut(ORM): provider:Literal["google","apple"]; created_at:datetime
class MeOut(UserOut): created_at:datetime; identities:list[UserIdentityOut]=Field(default_factory=list)
# Phase H3 (2026-07-07 integrity audit): display_name/timezone were the
# only free-form string fields on the auth path with no length bound --
# an unbounded display_name persists verbatim and is echoed on every
# authenticated response for the account's lifetime. 100 comfortably
# covers any real name; 64 comfortably covers the longest real IANA zone
# names (e.g. "America/Argentina/ComodRivadavia", under 40 chars).
class RegisterIn(BaseModel): email:EmailStr; password:str=Field(min_length=8,max_length=128); display_name:str|None=Field(default=None,max_length=100); timezone:str|None=Field(default=None,max_length=64)
class LoginIn(BaseModel): email:EmailStr; password:str=Field(max_length=128); timezone:str|None=Field(default=None,max_length=64)
class SocialLoginIn(BaseModel):
    provider:Literal["google","apple"]
    id_token:str=Field(min_length=1,max_length=8192)
    display_name:str|None=Field(default=None,max_length=100)
    # Raw nonce from POST /auth/social/nonce whose SHA-256 hex digest the
    # client passed to the provider. Required for both providers and
    # single-use; Optional here only so a missing one is a 401 like any
    # other failed sign-in rather than a 422.
    nonce:str|None=Field(default=None,min_length=16,max_length=256)
class SocialLinkIn(SocialLoginIn):
    # Required when the signed-in account is not a guest and has a password:
    # a bare access token must not be enough to attach a permanent sign-in.
    current_password:str|None=Field(default=None,max_length=128)
class SocialUnlinkIn(BaseModel):
    provider:Literal["google","apple"]
    current_password:str|None=Field(default=None,max_length=128)
class SocialNonceOut(BaseModel): nonce:str; expires_in:int
class AuthOut(BaseModel): access_token:str; refresh_token:str; token_type:Literal["bearer"]="bearer"; expires_in:int; user:UserOut
class RefreshIn(BaseModel):
    refresh_token:str=Field(min_length=1,max_length=512)
    # Optional client-chosen successor: a client that persists this value
    # BEFORE sending the request still holds its next refresh token even if
    # the response never arrives (page closed or reloaded mid-request).
    # At least 256 bits of base64url randomness.
    next_refresh_token:str|None=Field(default=None,min_length=43,max_length=128,pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("next_refresh_token")
    @classmethod
    def proposal_is_not_trivially_weak(cls,value:str|None) -> str|None:
        # The server cannot measure entropy, but it can refuse values no
        # CSPRNG would produce: 43+ random base64url characters use about 30
        # distinct symbols on average, and fewer than 16 essentially never.
        if value is not None and len(set(value))<16:
            raise ValueError("next_refresh_token is not random enough")
        return value
class RefreshOut(BaseModel): access_token:str; refresh_token:str; token_type:Literal["bearer"]="bearer"; expires_in:int
class LogoutIn(BaseModel): refresh_token:str=Field(min_length=1,max_length=512)
class AdminUserCreateIn(BaseModel): email:EmailStr; display_name:str=Field(min_length=1,max_length=100)
class AdminUserAdminIn(BaseModel): is_admin:bool
class AdminUserUnlockIn(BaseModel):
    course_id:str|None=None
    unit_id:str|None=None
    lesson_id:str|None=None

    @model_validator(mode="after")
    def exactly_one_target(self):
        targets=[self.course_id,self.unit_id,self.lesson_id]
        if sum(value is not None for value in targets)!=1:
            raise ValueError("Exactly one of course_id, unit_id, or lesson_id is required")
        return self
class AdminUserCourseOut(BaseModel): id:str; title:str
class AdminUserOut(BaseModel):
    id:str
    email:EmailStr
    display_name:str
    created_at:datetime
    xp:int
    streak:int
    last_activity:Any=None
    enrolled_courses:list[AdminUserCourseOut]=Field(default_factory=list)
    is_admin:bool
    is_active:bool
class AdminUserListOut(BaseModel): items:list[AdminUserOut]; total:int; limit:int; offset:int
class AdminUserCreateOut(BaseModel): user:AdminUserOut; temporary_password:str
class AdminPasswordResetOut(BaseModel): temporary_password:str
class AdminUserUnlockOut(BaseModel): completed_lessons:int; passed_checkpoints:int; introduced_lexemes:int
class LanguageOut(ORM): code:str; name:str; native_name:str; script:Literal["latin","cyrillic","han","arabic","devanagari","hangul","japanese"]; direction:Literal["ltr","rtl"]
class TextBlock(BaseModel): text:str; language_code:str; direction:Literal["ltr","rtl"]; speaker:str|None=None
# 2026-07-07 vocabulary-example addition (CONTRACT.md, AUTHORING_GUIDE.md #19):
# optional example sentences showing the card's word in real context —
# additive, cards without examples serialize exactly as before.
class TeachingExample(BaseModel): text_blocks:list[TextBlock]
class TeachingCard(BaseModel): kind:Literal["vocabulary","phrase","grammar_note","dialogue","pronunciation_note","cultural_note","reading"]; title:str|None=None; text_blocks:list[TextBlock]; note:str|None=None; content_key:str|None=None; examples:list[TeachingExample]|None=None; glosses:dict[str,str]|None=None
class ExerciseOut(BaseModel): id:str; type:ExerciseType; order:int; prompt:dict[str,Any]
class LessonDetail(BaseModel): id:str; unit_id:str; title:str; teaching:list[TeachingCard]; exercises:list[ExerciseOut]
class AnswerIn(BaseModel):
    response: str|list[Any]|dict[str,Any]|bool|int|float
    input_mode: Literal["typed", "spoken"] = "typed"
    client_operation_id: str|None=Field(default=None,max_length=36)
    self_grade: Literal["again","hard","good","easy"]|None=None
    latency_ms: int|None=Field(default=None,ge=0,le=3_600_000)
    @model_validator(mode="after")
    def bounded_response(self):
        _bounded_payload_size(self.response); return self
class AnswerOut(BaseModel): correct:bool; result:Literal["correct","almost","incorrect"]="correct"; correct_response:Any; xp_awarded:int; feedback:str|None=None
class LanguagePairOut(BaseModel): source_language:str; target_language:str; course_count:int
class CourseOut(BaseModel): id:str; source_language:str; target_language:str; title:str; level:CEFRLevel; unit_count:int; recommended:bool=False
class CourseDetail(CourseOut): description:str
class UnitOut(BaseModel): id:str; title:str; order:int; lesson_count:int; completed_lesson_count:int=0; section:UnitSection; locked:bool; checkpoint_passed:bool=False; content_key:str|None=None; track:Literal["core","situation"]="core"
class LessonOut(BaseModel): id:str; title:str; order:int; exercise_count:int
class StartOut(BaseModel): started_at:datetime
class CompleteOut(BaseModel): completed_at:datetime; xp_awarded:int; accuracy:float
class ReviewAnswerOut(AnswerOut): next_due_at:datetime
class StreakOut(BaseModel): streak_days:int; last_activity_date:Any=None; streak_freezes_available:int=0; freeze_used_today:bool=False; active_today:bool=False
class XPOut(BaseModel): total_xp:int; daily_goal:int; xp_today:int=0
class DailyGoalIn(BaseModel): daily_goal_xp:Literal[10,20,30,50]
class DailyGoalOut(BaseModel): daily_goal_xp:int
class QuestOut(BaseModel): code:str; title:str; description:str; xp_reward:int; completed:bool; progress:int; target:int
class QuestsOut(BaseModel): quests:list[QuestOut]
# updated_* counts are additive: content_key-matched rows that were
# updated in place (existing id, existing FKs untouched) rather than
# created. All default to 0 so any caller ignoring them sees no change
# in behavior from before content_key-based updates existed.
class ImportOut(BaseModel):
    imported_courses:int
    retired_exercises:int=0
    unretired_exercises:int=0
    updated_units:int=0
    updated_lessons:int=0
    updated_exercises:int=0
    updated_teaching_items:int=0
    created_units:int=0
    created_lessons:int=0
    created_exercises:int=0
    created_teaching_items:int=0
    # Non-fatal: per-item order conflicts skipped during a content_key
    # reconciliation (the request still succeeds -- everything else
    # that wasn't ambiguous was already created/updated). Distinct from
    # ValidationOut/the 422 content_invalid failure, which blocks the
    # whole request before anything is written.
    warnings:list[str]=[]
class ValidationOut(BaseModel): valid:bool; errors:list[str]
class ContentIssueReportIn(BaseModel):
    category:ContentIssueCategory; description:str|None=Field(default=None,max_length=2000); learner_response:Any|None=None
    @model_validator(mode="after")
    def bounded_learner_response(self):
        if self.learner_response is not None: _bounded_payload_size(self.learner_response)
        return self
class GeneralFeedbackIn(BaseModel):
    category:ContentIssueCategory
    description:str|None=Field(default=None,max_length=2000)
    page_path:str=Field(max_length=255)
    client_context:dict[str,Any]=Field(default_factory=dict)
    attachment_keys:list[str]=Field(default_factory=list,max_length=3)

    @model_validator(mode="after")
    def bounded_client_context(self):
        _bounded_payload_size(self.client_context)
        _bounded_payload_size(self.attachment_keys)
        return self
class ContentIssueCreatedOut(BaseModel): id:str; status:ContentIssueStatus
class FeedbackAttachmentUploadOut(BaseModel): attachment_key:str; expires_in_seconds:int
class ContentIssueAttachmentOut(ORM): id:str; content_type:str; byte_size:int
class ContentIssueUpdateIn(BaseModel):
    status:ContentIssueStatus|None=None
    triage_notes:str|None=Field(default=None,max_length=5000)
    duplicate_of_id:str|None=None

    @model_validator(mode="after")
    def has_update(self):
        if not self.model_fields_set: raise ValueError("At least one update field is required")
        if "status" in self.model_fields_set and self.status is None: raise ValueError("status cannot be null")
        return self
class ContentIssueOut(ORM):
    id:str
    reporter_user_id:str|None
    # At most one of these two is set (enforced by a DB check
    # constraint). Page-level feedback legitimately has neither id.
    exercise_id:str|None
    practice_item_id:str|None
    page_path:str|None
    content_release_id:str|None
    content_key_id:str|None
    attempt_id:str|None
    category:str
    description:str|None
    learner_response:Any|None
    client_context:dict[str,Any]
    status:str
    triage_notes:str|None
    duplicate_of_id:str|None
    created_at:datetime
    triaged_at:datetime|None
    resolved_at:datetime|None
    attachments:list[ContentIssueAttachmentOut]=Field(default_factory=list)
    # Triage enrichment, computed per-request by GET /admin/content/issues
    # (never stored on the report row) so an admin sees what the report is
    # about without spelunking YAML/psql: the referenced exercise's prompt
    # + answer key (or the generated practice item's stored prompt), and
    # how many OPEN reports point at the same exercise (duplicate
    # spotting). All default None — the PATCH endpoint returns the bare
    # row without re-running the enrichment joins, and page-level
    # feedback has no content to resolve. See docs/CONTRACT.md
    # "Issue-triage enrichment", 2026-07-10.
    exercise_prompt:dict[str,Any]|None=None
    exercise_correct_response:Any|None=None
    practice_item_prompt:dict[str,Any]|None=None
    open_report_count:int|None=None
class ContentCoverageOut(BaseModel): source_language:str; target_language:str; course_count:int; total_unit_count:int; total_lesson_count:int; open_issue_count:int

# content_key (optional, additive): a stable authoring key (e.g.
# "prs.a1.unit01.lesson01.exercise04.match_final_group") that, when
# present, lets import_content() update an already-shipped row in
# place instead of only ever matching by position. None on any of
# these means "no stable key supplied" - the importer falls back to
# today's position-only append/skip behavior for that item, exactly
# as before this field existed.
class ExerciseImport(BaseModel): type:ExerciseType; order:int=Field(ge=1); prompt:dict[str,Any]; correct_response:Any; feedback:str|None=None; xp:int=Field(default=10,ge=0); content_key:str|None=None
class TeachingImport(TeachingCard): pass
class LessonImport(BaseModel): title:str; order:int=Field(ge=1); teaching:list[TeachingImport]=Field(default_factory=list); exercises:list[ExerciseImport]; content_key:str|None=None
class UnitImport(BaseModel): title:str; order:int=Field(ge=1); section:UnitSection=UnitSection.reading_writing; lessons:list[LessonImport]; content_key:str|None=None; track:Literal["core","situation"]="core"
class ContentItemImport(BaseModel): kind:Literal["vocabulary","phrase","grammar_note","dialogue","pronunciation_note","cultural_note","reading"]; language_code:str; title:str=""; content:dict[str,Any]
class CourseImport(BaseModel):
    source_language:str
    target_language:str
    title:str
    description:str=""
    level:CEFRLevel=CEFRLevel.A1
    recommended:bool|None=None
    units:list[UnitImport]
    content_items:list[ContentItemImport]=[]

    @model_validator(mode="after")
    def distinct(self):
        if self.source_language==self.target_language: raise ValueError("source_language and target_language must differ")
        return self
class ImportRequest(BaseModel): courses:list[CourseImport]; retire_missing:bool=True
class ValidateRequest(BaseModel): content:ImportRequest
PracticeTemplateExerciseType=Literal["multiple_choice","fill_in_blank","word_order","translation","matching_pairs","listen_select"]
PracticeItemExerciseType=Literal["multiple_choice","fill_in_blank","word_order","translation","matching_pairs","listen_select","speak_repeat","speak_response","conversation"]
PracticeBatchMode=Literal["mixed","speaking","conversation"]
class PracticeTemplateImport(BaseModel):
    content_key:str=Field(min_length=1,max_length=255)
    lesson_content_key:str=Field(min_length=1,max_length=255)
    type:PracticeTemplateExerciseType
    frame:dict[str,Any]
    slots:dict[str,Any]
    slot_relations:list[dict[str,Any]]=Field(default_factory=list)
    answer_derivation:dict[str,Any]
    feedback_frame:dict[str,Any]
class PracticePackImport(BaseModel):
    pack_key:str
    unit_content_key:str
    tag_schema:dict[str,Any]
    templates:list[PracticeTemplateImport]
class PracticeArtifactImport(BaseModel):
    artifact_type:Literal["lingosquared.practice_templates"]
    artifact_version:Literal[1]
    source_language:str
    target_language:str
    packs:list[PracticePackImport]
class PracticeImportOut(BaseModel): imported_templates:int; updated_templates:int
class PracticeBatchIn(BaseModel):
    size:int=Field(default=10,ge=1,le=20)
    mode:PracticeBatchMode="mixed"
    types:list[str]|None=None
    target_lexeme_ids:list[str]|None=None

    @model_validator(mode="after")
    def valid_template_types(self):
        if self.types is not None:
            valid_types = {
                "multiple_choice", "fill_in_blank", "word_order",
                "translation", "matching_pairs", "listen_select",
            }
            self.types = [item_type for item_type in self.types if item_type in valid_types]
        return self
class PracticeItemOut(BaseModel): id:str; type:PracticeItemExerciseType; prompt:dict[str,Any]
class PracticeBatchOut(BaseModel): locked:bool; items:list[PracticeItemOut]
class PracticeAnswerOut(BaseModel): correct:bool; result:Literal["correct","almost","incorrect"]="correct"; correct_response:Any; xp_awarded:int; next_node:dict[str,Any]|None=None; feedback:str|None=None; next_due_at:datetime|None=None; next_interval_days:int|None=None
class ReviewDueCourseOut(BaseModel):
    course_id: str
    due_count: int
class ReviewDueOut(BaseModel):
    due_count: int
    by_course: list[ReviewDueCourseOut]
LexemeSort=Literal["due_soonest","mastery_asc","mastery_desc","alphabetical","recently_introduced"]
class LexemeOut(BaseModel):
    token:str
    english_gloss:str
    part_of_speech:str
    mastery:float
    interval_days:int
    repetitions:int
    due_at:datetime
    introduced_at:datetime
    suspended:bool
    last_reviewed_at:datetime|None
class LexemeListOut(BaseModel):
    items:list[LexemeOut]
    total_count:int
    limit:int
    offset:int
class LexemeMasteryBandsOut(BaseModel):
    new:int
    learning:int
    strong:int
class LexemeSummaryOut(BaseModel):
    total_tracked:int
    mastery_bands:LexemeMasteryBandsOut
    due_today:int
    suspended:int
class MistakeLexemeOut(BaseModel):
    token:str
    english_gloss:str
    part_of_speech:str
    mastery:float
    repetitions:int
    recent_accuracy:float
    wrong_attempt_count:int
    total_attempt_count:int
class MistakeLexemeListOut(BaseModel):
    items:list[MistakeLexemeOut]
    total_count:int
    limit:int
    offset:int
class ReviewSessionIn(BaseModel):
    course_id: str
    size: int = Field(default=10, ge=1, le=20)
class ReviewItemsOut(BaseModel):
    items: list[PracticeItemOut]
class CheckpointIn(BaseModel):
    size: int = Field(default=15, ge=12, le=15)
class CheckpointResultOut(BaseModel):
    status: Literal["in_progress","complete"]
    answered_items: int
    total_items: int
    passed: bool|None
    score: float|None
    weak_outcomes: list[str]
    weak_lexeme_ids: list[str] = []
    checkpoint_passed: bool
# Placement test (course-level), 2026-08-05. Recognition-only, assembled
# from the course's own existing multiple_choice/matching_pairs exercises;
# the MVP writes NOTHING (no ExerciseAttempt/LessonProgress/XP/SRS). Full
# design: docs/PLACEMENT_TEST_SPEC.md; contract: docs/CONTRACT.md placement
# section. `level` is the CEFR sublevel parsed from the owning Unit's
# content_key (never Course.level).
class PlacementProbeOut(BaseModel): id:str; level:str; type:ExerciseType; order:int; prompt:dict[str,Any]
class PlacementSetOut(BaseModel):
    course_id:str
    levels:list[str]
    block_size:int
    pass_threshold:int
    items:list[PlacementProbeOut]
# One answered probe. Same response union + serialized-size bound as
# AnswerIn (guards grade()'s O(len*len) comparison against a giant payload).
# Doubles as both the /answer request body and each element of /result's
# answers list.
class PlacementAnswerIn(BaseModel):
    exercise_id:str
    response: str|list[Any]|dict[str,Any]|bool|int|float
    @model_validator(mode="after")
    def bounded_response(self):
        _bounded_payload_size(self.response); return self
# Correct answers are only ever revealed by /answer (per-item, post-grade)
# -- never in the /placement set payload (PlacementProbeOut omits them).
class PlacementAnswerOut(BaseModel): correct:bool; result:Literal["correct","almost","incorrect"]="correct"; correct_response:Any
class PlacementResultIn(BaseModel):
    # Bounded so a single request can't force an unbounded number of
    # grade() passes (16 probes is a full A1-B2 ladder; 200 is generous).
    answers:list[PlacementAnswerIn]=Field(default_factory=list,max_length=200)
class PlacementLevelStatOut(BaseModel): correct:int; total:int
class PlacementResultOut(BaseModel):
    recommended_level:str|None
    recommended_unit_id:str|None
    recommended_unit_content_key:str|None
    recommended_unit_title:str|None
    per_level:dict[str,PlacementLevelStatOut]
class TTSIn(BaseModel): text:str=Field(min_length=1,max_length=5000); language_code:str; speaking_rate:float|None=Field(default=None,ge=0.25,le=2.0)
class TTSFallback(BaseModel): use_browser_tts:Literal[True]=True; reason:Literal["unsupported_language","quota_exceeded","provider_error"]
class STTWordOut(BaseModel): word:str; start:float; end:float; probability:float
class STTOut(BaseModel): transcript:str; words:list[STTWordOut]|None=None
class STTError(BaseModel): error:Literal["empty_audio","audio_too_large","transcription_failed"]
class PushSubscriptionKeysIn(BaseModel): p256dh:str=Field(min_length=1); auth:str=Field(min_length=1)
class PushSubscribeIn(BaseModel): endpoint:str=Field(min_length=1,max_length=1024); keys:PushSubscriptionKeysIn
class PushUnsubscribeIn(BaseModel): endpoint:str=Field(min_length=1,max_length=1024)
class PushVapidKeyOut(BaseModel): public_key:str|None; configured:bool
class PushNotifyOut(BaseModel): notified_users:int; notifications_sent:int
