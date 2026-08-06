from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


SAMPLE_RATE = 44_100


def _envelope(position: int, total: int) -> float:
    attack = max(1, int(total * 0.08))
    release = max(1, int(total * 0.3))
    if position < attack:
        return position / attack
    if position > total - release:
        return max(0.0, (total - position) / release)
    return 1.0


def _tone(frequency: float, duration: float, volume: float = 0.32) -> bytes:
    count = int(SAMPLE_RATE * duration)
    samples = bytearray()
    for index in range(count):
        time_value = index / SAMPLE_RATE
        fundamental = math.sin(2 * math.pi * frequency * time_value)
        harmonic = 0.28 * math.sin(2 * math.pi * frequency * 2.01 * time_value)
        shimmer = 0.1 * math.sin(2 * math.pi * frequency * 3.97 * time_value)
        value = (fundamental + harmonic + shimmer) * _envelope(index, count) * volume
        samples.extend(struct.pack("<h", int(max(-1, min(1, value)) * 32767)))
    return bytes(samples)


def _silence(duration: float) -> bytes:
    return bytes(int(SAMPLE_RATE * duration) * 2)


def write_chime(path: Path, notes: list[tuple[float, float]], gap: float = 0.025) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = bytearray()
    for frequency, duration in notes:
        frames.extend(_tone(frequency, duration))
        frames.extend(_silence(gap))
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(frames)
    return path


def ensure_chimes(data_dir: Path) -> dict[str, Path]:
    audio_dir = data_dir / "audio"
    definitions = {
        "boot": [(164.8, 0.2), (246.9, 0.2), (329.6, 0.24), (493.9, 0.34), (659.3, 0.48)],
        "wake": [(523.3, 0.09), (784.0, 0.14)],
        "done": [(392.0, 0.09), (587.3, 0.16)],
        "error": [(220.0, 0.14), (174.6, 0.22)],
    }
    paths: dict[str, Path] = {}
    for name, notes in definitions.items():
        target = audio_dir / f"{name}.wav"
        if not target.exists():
            write_chime(target, notes)
        paths[name] = target
    return paths


def play_chime(path: Path, asynchronous: bool = False) -> None:
    try:
        import winsound

        flags = winsound.SND_FILENAME
        if asynchronous:
            flags |= winsound.SND_ASYNC
        winsound.PlaySound(str(path), flags)
    except (ImportError, RuntimeError, OSError):
        return
