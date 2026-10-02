"""Build the application release assets: cytools-app.zip and cytools-app.zip.sha256.

The file list comes from Git and the repository's .gitignore, so the archive contains exactly what the
repository contains under app/, plus the LICENSE and the LICENCES folder of the root: no data, no runtime, no model weights,
no SDK wheel, no local files.
There is one list of exclusions, not two that could drift apart.

The archive is then checked with the application's own update code (safe_extract, verify_candidate),
the same checks the Updates tab applies before anything becomes pending, plus a scan for files that
must never be shipped.

    runtime\\python\\Scripts\\python.exe app\\scripts\\build_release.py [--out runtime\\build\\release]

Nothing is published: attaching the two files to a GitHub release stays a manual step.
"""
import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent
sys.path.insert(0, str(APP))

NAME = 'cytools-app.zip'
NEVER_SHIPPED_NAMES = {'AGENTS.md', 'CyToolsGuide.md', 'CLAUDE.md', '.env'}
NEVER_SHIPPED_SUFFIXES = {'.whl', '.exe', '.dll', '.pyc', '.pyo', '.log', '.tmp', '.bak', '.sqlite',
                          '.safetensors', '.gguf', '.ckpt', '.pt', '.pth', '.bin', '.onnx', '.npy',
                          '.wav', '.flac', '.ogg', '.mp3', '.m4a', '.aif', '.aiff'}


def tracked_files():
    """Paths under app/ that Git keeps, whether or not they are committed yet."""
    if (ROOT/'.git').exists():
        command = ['git', '-C', str(ROOT), '-c', 'core.quotepath=off', 'ls-files', '--cached', '--others', '--exclude-standard', '--', 'app']
        listing = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', check=True).stdout
    else:        # no repository yet: a throwaway Git directory reads the same .gitignore without creating one here
        scratch = Path(tempfile.mkdtemp(prefix='cytools-release-'))
        try:
            base = ['git', f'--git-dir={scratch/"git"}', f'--work-tree={ROOT}', '-c', 'core.quotepath=off']
            subprocess.run(base+['init', '-q'], check=True)
            listing = subprocess.run(base+['ls-files', '--others', '--exclude-standard', '--', 'app'],
                                     capture_output=True, text=True, encoding='utf-8', check=True).stdout
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
    files = sorted({line.strip() for line in listing.splitlines() if line.strip()})
    if not files: raise SystemExit('Git returned no file under app/: is git installed and the .gitignore present?')
    return files


def check_selection(files):
    problems = []
    for name in files:
        path = Path(name)
        if path.name in NEVER_SHIPPED_NAMES or path.suffix.lower() in NEVER_SHIPPED_SUFFIXES:
            problems.append('must not be shipped: '+name)
        if (ROOT/name).is_symlink(): problems.append('symbolic link: '+name)
        if not name.startswith('app/'): problems.append('outside app/: '+name)
    if problems: raise SystemExit('Refusing to build:\n  '+'\n  '.join(problems))


def build(files, out):
    out.mkdir(parents=True, exist_ok=True)
    archive = out/NAME
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name in files:
            bundle.write(ROOT/name, name)          # entries keep the single top-level app/ folder
        if (ROOT/'LICENSE').is_file():             # the licence texts travel with every copy of the program, updates included
            bundle.write(ROOT/'LICENSE', 'app/LICENSE')
        for notice in sorted((ROOT/'LICENCES').glob('*')) if (ROOT/'LICENCES').is_dir() else []:
            if notice.is_file(): bundle.write(notice, 'app/LICENCES/'+notice.name)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (out/(NAME+'.sha256')).write_text(f'{digest}  {NAME}\n', encoding='ascii')
    return archive, digest


def verify(archive):
    """The same checks as the Updates tab, on a temporary copy: nothing is staged or activated."""
    from maintenance import safe_extract, verify_candidate
    scratch = Path(tempfile.mkdtemp(prefix='cytools-release-check-'))
    try:
        safe_extract(archive, scratch/'unpacked')
        version = verify_candidate(scratch/'unpacked'/'app')
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
        tops = {name.split('/', 1)[0] for name in names}
        if tops != {'app'}: raise SystemExit(f'Archive must hold a single app/ folder, found {sorted(tops)}')
        return version, len(names)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', default=str(ROOT/'runtime'/'build'/'release'))
    args = parser.parse_args()

    files = tracked_files()
    check_selection(files)
    archive, digest = build(files, Path(args.out))
    version, count = verify(archive)
    print(f'{archive}  ({archive.stat().st_size/2**20:.2f} MB, {count} files, version {version})')
    print(f'sha256 {digest}')
    print('Verified with the application\'s own update checks. Attach both files to a GitHub release to publish.')


if __name__ == '__main__':
    main()
