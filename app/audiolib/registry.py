"""Model registry: descriptors, capabilities, versions, installation receipts, analysis keys.

The application never branches on a model name. A model is a descriptor (JSON) that names an
adapter, declares capabilities and carries its own version/revision/hash; several versions
of one model coexist. The official catalogue ships in app/models/catalog.json; user models
live in data/settings/models/ and survive application updates.
"""
import hashlib
import json
import re
import time
from pathlib import Path

from config import APP, MODELS, SETTINGS, read_json, write_json
from cytools_core import CyToolError

CAPABILITIES = ('AudioEmbedding', 'TextEmbedding', 'ZeroShotTagging', 'Tagging', 'Classification', 'Captioning',
                'Reranking', 'QuestionAnswering', 'QueryUnderstanding', 'QueryExpansion', 'Translation', 'StructuredOutput')
TYPES = ('AudioTextEmbedding', 'AudioEmbedding', 'LLM', 'AudioUnderstanding')
BUILTIN_ADAPTERS = {
    'm2d_clap': 'M2D-CLAP checkpoint folder (nttcslab/m2d portable runtime)',
    'hf_clap': 'Hugging Face ClapModel folder (LAION-CLAP family)',
    'omni_embed': 'Omni-Embed-Audio checkpoint + Qwen2.5-Omni / Nemotron backbone',
    'hf_causal_lm': 'Hugging Face causal language model folder (Qwen3 and compatible chat models)',
}
USER_CATALOG = SETTINGS/'models'
IDENTIFIER = re.compile(r'^[A-Za-z][A-Za-z0-9_.-]{0,63}$')
VERSION = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$')


def model_key(model_id, version): return f'{model_id}@{version}'


class Descriptor:
    def __init__(self, data, custom=False):
        self.data, self.custom = data, custom

    def __getitem__(self, key): return self.data[key]
    def get(self, key, default=None): return self.data.get(key, default)
    @property
    def key(self): return model_key(self.data['modelId'], self.data['version'])
    @property
    def capabilities(self): return set(self.data.get('capabilities', []))
    def has(self, *capabilities): return all(c in self.capabilities for c in capabilities)
    @property
    def is_embedding(self): return self.has('AudioEmbedding')
    @property
    def is_llm(self): return self.data.get('modelType') == 'LLM'

    @property
    def install_dir(self):
        local = self.data.get('localPath')
        return Path(local) if local else MODELS/self.data['modelId']/self.data['version']

    def receipt(self): return read_json(self.install_dir/'receipt.json') if not self.data.get('localPath') else read_json(USER_CATALOG/(self.key.replace('@', '__')+'.receipt.json'))

    @property
    def installed(self):
        receipt = self.receipt()
        if not receipt.get('verified'): return False
        return all((self.install_dir/item['path']).is_file() and (self.install_dir/item['path']).stat().st_size == item['size']
                   for item in receipt.get('files', []))

    @property
    def model_hash(self): return self.receipt().get('modelHash', '')

    def public(self):
        """Serializable view for the UI, the CLI and MCP clients."""
        value = {k: v for k, v in self.data.items() if k not in ('source', 'auxiliary')}
        receipt = self.receipt()
        value.update(modelKey=self.key, custom=self.custom, installed=self.installed, modelHash=receipt.get('modelHash', ''),
                     installedRevision=receipt.get('revision', ''), installPath=str(self.install_dir),
                     downloadSize=sum(item.get('size') or 0 for item in download_items(self)),
                     integrated=bool(self.data.get('adapter')))
        return value


def validate_descriptor(data):
    for field in ('modelId', 'version', 'displayName', 'modelType', 'capabilities'):
        if field not in data: raise CyToolError('InvalidParameters', 'Model descriptor lacks '+field)
    if not IDENTIFIER.match(str(data['modelId'])): raise CyToolError('InvalidParameters', 'Invalid modelId')
    if not VERSION.match(str(data['version'])): raise CyToolError('InvalidParameters', 'Invalid model version')
    if data['modelType'] not in TYPES: raise CyToolError('InvalidParameters', 'modelType must be one of '+', '.join(TYPES))
    unknown = set(data['capabilities'])-set(CAPABILITIES)
    if unknown: raise CyToolError('InvalidParameters', 'Unknown capabilities: '+', '.join(sorted(unknown)))
    profile = data.get('promptProfile')
    if profile:
        from .llm import PROFILES                 # the prompt profiles are defined where they are used
        if profile not in PROFILES:
            raise CyToolError('InvalidParameters', 'promptProfile must be one of '+', '.join(sorted(PROFILES)))
    adapter = data.get('adapter', '')
    if adapter and adapter not in BUILTIN_ADAPTERS and not adapter.startswith('file:'):
        raise CyToolError('InvalidParameters', 'adapter must be one of %s or file:<adapter.py>' % ', '.join(BUILTIN_ADAPTERS))
    return data


def load_registry():
    """{modelKey: Descriptor}; a user descriptor may not silently replace an official one."""
    registry = {}
    for data in read_json(APP/'models'/'catalog.json', []):
        descriptor = Descriptor(validate_descriptor(data)); registry[descriptor.key] = descriptor
    if USER_CATALOG.is_dir():
        for path in sorted(USER_CATALOG.glob('*.json')):
            if path.name.endswith('.receipt.json'): continue
            try: descriptor = Descriptor(validate_descriptor(read_json(path)), custom=True)
            except CyToolError: continue
            registry.setdefault(descriptor.key, descriptor)
    return registry


