"""Virtual Libraries: a portable definition file that references folders, never copies them.

The definition (data/libraries/<id>.json) holds LibraryId, Name, RootFolders, CacheLocation,
Settings, EnabledModels and Taxonomy. Every derived datum (database, waveforms, embeddings,
indexes, captions) lives under CacheLocation/Library_<id>/ and can be moved or rebuilt.
Nothing is ever written next to the original audio files.
"""
import os
import shutil
import threading
import time
import uuid
from pathlib import Path

from config import APP, DEFAULT_CACHE, LIBRARIES, read_json, write_json
from cytools_core import CyToolError

FORMAT = 'cytools-audiolibrary'
DEFAULT_LIBRARY_SETTINGS = {
    'segmentSeconds': 10.0,        # preferred chunk; a model descriptor may override it
    'segmentOverlap': 2.0,
    'maxSegmentsPerFile': 400,
    'computeLoudness': True,
    'autoTagThreshold': 0.05,      # softmax probability over the tag vocabulary above which an auto tag is kept
    'autoTagsPerFile': 6,
    'categoryThreshold': 0.2,      # softmax probability over all categories
    'categoriesPerFile': 3,
    'modelWeights': {},            # modelKey -> RRF weight, default 1.0
    'excludePenalty': 0.6,
    'hintBoost': 0.12,             # re-ordering bonus for candidates matching the categories the LLM suggested; 0 disables it
    'autoSync': 'auto',            # auto | ask | off : the standalone watches the folders in the background
    'autoSyncIntervalSeconds': 300,
    'autoAnalyze': True,           # after an automatic scan, embed the new/modified files with the enabled models
}
_locks = {}
_locks_guard = threading.Lock()


def lock_for(library_id):
    """One mutating maintenance job (scan, analysis, cache move) per Library at a time."""
    with _locks_guard:
        return _locks.setdefault(library_id, threading.Lock())


def default_taxonomy():
    return read_json(APP/'taxonomy.default.json', {'categories': [], 'tags': []})


