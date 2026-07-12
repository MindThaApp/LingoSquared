import io
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.api import router as router_module
from app.db.session import SessionLocal
from app.models import ContentIssueReport, FeedbackAttachment
from app.services import feedback_attachments as feedback_attachment_service


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 24
JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 24
WEBP_BYTES = b"RIFF\x18\x00\x00\x00WEBPVP8 " + b"\x00" * 24
EXE_BYTES = b"MZ" + b"\x00" * 32


@pytest.fixture
def isolated_feedback_uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(feedback_attachment_service, "FEEDBACK_UPLOAD_DIR", tmp_path)
    return tmp_path


def upload_attachment(client, data: bytes, filename: str = "screenshot.bin", content_type: str = "application/octet-stream"):
    return client.post(
        "/feedback/attachments",
        files={"file": (filename, io.BytesIO(data), content_type)},
    )


@pytest.mark.parametrize(
    ("data", "filename", "expected_content_type"),
    [
        (PNG_BYTES, "screenshot.exe", "image/png"),
        (JPEG_BYTES, "screenshot.txt", "image/jpeg"),
        (WEBP_BYTES, "screenshot.bin", "image/webp"),
    ],
)
def test_feedback_attachment_upload_accepts_sniffed_image_types(
    client,
    isolated_feedback_uploads,
    data,
    filename,
    expected_content_type,
):
    response = upload_attachment(
        client,
        data,
        filename=filename,
        content_type="application/x-msdownload",
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["attachment_key"].startswith("fb_")
    assert body["expires_in_seconds"] == 3600

    with SessionLocal() as db:
        attachment = db.scalar(
            select(FeedbackAttachment).where(
                FeedbackAttachment.key == body["attachment_key"]
            )
        )
        assert attachment is not None
        assert attachment.report_id is None
        assert attachment.content_type == expected_content_type
        assert attachment.byte_size == len(data)
        assert (isolated_feedback_uploads / attachment.key).read_bytes() == data


def test_feedback_attachment_upload_rejects_wrong_type_even_with_image_header(client, isolated_feedback_uploads):
    response = upload_attachment(
        client,
        EXE_BYTES,
        filename="renamed-screenshot.png",
        content_type="image/png",
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_feedback_attachment_type"


def test_feedback_attachment_upload_rejects_oversize_file(client, isolated_feedback_uploads):
    oversized = PNG_BYTES + b"\x00" * (
        feedback_attachment_service.MAX_FEEDBACK_ATTACHMENT_BYTES - len(PNG_BYTES) + 1
    )
    response = upload_attachment(client, oversized, filename="too-large.png", content_type="image/png")
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "feedback_attachment_too_large"


def test_feedback_attachment_upload_rate_limit_returns_429(client, isolated_feedback_uploads, monkeypatch):
    monkeypatch.setattr(router_module.FEEDBACK_ATTACHMENT_RATE_LIMIT, "limit", 2)

    for _ in range(2):
        response = upload_attachment(client, PNG_BYTES, filename="ok.png")
        assert response.status_code == 201, response.text

    response = upload_attachment(client, PNG_BYTES, filename="overflow.png")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "report_rate_limited"


def test_feedback_report_claims_uploaded_attachment(client, isolated_feedback_uploads):
    uploaded = upload_attachment(client, PNG_BYTES, filename="claim.png")
    assert uploaded.status_code == 201, uploaded.text
    key = uploaded.json()["attachment_key"]

    feedback = client.post(
        "/feedback",
        json={
            "category": "app_bug",
            "description": "Screenshot attached.",
            "page_path": "/home",
            "attachment_keys": [key],
        },
    )
    assert feedback.status_code == 201, feedback.text

    with SessionLocal() as db:
        attachment = db.scalar(select(FeedbackAttachment).where(FeedbackAttachment.key == key))
        assert attachment is not None
        assert attachment.report_id == feedback.json()["id"]


def test_feedback_report_silently_drops_bad_attachment_keys(client, isolated_feedback_uploads):
    feedback = client.post(
        "/feedback",
        json={
            "category": "app_bug",
            "page_path": "/settings",
            "attachment_keys": ["fb_missing_key"],
        },
    )
    assert feedback.status_code == 201, feedback.text

    with SessionLocal() as db:
        issue = db.get(ContentIssueReport, feedback.json()["id"])
        assert issue is not None
        assert issue.attachments == []


def test_feedback_attachment_upload_sweeps_expired_orphans(client, isolated_feedback_uploads):
    old_key = "fb_expired_orphan"
    old_path = isolated_feedback_uploads / old_key
    old_path.write_bytes(PNG_BYTES)
    old_attachment = FeedbackAttachment(
        key=old_key,
        report_id=None,
        content_type="image/png",
        byte_size=len(PNG_BYTES),
        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    with SessionLocal() as db:
        db.add(old_attachment)
        db.commit()

    response = upload_attachment(client, JPEG_BYTES, filename="new.jpg")
    assert response.status_code == 201, response.text

    with SessionLocal() as db:
        assert db.scalar(select(FeedbackAttachment).where(FeedbackAttachment.key == old_key)) is None
    assert not old_path.exists()


def test_feedback_attachment_admin_retrieval_requires_admin_and_streams_bytes(
    client,
    auth,
    admin,
    isolated_feedback_uploads,
):
    uploaded = upload_attachment(client, WEBP_BYTES, filename="screen.webp")
    assert uploaded.status_code == 201, uploaded.text
    key = uploaded.json()["attachment_key"]
    feedback = client.post(
        "/feedback",
        json={
            "category": "app_bug",
            "page_path": "/camera",
            "attachment_keys": [key],
        },
    )
    assert feedback.status_code == 201, feedback.text

    with SessionLocal() as db:
        attachment = db.scalar(select(FeedbackAttachment).where(FeedbackAttachment.key == key))
        assert attachment is not None
        attachment_id = attachment.id
    url = f"/admin/content/issues/{feedback.json()['id']}/attachments/{attachment_id}"

    anonymous = client.get(url)
    assert anonymous.status_code == 401
    non_admin = client.get(url, headers=auth)
    assert non_admin.status_code == 403

    response = client.get(url, headers=admin)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("image/webp")
    assert response.content == WEBP_BYTES


def test_content_issue_out_includes_attachment_metadata(client, admin, isolated_feedback_uploads):
    uploaded = upload_attachment(client, JPEG_BYTES, filename="screen.jpg")
    assert uploaded.status_code == 201, uploaded.text
    key = uploaded.json()["attachment_key"]
    feedback = client.post(
        "/feedback",
        json={
            "category": "general_feedback",
            "page_path": "/metadata",
            "attachment_keys": [key],
        },
    )
    assert feedback.status_code == 201, feedback.text

    listing = client.get("/admin/content/issues?status=open&limit=200", headers=admin)
    assert listing.status_code == 200, listing.text
    row = next(issue for issue in listing.json() if issue["id"] == feedback.json()["id"])
    assert len(row["attachments"]) == 1
    attachment = row["attachments"][0]
    assert set(attachment) == {"id", "content_type", "byte_size"}
    assert attachment["content_type"] == "image/jpeg"
    assert attachment["byte_size"] == len(JPEG_BYTES)
