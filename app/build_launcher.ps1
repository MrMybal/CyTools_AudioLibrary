# Compile CyTools_AudioLibrary.exe with the Visual C++ toolchain.
# Works from a normal PowerShell: MSVC is located with vswhere when cl.exe is
# not already on PATH. Warnings are treated as errors so that a mangled source
# can never produce a launcher that silently points at the wrong path.
$ErrorActionPreference = 'Stop'
$appRoot = $PSScriptRoot
$toolRoot = Split-Path -Parent $appRoot
$build = Join-Path $toolRoot 'runtime\build'
$source = Join-Path $appRoot 'launcher.cpp'
$target = Join-Path $toolRoot 'CyTools_AudioLibrary.exe'
New-Item -ItemType Directory -Force -Path $build | Out-Null

$flags = '/nologo /std:c++17 /MT /EHsc /O2 /W3 /WX'
$link = '/link /SUBSYSTEM:WINDOWS user32.lib'

Push-Location $build
try {
    if (Get-Command cl.exe -ErrorAction SilentlyContinue) {
        $line = "cl $flags `"$source`" /Fe:`"$target`" $link"
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
        $line = "call `"$vcvars`" >nul 2>&1 && cl $flags `"$source`" /Fe:`"$target`" $link 2>&1"
    }
    & cmd.exe /c $line
    if ($LASTEXITCODE -ne 0) { throw 'Compilation du lanceur echouee' }
} finally { Pop-Location }

if (-not (Test-Path -LiteralPath $target)) { throw 'Lanceur absent apres compilation' }
Write-Output ('Lanceur construit : ' + $target)
