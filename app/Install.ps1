# Creates the private base runtime of this folder, then (optionally) the AI engine and the default model.
#   powershell -ExecutionPolicy Bypass -File app\Install.ps1 [-Engine] [-CpuOnly]
# Models that require a licence acceptance are never installed by this script: install them from the
# Installation tab of the application, where you read and accept their licence yourself.
param([switch]$Engine, [switch]$CpuOnly)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$root = Split-Path -Parent $PSScriptRoot
$runtime = Join-Path $root 'runtime\python'
$python = Join-Path $runtime 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    $system = Get-Command python -ErrorAction SilentlyContinue
    if (-not $system) { throw 'Python 3.11 or newer is required: https://www.python.org/downloads/' }
    $version = & python -c "import sys;print('%d.%d'%sys.version_info[:2])"
    if ([version]$version -lt [version]'3.11') { throw "Python $version found; 3.11 or newer is required." }
    & python -m venv $runtime
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create the private runtime' }
}
# CyToolsCore is installed from its public repository at the revision pinned in requirements.txt: pip needs git.
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw 'git is required to install CyToolsCore from https://github.com/MrMybal/CyToolsCore: https://git-scm.com/download/win'
}
& $python -m pip --disable-pip-version-check install --keyring-provider disabled --timeout 60 --retries 3 -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Base installation failed (CyToolsCore, ImGui, MCP, audio libraries)' }
# The start-up script lives outside app/ (it is what swaps app/ during an update): install it from its source.
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'bootstrap.py') -Destination (Join-Path $root 'runtime\bootstrap.py') -Force
if ($Engine) {
    $arguments = @((Join-Path $PSScriptRoot 'setup_backend.py'))
    if ($CpuOnly) { $arguments += '--cpu-only' }
    & $python @arguments
    if ($LASTEXITCODE -ne 0) { throw 'AI engine installation failed; see the messages above' }
}
if (-not (Test-Path -LiteralPath (Join-Path $root 'CyTools_AudioLibrary.exe'))) {
    Write-Output 'The launcher is missing: build it with app\build_launcher.ps1 (Visual C++ build tools).'
}
Write-Output 'Done. Start CyTools_AudioLibrary.exe, then use the Installation tab for the AI engine and the models.'
