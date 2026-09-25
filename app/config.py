"""Paths and small persistent settings shared by the UI, the CLI/MCP runtime and maintenance.

Nothing here imports ImGui, PyTorch or a model. The cache of a Library never lives in
this module's folders unless the user keeps the default location: see audiolib.library.
"""
import json
import os
import sys
import uuid
from pathlib import Path

APP = Path(__file__).resolve().parent
ROOT = APP.parent
# Tests and portable setups may relocate the whole data tree; the default is <root>/data.
DATA = Path(os.environ['CYTOOLS_AUDIOLIBRARY_DATA']).resolve() if os.environ.get('CYTOOLS_AUDIOLIBRARY_DATA') else ROOT/'data'
RUNTIME = ROOT/'runtime'
SETTINGS = DATA/'settings'
LOGS = DATA/'logs'
REPORTS = DATA/'reports'
MODELS = DATA/'models'            # installed weights (official and custom), never in app/
LIBRARIES = DATA/'libraries'      # portable Library definition files
DEFAULT_CACHE = DATA/'cache'      # default cache root; each Library may point elsewhere
ENGINES = RUNTIME/'engines'       # private AI environments, created at their final path
ENGINE_SOURCES = RUNTIME/'sources'  # pinned upstream engine sources (m2d, Omni-Embed-Audio)
TOOL_ID = 'cy.tool.audiolibrary'
TOOL_NAME = 'CyTools_AudioLibrary'

DEFAULT_SETTINGS = {
    'device': 'auto',              # auto | gpu | cpu ; reaches the estimator and the worker
    'modelDevices': {},            # modelKey -> 'gpu' | 'cpu' : per-model override (e.g. a big model on CPU for search only)
    'idleUnloadSeconds': 300,      # the model host stops after this idle time and frees VRAM
    'scanThreads': 6,
    'autoPreview': False,
    'llmAssist': 'auto',           # off | auto | always
    'llmModel': '',                # default query understanding model for the interface, the CLI and MCP; empty = catalogue default
    'searchModels': [],            # empty = all enabled models of the Library
    'rrfK': 60,
    'topK': 200,
    'activeLibrary': '',
}


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {} if default is None else default


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)


def settings():
    stored = read_json(SETTINGS/'audiolibrary.json')
    return {**DEFAULT_SETTINGS, **{k: v for k, v in stored.items() if k in DEFAULT_SETTINGS}}


def device_for(model_key, requested=None):
    """Effective device of one model: an explicit gpu/cpu request wins, then the per-model setting, then the global one."""
    if requested in ('gpu', 'cpu'): return requested
    values = settings()
    chosen = values.get('modelDevices', {}).get(model_key)
    if not chosen:      # catalogue default for heavy models (Omni-Embed: CPU, a few seconds per query, no VRAM)
        try:
            from audiolib.registry import load_registry
            descriptor = load_registry().get(model_key); chosen = descriptor.get('defaultDevice') if descriptor else None
        except Exception: chosen = None
    return chosen or values['device']


def save_settings(values):
    current = settings()
    current.update({k: v for k, v in values.items() if k in DEFAULT_SETTINGS})
    write_json(SETTINGS/'audiolibrary.json', current)
    return current


def runtime_python():
    """Interpreter of the base runtime (UI, scanning, playback). Falls back to the current one."""
    candidate = RUNTIME/'python'/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    return str(candidate if candidate.is_file() else Path(sys.executable))


def engine_python(engine='torch'):
    """Interpreter of an AI engine environment, or '' when it is not installed.

    data/settings/backend.json records the active environment of each engine so that a
    staged engine update can be activated and rolled back without touching the other one.
    """
    chosen = read_json(SETTINGS/'backend.json').get(engine, {}).get('python', '')
    if chosen:
        candidate = (ROOT/chosen).resolve()
        if candidate.is_file():
            return str(candidate)
    candidate = ENGINES/engine/('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    return str(candidate) if candidate.is_file() else ''


def configure_tls():
    """Use the operating system trust store when available (corporate proxies)."""
    try:
        import truststore
        truststore.inject_into_ssl()
    except Exception:
        pass
