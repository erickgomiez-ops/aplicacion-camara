from __future__ import annotations

import sys
from types import SimpleNamespace

from jarvis_assistant.transcription import LocalTranscriber


def test_transcriber_uses_only_cached_model_during_normal_start(monkeypatch, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeWhisperModel:
        def __init__(self, model_name: str, **kwargs: object) -> None:
            calls.append({"model_name": model_name, **kwargs})

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=FakeWhisperModel))
    LocalTranscriber(tmp_path, model_name="base").warm_up()

    assert calls[0]["model_name"] == "base"
    assert calls[0]["local_files_only"] is True


def test_model_setup_can_download_missing_model(monkeypatch, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeWhisperModel:
        def __init__(self, model_name: str, **kwargs: object) -> None:
            calls.append({"model_name": model_name, **kwargs})

    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=FakeWhisperModel))
    LocalTranscriber(tmp_path, model_name="base", allow_download=True).warm_up()

    assert calls[0]["local_files_only"] is False
