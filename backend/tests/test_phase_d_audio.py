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
