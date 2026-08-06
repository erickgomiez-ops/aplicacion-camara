from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .audio_input import MicrophoneStream
from .chimes import ensure_chimes, play_chime
from .codex_bridge import CodexBridge, CodexResult, response_for_speech
from .commands import CommandRouter
from .config import JarvisConfig, config_path
from .speaker import LocalSpeaker
from .system_actions import WindowsActions
from .transcription import LocalTranscriber
from .tray import JarvisTray
from .types import ActionKind, AssistantState, CommandDecision
from .wakeword import WakeWordDetector


class JarvisAssistant:
    def __init__(self, config: JarvisConfig) -> None:
        self.config = config
        self._logger = logging.getLogger(__name__)
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._manual_trigger = threading.Event()
        self._interaction_lock = threading.Lock()
        self._microphone_lock = threading.Lock()
        self._state = AssistantState.STARTING
        self._last_activation = 0.0
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="jarvis-task")

        self.chimes = ensure_chimes(config.data_dir)
        self.router = CommandRouter()
        self.microphone = MicrophoneStream(config.input_device)
        self.detector = WakeWordDetector(config.models_dir, config.wake_keyword_threshold)
        self.transcriber = LocalTranscriber(
            config.models_dir,
            config.whisper_model,
            config.whisper_compute_type,
            config.language,
        )
        self.speaker = LocalSpeaker(
            config.voice_name_contains,
            config.voice_rate,
            config.voice_volume,
        )
        self.actions = WindowsActions()
        self.codex = CodexBridge(config)
        self.last_result_path = config.data_dir / "last-codex-response.md"
        self.tray = JarvisTray(
            on_toggle_pause=self.toggle_pause,
            on_listen_now=self.listen_now,
            on_test_voice=self.test_voice,
            on_quit=self.stop,
            config_path=config_path(),
            logs_dir=config.logs_dir,
            last_result_path=self.last_result_path,
        )

    def run(self) -> None:
        self._logger.info("Iniciando JARVIS Local")
        self.tray.start()
        try:
            self._set_state(AssistantState.STARTING)
            self.speaker.start()
            play_chime(self.chimes["boot"])
            self._speak(
                "JARVIS Local en línea. Diga Jarvis cuando me necesite."
            )
            self._executor.submit(self._warm_transcriber)
            self._start_microphone()
            self._set_state(AssistantState.LISTENING_FOR_WAKE_WORD)
            self._logger.info("JARVIS está escuchando la palabra de activación")
            self._listen_loop()
        except Exception:
            self._logger.exception("JARVIS terminó por un error")
            self._set_state(AssistantState.ERROR)
            self.tray.notify("JARVIS encontró un error. Revise los registros.")
            raise
        finally:
            self._shutdown_components()

    def stop(self) -> None:
        self._stop.set()

    def toggle_pause(self) -> None:
        if self._paused.is_set():
            self.resume_listening()
        else:
            self.pause_listening()

    def pause_listening(self) -> None:
        self._paused.set()
        with self._microphone_lock:
            self.microphone.stop()
        self._set_state(AssistantState.PAUSED)

    def resume_listening(self) -> None:
        try:
            with self._microphone_lock:
                self.microphone.start()
            self._paused.clear()
            self._set_state(AssistantState.LISTENING_FOR_WAKE_WORD)
            self.tray.notify("Micrófono reactivado.")
        except Exception:
            self._logger.exception("No se pudo reactivar el micrófono")
            self._set_state(AssistantState.ERROR)

    def listen_now(self) -> None:
        if self._paused.is_set():
            self.resume_listening()
        self._manual_trigger.set()

    def test_voice(self) -> None:
        self._executor.submit(self._speak, "Prueba de voz completada. Todos los sistemas responden.")

    def process_text(self, text: str) -> CommandDecision:
        return self.router.handle(text)

    def _listen_loop(self) -> None:
        while not self._stop.is_set():
            if self._paused.is_set():
                self._stop.wait(0.25)
                continue
            if self.speaker.speaking.is_set():
                self.microphone.clear()
                self._stop.wait(0.08)
                continue
            if self._manual_trigger.is_set():
                self._manual_trigger.clear()
                self._handle_activation()
                continue
            chunk = self.microphone.read(timeout=0.4)
            if chunk is None:
                continue
            if time.monotonic() - self._last_activation < self.config.wake_cooldown_seconds:
                continue
            keyword = self.detector.detected_keyword(chunk)
            if keyword:
                self._handle_activation(keyword)

    def _handle_activation(self, activation_keyword: str = "") -> None:
        if not self._interaction_lock.acquire(blocking=False):
            return
        try:
            self._last_activation = time.monotonic()
            self._set_state(AssistantState.CAPTURING_COMMAND)
            play_chime(self.chimes["wake"])
            if activation_keyword in {"holaa", "olaa"}:
                self._logger.info("Saludo directo detectado")
                self._execute_decision(self.router.handle("hola"))
                return
            self._logger.info("Capturando orden de voz")
            capture = self.microphone.capture_utterance(
                max_seconds=self.config.command_max_seconds,
                silence_seconds=self.config.command_silence_seconds,
                minimum_rms=self.config.microphone_rms_threshold,
            )
            self._logger.info(
                "Captura terminada: speech=%s, duracion=%.2fs, threshold=%.1f",
                capture.speech_detected,
                capture.duration_seconds,
                capture.threshold,
            )
            if not capture.speech_detected:
                self._speak("No escuché una orden. Inténtelo de nuevo.")
                return

            self._set_state(AssistantState.THINKING)
            text = self.transcriber.transcribe(capture.audio)
            self._logger.info("Orden transcrita: %r", text)
            if not text:
                self._speak("No pude entender la orden.")
                return
            decision = self.router.handle(text)
            self._logger.info("Decision local: action=%s, spoken=%r", decision.action.value, decision.spoken)
            self._execute_decision(decision)
        except Exception:
            self._logger.exception("Falló el procesamiento de una orden de voz")
            play_chime(self.chimes["error"])
            self._speak("Encontré un error procesando la orden. Revise el registro local.")
        finally:
            self.microphone.clear()
            self._interaction_lock.release()
            if not self._paused.is_set() and not self._stop.is_set():
                self._set_state(
                    AssistantState.CODEX_WORKING if self.codex.busy else AssistantState.LISTENING_FOR_WAKE_WORD
                )

    def _execute_decision(self, decision: CommandDecision) -> None:
        if decision.action is ActionKind.NONE:
            self._speak(decision.spoken)
            return
        if decision.action is ActionKind.SYSTEM_STATUS:
            self._speak(self.actions.system_status().for_speech())
        elif decision.action is ActionKind.OPEN_APPLICATION:
            self._speak(decision.spoken)
            if not self.actions.open_application(decision.payload):
                self._speak("No pude abrir esa aplicación.")
        elif decision.action is ActionKind.VOLUME:
            self.actions.change_volume(decision.payload)
            self._speak(decision.spoken)
        elif decision.action is ActionKind.PLAY_BOOT_SOUND:
            self._speak(decision.spoken)
            play_chime(self.chimes["boot"])
        elif decision.action is ActionKind.PAUSE_LISTENING:
            self._speak(decision.spoken)
            self.pause_listening()
        elif decision.action is ActionKind.CANCEL_POWER:
            cancelled = self.actions.cancel_power()
            self._speak(decision.spoken if cancelled else "No había un apagado pendiente que cancelar.")
        elif decision.action is ActionKind.POWER:
            self._speak(decision.spoken)
            if not self.actions.power(decision.payload):
                self._speak("Windows rechazó la orden de energía.")
        elif decision.action is ActionKind.CODEX_TASK:
            if self.codex.busy:
                self._speak("Codex ya está trabajando. Espere a que termine antes de enviar otra tarea.")
            else:
                self._speak(decision.spoken)
                self._set_state(AssistantState.CODEX_WORKING)
                self._executor.submit(self._run_codex_task, decision.payload)
        elif decision.action is ActionKind.ANALYZE_SCREEN:
            if self.codex.busy:
                self._speak("Codex está ocupado. Inténtelo de nuevo cuando termine.")
            else:
                self._speak(decision.spoken)
                self._set_state(AssistantState.CODEX_WORKING)
                self._executor.submit(self._run_screen_analysis)

    def _run_codex_task(self, task: str) -> None:
        result = self.codex.run_coding_task(task)
        self._announce_codex_result(result, "Codex terminó la tarea.")

    def _run_screen_analysis(self) -> None:
        screenshot: Path | None = None
        try:
            screenshot = self.actions.capture_screen(self.config.screenshots_dir)
            result = self.codex.analyze_screen(screenshot)
            self._announce_codex_result(result, "Terminé de revisar la pantalla.")
        except Exception as error:
            self._logger.exception("No se pudo analizar la pantalla")
            self._announce_codex_result(CodexResult(False, "", str(error)), "")
        finally:
            if screenshot is not None:
                screenshot.unlink(missing_ok=True)

    def _announce_codex_result(self, result: CodexResult, success_prefix: str) -> None:
        with self._interaction_lock:
            if result.ok:
                self.last_result_path.parent.mkdir(parents=True, exist_ok=True)
                self.last_result_path.write_text(result.response + "\n", encoding="utf-8")
                play_chime(self.chimes["done"])
                spoken_result = response_for_speech(result.response, self.config.speak_codex_max_chars)
                self._speak(f"{success_prefix} {spoken_result}".strip())
                self.tray.notify(success_prefix)
            else:
                play_chime(self.chimes["error"])
                reason = response_for_speech(result.error or "Error desconocido.", 260)
                self._speak(f"Codex no pudo completar la solicitud. {reason}")
                self.tray.notify("Codex no pudo completar la solicitud.")
            if not self._paused.is_set():
                self._set_state(AssistantState.LISTENING_FOR_WAKE_WORD)

    def _speak(self, text: str) -> None:
        self._set_state(AssistantState.SPEAKING)
        self.speaker.speak(text, block=True)
        self.microphone.clear()

    def _warm_transcriber(self) -> None:
        try:
            self.transcriber.warm_up()
        except Exception:
            self._logger.exception("No se pudo precargar Whisper")
            self.tray.notify("No se pudo preparar el reconocimiento de voz.")

    def _start_microphone(self) -> None:
        with self._microphone_lock:
            self.microphone.start()

    def _set_state(self, state: AssistantState) -> None:
        self._state = state
        self.tray.set_state(state)

    def _shutdown_components(self) -> None:
        self._logger.info("Deteniendo JARVIS Local")
        self._stop.set()
        with self._microphone_lock:
            self.microphone.stop()
        self.speaker.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
        self._set_state(AssistantState.STOPPED)
        self.tray.stop()
