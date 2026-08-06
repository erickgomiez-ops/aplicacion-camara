from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path

from .config import JarvisConfig, repository_root


CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
CREATE_NEW_PROCESS_GROUP = 0x00000200 if os.name == "nt" else 0


@dataclass(frozen=True, slots=True)
class CodexResult:
    ok: bool
    response: str
    error: str = ""


class CodexBridge:
    def __init__(self, config: JarvisConfig) -> None:
        self.config = config
        self._lock = threading.Lock()
        self._logger = logging.getLogger(__name__)

    @property
    def busy(self) -> bool:
        return self._lock.locked()

    def command(self) -> list[str]:
        local_script = repository_root() / "desktop" / "codex-cli" / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
        node = shutil.which("node")
        if node and local_script.exists():
            return [node, str(local_script)]

        codex = shutil.which("codex")
        if codex:
            return [codex]
        raise FileNotFoundError(
            "No está instalado el Codex CLI local. Ejecute desktop\\scripts\\install.ps1."
        )

    def login_status(self) -> CodexResult:
        try:
            completed = self._run_process([*self.command(), "login", "status"], timeout=30)
        except (FileNotFoundError, OSError) as error:
            return CodexResult(False, "", str(error))
        output = (completed.stdout or "").strip()
        error = (completed.stderr or "").strip()
        if completed.returncode == 0:
            return CodexResult(True, output or error)
        return CodexResult(False, output, error)

    def run_coding_task(self, user_request: str) -> CodexResult:
        if not self.config.codex_enabled:
            return CodexResult(False, "", "La integración con Codex está desactivada.")
        prompt = coding_prompt(user_request)
        return self._run_exec(
            prompt=prompt,
            workspace=self.config.workspace_path,
            sandbox="workspace-write",
        )

    def health_check(self) -> CodexResult:
        return self._run_exec(
            prompt=(
                "No modifiques archivos ni ejecutes comandos. "
                "Responde únicamente con el texto JARVIS_CODEX_OK."
            ),
            workspace=self.config.workspace_path,
            sandbox="read-only",
        )

    def analyze_screen(self, image_path: Path) -> CodexResult:
        if not self.config.screen_analysis_enabled:
            return CodexResult(False, "", "El análisis de pantalla está desactivado.")
        prompt = (
            "Analiza la captura de pantalla adjunta para el usuario. Responde en español claro y conciso. "
            "Describe qué aplicación o página parece estar abierta, qué información importante se ve y si hay "
            "algún error visible. No inventes texto ilegible. No modifiques archivos ni ejecutes acciones."
        )
        return self._run_exec(
            prompt=prompt,
            workspace=self.config.workspace_path,
            sandbox="read-only",
            image_path=image_path,
        )

    def _run_exec(
        self,
        prompt: str,
        workspace: Path,
        sandbox: str,
        image_path: Path | None = None,
    ) -> CodexResult:
        if not self._lock.acquire(blocking=False):
            return CodexResult(False, "", "Codex ya está trabajando en otra tarea.")
        try:
            command = [
                *self.command(),
                "exec",
                "--ephemeral",
                "--color",
                "never",
                "--sandbox",
                sandbox,
                "-C",
                str(workspace),
            ]
            if image_path is not None:
                # --image accepts multiple values, so terminate it before the positional prompt.
                command.extend(["--image", str(image_path), "--"])
            command.append(prompt)
            completed = self._run_process(command, timeout=self.config.codex_timeout_seconds)
            response = clean_codex_response(completed.stdout or "")
            error = clean_codex_response(completed.stderr or "")
            if completed.returncode != 0:
                self._logger.error("Codex terminó con código %s: %s", completed.returncode, error[-600:])
                return CodexResult(False, response, error or "Codex no pudo completar la tarea.")
            return CodexResult(True, response or "Codex terminó sin devolver un resumen.")
        except subprocess.TimeoutExpired:
            return CodexResult(False, "", "Codex agotó el tiempo máximo de la tarea.")
        except (FileNotFoundError, OSError) as error:
            return CodexResult(False, "", str(error))
        finally:
            self._lock.release()

    def _run_process(self, command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["NO_COLOR"] = "1"
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._terminate_tree(process)
            raise
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)

    @staticmethod
    def _terminate_tree(process: subprocess.Popen[str]) -> None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
                creationflags=CREATE_NO_WINDOW,
            )
        elif process.poll() is None:
            process.kill()


def coding_prompt(user_request: str) -> str:
    return (
        "Estás trabajando a través de JARVIS Local. La siguiente petición fue transcrita desde la voz del "
        "usuario y puede contener pequeños errores de dictado:\n\n"
        f"PETICIÓN DEL USUARIO:\n{user_request.strip()}\n\n"
        "Trabaja únicamente dentro del repositorio actual. Lee y respeta AGENTS.md y las instrucciones del "
        "proyecto. Antes de editar, revisa el estado de Git. Si la petición es ambigua o podría causar un cambio "
        "distinto al solicitado, no adivines: no modifiques nada y devuelve una sola pregunta breve de aclaración. "
        "Si es clara, impleméntala de punta a punta, valida el resultado y deja un resumen breve en español. "
        "No ejecutes órdenes de energía, no accedas a credenciales y no salgas del espacio de trabajo."
    )


def clean_codex_response(text: str) -> str:
    without_ansi = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
    return without_ansi.strip()


def response_for_speech(text: str, max_chars: int) -> str:
    clean = re.sub(r"[`*_#>|]", "", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    if len(clean) <= max_chars:
        return clean
    shortened = clean[:max_chars].rsplit(" ", 1)[0].rstrip(".,;:")
    return shortened + ". El resultado completo quedó guardado en JARVIS."
