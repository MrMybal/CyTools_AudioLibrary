# Compile CyTools_AudioLibrary.exe with the Visual C++ toolchain.
#   powershell -ExecutionPolicy Bypass -File app\build_launcher.ps1 [-Output <path of the .exe>]
# Works from a normal PowerShell: MSVC is located with vswhere when cl.exe is not already on PATH.
# Warnings are treated as errors so that a mangled source can never produce a launcher that silently
# points at the wrong path. The executable carries a version resource (publisher, product, version,
# licence) and a standard manifest: an anonymous binary that starts another program is exactly what
# antivirus heuristics flag, so it must say what it is.
param([string]$Output = '')
$ErrorActionPreference = 'Stop'
$appRoot = $PSScriptRoot
$toolRoot = Split-Path -Parent $appRoot
$build = Join-Path $toolRoot 'runtime\build'
$source = Join-Path $appRoot 'launcher.cpp'
$target = if ($Output) { [System.IO.Path]::GetFullPath($Output) } else { Join-Path $toolRoot 'CyTools_AudioLibrary.exe' }
New-Item -ItemType Directory -Force -Path $build, (Split-Path -Parent $target) | Out-Null

# Version resource and manifest, generated from app/release.json.
$version = (Get-Content -Raw -LiteralPath (Join-Path $appRoot 'release.json') | ConvertFrom-Json).version
if ($version -notmatch '^\d+\.\d+\.\d+$') { throw "Unexpected version in release.json: $version" }
$binary = ($version.Split('.') + '0') -join ','
Set-Content -LiteralPath (Join-Path $build 'launcher.version.h') -Encoding ascii -Value @(
    "#define LAUNCHER_VERSION_BINARY $binary",
    "#define LAUNCHER_VERSION_TEXT `"$version`"")
(Get-Content -Raw -LiteralPath (Join-Path $appRoot 'launcher.manifest')).Replace('@VERSION@', "$version.0") |
    Set-Content -LiteralPath (Join-Path $build 'launcher.generated.manifest') -Encoding utf8
$resource = Join-Path $build 'launcher.res'

$flags = '/nologo /std:c++17 /MT /EHsc /O2 /W3 /WX'
$link = "/link /SUBSYSTEM:WINDOWS /MANIFEST:NO user32.lib `"$resource`""
$rc = "rc /nologo /I `"$build`" /I `"$appRoot`" /fo `"$resource`" `"$(Join-Path $appRoot 'launcher.rc')`""
$cl = "cl $flags `"$source`" /Fe:`"$target`" $link"

Push-Location $build
try {
    if (Get-Command cl.exe -ErrorAction SilentlyContinue) {
        $line = "$rc && $cl"
    } else {
        $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
        if (-not (Test-Path -LiteralPath $vswhere)) {
            throw "Visual Studio introuvable ($vswhere absent). Installer 'Outils de build C++'."
        }
        $install = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
        if (-not $install) { throw "Composant 'Outils de build C++' absent de Visual Studio." }
        $vcvars = Join-Path $install 'VC\Auxiliary\Build\vcvars64.bat'
        if (-not (Test-Path -LiteralPath $vcvars)) { throw "vcvars64.bat introuvable dans $install." }
        # vcvars64.bat calls vswhere.exe itself: make it reachable, and keep its stderr inside cmd so that
        # Windows PowerShell 5.1 does not turn a harmless warning into a terminating error.
        $env:PATH = (Split-Path -Parent $vswhere) + ';' + $env:PATH
        $line = "call `"$vcvars`" >nul 2>&1 && $rc 2>&1 && $cl 2>&1"
    }
    & cmd.exe /c $line
    if ($LASTEXITCODE -ne 0) { throw 'Compilation du lanceur echouee' }
} finally { Pop-Location }

if (-not (Test-Path -LiteralPath $target)) { throw 'Lanceur absent apres compilation' }
Write-Output ('Lanceur construit : ' + $target)
