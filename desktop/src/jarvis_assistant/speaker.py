from __future__ import annotations

import json
import logging
import os
import queue
import subprocess
import sys
import threading
from dataclasses import dataclass
from html import escape


CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


@dataclass(slots=True)
class _SpeechRequest:
    text: str
    finished: threading.Event


class LocalSpeaker:
    def __init__(
        self,
        preferred_voice: str = "Raul",
        rate: int = 172,
        volume: float = 0.95,
    ) -> None:
        self.preferred_voice = preferred_voice
        self.rate = rate
        self.volume = volume
        self.speaking = threading.Event()
        self._ready = threading.Event()
        self._requests: queue.Queue[_SpeechRequest | None] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._process: subprocess.Popen[str] | None = None
        self._logger = logging.getLogger(__name__)
        self._voice_description = ""
        self._startup_error: Exception | None = None

    @property
    def voice_description(self) -> str:
        return self._voice_description

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._worker, name="jarvis-voice", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=15):
            self._terminate_voice_host()
            raise RuntimeError("El motor de voz no respondió")
        if self._startup_error:
            raise RuntimeError("No se pudo iniciar la voz local") from self._startup_error

    def speak(self, text: str, block: bool = True, timeout: float = 120.0) -> bool:
        clean_text = " ".join(text.split()).strip()
        if not clean_text:
            return True
        self.start()
        finished = threading.Event()
        self._requests.put(_SpeechRequest(clean_text, finished))
        return finished.wait(timeout=timeout) if block else True

    def stop(self) -> None:
        if not self._thread:
            return
        self._requests.put(None)
        self._thread.join(timeout=5)
        self._terminate_voice_host()
        self._thread = None

    def _worker(self) -> None:
        try:
            self._voice_host_worker()
        except Exception as host_error:
            self._logger.warning("El host de voz nativo falló; se usará SAPI: %s", host_error)
            self._terminate_voice_host()
            try:
                self._sapi_worker()
            except Exception as sapi_error:
                self._startup_error = sapi_error
                self._logger.exception("No se pudo iniciar ningún motor de voz")
                self._ready.set()
                self._finish_waiting_requests()

    def _voice_host_worker(self) -> None:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "jarvis_assistant.voice_host",
                "--voice",
                self.preferred_voice,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=CREATE_NO_WINDOW,
        )
        self._process = process
        if process.stdout is None or process.stdin is None:
            raise RuntimeError("No se pudo abrir el canal del host de voz")
        ready_line = process.stdout.readline()
        if not ready_line:
            raise RuntimeError("El host de voz terminó durante el arranque")
        ready = json.loads(ready_line)
        if not ready.get("ok"):
            raise RuntimeError(str(ready.get("error", "La voz nativa no está disponible")))
        self._voice_description = str(ready.get("voice", "Voz nativa de Windows"))
        self._ready.set()

        while True:
            request = self._requests.get()
            if request is None:
                self._send_host({"command": "stop"})
                process.wait(timeout=5)
                break
            self.speaking.set()
            try:
                self._send_host({
                    "command": "speak",
                    "text": request.text,
                    "rate": self.rate,
                    "volume": self.volume,
                })
                response_line = process.stdout.readline()
                if not response_line:
                    raise RuntimeError("El host de voz dejó de responder")
                response = json.loads(response_line)
                if not response.get("ok"):
                    raise RuntimeError(str(response.get("error", "No se pudo reproducir la voz")))
            except Exception:
                self._logger.exception("No se pudo reproducir una respuesta de voz")
            finally:
                self.speaking.clear()
                request.finished.set()

    def _send_host(self, message: dict[str, object]) -> None:
        if self._process is None or self._process.stdin is None:
            raise RuntimeError("El host de voz no está activo")
        self._process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self._process.stdin.flush()

    def _sapi_worker(self) -> None:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        tokens = list(voice.GetVoices())
        preferred = self.preferred_voice.casefold().strip()
        selected = next(
            (token for token in tokens if preferred and preferred in token.GetDescription().casefold()),
            None,
        )
        if selected is None:
            selected = next(
                (token for token in tokens if "spanish" in token.GetDescription().casefold()),
                tokens[0] if tokens else None,
            )
        if selected is not None:
            voice.Voice = selected
        voice.Rate = max(-4, min(3, round((self.rate - 180) / 12)))
        voice.Volume = max(0, min(100, round(self.volume * 100)))
        self._voice_description = voice.Voice.GetDescription()
        self._ready.set()

        while True:
            request = self._requests.get()
            if request is None:
                break
            self.speaking.set()
            try:
                voice.Speak(request.text)
            finally:
                self.speaking.clear()
                request.finished.set()
        pythoncom.CoUninitialize()

    def _terminate_voice_host(self) -> None:
        process = self._process
        self._process = None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()

    def _finish_waiting_requests(self) -> None:
        while True:
            try:
                request = self._requests.get_nowait()
            except queue.Empty:
                break
            if request is not None:
                request.finished.set()


def speech_ssml(text: str, rate: int = 172, volume: float = 0.95, language: str = "es-MX") -> str:
    rate_percent = max(-35, min(35, round((rate - 180) / 180 * 100)))
    volume_percent = max(0, min(100, round(volume * 100)))
    clean_text = escape(" ".join(text.split()))
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{escape(language)}">'
        f'<prosody rate="{rate_percent:+d}%" pitch="-8%" volume="{volume_percent}%">'
        f"{clean_text}</prosody></speak>"
    )


def speech_xml(text: str) -> str:
    return f'<pitch middle="-2">{escape(" ".join(text.split()))}</pitch>'
