@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install.ps1"
if errorlevel 1 (
  echo.
  echo La instalacion encontro un error. Revise el mensaje anterior.
  pause
  exit /b 1
)
echo.
echo JARVIS Local esta listo.
pause
