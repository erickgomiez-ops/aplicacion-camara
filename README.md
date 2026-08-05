# JARVIS Lite

Asistente web ligero estilo JARVIS, construido con Vite, React y TypeScript.

## Que hace

- Responde a frases simples como `hola`, `hora`, `fecha`, `estado`, `ayuda`, `gracias` y `musica`.
- Habla usando la voz disponible del navegador con un tono bajo tipo asistente.
- Permite escribir comandos o usar el microfono si el navegador soporta reconocimiento de voz.
- Al iniciar intenta reproducir `public/audio/iron-man.mp3`.
- Si no existe ese archivo, reproduce un arranque sintetico original hecho en el navegador.

## Nota legal sobre la cancion

El repositorio no incluye musica con copyright. Si tienes un archivo autorizado de la cancion, colocalo como:

```text
public/audio/iron-man.mp3
```

Los navegadores bloquean audio automatico sin interaccion del usuario, por eso el arranque se activa con el boton `Iniciar`.

## Desarrollo

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Render

El archivo `render.yaml` deja el proyecto listo como Static Site en Render:

- Build Command: `npm ci && npm run build`
- Publish Directory: `dist`
