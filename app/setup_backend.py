"""Install the private AI engine: a separate environment created at its final path, plus the
pinned upstream sources of the engines (git checkout of an exact revision, never a reset of
a user folder). Used by the Installation tab, by Install.ps1 and by engine updates.

    python app/setup_backend.py [--cpu-only] [--environment DIR] [--sources-only] [--status]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import APP, ENGINES, ENGINE_SOURCES, ROOT, SETTINGS, read_json, write_json

SPEC = read_json(APP/'engine.json')
NO_WINDOW = 0x08000000 if os.name == 'nt' else 0


def say(text): print(text, flush=True)


def run(command, **options):
    say('> '+' '.join(str(c) for c in command))
    subprocess.run([str(c) for c in command], check=True, creationflags=NO_WINDOW, **options)


def python_of(environment):
    return Path(environment)/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def base_interpreter():
    """The interpreter that created the base runtime; a venv cannot create a usable venv from its own shim reliably."""
    return getattr(sys, '_base_executable', None) or sys.executable


def install_sources(only=None):
    ENGINE_SOURCES.mkdir(parents=True, exist_ok=True)
    git = shutil.which('git')
    if not git: raise SystemExit('git is required to fetch the engine sources: https://git-scm.com/downloads')
    for name, spec in SPEC['sources'].items():
        if only and name not in only: continue
        target = ENGINE_SOURCES/name
        if not (target/'.git').is_dir():
            run([git, 'clone', '--no-checkout', '--filter=blob:none', spec['repository'], target])
        head = subprocess.run([git, '-C', str(target), 'rev-parse', 'HEAD'], capture_output=True, text=True, creationflags=NO_WINDOW).stdout.strip()
        populated = (target/spec['requiredFile']).is_file()
        if head != spec['revision'] or not populated:
            dirty = subprocess.run([git, '-C', str(target), 'status', '--porcelain'], capture_output=True, text=True, creationflags=NO_WINDOW).stdout.strip()
            if dirty and populated: raise SystemExit(f'{target} has local modifications; they are left untouched. Move them away, then retry.')
            known = subprocess.run([git, '-C', str(target), 'cat-file', '-e', spec['revision']+'^{commit}'], creationflags=NO_WINDOW).returncode == 0
            if not known: run([git, '-C', target, 'fetch', '--depth', '1', 'origin', spec['revision']])
            run([git, '-C', target, 'checkout', '--detach', spec['revision']])
        if not (target/spec['requiredFile']).is_file(): raise SystemExit(f"{name}: {spec['requiredFile']} is missing after checkout")
        say(f"{name}: revision {spec['revision'][:12]} ready")


def install_environment(environment, cpu_only):
    environment = Path(environment)
    python = python_of(environment)
    if not python.is_file():
        environment.parent.mkdir(parents=True, exist_ok=True)
        run([base_interpreter(), '-m', 'venv', environment])
    pip = [python, '-m', 'pip', '--disable-pip-version-check', 'install', '--keyring-provider', 'disabled', '--timeout', '60', '--retries', '3']
    flavour = SPEC['torch']['cpu' if cpu_only else 'cuda']
    run(pip+['torch=='+SPEC['torch']['version'], 'torchvision=='+SPEC['torch']['torchvision'], '--index-url', flavour['index']])
    # Without this constraint a dependency (timm -> torchvision) lets pip replace the CUDA build by the newest CPU wheel of PyPI.
    constraints = environment/'cytools-constraints.txt'
    constraints.write_text('torch=='+SPEC['torch']['version']+'\ntorchvision=='+SPEC['torch']['torchvision']+'\n', 'utf-8')
    run(pip+['-c', constraints, '-r', APP/'requirements-engine.txt'])
    check = ("import torch,transformers,timm,einops,nnAudio,peft,soundfile,av,json;"
             "print(json.dumps({'torch':torch.__version__,'cuda':torch.cuda.is_available(),"
             "'device':torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu','transformers':transformers.__version__}))")
    result = subprocess.run([str(python), '-c', check], capture_output=True, text=True, creationflags=NO_WINDOW)
    if result.returncode: raise SystemExit('Engine import check failed:\n'+result.stderr[-3000:])
    report = json.loads(result.stdout.strip().splitlines()[-1])
    if not report['torch'].startswith(SPEC['torch']['version']):
        raise SystemExit('Unexpected PyTorch version after installation: '+report['torch'])
    if not cpu_only and '+cpu' in report['torch']: raise SystemExit('A CPU build of PyTorch was installed instead of the CUDA build')
    say('Engine check: '+json.dumps(report))
    return python, report


def status():
    backend = read_json(SETTINGS/'backend.json').get('torch', {})
    python = (ROOT/backend['python']) if backend.get('python') else python_of(ENGINES/'torch')
    sources = {}
    for name, spec in SPEC['sources'].items():
        sources[name] = {'present': (ENGINE_SOURCES/name/spec['requiredFile']).is_file(), 'revision': spec['revision']}
    return {'installed': python.is_file(), 'python': str(python), 'report': backend.get('report', {}), 'sources': sources,
            'torchVersion': SPEC['torch']['version']}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--cpu-only', action='store_true'); parser.add_argument('--environment', default=str(ENGINES/'torch'))
    parser.add_argument('--sources-only', action='store_true'); parser.add_argument('--status', action='store_true')
    parser.add_argument('--no-activate', action='store_true', help='Prepare the environment without making it the active engine')
    args = parser.parse_args()
    if args.status: say(json.dumps(status(), indent=2)); return 0
    install_sources()
    if args.sources_only: return 0
    environment = Path(args.environment).resolve()
    if not environment.is_relative_to(ENGINES.resolve()): raise SystemExit('The engine environment must live under runtime/engines')
    python, report = install_environment(environment, args.cpu_only)
    if not args.no_activate:
        backend = read_json(SETTINGS/'backend.json')
        if backend.get('torch', {}).get('python') and backend['torch']['python'] != str(python.relative_to(ROOT)):
            write_json(SETTINGS/'backend-previous.json', backend)
        backend['torch'] = {'python': str(python.relative_to(ROOT)).replace('\\', '/'), 'report': report, 'cpuOnly': bool(args.cpu_only)}
        write_json(SETTINGS/'backend.json', backend)
    say('AI engine ready: '+str(python))
    return 0


if __name__ == '__main__':
    try: raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        say('Command failed with exit code '+str(error.returncode)); raise SystemExit(1)
