from __future__ import annotations

import ctypes
import os
import subprocess
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psutil
from PIL import ImageGrab


CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


@dataclass(frozen=True, slots=True)
class SystemStatus:
    cpu_percent: float
    memory_percent: float
    battery_percent: float | None
    plugged_in: bool | None

    def for_speech(self) -> str:
        parts = [
            f"Procesador al {self.cpu_percent:.0f} por ciento",
            f"memoria al {self.memory_percent:.0f} por ciento",
        ]
        if self.battery_percent is not None:
            charging = "y cargando" if self.plugged_in else ""
            parts.append(f"batería al {self.battery_percent:.0f} por ciento {charging}".strip())
        return ", ".join(parts) + "."


class WindowsActions:
    def system_status(self) -> SystemStatus:
        battery = psutil.sensors_battery()
        return SystemStatus(
            cpu_percent=psutil.cpu_percent(interval=0.2),
            memory_percent=psutil.virtual_memory().percent,
            battery_percent=battery.percent if battery else None,
            plugged_in=battery.power_plugged if battery else None,
        )

    def open_application(self, identifier: str) -> bool:
        try:
            if identifier == "browser":
                return webbrowser.open("https://www.google.com")
            if identifier == "chrome":
                self._spawn(["chrome.exe"])
            elif identifier == "calculator":
                self._spawn(["calc.exe"])
            elif identifier == "notepad":
                self._spawn(["notepad.exe"])
            elif identifier == "explorer":
                self._spawn(["explorer.exe"])
            elif identifier == "settings":
                os.startfile("ms-settings:")
            elif identifier == "terminal":
                try:
                    self._spawn(["wt.exe"])
                except OSError:
                    self._spawn(["powershell.exe"])
            else:
                return False
            return True
        except OSError:
            return False

    def change_volume(self, direction: str) -> bool:
        keys = {"mute": 0xAD, "down": 0xAE, "up": 0xAF}
        virtual_key = keys.get(direction)
        if virtual_key is None or os.name != "nt":
            return False
        key_up = 0x0002
        ctypes.windll.user32.keybd_event(virtual_key, 0, 0, 0)
        ctypes.windll.user32.keybd_event(virtual_key, 0, key_up, 0)
        return True

    def power(self, action: str) -> bool:
        if action == "shutdown":
            self._spawn([
                "shutdown.exe", "/s", "/t", "30", "/c",
                "Apagado confirmado por JARVIS. Use 'shutdown /a' para cancelar.",
            ])
        elif action == "restart":
            self._spawn([
                "shutdown.exe", "/r", "/t", "30", "/c",
                "Reinicio confirmado por JARVIS. Use 'shutdown /a' para cancelar.",
            ])
        elif action == "sleep":
            if os.name != "nt":
                return False
            result = ctypes.windll.powrprof.SetSuspendState(False, False, False)
            return bool(result)
        elif action == "lock":
            if os.name != "nt":
                return False
            return bool(ctypes.windll.user32.LockWorkStation())
        else:
            return False
        return True

    def cancel_power(self) -> bool:
        completed = subprocess.run(
            ["shutdown.exe", "/a"],
            capture_output=True,
            check=False,
            creationflags=CREATE_NO_WINDOW,
        )
        return completed.returncode == 0

    def capture_screen(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / f"screen-{datetime.now():%Y%m%d-%H%M%S}.png"
        image = ImageGrab.grab(all_screens=True)
        image.save(target, format="PNG", optimize=True)
        self._trim_screenshots(output_dir)
        return target

    @staticmethod
    def _trim_screenshots(output_dir: Path, keep: int = 10) -> None:
        screenshots = sorted(output_dir.glob("screen-*.png"), key=lambda path: path.stat().st_mtime)
        for old_path in screenshots[:-keep]:
            old_path.unlink(missing_ok=True)

    @staticmethod
    def _spawn(command: list[str]) -> None:
        subprocess.Popen(
            command,
            creationflags=CREATE_NO_WINDOW,
            close_fds=True,
        )
