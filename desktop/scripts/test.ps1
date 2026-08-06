[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$desktopRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $desktopRoot ".venv310\Scripts\python.exe"

& $python -m pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $python -m compileall -q (Join-Path $desktopRoot "src") (Join-Path $desktopRoot "tests")
exit $LASTEXITCODE
