[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$localData = Join-Path $env:LOCALAPPDATA "JarvisLocal"
$startupShortcut = Join-Path ([Environment]::GetFolderPath("Startup")) "JARVIS Local.lnk"
$voiceTarget = "HKCU\SOFTWARE\Microsoft\Speech\Voices\Tokens\MSTTS_V110_esMX_RaulMM"
$voiceFlag = Join-Path $localData "voice-registration-created.flag"

& (Join-Path $PSScriptRoot "stop.ps1")

if (Test-Path -LiteralPath $startupShortcut) {
    Remove-Item -LiteralPath $startupShortcut -Force
}

if (Test-Path -LiteralPath $voiceFlag) {
    & reg.exe delete $voiceTarget /f | Out-Null
    Remove-Item -LiteralPath $voiceFlag -Force
}

Write-Host "JARVIS fue retirado del inicio de Windows. Los modelos y la configuracion local se conservaron."
