"""Build every asset of a GitHub release of CyTools_AudioLibrary from the committed code.

    CyTools_AudioLibrary-<version>-windows-x64.zip   what a person downloads: the committed files + the launcher
    cytools-app.zip, cytools-app.zip.sha256          what the Updates tab of an installed copy downloads
    SHA256SUMS.txt                                   the checksums of all of the above

    runtime\\python\\Scripts\\python.exe app\\scripts\\build_package.py

The user package comes from `git archive HEAD`, not from the working folder, so it holds exactly what the
repository holds at that commit (LICENSE and LICENCES/ included), plus the launcher, which must have been
built from that same commit with app\\build_launcher.ps1. Git-only files are left out. Nothing is published.
"""
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent
GIT_ONLY = {'.gitignore', '.gitattributes', 'app/.gitignore'}
REPOSITORY_ONLY = ('.github/',)      # README screenshots: shown on GitHub, not shipped
REQUIRED = ('LICENSE', 'LICENCES/CyToolsCore-MIT.txt', 'LICENCES/SOURCES.txt', 'CyTools_AudioLibrary.exe')


def git(*arguments, binary=False):
    result = subprocess.run(['git', '-C', str(ROOT), *arguments], capture_output=True, check=True)
    return result.stdout if binary else result.stdout.decode('utf-8').strip()


def main():
    if git('status', '--porcelain'): raise SystemExit('The working tree has uncommitted changes: a release is built from a commit.')
    launcher = ROOT/'CyTools_AudioLibrary.exe'
    if not launcher.is_file(): raise SystemExit('Build the launcher first: app\\build_launcher.ps1')
    commit = git('rev-parse', 'HEAD')
    version = json.loads((APP/'release.json').read_text(encoding='utf-8'))['version']
    out = ROOT/'runtime'/'build'/'release'/version
    out.mkdir(parents=True, exist_ok=True)
    for old in out.iterdir():
        if old.is_file(): old.unlink()

    package = out/f'CyTools_AudioLibrary-{version}-windows-x64.zip'
    top, names = 'CyTools_AudioLibrary/', []
    with tarfile.open(fileobj=io.BytesIO(git('archive', '--format=tar', 'HEAD', binary=True))) as tar, \
            zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for member in sorted(tar.getmembers(), key=lambda m: m.name):
            if not member.isfile() or member.name in GIT_ONLY or member.name.startswith(REPOSITORY_ONLY): continue
            entry = zipfile.ZipInfo(top+member.name, date_time=(2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(entry, tar.extractfile(member).read())
            names.append(member.name)
        bundle.write(launcher, top+'CyTools_AudioLibrary.exe'); names.append('CyTools_AudioLibrary.exe')
    missing = [name for name in REQUIRED if name not in names]
    if missing: raise SystemExit(f'The package would ship without {missing}')

    built = subprocess.run([sys.executable, str(APP/'scripts'/'build_release.py'), '--out', str(out)], capture_output=True, text=True, encoding='utf-8')
    if built.returncode: raise SystemExit('build_release.py failed:\n'+built.stdout+built.stderr)

    sums = [f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}' for path in sorted(out.iterdir())
            if path.is_file() and path.name != 'SHA256SUMS.txt']
    (out/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n', encoding='ascii')
    print(json.dumps({'version': version, 'commit': commit, 'folder': str(out), 'packageFiles': len(names),
                      'assets': {p.name: p.stat().st_size for p in sorted(out.iterdir()) if p.is_file()}}, indent=1))


if __name__ == '__main__':
    main()
