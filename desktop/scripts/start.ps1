[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$desktopRoot = Split-Path -Parent $PSScriptRoot
$pythonw = Join-Path $desktopRoot ".venv310\Scripts\pythonw.exe"
$pidPath = Join-Path $env:LOCALAPPDATA "JarvisLocal\jarvis.pid"

if (-not (Test-Path -LiteralPath $pythonw)) {
    throw "JARVIS no esta instalado. Ejecute primero desktop\scripts\install.ps1."
}

if (Test-Path -LiteralPath $pidPath) {
    $existingPid = (Get-Content -LiteralPath $pidPath -Raw).Trim()
    if ($existingPid -match "^\d+$") {
        $existingProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $existingPid" -ErrorAction SilentlyContinue
        if ($existingProcess -and $existingProcess.CommandLine -match "jarvis_assistant") {
            Write-Host "JARVIS ya esta ejecutandose con PID $existingPid."
            exit 0
        }
    }
    Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
}

Start-Process -FilePath $pythonw -ArgumentList "-m", "jarvis_assistant" -WorkingDirectory $desktopRoot -WindowStyle Hidden
for ($attempt = 0; $attempt -lt 30 -and -not (Test-Path -LiteralPath $pidPath); $attempt++) {
    Start-Sleep -Milliseconds 500
}

if (-not (Test-Path -LiteralPath $pidPath)) {
    throw "JARVIS no inicio. Revise $env:LOCALAPPDATA\JarvisLocal\logs\jarvis.log"
}

$startedPid = (Get-Content -LiteralPath $pidPath -Raw).Trim()
Write-Host "JARVIS esta activo con PID $startedPid."
