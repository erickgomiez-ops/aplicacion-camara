[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$desktopRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $desktopRoot ".venv310\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "JARVIS no esta instalado."
}

& $python -m jarvis_assistant --diagnose
exit $LASTEXITCODE
