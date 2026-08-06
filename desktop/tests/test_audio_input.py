import numpy as np

from jarvis_assistant.audio_input import pcm_rms


def test_pcm_rms_for_silence() -> None:
    assert pcm_rms(np.zeros(1280, dtype=np.int16)) == 0


def test_pcm_rms_detects_signal() -> None:
    signal = np.full(1280, 1000, dtype=np.int16)
    assert 999 <= pcm_rms(signal) <= 1001
