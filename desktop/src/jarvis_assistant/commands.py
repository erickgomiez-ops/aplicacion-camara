from __future__ import annotations

import random
import re
import time
import unicodedata
from datetime import datetime

from .types import ActionKind, CommandDecision, PendingAction


CONFIRMATIONS = {"si", "confirmo", "adelante", "hazlo", "procede", "correcto"}
CANCELLATIONS = {"no", "cancela", "cancelar", "olvidalo", "detente", "negativo"}


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ\s]", " ", without_marks)).strip()


class CommandRouter:
    def __init__(self, confirmation_seconds: float = 20.0) -> None:
        self.confirmation_seconds = confirmation_seconds
        self.pending: PendingAction | None = None

    def handle(self, text: str, now: float | None = None) -> CommandDecision:
        current_time = now if now is not None else time.monotonic()
        original = text.strip()
        command = normalize(original)
        command = re.sub(r"^(jarvis|jervis|yarvis)\s+", "", command).strip()
        command = re.sub(r"\s+(jarvis|jervis|yarvis)$", "", command).strip()

        if not command:
            return CommandDecision("No alcancé a escuchar una orden.")

        pending_result = self._handle_pending(command, current_time)
        if pending_result is not None:
            return pending_result

        if any(phrase in command for phrase in ("cancela el apagado", "aborta el apagado", "no apagues")):
            return CommandDecision(
                "Cancelando cualquier apagado o reinicio pendiente.",
                ActionKind.CANCEL_POWER,
            )

        if command in {"hola", "buenas", "hey", "hola jarvis", "buenos dias", "buenas tardes", "buenas noches"}:
            return CommandDecision(random.choice([
                "Hola. Sistemas activos y a su servicio.",
                "Aquí estoy. ¿Qué vamos a construir?",
                "Buenas. Todo funcionando dentro de parámetros razonablemente elegantes.",
            ]))

        if "como estas" in command or command in {"estado", "estado del sistema", "reporte"}:
            return CommandDecision("Revisando el estado del equipo.", ActionKind.SYSTEM_STATUS)

        if re.search(r"\b(hora|que hora)\b", command):
            now_value = datetime.now()
            return CommandDecision(f"Son las {now_value:%H:%M}.")

        if re.search(r"\b(fecha|que dia|dia es hoy)\b", command):
            days = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
            months = [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
            ]
            today = datetime.now()
            return CommandDecision(
                f"Hoy es {days[today.weekday()]} {today.day} de {months[today.month - 1]} de {today.year}."
            )

        if "quien eres" in command or "que eres" in command:
            return CommandDecision(
                "Soy Jarvis Local, su asistente privado para Windows y enlace de voz con Codex."
            )

        if command in {"ayuda", "comandos", "que puedes hacer", "que sabes hacer"}:
            return CommandDecision(
                "Puedo decir la hora y el estado, abrir aplicaciones, controlar volumen, "
                "capturar la pantalla, suspender o apagar con confirmación, y enviar ideas de código a Codex."
            )

        if "gracias" in command:
            return CommandDecision("Para eso estoy.")

        if "chiste" in command:
            return CommandDecision(
                "¿Cuántos programadores hacen falta para cambiar un foco? Ninguno. Es un problema de hardware."
            )

        if command in {"sonido de inicio", "sonido de arranque", "reproduce el arranque", "inicia protocolo"}:
            return CommandDecision("Ejecutando secuencia de arranque.", ActionKind.PLAY_BOOT_SOUND)

        if any(phrase in command for phrase in ("deja de escuchar", "pausa el microfono", "modo privado", "silencio total")):
            return CommandDecision(
                "Micrófono pausado. Puede reactivarme desde el icono junto al reloj.",
                ActionKind.PAUSE_LISTENING,
            )

        volume = self._volume_command(command)
        if volume is not None:
            return volume

        application = self._application_command(command)
        if application is not None:
            return application

        power = self._power_command(command, current_time)
        if power is not None:
            return power

        if any(phrase in command for phrase in (
            "que ves en mi pantalla",
            "mira mi pantalla",
            "analiza mi pantalla",
            "lee mi pantalla",
        )):
            return self._request_confirmation(
                ActionKind.ANALYZE_SCREEN,
                original,
                "Voy a capturar la pantalla actual y compartir esa imagen con Codex para analizarla. ¿Confirmas?",
                current_time,
            )

        codex_task = self._extract_codex_task(original, command)
        if codex_task:
            preview = codex_task if len(codex_task) <= 180 else codex_task[:177] + "..."
            return self._request_confirmation(
                ActionKind.CODEX_TASK,
                codex_task,
                f"Entendí esta tarea para Codex: {preview}. ¿La ejecuto?",
                current_time,
            )

        return CommandDecision(
            "Eso no corresponde a un comando local. Para convertirlo en trabajo de programación, "
            "diga Codex y luego la idea."
        )

    def _handle_pending(self, command: str, current_time: float) -> CommandDecision | None:
        if self.pending is None:
            return None
        pending = self.pending
        if current_time > pending.expires_at:
            self.pending = None
            return CommandDecision("La confirmación expiró. Repita la orden si todavía la necesita.")
        if command in CONFIRMATIONS or command.startswith("si "):
            self.pending = None
            acknowledgements = {
                ActionKind.POWER: "Confirmado. Ejecutando la orden de energía.",
                ActionKind.CODEX_TASK: "Confirmado. Le paso la tarea a Codex y le aviso cuando termine.",
                ActionKind.ANALYZE_SCREEN: "Confirmado. Analizando la pantalla actual.",
            }
            return CommandDecision(
                acknowledgements.get(pending.action, "Confirmado."),
                pending.action,
                pending.payload,
            )
        if command in CANCELLATIONS or command.startswith("no "):
            self.pending = None
            return CommandDecision("Orden cancelada.")
        return CommandDecision("Tengo una acción pendiente. Diga confirmar o cancelar.")

    def _request_confirmation(
        self,
        action: ActionKind,
        payload: str,
        prompt: str,
        current_time: float,
    ) -> CommandDecision:
        self.pending = PendingAction(
            action=action,
            payload=payload,
            prompt=prompt,
            expires_at=current_time + self.confirmation_seconds,
        )
        return CommandDecision(prompt)

    def _power_command(self, command: str, current_time: float) -> CommandDecision | None:
        requested = ""
        if any(phrase in command for phrase in ("apaga la laptop", "apaga la computadora", "apaga el equipo")):
            requested = "shutdown"
            label = "apagar el equipo"
        elif any(phrase in command for phrase in ("reinicia la laptop", "reinicia la computadora", "reinicia el equipo")):
            requested = "restart"
            label = "reiniciar el equipo"
        elif any(phrase in command for phrase in ("suspende la laptop", "suspende la computadora", "modo suspension")):
            requested = "sleep"
            label = "suspender el equipo"
        elif any(phrase in command for phrase in ("bloquea la laptop", "bloquea la computadora", "bloquea la sesion")):
            requested = "lock"
            label = "bloquear la sesión"
        else:
            return None
        return self._request_confirmation(
            ActionKind.POWER,
            requested,
            f"Está a punto de {label}. Diga confirmar o cancelar.",
            current_time,
        )

    @staticmethod
    def _application_command(command: str) -> CommandDecision | None:
        if not re.search(r"\b(abre|inicia|ejecuta)\b", command):
            return None
        applications = {
            "navegador": ("browser", "Abriendo el navegador."),
            "internet": ("browser", "Abriendo el navegador."),
            "chrome": ("chrome", "Abriendo Chrome."),
            "calculadora": ("calculator", "Abriendo la calculadora."),
            "bloc de notas": ("notepad", "Abriendo el bloc de notas."),
            "notas": ("notepad", "Abriendo el bloc de notas."),
            "explorador": ("explorer", "Abriendo el explorador de archivos."),
            "configuracion": ("settings", "Abriendo la configuración."),
            "terminal": ("terminal", "Abriendo la terminal."),
        }
        for phrase, (identifier, response) in applications.items():
            if phrase in command:
                return CommandDecision(response, ActionKind.OPEN_APPLICATION, identifier)
        return None

    @staticmethod
    def _volume_command(command: str) -> CommandDecision | None:
        if "silencia" in command or "quita el sonido" in command or "mute" in command:
            return CommandDecision("Alternando silencio del sistema.", ActionKind.VOLUME, "mute")
        if "sube el volumen" in command:
            return CommandDecision("Subiendo el volumen.", ActionKind.VOLUME, "up")
        if "baja el volumen" in command:
            return CommandDecision("Bajando el volumen.", ActionKind.VOLUME, "down")
        return None

    @staticmethod
    def _extract_codex_task(original: str, normalized: str) -> str:
        prefixes = (
            "codex ",
            "oye codex ",
            "dile a codex ",
            "manda a codex ",
        )
        for prefix in prefixes:
            if normalized.startswith(prefix):
                words_to_remove = len(prefix.split())
                return " ".join(original.split()[words_to_remove:]).strip()
        coding_starts = (
            "implementa ",
            "programa ",
            "arregla el codigo ",
            "modifica el proyecto ",
            "crea en el proyecto ",
        )
        if normalized.startswith(coding_starts):
            return original
        return ""
