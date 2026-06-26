from pathlib import Path

from fastapi.testclient import TestClient
import pytest

import app.api.videos as videos_api
from app.main import app


def _set_upload_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SMARTTRAFFIC_LOCAL_VIDEOS_DIR", str(tmp_path / "videos"))
    monkeypatch.setenv("SMARTTRAFFIC_MAX_UPLOAD_MB", "200")
    monkeypatch.setenv("SMARTTRAFFIC_MAX_VIDEO_DURATION_SECONDS", "600")
    monkeypatch.setenv("SMARTTRAFFIC_ALLOWED_VIDEO_CODECS", "avc1,h264,mp4v,xvid,mjpg")


def _metadata(*, duration: float = 1.0, codec: str = "mp4v") -> dict:
    return {
        "video_path": "upload.mp4",
        "filename": "upload.mp4",
        "fps": 10.0,
        "width": 64,
        "height": 48,
        "total_frames": 10,
        "duration_seconds": duration,
        "codec": codec,
        "fourcc": 1983148141,
        "backend": "test",
    }


def _post_upload(filename: str, content: bytes) -> object:
    client = TestClient(app)
    return client.post(
        "/api/videos/upload",
        files={"file": (filename, content, "video/mp4")},
    )


def test_upload_rejects_unsupported_extension(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_upload_env(monkeypatch, tmp_path)

    response = _post_upload("upload.txt", b"not-video")

    assert response.status_code == 400
    assert "unsupported video type" in response.json()["detail"]


def test_upload_rejects_empty_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_upload_env(monkeypatch, tmp_path)

    response = _post_upload("empty.mp4", b"")

    assert response.status_code == 400
    assert response.json()["detail"] == "uploaded video is empty"


def test_upload_rejects_oversized_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_upload_env(monkeypatch, tmp_path)
    monkeypatch.setenv("SMARTTRAFFIC_MAX_UPLOAD_MB", "1")

    response = _post_upload("large.mp4", b"x" * (1024 * 1024 + 1))

    assert response.status_code == 413
    assert "exceeds 1 MB limit" in response.json()["detail"]
    assert not (tmp_path / "videos" / "large.mp4").exists()


def test_upload_rejects_too_long_duration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_upload_env(monkeypatch, tmp_path)
    monkeypatch.setenv("SMARTTRAFFIC_MAX_VIDEO_DURATION_SECONDS", "1")
    monkeypatch.setattr(
        videos_api,
        "read_video_metadata",
        lambda path: _metadata(duration=2.0),
    )

    response = _post_upload("long.mp4", b"fake-video")

    assert response.status_code == 400
    assert "duration exceeds 1 seconds limit" in response.json()["detail"]
    assert not (tmp_path / "videos" / "long.mp4").exists()


def test_upload_rejects_unsupported_codec(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_upload_env(monkeypatch, tmp_path)
    monkeypatch.setattr(
        videos_api,
        "read_video_metadata",
        lambda path: _metadata(codec="vp90"),
    )

    response = _post_upload("codec.mp4", b"fake-video")

    assert response.status_code == 400
    assert response.json()["detail"] == "unsupported video codec: vp90"
    assert not (tmp_path / "videos" / "codec.mp4").exists()


def test_upload_accepts_opencv_fmp4_alias_for_mp4v(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_upload_env(monkeypatch, tmp_path)
    monkeypatch.setattr(
        videos_api,
        "read_video_metadata",
        lambda path: _metadata(codec="fmp4"),
    )

    response = _post_upload("alias.mp4", b"fake-video")

    assert response.status_code == 200
    assert response.json()["filename"] == "alias.mp4"


def test_upload_accepts_valid_mocked_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _set_upload_env(monkeypatch, tmp_path)
    calls: list[Path] = []

    def fake_metadata(path: Path) -> dict:
        calls.append(path)
        return _metadata(duration=1.0, codec="mp4v")

    monkeypatch.setattr(videos_api, "read_video_metadata", fake_metadata)

    response = _post_upload("valid.mp4", b"fake-video")

    assert response.status_code == 200
    assert response.json()["filename"] == "valid.mp4"
    assert response.json()["duration_seconds"] == 1.0
    assert calls == [tmp_path / "videos" / "valid.mp4"]
