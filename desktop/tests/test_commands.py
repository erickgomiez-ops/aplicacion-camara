from jarvis_assistant.commands import CommandRouter, normalize
from jarvis_assistant.types import ActionKind


def test_normalize_spanish_text() -> None:
    assert normalize("  ¡SÍ, apágala!  ") == "si apagala"


def test_greeting_is_local() -> None:
    decision = CommandRouter().handle("Hola Jarvis")
    assert decision.action is ActionKind.NONE
    assert decision.spoken


def test_shutdown_requires_confirmation() -> None:
    router = CommandRouter()
    request = router.handle("apaga la laptop", now=10)
    assert request.action is ActionKind.NONE
    assert router.pending is not None

    confirmed = router.handle("sí", now=11)
    assert confirmed.action is ActionKind.POWER
    assert confirmed.payload == "shutdown"
    assert router.pending is None


def test_codex_task_requires_confirmation_and_keeps_original_text() -> None:
    router = CommandRouter()
    request = router.handle("Codex crea una pantalla de pagos", now=20)
    assert request.action is ActionKind.NONE
    assert router.pending is not None
    assert router.pending.payload == "crea una pantalla de pagos"

    confirmed = router.handle("adelante", now=21)
    assert confirmed.action is ActionKind.CODEX_TASK
    assert confirmed.payload == "crea una pantalla de pagos"


def test_pending_action_can_be_cancelled() -> None:
    router = CommandRouter()
    router.handle("reinicia la computadora", now=30)
    cancelled = router.handle("no", now=31)
    assert cancelled.action is ActionKind.NONE
    assert "cancelada" in cancelled.spoken.lower()
    assert router.pending is None


def test_screen_capture_requires_confirmation() -> None:
    router = CommandRouter()
    router.handle("Jarvis, qué ves en mi pantalla", now=40)
    confirmed = router.handle("confirmo", now=41)
    assert confirmed.action is ActionKind.ANALYZE_SCREEN


def test_unknown_command_does_not_execute_anything() -> None:
    decision = CommandRouter().handle("compra cien acciones")
    assert decision.action is ActionKind.NONE
