from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

import numpy as np


PRONUNCIATIONS = {
    "jarvish": "HH AA R V IY S",
    "jarvisj": "JH AA R V AH S",
    "jarvisy": "Y AA R V IY S",
    "holaa": "HH AA L AA",
    "olaa": "AA L AA",
}


def wake_models_ready(models_dir: Path) -> bool:
    del models_dir
    return importlib.util.find_spec("pocketsphinx") is not None


def write_keyword_file(models_dir: Path, threshold: float) -> Path:
    keyword_dir = models_dir / "keyword"
    keyword_dir.mkdir(parents=True, exist_ok=True)
    target = keyword_dir / "jarvis.keywords"
    threshold_text = f"{threshold:.0e}"
    contents = "".join(f"{word} /{threshold_text}/\n" for word in PRONUNCIATIONS)
    target.write_text(contents, encoding="ascii")
    return target


class WakeWordDetector:
    def __init__(self, models_dir: Path, threshold: float = 1e-20) -> None:
        from pocketsphinx import Decoder

        self._logger = logging.getLogger(__name__)
        keyword_file = write_keyword_file(models_dir, threshold)
        self._decoder = Decoder(kws_threshold=threshold, loglevel="ERROR")
        for word, pronunciation in PRONUNCIATIONS.items():
            self._decoder.add_word(word, pronunciation, False)
        self._decoder.add_kws("jarvis", str(keyword_file))
        self._decoder.activate_search("jarvis")
        self._decoder.start_utt()
        self.last_hypothesis = ""

    def detected(self, chunk: np.ndarray) -> bool:
        return self.detected_keyword(chunk) is not None

    def detected_keyword(self, chunk: np.ndarray) -> str | None:
        self._decoder.process_raw(chunk.astype(np.int16, copy=False).tobytes(), False, False)
        hypothesis = self._decoder.hyp()
        if hypothesis is None:
            return None
        self._logger.info("Palabra de activación detectada")
        self.last_hypothesis = hypothesis.hypstr or ""
        self._logger.info("Hipotesis de activacion: %s", self.last_hypothesis)
        self.reset()
        return self.last_hypothesis

    def score(self, chunk: np.ndarray) -> float:
        return 1.0 if self.detected(chunk) else 0.0

    def reset(self) -> None:
        self._decoder.end_utt()
        self._decoder.start_utt()
