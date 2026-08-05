const preferredVoiceKeywords = [
  "es-mx",
  "sabina",
  "jorge",
  "dalia",
  "microsoft david",
  "microsoft mark",
  "google us english",
  "english",
];

export function getBestVoice(): SpeechSynthesisVoice | null {
  if (!("speechSynthesis" in window)) {
    return null;
  }

  const voices = window.speechSynthesis.getVoices();

  return (
    voices.find((voice) =>
      preferredVoiceKeywords.some((keyword) =>
        `${voice.lang} ${voice.name}`.toLowerCase().includes(keyword),
      ),
    ) ?? voices[0] ?? null
  );
}

export function speakLikeJarvis(text: string, onEnd?: () => void) {
  if (!("speechSynthesis" in window)) {
    onEnd?.();
    return;
  }

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  const voice = getBestVoice();

  if (voice) {
    utterance.voice = voice;
    utterance.lang = voice.lang;
  } else {
    utterance.lang = "es-MX";
  }

  utterance.pitch = 0.78;
  utterance.rate = 0.92;
  utterance.volume = 1;
  utterance.onend = () => onEnd?.();
  utterance.onerror = () => onEnd?.();

  window.speechSynthesis.speak(utterance);
}

export function stopSpeech() {
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}
