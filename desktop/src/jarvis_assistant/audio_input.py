from __future__ import annotations

import logging
import queue
import time
from collections import deque
from dataclasses import dataclass

import numpy as np
import sounddevice as sd


SAMPLE_RATE = 16_000
FRAME_SAMPLES = 1_280
FRAME_SECONDS = FRAME_SAMPLES / SAMPLE_RATE


def pcm_rms(chunk: np.ndarray) -> float:
    if chunk.size == 0:
        return 0.0
    values = chunk.astype(np.float32)
    return float(np.sqrt(np.mean(values * values)))


@dataclass(frozen=True, slots=True)
class CaptureResult:
    audio: np.ndarray
    speech_detected: bool
    threshold: float
    duration_seconds: float


class MicrophoneStream:
    def __init__(
        self,
        device: int | None = None,
        sample_rate: int = SAMPLE_RATE,
        frame_samples: int = FRAME_SAMPLES,
    ) -> None:
        self.device = device
        self.sample_rate = sample_rate
        self.frame_samples = frame_samples
        self._queue: queue.Queue[bytes] = queue.Queue(maxsize=250)
        self._stream: sd.RawInputStream | None = None
        self._ambient_rms = 120.0
        self._logger = logging.getLogger(__name__)

    @property
    def ambient_rms(self) -> float:
        return self._ambient_rms

    def start(self) -> None:
        if self._stream is not None:
            return
        self._stream = sd.RawInputStream(
            samplerate=self.sample_rate,
            blocksize=self.frame_samples,
            device=self.device,
            dtype="int16",
            channels=1,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None
        self.clear()

    def clear(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return

    def read(self, timeout: float = 0.5, update_ambient: bool = True) -> np.ndarray | None:
        try:
            raw = self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
        chunk = np.frombuffer(raw, dtype=np.int16).copy()
        if update_ambient:
            level = pcm_rms(chunk)
            if level < max(1_800.0, self._ambient_rms * 4):
                self._ambient_rms = self._ambient_rms * 0.96 + level * 0.04
        return chunk

    def capture_utterance(
        self,
        max_seconds: float,
        silence_seconds: float,
        minimum_rms: int,
        speech_start_timeout: float = 6.0,
    ) -> CaptureResult:
        self.clear()
        start = time.monotonic()
        threshold = max(float(minimum_rms), self._ambient_rms * 2.4)
        speech_started = False
        silence_frames = 0
        required_silence_frames = max(1, int(silence_seconds / FRAME_SECONDS))
        pre_roll: deque[np.ndarray] = deque(maxlen=4)
        captured: list[np.ndarray] = []

        while time.monotonic() - start < max_seconds:
            chunk = self.read(timeout=0.5, update_ambient=False)
            if chunk is None:
                continue
            level = pcm_rms(chunk)

            if not speech_started:
                pre_roll.append(chunk)
                if level >= threshold:
                    speech_started = True
                    captured.extend(pre_roll)
                    silence_frames = 0
                elif time.monotonic() - start >= speech_start_timeout:
                    break
                continue

            captured.append(chunk)
            if level >= threshold:
                silence_frames = 0
            else:
                silence_frames += 1
                if silence_frames >= required_silence_frames:
                    break

        audio = np.concatenate(captured) if captured else np.empty(0, dtype=np.int16)
        return CaptureResult(
            audio=audio,
            speech_detected=speech_started,
            threshold=threshold,
            duration_seconds=audio.size / self.sample_rate,
        )

    def _callback(self, indata: object, frames: int, time_info: object, status: sd.CallbackFlags) -> None:
        del frames, time_info
        if status:
            self._logger.debug("Estado de PortAudio: %s", status)
        raw = bytes(indata)
        try:
            self._queue.put_nowait(raw)
        except queue.Full:
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(raw)
            except queue.Empty:
                return

    def __enter__(self) -> "MicrophoneStream":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.stop()
