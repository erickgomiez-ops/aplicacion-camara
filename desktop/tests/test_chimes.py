import wave
from pathlib import Path

from jarvis_assistant.chimes import ensure_chimes


def test_chimes_are_valid_wave_files(tmp_path: Path) -> None:
    paths = ensure_chimes(tmp_path)
    assert set(paths) == {"boot", "wake", "done", "error"}
    with wave.open(str(paths["boot"]), "rb") as audio_file:
        assert audio_file.getframerate() == 44_100
        assert audio_file.getnchannels() == 1
        assert audio_file.getnframes() > 0
