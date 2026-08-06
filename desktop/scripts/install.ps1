[CmdletBinding()]
param(
    [switch]$SkipModels,
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"
$desktopRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $desktopRoot ".venv310\Scripts\python.exe"
$venvPythonw = Join-Path $desktopRoot ".venv310\Scripts\pythonw.exe"
$codexRoot = Join-Path $desktopRoot "codex-cli"
$localData = Join-Path $env:LOCALAPPDATA "JarvisLocal"
$startupShortcut = Join-Path ([Environment]::GetFolderPath("Startup")) "JARVIS Local.lnk"
$voiceTarget = "HKCU\SOFTWARE\Microsoft\Speech\Voices\Tokens\MSTTS_V110_esMX_RaulMM"
$voiceFlag = Join-Path $localData "voice-registration-created.flag"

Write-Host "[1/7] Preparando Python 3.10..."
if (-not (Test-Path -LiteralPath $venvPython)) {
    & py -3.10 -m venv (Join-Path $desktopRoot ".venv310")
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno de Python 3.10." }
}

Write-Host "[2/7] Instalando el motor local de voz..."
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "No se pudo actualizar pip." }
& $venvPython -m pip install -e "${desktopRoot}[dev]"
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias de JARVIS." }

Write-Host "[3/7] Instalando Codex CLI local..."
& npm.cmd ci --prefix $codexRoot --no-fund --no-audit
if ($LASTEXITCODE -ne 0) { throw "No se pudo instalar Codex CLI." }

Write-Host "[4/7] Preparando la voz nativa de Windows..."
if (Test-Path -LiteralPath $voiceFlag) {
    & reg.exe delete $voiceTarget /f | Out-Null
    Remove-Item -LiteralPath $voiceFlag -Force
}

Write-Host "[5/7] Preparando modelos gratuitos..."
if (-not $SkipModels) {
    & $venvPython -m jarvis_assistant --setup-models
    if ($LASTEXITCODE -ne 0) { throw "No se pudieron preparar los modelos locales." }
} else {
    Write-Host "Modelos omitidos por solicitud."
}

Write-Host "[6/7] Creando inicio automatico con Windows..."
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($startupShortcut)
$shortcut.TargetPath = $venvPythonw
$shortcut.Arguments = "-m jarvis_assistant"
$shortcut.WorkingDirectory = $desktopRoot
$shortcut.Description = "JARVIS Local - asistente privado de voz"
$shortcut.Save()

Write-Host "[7/7] Ejecutando diagnostico..."
& $venvPython -m jarvis_assistant --diagnose
if ($LASTEXITCODE -ne 0) {
    Write-Warning "La instalacion termino, pero uno o mas diagnosticos requieren atencion."
}

if (-not $NoStart) {
    & (Join-Path $PSScriptRoot "start.ps1")
}

Write-Host "JARVIS Local quedo instalado. Diga 'Jarvis' para activarlo."
