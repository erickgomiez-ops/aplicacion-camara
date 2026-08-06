import subprocess

from jarvis_assistant.codex_bridge import CodexBridge, coding_prompt, clean_codex_response, response_for_speech
from jarvis_assistant.config import JarvisConfig


def test_coding_prompt_contains_guardrails_and_request() -> None:
    prompt = coding_prompt("crea un botón de pago")
    assert "crea un botón de pago" in prompt
    assert "únicamente dentro del repositorio" in prompt
    assert "no adivines" in prompt


def test_clean_codex_response_removes_terminal_colors() -> None:
    assert clean_codex_response("\x1b[32mlisto\x1b[0m\n") == "listo"


def test_response_for_speech_is_bounded() -> None:
    result = response_for_speech("palabra " * 200, 80)
    assert len(result) < 140
    assert "resultado completo" in result


def test_image_option_is_terminated_before_prompt(monkeypatch, tmp_path) -> None:
    bridge = CodexBridge(JarvisConfig(codex_workspace=str(tmp_path)))
    captured: list[str] = []

    monkeypatch.setattr(bridge, "command", lambda: ["codex"])

    def fake_run(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        del timeout
        captured.extend(command)
        return subprocess.CompletedProcess(command, 0, "pantalla lista", "")

    monkeypatch.setattr(bridge, "_run_process", fake_run)
    result = bridge.analyze_screen(tmp_path / "screen.png")

    assert result.ok
    image_index = captured.index("--image")
    assert captured[image_index + 2] == "--"
    assert captured[-1].startswith("Analiza la captura")
