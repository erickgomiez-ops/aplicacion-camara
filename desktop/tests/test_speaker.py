from jarvis_assistant.speaker import speech_ssml, speech_xml


def test_speech_xml_escapes_user_text() -> None:
    assert speech_xml("usa <main> & listo") == '<pitch middle="-2">usa &lt;main&gt; &amp; listo</pitch>'


def test_ssml_uses_spanish_and_bounds_settings() -> None:
    result = speech_ssml("listo & activo", rate=999, volume=4, language="es-MX")
    assert 'xml:lang="es-MX"' in result
    assert 'rate="+35%"' in result
    assert 'volume="100%"' in result
    assert "listo &amp; activo" in result
