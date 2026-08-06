from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from .speaker import speech_ssml


def _write(message: dict[str, Any]) -> None:
    sys.stdout.buffer.write((json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()


def _read() -> dict[str, Any] | None:
    line = sys.stdin.buffer.readline()
    if not line:
        return None
    return json.loads(line.decode("utf-8"))


async def run_host(preferred_voice: str) -> int:
    import winsound

    from winrt.windows.media.speechsynthesis import SpeechSynthesizer
    from winrt.windows.storage.streams import DataReader

    synthesizer = SpeechSynthesizer()
    voices = list(SpeechSynthesizer.all_voices)
    preferred = preferred_voice.casefold().strip()
    selected = next(
        (voice for voice in voices if preferred and preferred in voice.display_name.casefold()),
        None,
    )
    if selected is None:
        selected = next(
            (voice for voice in voices if voice.language.casefold() == "es-mx" and "raul" in voice.display_name.casefold()),
            None,
        )
    if selected is None:
        selected = next((voice for voice in voices if voice.language.casefold().startswith("es")), None)
    if selected is not None:
        synthesizer.voice = selected

    _write({
        "ok": True,
        "voice": f"{synthesizer.voice.display_name} - {synthesizer.voice.language}",
    })

    loop = asyncio.get_running_loop()
    while True:
        message = await loop.run_in_executor(None, _read)
        if message is None or message.get("command") == "stop":
            break
        if message.get("command") != "speak":
            _write({"ok": False, "error": "Comando de voz desconocido"})
            continue
        try:
            text = str(message.get("text", ""))
            rate = int(message.get("rate", 172))
            volume = float(message.get("volume", 0.95))
            try:
                stream = await synthesizer.synthesize_ssml_to_stream_async(
                    speech_ssml(text, rate, volume, synthesizer.voice.language)
                )
            except Exception:
                stream = await synthesizer.synthesize_text_to_stream_async(text)
            reader = DataReader(stream.get_input_stream_at(0))
            size = int(stream.size)
            await reader.load_async(size)
            audio = bytearray(size)
            reader.read_bytes(audio)
            winsound.PlaySound(bytes(audio), winsound.SND_MEMORY)
            _write({"ok": True})
        except Exception as error:
            _write({"ok": False, "error": str(error)})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--voice", default="Raul")
    args = parser.parse_args()
    try:
        return asyncio.run(run_host(args.voice))
    except Exception as error:
        _write({"ok": False, "error": str(error)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
