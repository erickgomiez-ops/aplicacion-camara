from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_data_dir() -> Path:
    user_profile = os.environ.get("USERPROFILE")
    if os.name == "nt" and user_profile:
        # Microsoft Store Python virtualizes LOCALAPPDATA into a much longer path.
        return Path(user_profile) / "AppData" / "Local" / "JarvisLocal"
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "JarvisLocal"
    return Path.home() / "AppData" / "Local" / "JarvisLocal"


@dataclass(slots=True)
class JarvisConfig:
    assistant_name: str = "Jarvis"
    language: str = "es"
    input_device: int | None = None
    wake_keyword_threshold: float = 1e-20
    wake_cooldown_seconds: float = 2.5
    command_max_seconds: float = 20.0
    command_silence_seconds: float = 1.2
    microphone_rms_threshold: int = 420
    whisper_model: str = "base"
    whisper_compute_type: str = "int8"
    voice_name_contains: str = "Raul"
    voice_rate: int = 172
    voice_volume: float = 0.95
    codex_enabled: bool = True
    codex_confirm_tasks: bool = True
    codex_workspace: str = ""
    codex_timeout_seconds: int = 1800
    speak_codex_max_chars: int = 520
    screen_analysis_enabled: bool = True
    start_with_windows: bool = True

    @property
    def data_dir(self) -> Path:
        return default_data_dir()

    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def screenshots_dir(self) -> Path:
        return self.data_dir / "screenshots"

    @property
    def workspace_path(self) -> Path:
        raw = self.codex_workspace.strip()
        return Path(raw).expanduser().resolve() if raw else repository_root()

    def validate(self) -> None:
        if not 1e-50 <= self.wake_keyword_threshold <= 1e-3:
            raise ValueError("wake_keyword_threshold debe estar entre 1e-50 y 1e-3")
        if self.command_max_seconds < 3:
            raise ValueError("command_max_seconds debe ser al menos 3")
        if self.command_silence_seconds < 0.4:
            raise ValueError("command_silence_seconds debe ser al menos 0.4")
        if not 0 <= self.voice_volume <= 1:
            raise ValueError("voice_volume debe estar entre 0 y 1")
        if self.codex_enabled and not self.workspace_path.exists():
            raise ValueError(f"No existe el proyecto configurado para Codex: {self.workspace_path}")


def config_path() -> Path:
    return default_data_dir() / "config.json"


def _known_values(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = {field.name for field in fields(JarvisConfig)}
    return {key: value for key, value in raw.items() if key in allowed}


def load_config(path: Path | None = None) -> JarvisConfig:
    target = path or config_path()
    if target.exists():
        with target.open("r", encoding="utf-8") as config_file:
            raw = json.load(config_file)
        config = JarvisConfig(**_known_values(raw))
    else:
        config = JarvisConfig(codex_workspace=str(repository_root()))
        save_config(config, target)
    config.validate()
    return config


def save_config(config: JarvisConfig, path: Path | None = None) -> Path:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    public_values = asdict(config)
    target.write_text(
        json.dumps(public_values, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return target