class Library:
    def __init__(self, data, path):
        self.data, self.path = data, Path(path)

    # -- identity ------------------------------------------------------
    @property
    def id(self): return self.data['libraryId']
    @property
    def name(self): return self.data['name']
    @property
    def settings(self): return {**DEFAULT_LIBRARY_SETTINGS, **self.data.get('settings', {})}
    @property
    def roots(self): return self.data['rootFolders']
    @property
    def enabled_models(self): return list(self.data.get('enabledModels', []))
    @property
    def taxonomy(self): return self.data.get('taxonomy') or default_taxonomy()

    # -- cache layout ---------------------------------------------------
    @property
    def cache_root(self):
        configured = self.data.get('cacheLocation') or ''
        return Path(configured) if configured else DEFAULT_CACHE

    @property
    def cache(self): return self.cache_root/('Library_'+self.id)
    @property
    def database_path(self): return self.cache/'Common'/'Database'/'library.sqlite'
    @property
    def waveforms(self): return self.cache/'Common'/'Waveforms'
    @property
    def temporary(self): return self.cache/'Temporary'

    def model_dir(self, model_id, version):
        safe = lambda text: ''.join(c if c.isalnum() or c in '._-' else '_' for c in str(text))
        return self.cache/'Models'/safe(model_id)/safe(version)

    def ensure_cache(self):
        for folder in (self.database_path.parent, self.waveforms, self.temporary, self.cache/'Models'):
            folder.mkdir(parents=True, exist_ok=True)
        marker = self.cache/'cache.json'
        if not marker.is_file():
            write_json(marker, {'format': FORMAT+'-cache', 'schemaVersion': 1, 'libraryId': self.id,
                                'note': 'Derived data only. Safe to move with the Tool closed, or to delete and rebuild.'})

    def save(self):
        self.data['modified'] = time.time()
        write_json(self.path, self.data)

    # -- folders --------------------------------------------------------
    def root(self, root_id):
        for root in self.roots:
            if root['rootId'] == root_id: return root
        raise CyToolError('NotFound', 'Unknown folder: '+str(root_id))

    def add_root(self, folder):
        folder = Path(folder).expanduser()
        if not folder.is_absolute(): raise CyToolError('InvalidParameters', 'Folder path must be absolute')
        if not folder.is_dir(): raise CyToolError('NotFound', 'Folder does not exist: '+str(folder))
        resolved = os.path.normcase(str(folder.resolve()))
        cache = os.path.normcase(str(self.cache.resolve()))
        if cache.startswith(resolved+os.sep) or cache == resolved:
            raise CyToolError('InvalidParameters', 'The cache of this Library is inside that folder; choose another cache location first')
        for root in self.roots:
            existing = os.path.normcase(str(Path(root['path']).resolve()))
            if existing == resolved: return root
        root = {'rootId': uuid.uuid4().hex[:12], 'path': str(folder), 'enabled': True, 'added': time.time(), 'lastScan': None}
        self.roots.append(root); self.save()
        return root

    def remove_root(self, root_id):
        self.root(root_id)
        self.data['rootFolders'] = [r for r in self.roots if r['rootId'] != root_id]; self.save()

    def set_root_enabled(self, root_id, enabled):
        self.root(root_id)['enabled'] = bool(enabled); self.save()

    # -- models and taxonomy -------------------------------------------
    def set_model_enabled(self, model_key, enabled):
        models = [m for m in self.enabled_models if m != model_key]
        if enabled: models.append(model_key)
        self.data['enabledModels'] = models; self.save()

    def update_settings(self, values):
        unknown = set(values)-set(DEFAULT_LIBRARY_SETTINGS)
        if unknown: raise CyToolError('InvalidParameters', 'Unknown Library settings: '+', '.join(sorted(unknown)))
        self.data['settings'] = {**self.data.get('settings', {}), **values}; self.save()

    def set_taxonomy(self, taxonomy):
        validate_taxonomy(taxonomy); self.data['taxonomy'] = taxonomy; self.save()

    # -- cache relocation ----------------------------------------------
    def move_cache(self, destination, progress=None, cancelled=None):
        """Copy the cache to a new root, verify, switch the definition, keep the old copy.

        The previous folder is left in place (renamed) so that the move stays reversible; the
        user deletes it explicitly. Embedding stores use paths relative to the cache.
        """
        destination = Path(destination)
        if not destination.is_absolute(): raise CyToolError('InvalidParameters', 'Cache location must be absolute')
        for root in self.roots:
            base = os.path.normcase(str(Path(root['path']).resolve()))
            target = os.path.normcase(str(destination.resolve()))
            if target == base or target.startswith(base+os.sep):
                raise CyToolError('InvalidParameters', 'The cache must stay outside the audio folders: '+root['path'])
        source, target = self.cache, destination/('Library_'+self.id)
        if source.resolve() == target.resolve(): return {'moved': False, 'cache': str(target)}
        if target.exists() and any(target.iterdir()):
            raise CyToolError('InvalidState', 'Destination already contains a cache for this Library: '+str(target))
        copied = 0
        if source.is_dir():
            files = [p for p in source.rglob('*') if p.is_file() and 'Temporary' not in p.relative_to(source).parts]
            total = sum(p.stat().st_size for p in files) or 1
            free = shutil.disk_usage(destination if destination.exists() else destination.anchor).free
            if free < total*1.05: raise CyToolError('InsufficientDisk', 'Not enough free space at the destination')
            done = 0
            for item in files:
                if cancelled and cancelled():
                    shutil.rmtree(target, ignore_errors=True)
                    raise CyToolError('Cancelled', 'Cache move cancelled; the original cache is unchanged')
                out = target/item.relative_to(source); out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, out); copied += 1; done += item.stat().st_size
                if progress: progress(100*done/total, item.name)
            for item in files:
                if (target/item.relative_to(source)).stat().st_size != item.stat().st_size:
                    shutil.rmtree(target, ignore_errors=True)
                    raise CyToolError('VerificationFailed', 'Copied cache differs from the source; nothing was changed')
        previous = None
        if source.is_dir():
            previous = source.with_name(source.name+'.moved-'+time.strftime('%Y%m%d-%H%M%S'))
            source.rename(previous)
        self.data['cacheLocation'] = str(destination); self.save(); self.ensure_cache()
        return {'moved': True, 'cache': str(target), 'files': copied, 'previous': str(previous) if previous else ''}


