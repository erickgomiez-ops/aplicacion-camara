from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from .types import AssistantState


STATE_LABELS = {
    AssistantState.STARTING: "Iniciando",
    AssistantState.LISTENING_FOR_WAKE_WORD: "Escuchando 'Jarvis'",
    AssistantState.CAPTURING_COMMAND: "Escuchando orden",
    AssistantState.THINKING: "Procesando",
    AssistantState.CODEX_WORKING: "Codex trabajando",
    AssistantState.SPEAKING: "Respondiendo",
    AssistantState.PAUSED: "Micrófono pausado",
    AssistantState.ERROR: "Requiere atención",
    AssistantState.STOPPED: "Detenido",
}

STATE_COLORS = {
    AssistantState.STARTING: "#e6b84a",
    AssistantState.LISTENING_FOR_WAKE_WORD: "#37d7e8",
    AssistantState.CAPTURING_COMMAND: "#f6f7f8",
    AssistantState.THINKING: "#e6b84a",
    AssistantState.CODEX_WORKING: "#57a6ff",
    AssistantState.SPEAKING: "#76e39a",
    AssistantState.PAUSED: "#7d8790",
    AssistantState.ERROR: "#f06a6a",
    AssistantState.STOPPED: "#353b40",
}


class JarvisTray:
    def __init__(
        self,
        on_toggle_pause: Callable[[], None],
        on_listen_now: Callable[[], None],
        on_test_voice: Callable[[], None],
        on_quit: Callable[[], None],
        config_path: Path,
        logs_dir: Path,
        last_result_path: Path,
    ) -> None:
        self._state = AssistantState.STARTING
        self._on_toggle_pause = on_toggle_pause
        self._on_listen_now = on_listen_now
        self._on_test_voice = on_test_voice
        self._on_quit = on_quit
        self._config_path = config_path
        self._logs_dir = logs_dir
        self._last_result_path = last_result_path
        self._icon = pystray.Icon(
            "jarvis-local",
            self._draw_icon(self._state),
            self._title(),
            menu=pystray.Menu(
                pystray.MenuItem(lambda _: self._title(), None, enabled=False),
                pystray.MenuItem("Escuchar ahora", self._listen_now, default=True),
                pystray.MenuItem(self._pause_label, self._toggle_pause),
                pystray.MenuItem("Probar voz", self._test_voice),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Abrir configuración", self._open_config),
                pystray.MenuItem("Abrir último resultado de Codex", self._open_last_result),
                pystray.MenuItem("Abrir registros", self._open_logs),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Salir", self._quit),
            ),
        )

    def start(self) -> None:
        self._icon.run_detached()

    def stop(self) -> None:
        self._icon.stop()

    def set_state(self, state: AssistantState) -> None:
        self._state = state
        self._icon.icon = self._draw_icon(state)
        self._icon.title = self._title()
        self._icon.update_menu()

    def notify(self, message: str) -> None:
        try:
            self._icon.notify(message, "JARVIS Local")
        except (NotImplementedError, OSError):
            return

    def _title(self) -> str:
        return f"JARVIS Local - {STATE_LABELS[self._state]}"

    def _pause_label(self, _: object) -> str:
        return "Reanudar micrófono" if self._state is AssistantState.PAUSED else "Pausar micrófono"

    def _toggle_pause(self, _: object, __: object) -> None:
        self._on_toggle_pause()

    def _listen_now(self, _: object, __: object) -> None:
        self._on_listen_now()

    def _test_voice(self, _: object, __: object) -> None:
        self._on_test_voice()

    def _open_config(self, _: object, __: object) -> None:
        os.startfile(self._config_path)

    def _open_logs(self, _: object, __: object) -> None:
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(self._logs_dir)

    def _open_last_result(self, _: object, __: object) -> None:
        if self._last_result_path.exists():
            os.startfile(self._last_result_path)
        else:
            self.notify("Todavía no hay un resultado de Codex guardado.")

    def _quit(self, _: object, __: object) -> None:
        self._on_quit()

    @staticmethod
    def _draw_icon(state: AssistantState) -> Image.Image:
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        color = STATE_COLORS[state]
        draw.ellipse((6, 6, 58, 58), fill="#10171b", outline=color, width=4)
        draw.ellipse((17, 17, 47, 47), outline=color, width=3)
        draw.ellipse((26, 26, 38, 38), fill=color)
        return image
