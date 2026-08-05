let currentTrack: HTMLAudioElement | null = null;

const playTone = (
  audioContext: AudioContext,
  start: number,
  frequency: number,
  duration: number,
  gainValue: number,
) => {
  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();

  oscillator.type = "sawtooth";
  oscillator.frequency.setValueAtTime(frequency, start);
  oscillator.frequency.exponentialRampToValueAtTime(frequency * 0.98, start + duration);

  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(gainValue, start + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);

  oscillator.connect(gain);
  gain.connect(audioContext.destination);
  oscillator.start(start);
  oscillator.stop(start + duration + 0.02);
};

export function stopStartupAudio() {
  if (currentTrack) {
    currentTrack.pause();
    currentTrack.currentTime = 0;
    currentTrack = null;
  }
}

export async function playStartupAudio() {
  stopStartupAudio();

  try {
    const response = await fetch("/audio/iron-man.mp3", { method: "HEAD", cache: "no-store" });

    if (response.ok) {
      currentTrack = new Audio("/audio/iron-man.mp3");
      currentTrack.volume = 0.72;
      await currentTrack.play();
      return "Reproduciendo pista de arranque autorizada.";
    }
  } catch {
    // If the file is unavailable, the synthetic boot riff keeps startup responsive.
  }

  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  const audioContext = new AudioContextClass();
  const now = audioContext.currentTime;
  const notes = [82.41, 98, 110, 123.47, 110, 98];

  notes.forEach((note, index) => {
    playTone(audioContext, now + index * 0.18, note, 0.14, 0.12);
    playTone(audioContext, now + index * 0.18, note * 2, 0.1, 0.045);
  });

  playTone(audioContext, now + 1.25, 65.41, 0.55, 0.16);
  window.setTimeout(() => void audioContext.close(), 2400);

  return "Pista autorizada no encontrada. Use arranque sintetico original.";
}
