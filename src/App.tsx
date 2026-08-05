import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Mic, Pause, Play, Power, Send, Volume2 } from "lucide-react";
import { playStartupAudio, stopStartupAudio } from "./audio";
import { answerAsJarvis } from "./jarvisBrain";
import { createSpeechRecognition } from "./speechRecognition";
import { AssistantStatus, ChatMessage } from "./types";
import { speakLikeJarvis, stopSpeech } from "./voice";

const initialMessages: ChatMessage[] = [
  {
    id: "system-boot",
    role: "system",
    text: "Sistema listo. Pulsa iniciar para activar JARVIS Lite.",
    timestamp: "standby",
  },
];

const nowLabel = () =>
  new Intl.DateTimeFormat("es-MX", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());

const createMessage = (role: ChatMessage["role"], text: string): ChatMessage => ({
  id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2)}`,
  role,
  text,
  timestamp: nowLabel(),
});

export function App() {
  const [status, setStatus] = useState<AssistantStatus>("offline");
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [input, setInput] = useState("");
  const [bootNote, setBootNote] = useState("Esperando activacion manual.");
  const [audioEnabled, setAudioEnabled] = useState(true);
  const recognitionRef = useRef<ReturnType<typeof createSpeechRecognition>>(null);
  const transcriptEndRef = useRef<HTMLDivElement>(null);

  const statusLabel = useMemo(() => {
    const labels: Record<AssistantStatus, string> = {
      offline: "En espera",
      booting: "Inicializando",
      online: "En linea",
      listening: "Escuchando",
      speaking: "Respondiendo",
    };

    return labels[status];
  }, [status]);

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const bootAssistant = async () => {
    setStatus("booting");
    const note = await playStartupAudio();
    setBootNote(note);
    const greeting =
      "Buenos dias, senor. JARVIS Lite esta despierto, calibrado y peligrosamente funcional.";

    setMessages((current) => [...current, createMessage("assistant", greeting)]);
    setStatus("speaking");
    speakLikeJarvis(greeting, () => setStatus("online"));
  };

  const handlePrompt = useCallback((prompt: string) => {
    const userMessage = createMessage("user", prompt);
    const answer = answerAsJarvis(prompt);
    const assistantMessage = createMessage("assistant", answer);

    setMessages((current) => [...current, userMessage, assistantMessage]);

    if (prompt.toLowerCase().includes("silencio") || prompt.toLowerCase().includes("callate")) {
      stopSpeech();
      stopStartupAudio();
      setStatus("online");
      return;
    }

    if (prompt.toLowerCase().includes("arranque") || prompt.toLowerCase().includes("musica")) {
      void playStartupAudio().then(setBootNote);
    }

    if (audioEnabled) {
      setStatus("speaking");
      speakLikeJarvis(answer, () => setStatus("online"));
    }
  }, [audioEnabled]);

  useEffect(() => {
    const recognition = createSpeechRecognition();
    recognitionRef.current = recognition;

    if (!recognition) {
      return;
    }

    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript ?? "";
      setStatus("online");
      if (transcript) {
        handlePrompt(transcript);
      }
    };
    recognition.onerror = () => setStatus("online");
    recognition.onend = () => {
      setStatus((current) => (current === "listening" ? "online" : current));
    };

    return () => recognition.abort();
  }, [handlePrompt]);

  const submitPrompt = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const prompt = input.trim();

    if (!prompt) {
      return;
    }

    setInput("");
    handlePrompt(prompt);
  };

  const startListening = () => {
    const recognition = recognitionRef.current;

    if (!recognition) {
      const answer = "Tu navegador no tiene reconocimiento de voz disponible. Escribe la orden y seguimos.";
      setMessages((current) => [...current, createMessage("assistant", answer)]);
      if (audioEnabled) {
        speakLikeJarvis(answer, () => setStatus("online"));
      }
      return;
    }

    setStatus("listening");
    recognition.start();
  };

  const toggleAudio = () => {
    const nextValue = !audioEnabled;
    setAudioEnabled(nextValue);

    if (!nextValue) {
      stopSpeech();
      stopStartupAudio();
      setStatus("online");
    }
  };

  return (
    <main className="app-shell">
      <section className="command-surface" aria-label="JARVIS Lite">
        <div className="topline">
          <div>
            <p className="eyebrow">JARVIS Lite</p>
            <h1>Asistente personal activo</h1>
          </div>
          <span className={`status-pill status-${status}`}>{statusLabel}</span>
        </div>

        <div className="workspace">
          <div className="reactor-panel" aria-hidden="true">
            <div className={`reactor-core ${status}`}>
              <span />
              <span />
              <span />
            </div>
            <div className="metrics-strip">
              <strong>CORE</strong>
              <span>local rules</span>
              <span>voice synth</span>
            </div>
          </div>

          <div className="transcript-panel">
            <div className="transcript">
              {messages.map((message) => (
                <article className={`message ${message.role}`} key={message.id}>
                  <div className="message-meta">
                    <span>{message.role === "user" ? "Tu" : message.role === "system" ? "Sistema" : "JARVIS"}</span>
                    <time>{message.timestamp}</time>
                  </div>
                  <p>{message.text}</p>
                </article>
              ))}
              <div ref={transcriptEndRef} />
            </div>

            <form className="command-bar" onSubmit={submitPrompt}>
              <input
                aria-label="Escribe una orden para JARVIS"
                disabled={status === "offline"}
                onChange={(event) => setInput(event.target.value)}
                placeholder={status === "offline" ? "Primero inicia el sistema" : "Prueba: hola, hora, fecha, estado..."}
                value={input}
              />
              <button className="icon-button" disabled={status === "offline"} title="Enviar orden" type="submit">
                <Send size={20} />
              </button>
              <button
                className="icon-button"
                disabled={status === "offline" || status === "speaking"}
                onClick={startListening}
                title="Hablar con JARVIS"
                type="button"
              >
                <Mic size={20} />
              </button>
            </form>
          </div>
        </div>

        <div className="control-row">
          <button className="primary-action" disabled={status !== "offline"} onClick={bootAssistant} type="button">
            <Power size={20} />
            Iniciar
          </button>
          <button className="secondary-action" onClick={() => void playStartupAudio().then(setBootNote)} type="button">
            <Play size={20} />
            Arranque
          </button>
          <button className="secondary-action" onClick={toggleAudio} type="button">
            {audioEnabled ? <Volume2 size={20} /> : <Pause size={20} />}
            Voz {audioEnabled ? "activa" : "pausada"}
          </button>
          <p className="boot-note">{bootNote}</p>
        </div>
      </section>
    </main>
  );
}
