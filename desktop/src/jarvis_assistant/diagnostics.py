from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import sounddevice as sd
from PIL import ImageGrab

from .audio_input import MicrophoneStream, pcm_rms
from .chimes import ensure_chimes
from .codex_bridge import CodexBridge
from .config import JarvisConfig, config_path
from .speaker import LocalSpeaker
from .transcription import LocalTranscriber
from .wakeword import WakeWordDetector, wake_models_ready


@dataclass(frozen=True, slots=True)
class DiagnosticCheck:
    name: str
    ok: bool
    detail: str


def setup_local_models(config: JarvisConfig) -> list[str]:
    messages = ["Generando sonidos originales de JARVIS..."]
    ensure_chimes(config.data_dir)
    messages.append("Preparando detector local de 'Jarvis'...")
    WakeWordDetector(config.models_dir, config.wake_keyword_threshold)
    messages.append(f"Descargando y preparando Whisper {config.whisper_model}...")
    LocalTranscriber(
        config.models_dir,
        config.whisper_model,
        config.whisper_compute_type,
        config.language,
        allow_download=True,
    ).warm_up()
    messages.append("Modelos locales listos.")
    return messages


def run_diagnostics(config: JarvisConfig) -> list[DiagnosticCheck]:
    checks: list[DiagnosticCheck] = []
    checks.append(DiagnosticCheck("Python", sys.version_info[:2] == (3, 10), sys.version.split()[0]))
    checks.append(DiagnosticCheck("Configuración", config_path().exists(), str(config_path())))
    checks.append(DiagnosticCheck("Proyecto Codex", config.workspace_path.is_dir(), str(config.workspace_path)))
    checks.append(DiagnosticCheck("Detector de Jarvis", wake_models_ready(config.models_dir), "PocketSphinx local"))

    try:
        input_device = sd.query_devices(config.input_device, "input")
        with MicrophoneStream(config.input_device) as microphone:
            sample = microphone.read(timeout=2.0)
        if sample is None:
            raise RuntimeError("El dispositivo abrio, pero no entrego audio")
        detail = f"{input_device['name']} ({input_device['max_input_channels']} canales, RMS {pcm_rms(sample):.1f})"
        checks.append(DiagnosticCheck("Micrófono", input_device["max_input_channels"] > 0, detail))
    except Exception as error:
        checks.append(DiagnosticCheck("Micrófono", False, str(error)))

    speaker = LocalSpeaker(config.voice_name_contains, config.voice_rate, config.voice_volume)
    try:
        speaker.start()
        checks.append(DiagnosticCheck("Voz", True, speaker.voice_description))
    except Exception as error:
        checks.append(DiagnosticCheck("Voz", False, str(error)))
    finally:
        speaker.stop()

    try:
        image = ImageGrab.grab(bbox=(0, 0, 2, 2))
        checks.append(DiagnosticCheck("Captura de pantalla", image.size == (2, 2), "Permiso disponible"))
    except Exception as error:
        checks.append(DiagnosticCheck("Captura de pantalla", False, str(error)))

    codex = CodexBridge(config).login_status()
    checks.append(DiagnosticCheck("Codex", codex.ok, codex.response or codex.error))
    return checks


def diagnostics_json(checks: list[DiagnosticCheck]) -> str:
    return json.dumps([asdict(check) for check in checks], ensure_ascii=False, indent=2)
