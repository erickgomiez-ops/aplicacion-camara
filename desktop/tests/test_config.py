import json
from pathlib import Path

from jarvis_assistant.config import JarvisConfig, default_data_dir, load_config, save_config


def test_config_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "config.json"
    config = JarvisConfig(codex_enabled=False, voice_rate=180)
    save_config(config, target)

    loaded = load_config(target)
    assert loaded.voice_rate == 180
    assert loaded.codex_enabled is False


def test_unknown_config_values_are_ignored(tmp_path: Path) -> None:
    target = tmp_path / "config.json"
    target.write_text(json.dumps({"codex_enabled": False, "future_value": 7}), encoding="utf-8")
    loaded = load_config(target)
    assert loaded.codex_enabled is False


def test_config_contains_no_credential_fields() -> None:
    names = set(JarvisConfig.__dataclass_fields__)
    assert not {"api_key", "token", "password"} & names


def test_windows_data_path_avoids_store_virtualization(monkeypatch) -> None:
    monkeypatch.setenv("USERPROFILE", r"C:\Users\test")
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\test\AppData\Local\Packages\Python\LocalCache\Local")
    assert str(default_data_dir()) == r"C:\Users\test\AppData\Local\JarvisLocal"