def get_model(key, registry=None):
    registry = registry or load_registry()
    if key not in registry: raise CyToolError('NotFound', 'Unknown model: '+str(key), suggested_action='Call list_models for the registered model keys')
    return registry[key]


def download_items(descriptor):
    items = []
    source = descriptor.get('source') or {}
    if source.get('kind') == 'url-archive': items.append({'size': source.get('size')})
    for block in ([source] if source.get('kind') == 'huggingface' else [])+[a for a in descriptor.get('auxiliary', []) if a.get('kind') == 'huggingface']:
        items += [{'size': f.get('size')} for f in block.get('files', [])]
    return items


def file_sha256(path, cancelled=None):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        while True:
            if cancelled and cancelled(): raise CyToolError('Cancelled', 'Verification cancelled')
            chunk = handle.read(1 << 22)
            if not chunk: break
            digest.update(chunk)
    return digest.hexdigest()


def write_receipt(descriptor, files, revision=''):
    """files: [(relative path, size, sha256)]. ModelHash covers names and content hashes of every weight file."""
    digest = hashlib.sha256()
    for path, size, sha in sorted(files): digest.update(f'{path}\0{size}\0{sha}\n'.encode())
    receipt = {'modelKey': descriptor.key, 'revision': revision or descriptor.get('revision', ''), 'verified': True,
               'modelHash': digest.hexdigest(), 'installedAt': time.time(),
               'files': [{'path': p, 'size': s, 'sha256': h} for p, s, h in sorted(files)]}
    target = (descriptor.install_dir/'receipt.json') if not descriptor.get('localPath') else USER_CATALOG/(descriptor.key.replace('@', '__')+'.receipt.json')
    write_json(target, receipt)
    return receipt


WEIGHT_SUFFIXES = ('.pth', '.pt', '.bin', '.safetensors', '.ckpt', '.gguf', '.onnx', '.json', '.txt', '.model', '.py')


def register_custom(data, cancelled=None):
    """Register a local model (custom, fine-tuned or another version) in place; weights are not copied."""
    data = dict(data); data.setdefault('provider', 'Custom'); data.setdefault('license', {'name': 'Not declared', 'url': ''})
    validate_descriptor(data)
    local = Path(str(data.get('localPath', '')))
    if not local.is_absolute() or not local.exists(): raise CyToolError('NotFound', 'localPath must be an existing absolute file or folder')
    if not data.get('adapter'): raise CyToolError('InvalidParameters', 'A custom model needs an adapter')
    if data['adapter'].startswith('file:') and not Path(data['adapter'][5:]).is_file():
        raise CyToolError('NotFound', 'Adapter file not found: '+data['adapter'][5:])
    registry = load_registry()
    descriptor = Descriptor(data, custom=True)
    if descriptor.key in registry and not registry[descriptor.key].custom:
        raise CyToolError('InvalidState', 'This modelId/version belongs to the official catalogue; choose another version label')
    base = local if local.is_dir() else local.parent
    data['localPath'] = str(base)
    if local.is_file(): data['weightFile'] = local.name
    found = [p for p in (base.rglob('*') if local.is_dir() else [local]) if p.is_file() and p.suffix.lower() in WEIGHT_SUFFIXES and p.name != 'receipt.json']
    if not found: raise CyToolError('InvalidParameters', 'No model file found in '+str(base))
    files = [(p.relative_to(base).as_posix(), p.stat().st_size, file_sha256(p, cancelled)) for p in found]
    USER_CATALOG.mkdir(parents=True, exist_ok=True)
    write_json(USER_CATALOG/(descriptor.key.replace('@', '__')+'.json'), data)
    write_receipt(Descriptor(data, custom=True), files, data.get('revision', ''))
    return Descriptor(data, custom=True)


def unregister_custom(key):
    descriptor = get_model(key)
    if not descriptor.custom: raise CyToolError('InvalidState', 'Official catalogue entries cannot be unregistered; remove their weights instead')
    for suffix in ('.json', '.receipt.json'):
        path = USER_CATALOG/(key.replace('@', '__')+suffix)
        if path.is_file(): path.unlink()
    return {'modelKey': key, 'weightsDeleted': False}


# ---------------------------------------------------------------------------
# Analysis identity
# ---------------------------------------------------------------------------
def analysis_config(descriptor, library_settings):
    chunk = descriptor.get('preferredChunkDuration') or library_settings['segmentSeconds']
    maximum = descriptor.get('maximumAudioDuration')
    if maximum: chunk = min(chunk, maximum)
    return {'segmentSeconds': float(chunk), 'segmentOverlap': float(min(library_settings['segmentOverlap'], chunk/2)),
            'maxSegmentsPerFile': int(library_settings['maxSegmentsPerFile']), 'sampleRate': descriptor.get('requiredSampleRate'),
            'channels': 'mono-mean', 'wholeClip': 'mean-of-segments', 'normalize': 'l2'}


def analysis_key(descriptor, config):
    """ModelId + Version + Revision + ModelHash + AnalysisConfigHash -> short stable key.

    A different revision, different weights or different segmentation yields another key:
    older embeddings stay valid for what they are and are never silently mixed with new ones.
    """
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    receipt = descriptor.receipt()
    identity = [descriptor['modelId'], descriptor['version'], receipt.get('revision') or descriptor.get('revision', ''),
                receipt.get('modelHash', ''), config_hash]
    return hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:16], config_hash
