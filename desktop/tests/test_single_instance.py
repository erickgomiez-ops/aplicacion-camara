from jarvis_assistant.single_instance import SingleInstance


def test_single_instance_blocks_duplicate() -> None:
    first = SingleInstance("Local\\JarvisLocalAssistantTest")
    second = SingleInstance("Local\\JarvisLocalAssistantTest")
    assert first.acquire() is True
    try:
        assert second.acquire() is False
    finally:
        first.release()
