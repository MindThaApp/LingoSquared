import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import fail
from app.models import ContentIssueReport, FeedbackAttachment


FEEDBACK_UPLOAD_DIR = Path(__file__).resolve().parents[2] / "feedback_uploads"
MAX_FEEDBACK_ATTACHMENT_BYTES = 5 * 1024 * 1024
FEEDBACK_ATTACHMENT_EXPIRES_SECONDS = 60 * 60


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sniff_image_content_type(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def feedback_attachment_path(key: str) -> Path:
    return FEEDBACK_UPLOAD_DIR / key


def _new_attachment_key(db: Session) -> str:
    for _ in range(20):
        key = f"fb_{secrets.token_urlsafe(24)}"
        if db.scalar(select(FeedbackAttachment.id).where(FeedbackAttachment.key == key)) is None:
            return key
    fail(500, "attachment_key_generation_failed", "Could not allocate attachment key")


def _validated_upload_bytes(file: UploadFile) -> tuple[bytes, str]:
    data = file.file.read(MAX_FEEDBACK_ATTACHMENT_BYTES + 1)
    if len(data) > MAX_FEEDBACK_ATTACHMENT_BYTES:
        fail(413, "feedback_attachment_too_large", "Feedback attachments must be 5 MB or smaller")
    content_type = sniff_image_content_type(data)
    if content_type is None:
        fail(415, "unsupported_feedback_attachment_type", "Feedback attachments must be PNG, JPEG, or WebP images")
    return data, content_type


def sweep_expired_orphan_attachments(db: Session, now_value: datetime | None = None) -> int:
    now_value = now_value or utc_now()
    cutoff = now_value - timedelta(seconds=FEEDBACK_ATTACHMENT_EXPIRES_SECONDS)
    expired = list(
        db.scalars(
            select(FeedbackAttachment).where(
                FeedbackAttachment.report_id.is_(None),
                FeedbackAttachment.created_at < cutoff,
            )
        )
    )
    for attachment in expired:
        try:
            feedback_attachment_path(attachment.key).unlink(missing_ok=True)
        except OSError:
            pass
        db.delete(attachment)
    return len(expired)


def store_feedback_attachment(db: Session, file: UploadFile) -> FeedbackAttachment:
    now_value = utc_now()
    sweep_expired_orphan_attachments(db, now_value)
    data, content_type = _validated_upload_bytes(file)
    key = _new_attachment_key(db)
    FEEDBACK_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    feedback_attachment_path(key).write_bytes(data)
    attachment = FeedbackAttachment(
        key=key,
        report_id=None,
        content_type=content_type,
        byte_size=len(data),
        created_at=now_value,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


def claim_feedback_attachments(
    db: Session,
    issue: ContentIssueReport,
    attachment_keys: list[str],
    now_value: datetime | None = None,
) -> None:
    if not attachment_keys:
        return
    unique_keys = list(dict.fromkeys(attachment_keys))[:3]
    now_value = now_value or utc_now()
    cutoff = now_value - timedelta(seconds=FEEDBACK_ATTACHMENT_EXPIRES_SECONDS)
    attachments = list(
        db.scalars(
            select(FeedbackAttachment).where(
                FeedbackAttachment.key.in_(unique_keys),
                FeedbackAttachment.report_id.is_(None),
                FeedbackAttachment.created_at >= cutoff,
            )
        )
    )
    for attachment in attachments[:3]:
        attachment.report_id = issue.id
