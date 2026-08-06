[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$pidPath = Join-Path $env:LOCALAPPDATA "JarvisLocal\jarvis.pid"

if (-not (Test-Path -LiteralPath $pidPath)) {
    Write-Host "JARVIS no esta ejecutandose."
    exit 0
}

$jarvisPid = (Get-Content -LiteralPath $pidPath -Raw).Trim()
if ($jarvisPid -notmatch "^\d+$") {
    throw "El archivo de proceso de JARVIS no es valido."
}

$processInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $jarvisPid" -ErrorAction SilentlyContinue
if ($processInfo -and $processInfo.CommandLine -match "jarvis_assistant") {
    & taskkill.exe /PID $jarvisPid /T /F | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Windows no pudo detener JARVIS." }
    Write-Host "JARVIS fue detenido."
} elseif ($processInfo) {
    throw "El PID guardado pertenece a otro programa; no se detuvo ningun proceso."
}

Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
