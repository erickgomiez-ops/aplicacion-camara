# JARVIS Local para Windows

Asistente de voz privado que corre en segundo plano. El micrófono se procesa localmente; no guarda grabaciones ni transcripciones. Solo una tarea confirmada para Codex usa la sesión de ChatGPT ya iniciada en el equipo.

## Instalación

La forma más sencilla es ejecutar `INSTALAR-JARVIS.cmd`. Desde PowerShell también puede usar:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

La primera instalación descarga aproximadamente unos cientos de MB en modelos gratuitos de activación y reconocimiento. Después, la activación y la transcripción funcionan desde el equipo. No pide API key ni datos de pago.

## Uso

1. Diga `Jarvis` o `Hey Jarvis`.
2. Espere el tono corto.
3. Diga la orden.

También puede hacer doble clic en el icono de JARVIS junto al reloj para escuchar una orden sin usar la frase de activación.

Órdenes incluidas:

- `Hola`, `qué hora es`, `qué día es hoy`, `estado del sistema`.
- `Abre la calculadora`, `abre notas`, `abre el navegador`.
- `Sube el volumen`, `baja el volumen`, `silencia el equipo`.
- `Mira mi pantalla` y después `confirmo`.
- `Codex crea...` y después `confirmo`.
- `Bloquea la laptop`, `suspende la laptop`, `reinicia la laptop` o `apaga la laptop`; todas requieren confirmación.
- `Deja de escuchar`; el micrófono solo se reactiva desde el icono de la bandeja.

## Seguridad y privacidad

- Las acciones de energía, las capturas de pantalla y las tareas para Codex requieren una segunda confirmación.
- Codex queda limitado al repositorio indicado por `codex_workspace` y usa `workspace-write`; el análisis de pantalla usa `read-only`.
- Las capturas se eliminan después del análisis.
- No se guarda audio ni texto dictado.
- La configuración no contiene claves, tokens o contraseñas.
- El último resultado textual de Codex se guarda localmente en `%LOCALAPPDATA%\JarvisLocal\last-codex-response.md`.

## Configuración

El primer inicio crea `%LOCALAPPDATA%\JarvisLocal\config.json`. Desde el icono de JARVIS puede abrirlo para cambiar el micrófono, sensibilidad, voz o proyecto de Codex.

La palabra de activación acepta pronunciación inglesa o mexicana de `Jarvis`. El reconocimiento de órdenes usa Whisper `base` en CPU y está configurado para español.

## Mantenimiento

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\diagnose.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\test.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\uninstall.ps1
```

El sonido de arranque incluido es original y la voz instalada es `Microsoft Raul` ajustada como asistente. No se distribuye la canción de Iron Man ni se clona la voz de un actor.

El desinstalador quita JARVIS del inicio de Windows. Conserva modelos y configuración para no descargar todo nuevamente.
