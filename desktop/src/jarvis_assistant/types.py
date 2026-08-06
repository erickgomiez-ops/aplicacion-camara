from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class AssistantState(Enum):
    STARTING = auto()
    LISTENING_FOR_WAKE_WORD = auto()
    CAPTURING_COMMAND = auto()
    THINKING = auto()
    CODEX_WORKING = auto()
    SPEAKING = auto()
    PAUSED = auto()
    ERROR = auto()
    STOPPED = auto()


class ActionKind(Enum):
    NONE = auto()
    SYSTEM_STATUS = auto()
    OPEN_APPLICATION = auto()
    VOLUME = auto()
    PLAY_BOOT_SOUND = auto()
    PAUSE_LISTENING = auto()
    POWER = auto()
    CANCEL_POWER = auto()
    CODEX_TASK = auto()
    ANALYZE_SCREEN = auto()


@dataclass(frozen=True, slots=True)
class CommandDecision:
    spoken: str
    action: ActionKind = ActionKind.NONE
    payload: str = ""


@dataclass(frozen=True, slots=True)
class PendingAction:
    action: ActionKind
    payload: str
    prompt: str
    expires_at: float
