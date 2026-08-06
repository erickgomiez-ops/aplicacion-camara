from pathlib import Path

from jarvis_assistant.wakeword import PRONUNCIATIONS, write_keyword_file


def test_keyword_file_contains_multiple_jarvis_pronunciations(tmp_path: Path) -> None:
    target = write_keyword_file(tmp_path, 1e-20)
    text = target.read_text(encoding="ascii")
    assert len(text.splitlines()) == len(PRONUNCIATIONS)
    assert "jarvish /1e-20/" in text
    assert "jarvisj /1e-20/" in text
