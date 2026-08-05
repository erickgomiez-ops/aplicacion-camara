const normalize = (input: string) =>
  input
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\w\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

const formatTime = () =>
  new Intl.DateTimeFormat("es-MX", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());

const formatDate = () =>
  new Intl.DateTimeFormat("es-MX", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date());

const hasAny = (text: string, words: string[]) => words.some((word) => text.includes(word));

export function answerAsJarvis(rawInput: string): string {
  const input = normalize(rawInput);

  if (!input) {
    return "Estoy en linea, senor. Dame una instruccion y prometo no fingir que no escuche.";
  }

  if (hasAny(input, ["hola", "buenas", "hey", "que tal", "saludos"])) {
    return "Hola, senor. JARVIS Lite en linea. Sistemas estables y actitud ligeramente superior, como debe ser.";
  }

  if (hasAny(input, ["como estas", "como andas", "estado", "sistema"])) {
    return "Operando al cien. Procesador tranquilo, interfaz lista y cero drama tecnico por el momento.";
  }

  if (hasAny(input, ["hora", "que hora"])) {
    return `Son las ${formatTime()}. Tiempo suficiente para hacer algo brillante.`;
  }

  if (hasAny(input, ["fecha", "dia es", "que dia"])) {
    return `Hoy es ${formatDate()}. Lo tengo registrado en el calendario mental.`;
  }

  if (hasAny(input, ["quien eres", "tu nombre", "que eres"])) {
    return "Soy JARVIS Lite: una version web, ligera y obedientemente elegante de tu asistente personal.";
  }

  if (hasAny(input, ["ayuda", "que puedes hacer", "comandos"])) {
    return "Puedo saludarte, decir la hora, la fecha, mi estado, responder preguntas simples, repetir el arranque y quedarme callado cuando me lo pidas.";
  }

  if (hasAny(input, ["gracias", "thank you"])) {
    return "Para eso estoy, senor. Resolver sin hacer escandalo tambien es un talento.";
  }

  if (hasAny(input, ["iron man", "musica", "cancion", "riff", "arranque"])) {
    return "Puedo activar el arranque sonoro. Si agregas tu archivo autorizado en public/audio/iron-man.mp3, lo usare; si no, usare mi riff sintetico original.";
  }

  if (hasAny(input, ["callate", "silencio", "para", "stop"])) {
    return "Modo discreto activado. Bajo el volumen y dejo de hablar.";
  }

  if (hasAny(input, ["chiste", "broma"])) {
    return "Claro. Mi prueba de humanidad: entiendo JavaScript y aun asi decidi seguir funcionando.";
  }

  if (hasAny(input, ["adios", "bye", "descansa", "apagate"])) {
    return "Me quedo en espera, senor. Cuando necesites algo, no hagas desastre: solo llamame.";
  }

  return "No tengo un modelo grande conectado todavia, pero puedo manejar comandos simples. Prueba con hola, hora, fecha, estado o ayuda.";
}
