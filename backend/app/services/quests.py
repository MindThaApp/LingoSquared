from datetime import date, datetime, timezone
import hashlib
import random

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import (
    LessonProgress,
    CheckpointAttempt,
    ExerciseAttempt,
    PracticeAttempt,
    QuestCompletion,
    UserLexemeSRS,
)
from app.services.progress import (
    activity_day_bounds,
    award_xp,
    stats_for,
)


QUEST_DEFINITIONS = (
    {
        "code": "clear_reviews",
        "title": "Clear your due reviews",
        "description": "Complete all reviews that are currently due.",
        "xp_reward": 10,
        "target": 1,
    },
    {
        "code": "complete_lesson",
        "title": "Complete a lesson",
        "description": "Complete one lesson today.",
        "xp_reward": 10,
        "target": 1,
    },
    {
        "code": "practice_correct_5",
        "title": "5 correct in practice",
        "description": "Answer five practice items correctly today.",
        "xp_reward": 10,
        "target": 5,
    },
    {"code":"answer_reviews_3","title":"Answer 3 reviews","description":"Complete three reviews today.","xp_reward":10,"target":3},
    {"code":"accurate_lesson","title":"Finish a lesson accurately","description":"Complete a lesson with at least 80% correct today.","xp_reward":10,"target":1},
    {"code":"practice_items_10","title":"Practice 10 items","description":"Answer ten practice items today.","xp_reward":10,"target":10},
    {"code":"earn_daily_goal","title":"Reach your daily XP goal","description":"Earn XP from learning until you reach your daily goal.","xp_reward":10,"target":20},
    {"code":"complete_checkpoint","title":"Complete a checkpoint","description":"Finish a unit checkpoint today.","xp_reward":15,"target":1},
)


def selected_quest_definitions(user_id: str, quest_date: date) -> tuple[dict, ...]:
    """Pick a stable three-quest set for this user's local calendar day."""
    seed = hashlib.sha256(f"{user_id}:{quest_date.isoformat()}".encode()).digest()
    selected = set(random.Random(int.from_bytes(seed, "big")).sample(range(len(QUEST_DEFINITIONS)), 3))
    return tuple(item for index, item in enumerate(QUEST_DEFINITIONS) if index in selected)


def _live_progress(
    db: Session,
    user_id: str,
    day_start: datetime,
    day_end: datetime,
) -> dict[str, int]:
    now = datetime.now(timezone.utc)

    lexeme_count = db.scalar(
        select(func.count(UserLexemeSRS.id)).where(
            UserLexemeSRS.user_id == user_id,
        )
    ) or 0
    due_count = db.scalar(
        select(func.count(UserLexemeSRS.id)).where(
            UserLexemeSRS.user_id == user_id,
            UserLexemeSRS.due_at <= now,
            UserLexemeSRS.suspended.is_(False),
        )
    ) or 0
    reviewed_today = db.scalar(
        select(func.count(UserLexemeSRS.id)).where(
            UserLexemeSRS.user_id == user_id,
            UserLexemeSRS.last_reviewed_at >= day_start,
            UserLexemeSRS.last_reviewed_at < day_end,
        )
    ) or 0

    lessons_completed = db.scalar(
        select(func.count(LessonProgress.id)).where(
            LessonProgress.user_id == user_id,
            LessonProgress.completed_at >= day_start,
            LessonProgress.completed_at < day_end,
        )
    ) or 0

    correct_practice = db.scalar(
        select(func.count(PracticeAttempt.id)).where(
            PracticeAttempt.user_id == user_id,
            PracticeAttempt.correct.is_(True),
            PracticeAttempt.created_at >= day_start,
            PracticeAttempt.created_at < day_end,
        )
    ) or 0
    practice_count = db.scalar(
        select(func.count(PracticeAttempt.id)).where(
            PracticeAttempt.user_id == user_id,
            PracticeAttempt.created_at >= day_start,
            PracticeAttempt.created_at < day_end,
        )
    ) or 0
    accurate_lessons = db.scalar(
        select(func.count(LessonProgress.id)).where(
            LessonProgress.user_id == user_id,
            LessonProgress.completed_at >= day_start,
            LessonProgress.completed_at < day_end,
            LessonProgress.answer_count > 0,
            LessonProgress.correct_count * 100 >= LessonProgress.answer_count * 80,
        )
    ) or 0
    checkpoints = db.scalar(
        select(func.count(CheckpointAttempt.id)).where(
            CheckpointAttempt.user_id == user_id,
            CheckpointAttempt.scored_at >= day_start,
            CheckpointAttempt.scored_at < day_end,
        )
    ) or 0
    review_count = reviewed_today
    learning_xp = sum((db.scalar(select(func.coalesce(func.sum(model.xp_awarded), 0)).where(
        model.user_id == user_id, model.created_at >= day_start, model.created_at < day_end,
    )) or 0) for model in (ExerciseAttempt, PracticeAttempt))

    return {
        # A user with no vocabulary has no actionable review quest yet.
        "clear_reviews": int(lexeme_count > 0 and reviewed_today > 0 and due_count == 0),
        "complete_lesson": min(lessons_completed, 1),
        "practice_correct_5": min(correct_practice, 5),
        "answer_reviews_3": min(review_count, 3),
        "accurate_lesson": min(accurate_lessons, 1),
        "practice_items_10": min(practice_count, 10),
        "earn_daily_goal": learning_xp,
        "complete_checkpoint": min(checkpoints, 1),
    }


def daily_quests_for(
    db: Session,
    user_id: str,
    user_timezone: str | None,
) -> list[dict]:
    day_start, day_end = activity_day_bounds(user_timezone)
    quest_date = day_start.date()
    progress_by_code = _live_progress(
        db,
        user_id,
        day_start,
        day_end,
    )

    completed_codes = set(
        db.scalars(
            select(QuestCompletion.quest_code).where(
                QuestCompletion.user_id == user_id,
                QuestCompletion.date == quest_date,
            )
        )
    )

    results = []
    daily_goal = stats_for(db, user_id).daily_goal
    for definition in selected_quest_definitions(user_id, quest_date):
        if definition["code"] == "earn_daily_goal":
            definition = {**definition, "target": daily_goal}
        code = definition["code"]
        target = definition["target"]
        progress = progress_by_code[code]
        live_completed = progress >= target

        if live_completed and code not in completed_codes:
            inserted_id = db.scalar(
                pg_insert(QuestCompletion)
                .values(user_id=user_id, quest_code=code, date=quest_date)
                .on_conflict_do_nothing(
                    constraint="uq_quest_completions_user_code_date"
                )
                .returning(QuestCompletion.id)
            )
            if inserted_id:
                award_xp(db, user_id, definition["xp_reward"])
            completed_codes.add(code)

        completed = code in completed_codes
        results.append(
            {
                **definition,
                "completed": completed,
                "progress": target if completed else progress,
            }
        )

    return results
