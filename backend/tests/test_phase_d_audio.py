from types import SimpleNamespace

import app.api.router as api_router

# Compiler tests for this phase (dialogue single-block validator) live in
# scripts/tests/test_compile_content.py instead of here: the backend
# Docker container's `.:/app` mount only covers backend/, so a test in
# backend/tests/ importing scripts/compile_content.py by path fails
# inside the container even though it works locally via .content-venv
# (see CLAUDE.md's footgun list). Only genuine API/DB integration tests
# belong in this file.

def configure_asset_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(api_router, "MEDIA_ASSETS_DIR", tmp_path)


def test_admin_can_upload_and_serve_recorded_audio(
    client,
    admin,
    monkeypatch,
    tmp_path,
):
    configure_asset_directory(monkeypatch, tmp_path)
    key = "fa.a1.audio.salam.neutral.01"
    audio = b"ID3-test-recording"

    upload = client.post(
        "/admin/media/upload",
        headers=admin,
        data={"key": key},
        files={"file": ("salam.mp3", audio, "audio/mpeg")},
    )

    assert upload.status_code == 200
    assert upload.json()["key"] == key
    assert upload.json()["url"].endswith(f"/media/{key}")

    response = client.get(f"/media/{key}")

    assert response.status_code == 200
    assert response.content == audio
    assert response.headers["content-type"].startswith("audio/mpeg")

    cache_control = response.headers["cache-control"]
    assert "immutable" in cache_control
    max_age = next(
        int(part.split("=", 1)[1])
        for part in cache_control.split(",")
        if part.strip().startswith("max-age=")
    )
    assert max_age >= 7 * 24 * 60 * 60


def test_missing_recording_returns_real_404(
    client,
    monkeypatch,
    tmp_path,
):
    configure_asset_directory(monkeypatch, tmp_path)

    response = client.get("/media/fa.a1.audio.not-recorded.01")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "media_asset_not_found"


def test_upload_rejects_path_traversal_key(
    client,
    admin,
    monkeypatch,
    tmp_path,
):
    configure_asset_directory(monkeypatch, tmp_path)

    response = client.post(
        "/admin/media/upload",
        headers=admin,
        data={"key": "../outside"},
        files={"file": ("clip.mp3", b"ID3-audio", "audio/mpeg")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_media_asset_key"
    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_non_admin(
    client,
    auth,
    monkeypatch,
    tmp_path,
):
    configure_asset_directory(monkeypatch, tmp_path)

    response = client.post(
        "/admin/media/upload",
        headers=auth,
        data={"key": "fa.a1.audio.forbidden.01"},
        files={"file": ("clip.mp3", b"ID3-audio", "audio/mpeg")},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "admin_required"
    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_empty_audio(
    client,
    admin,
    monkeypatch,
    tmp_path,
):
    configure_asset_directory(monkeypatch, tmp_path)

    response = client.post(
        "/admin/media/upload",
        headers=admin,
        data={"key": "fa.a1.audio.empty.01"},
        files={"file": ("empty.mp3", b"", "audio/mpeg")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "empty_media_asset"
    assert list(tmp_path.iterdir()) == []


def test_upload_rejects_oversized_audio(
    client,
    admin,
    monkeypatch,
    tmp_path,
):
    configure_asset_directory(monkeypatch, tmp_path)

    response = client.post(
        "/admin/media/upload",
        headers=admin,
        data={"key": "fa.a1.audio.too-large.01"},
        files={
            "file": (
                "large.mp3",
                b"x" * (api_router.MAX_AUDIO_SIZE_BYTES + 1),
                "audio/mpeg",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "media_asset_too_large"
    assert list(tmp_path.iterdir()) == []


def test_stt_transcribe_default_shape_unchanged(client, auth, monkeypatch):
    from app.services import stt as stt_service

    def fake_transcribe(audio_bytes, language_code):
        assert audio_bytes == b"webm-bytes"
        assert language_code == "en"
        return "it will probably take two months"

    def fail_word_detail(*_args, **_kwargs):
        raise AssertionError("word-detail STT path should not run by default")

    monkeypatch.setattr(stt_service, "transcribe_audio", fake_transcribe)
    monkeypatch.setattr(stt_service, "transcribe_audio_with_words", fail_word_detail)

    response = client.post(
        "/stt/transcribe",
        headers=auth,
        data={"language_code": "en"},
        files={"audio": ("answer.webm", b"webm-bytes", "audio/webm")},
    )

    assert response.status_code == 200
    assert response.content == b'{"transcript":"it will probably take two months"}'


def test_stt_transcribe_detail_words_returns_word_array(client, auth, monkeypatch):
    from app.services import stt as stt_service

    captured = {}

    class FakeModel:
        def transcribe(self, audio_file, **kwargs):
            captured["audio_bytes"] = audio_file.read()
            captured["kwargs"] = kwargs
            return [
                SimpleNamespace(
                    text=" it will",
                    words=[
                        SimpleNamespace(
                            word=" it",
                            start=0.12,
                            end=0.24,
                            probability=0.97,
                        ),
                        SimpleNamespace(
                            word=" will",
                            start=0.25,
                            end=0.44,
                            probability=0.91,
                        ),
                    ],
                ),
                SimpleNamespace(
                    text=" probably",
                    words=[
                        SimpleNamespace(
                            word=" probably",
                            start=0.61,
                            end=1.02,
                            probability=0.41,
                        ),
                    ],
                ),
            ], SimpleNamespace()

    monkeypatch.setattr(stt_service, "get_model", lambda: FakeModel())

    response = client.post(
        "/stt/transcribe",
        headers=auth,
        data={"language_code": "en", "detail": "words"},
        files={"audio": ("answer.webm", b"webm-bytes", "audio/webm")},
    )

    assert response.status_code == 200
    assert captured["audio_bytes"] == b"webm-bytes"
    assert captured["kwargs"]["word_timestamps"] is True
    assert response.json() == {
        "transcript": "it will probably",
        "words": [
            {"word": "it", "start": 0.12, "end": 0.24, "probability": 0.97},
            {"word": "will", "start": 0.25, "end": 0.44, "probability": 0.91},
            {"word": "probably", "start": 0.61, "end": 1.02, "probability": 0.41},
        ],
    }
