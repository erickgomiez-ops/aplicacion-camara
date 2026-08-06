from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

import numpy as np


PRONUNCIATIONS = {
    "jarvish": "HH AA R V IY S",
    "jarvisj": "JH AA R V AH S",
    "jarvisy": "Y AA R V IY S",
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

    def detected(self, chunk: np.ndarray) -> bool:
        self._decoder.process_raw(chunk.astype(np.int16, copy=False).tobytes(), False, False)
        hypothesis = self._decoder.hyp()
        if hypothesis is None:
            return False
        self._logger.info("Palabra de activación detectada")
        self.reset()
        return True

    def score(self, chunk: np.ndarray) -> float:
        return 1.0 if self.detected(chunk) else 0.0

    def reset(self) -> None:
        self._decoder.end_utt()
        self._decoder.start_utt()
