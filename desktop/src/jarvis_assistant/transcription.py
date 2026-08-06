from __future__ import annotations

import logging
import os
import threading
from pathlib import Path

import numpy as np


class LocalTranscriber:
    def __init__(
        self,
        models_dir: Path,
        model_name: str = "base",
        compute_type: str = "int8",
        language: str = "es",
        allow_download: bool = False,
    ) -> None:
        self.models_dir = models_dir
        self.model_name = model_name
        self.compute_type = compute_type
        self.language = language
        self.allow_download = allow_download
        self._model: object | None = None
        self._lock = threading.Lock()
        self._logger = logging.getLogger(__name__)

    @property
    def ready(self) -> bool:
        return self._model is not None

    def warm_up(self) -> None:
        self._get_model()

    def transcribe(self, pcm_audio: np.ndarray) -> str:
        if pcm_audio.size == 0:
            return ""
        model = self._get_model()
        normalized = pcm_audio.astype(np.float32) / 32768.0
        segments, info = model.transcribe(
            normalized,
            language=self.language,
            beam_size=3,
            vad_filter=True,
            condition_on_previous_text=False,
            without_timestamps=True,
        )
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
        self._logger.info("Idioma detectado: %s, duración: %.2fs", info.language, info.duration)
        return text

    def _get_model(self) -> object:
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is not None:
                return self._model
            os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
            from faster_whisper import WhisperModel

            download_root = self.models_dir / "whisper"
            download_root.mkdir(parents=True, exist_ok=True)
            cpu_count = os.cpu_count() or 4
            self._model = WhisperModel(
                self.model_name,
                device="cpu",
                compute_type=self.compute_type,
                cpu_threads=max(2, min(8, cpu_count // 2)),
                download_root=str(download_root),
                local_files_only=not self.allow_download,
            )
            return self._model