def validate_taxonomy(taxonomy):
    if not isinstance(taxonomy, dict) or not isinstance(taxonomy.get('categories'), list):
        raise CyToolError('InvalidParameters', 'Taxonomy needs a categories list')
    seen = set()
    def visit(node, depth):
        if depth > 6: raise CyToolError('InvalidParameters', 'Taxonomy is limited to 6 levels')
        if not isinstance(node, dict) or not str(node.get('id', '')).strip() or not str(node.get('name', '')).strip():
            raise CyToolError('InvalidParameters', 'Each category needs an id and a name')
        if node['id'] in seen: raise CyToolError('InvalidParameters', 'Duplicate category id: '+node['id'])
        seen.add(node['id'])
        for child in node.get('children', []): visit(child, depth+1)
    for node in taxonomy['categories']: visit(node, 1)
    if not all(isinstance(t, str) for t in taxonomy.get('tags', [])):
        raise CyToolError('InvalidParameters', 'Taxonomy tags must be strings')


def flatten_taxonomy(taxonomy):
    """[(id, name, parent ids tuple, prompts)] in depth-first order."""
    out = []
    def visit(node, parents):
        prompts = [p for p in node.get('prompts', []) if isinstance(p, str) and p.strip()] or [node['name']]
        out.append((node['id'], node['name'], tuple(parents), prompts))
        for child in node.get('children', []): visit(child, parents+[node['id']])
    for node in taxonomy.get('categories', []): visit(node, [])
    return out


def list_libraries():
    LIBRARIES.mkdir(parents=True, exist_ok=True)
    found = []
    for path in sorted(LIBRARIES.glob('*.json')):
        data = read_json(path)
        if data.get('format') == FORMAT and data.get('libraryId'): found.append(Library(data, path))
    return found


def get_library(library_id):
    for library in list_libraries():
        if library.id == library_id: return library
    raise CyToolError('NotFound', 'Unknown Library: '+str(library_id))


def create_library(name, cache_location=''):
    name = str(name).strip()
    if not name: raise CyToolError('InvalidParameters', 'Library name is required')
    if cache_location and not Path(cache_location).is_absolute():
        raise CyToolError('InvalidParameters', 'Cache location must be an absolute path')
    library_id = uuid.uuid4().hex[:8]
    data = {'format': FORMAT, 'schemaVersion': 1, 'libraryId': library_id, 'name': name,
            'rootFolders': [], 'cacheLocation': str(cache_location or ''), 'settings': {},
            'enabledModels': [], 'taxonomy': default_taxonomy(), 'created': time.time()}
    library = Library(data, LIBRARIES/(library_id+'.json'))
    library.save(); library.ensure_cache()
    return library


def delete_library(library_id, delete_cache=False):
    """Remove the definition. The definition is kept as .deleted for recovery; audio is never touched."""
    library = get_library(library_id)
    with lock_for(library_id):
        from .database import close_database
        close_database(library)
        removed_cache = False
        if delete_cache and library.cache.is_dir():
            shutil.rmtree(library.cache); removed_cache = True
        library.path.replace(library.path.with_suffix('.deleted'))
    return {'libraryId': library_id, 'cacheDeleted': removed_cache}
