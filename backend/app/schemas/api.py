import json
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
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
class UserOut(ORM): id:str; email:EmailStr; display_name:str
class MeOut(UserOut): created_at:datetime
# Phase H3 (2026-07-07 integrity audit): display_name/timezone were the
# only free-form string fields on the auth path with no length bound --
# an unbounded display_name persists verbatim and is echoed on every
# authenticated response for the account's lifetime. 100 comfortably
# covers any real name; 64 comfortably covers the longest real IANA zone
# names (e.g. "America/Argentina/ComodRivadavia", under 40 chars).
class RegisterIn(BaseModel): email:EmailStr; password:str=Field(min_length=8,max_length=128); display_name:str|None=Field(default=None,max_length=100); timezone:str|None=Field(default=None,max_length=64)
class LoginIn(BaseModel): email:EmailStr; password:str=Field(max_length=128); timezone:str|None=Field(default=None,max_length=64)
class AuthOut(BaseModel): access_token:str; token_type:Literal["bearer"]="bearer"; expires_in:int; user:UserOut
class LanguageOut(ORM): code:str; name:str; native_name:str; script:Literal["latin","cyrillic","han","arabic","devanagari"]; direction:Literal["ltr","rtl"]
class TextBlock(BaseModel): text:str; language_code:str; direction:Literal["ltr","rtl"]; speaker:str|None=None
# 2026-07-07 vocabulary-example addition (CONTRACT.md, AUTHORING_GUIDE.md #19):
# optional example sentences showing the card's word in real context —
# additive, cards without examples serialize exactly as before.
class TeachingExample(BaseModel): text_blocks:list[TextBlock]
class TeachingCard(BaseModel): kind:Literal["vocabulary","phrase","grammar_note","dialogue","pronunciation_note","cultural_note","reading"]; title:str|None=None; text_blocks:list[TextBlock]; note:str|None=None; content_key:str|None=None; examples:list[TeachingExample]|None=None
class ExerciseOut(BaseModel): id:str; type:ExerciseType; order:int; prompt:dict[str,Any]
class LessonDetail(BaseModel): id:str; unit_id:str; title:str; teaching:list[TeachingCard]; exercises:list[ExerciseOut]
class AnswerIn(BaseModel):
    response: str|list[Any]|dict[str,Any]|bool|int|float
    @model_validator(mode="after")
    def bounded_response(self):
        _bounded_payload_size(self.response); return self
class AnswerOut(BaseModel): correct:bool; result:Literal["correct","almost","incorrect"]="correct"; correct_response:Any; xp_awarded:int; feedback:str|None=None
class LanguagePairOut(BaseModel): source_language:str; target_language:str; course_count:int
class CourseOut(BaseModel): id:str; source_language:str; target_language:str; title:str; level:CEFRLevel; unit_count:int
class CourseDetail(CourseOut): description:str
class UnitOut(BaseModel): id:str; title:str; order:int; lesson_count:int; completed_lesson_count:int=0; section:UnitSection; locked:bool; checkpoint_passed:bool=False; content_key:str|None=None
class LessonOut(BaseModel): id:str; title:str; order:int; exercise_count:int
class StartOut(BaseModel): started_at:datetime
class CompleteOut(BaseModel): completed_at:datetime; xp_awarded:int; accuracy:float
class ReviewAnswerOut(AnswerOut): next_due_at:datetime
class StreakOut(BaseModel): streak_days:int; last_activity_date:Any=None; streak_freezes_available:int=0; freeze_used_today:bool=False
class XPOut(BaseModel): total_xp:int; daily_goal:int
class QuestOut(BaseModel): code:str; title:str; description:str; xp_reward:int; completed:bool; progress:int; target:int
class QuestsOut(BaseModel): quests:list[QuestOut]
# updated_* counts are additive: content_key-matched rows that were
# updated in place (existing id, existing FKs untouched) rather than
# created. All default to 0 so any caller ignoring them sees no change
# in behavior from before content_key-based updates existed.
class ImportOut(BaseModel):
    imported_courses:int
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

    @model_validator(mode="after")
    def bounded_client_context(self):
        _bounded_payload_size(self.client_context)
        return self
class ContentIssueCreatedOut(BaseModel): id:str; status:ContentIssueStatus
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
class UnitImport(BaseModel): title:str; order:int=Field(ge=1); section:UnitSection=UnitSection.reading_writing; lessons:list[LessonImport]; content_key:str|None=None
class ContentItemImport(BaseModel): kind:Literal["vocabulary","phrase","grammar_note","dialogue","pronunciation_note","cultural_note","reading"]; language_code:str; title:str=""; content:dict[str,Any]
class CourseImport(BaseModel):
    source_language:str
    target_language:str
    title:str
    description:str=""
    level:CEFRLevel=CEFRLevel.A1
    units:list[UnitImport]
    content_items:list[ContentItemImport]=[]

    @model_validator(mode="after")
    def distinct(self):
        if self.source_language==self.target_language: raise ValueError("source_language and target_language must differ")
        return self
class ImportRequest(BaseModel): courses:list[CourseImport]
class ValidateRequest(BaseModel): content:ImportRequest
PracticeExerciseType=Literal["multiple_choice","fill_in_blank","word_order","translation","matching_pairs","listen_select"]
class PracticeTemplateImport(BaseModel):
    content_key:str=Field(min_length=1,max_length=255)
    lesson_content_key:str=Field(min_length=1,max_length=255)
    type:PracticeExerciseType
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
class PracticeBatchIn(BaseModel): size:int=Field(default=10,ge=1,le=20)
class PracticeItemOut(BaseModel): id:str; type:PracticeExerciseType; prompt:dict[str,Any]
class PracticeBatchOut(BaseModel): locked:bool; items:list[PracticeItemOut]
class PracticeAnswerOut(BaseModel): correct:bool; result:Literal["correct","almost","incorrect"]="correct"; correct_response:Any; xp_awarded:int
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
    checkpoint_passed: bool
class TTSIn(BaseModel): text:str=Field(min_length=1,max_length=5000); language_code:str; speaking_rate:float|None=Field(default=None,ge=0.25,le=2.0)
class TTSFallback(BaseModel): use_browser_tts:Literal[True]=True; reason:Literal["unsupported_language","quota_exceeded","provider_error"]
class STTOut(BaseModel): transcript:str
class STTError(BaseModel): error:Literal["empty_audio","audio_too_large","transcription_failed"]
class PushSubscriptionKeysIn(BaseModel): p256dh:str=Field(min_length=1); auth:str=Field(min_length=1)
class PushSubscribeIn(BaseModel): endpoint:str=Field(min_length=1,max_length=1024); keys:PushSubscriptionKeysIn
class PushUnsubscribeIn(BaseModel): endpoint:str=Field(min_length=1,max_length=1024)
class PushVapidKeyOut(BaseModel): public_key:str|None; configured:bool
class PushNotifyOut(BaseModel): notified_users:int; notifications_sent:int
