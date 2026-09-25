"""Per-model embedding stores and index providers.

One store per analysis key (model + version + revision + weights hash + analysis config), in
its own folder of the Library cache. Vectors of different models are never mixed, added or
compared: each store has its own index and answers its own queries; fusion happens on ranks.
"""
import json
import shutil
import threading
import time

import numpy as np

from cytools_core import CyToolError
from .registry import analysis_config, analysis_key

_cache = {}
_cache_lock = threading.Lock()


class EmbeddingStore:
    def __init__(self, library, database, key, row):
        self.library, self.database, self.key = library, database, key
        self.model_key, self.dimension = row['model_key'], row['dimension']
        self.descriptor, self.config = json.loads(row['descriptor']), json.loads(row['config'])
        self.directory = library.cache/row['relative_dir']
        self.vectors_path = self.directory/'Embeddings'/'vectors.f16'
        self._write_lock = threading.Lock()

    # -- creation / lookup -------------------------------------------------
    @classmethod
    def for_model(cls, library, database, descriptor, create=False):
        config = analysis_config(descriptor, library.settings)
        key, config_hash = analysis_key(descriptor, config)
        row = database.one('SELECT * FROM stores WHERE analysis_key=?', (key,))
        if row is None:
            if not create: return None
            dimension = int(descriptor.get('embeddingDimension') or 0)
            if dimension <= 0: raise CyToolError('InvalidState', 'Model descriptor has no embeddingDimension')
            directory = library.model_dir(descriptor['modelId'], descriptor['version'])/key
            (directory/'Embeddings').mkdir(parents=True, exist_ok=True); (directory/'Index').mkdir(exist_ok=True)
            snapshot = {k: descriptor.get(k) for k in ('modelId', 'version', 'revision', 'displayName', 'family', 'embeddingDimension',
                                                       'requiredSampleRate', 'adapter', 'indexProvider')}
            snapshot.update(modelHash=descriptor.model_hash, analysisConfigHash=config_hash)
            relative = directory.relative_to(library.cache).as_posix()
            database.execute('INSERT INTO stores(analysis_key,model_key,descriptor,config,dimension,relative_dir,created) VALUES(?,?,?,?,?,?,?)',
                             (key, descriptor.key, json.dumps(snapshot), json.dumps(config), dimension, relative, time.time()))
            (directory/'store.json').write_text(json.dumps({'analysisKey': key, 'model': snapshot, 'config': config, 'dtype': 'float16',
                                                            'layout': 'rows of L2-normalised vectors; row table in the Library database'}, indent=2), 'utf-8')
            row = database.one('SELECT * FROM stores WHERE analysis_key=?', (key,))
        return cls(library, database, key, row)

    @classmethod
    def open(cls, library, database, key):
        row = database.one('SELECT * FROM stores WHERE analysis_key=?', (key,))
        if row is None: raise CyToolError('NotFound', 'Unknown analysis store: '+str(key))
        return cls(library, database, key, row)

    # -- writing -------------------------------------------------------------
    def add(self, audio_id, segments, vectors):
        """segments: [(index, start, stop)] ; vectors: float array [len(segments), dim], index -1 = whole clip."""
        vectors = np.asarray(vectors, dtype=np.float32)
        if vectors.ndim != 2 or vectors.shape != (len(segments), self.dimension):
            raise CyToolError('InvalidOutput', f'Adapter returned shape {vectors.shape}, expected ({len(segments)}, {self.dimension})')
        if not np.isfinite(vectors).all(): raise CyToolError('InvalidOutput', 'Adapter returned non-finite embeddings')
        norms = np.linalg.norm(vectors, axis=1, keepdims=True); vectors = vectors/np.maximum(norms, 1e-12)
        with self._write_lock, self.database.transaction():
            row = self.database.one('SELECT next_row FROM stores WHERE analysis_key=?', (self.key,))['next_row']
            self.vectors_path.parent.mkdir(parents=True, exist_ok=True)
            with self.vectors_path.open('r+b' if self.vectors_path.is_file() else 'w+b') as handle:
                handle.seek(row*self.dimension*2); handle.write(vectors.astype(np.float16).tobytes()); handle.truncate()
            self.database.execute('DELETE FROM vectors WHERE analysis_key=? AND audio_id=?', (self.key, audio_id))
            self.database.connection().executemany('INSERT INTO vectors VALUES(?,?,?,?,?,?)',
                [(self.key, row+i, audio_id, int(s[0]), float(s[1]), float(s[2])) for i, s in enumerate(segments)])
            self.database.execute('UPDATE stores SET next_row=? WHERE analysis_key=?', (row+len(segments), self.key))
            self.database.execute("""INSERT INTO analysis(audio_id,analysis_key,model_key,state,segments,error,updated) VALUES(?,?,?,'Ready',?,NULL,?)
                ON CONFLICT(audio_id,analysis_key) DO UPDATE SET state='Ready',segments=excluded.segments,error=NULL,updated=excluded.updated""",
                (audio_id, self.key, self.model_key, sum(1 for s in segments if s[0] >= 0), time.time()))

    def mark(self, audio_id, state, error=None):
        self.database.execute("""INSERT INTO analysis(audio_id,analysis_key,model_key,state,segments,error,updated) VALUES(?,?,?,?,0,?,?)
            ON CONFLICT(audio_id,analysis_key) DO UPDATE SET state=excluded.state,error=excluded.error,updated=excluded.updated""",
            (audio_id, self.key, self.model_key, state, error, time.time()))

    # -- reading -------------------------------------------------------------
    def pending(self, retry_failed=False, audio_ids=None):
        states = "('Ready')" if retry_failed else "('Ready','Failed')"
        rows = self.database.query(f"""SELECT a.audio_id,a.absolute_path,a.filename,a.duration FROM assets a WHERE a.status='present'
            AND a.metadata_state='Ready' AND NOT EXISTS(SELECT 1 FROM analysis s WHERE s.audio_id=a.audio_id AND s.analysis_key=? AND s.state IN {states})
            ORDER BY a.duration""", (self.key,))
        if audio_ids is not None:
            wanted = set(audio_ids); rows = [r for r in rows if r['audio_id'] in wanted]
        return rows

    def progress(self):
        row = self.database.one("""SELECT SUM(s.state='Ready') ready, SUM(s.state='Failed') failed FROM analysis s JOIN assets a
            ON a.audio_id=s.audio_id AND a.status='present' WHERE s.analysis_key=?""", (self.key,))
        return {'ready': row['ready'] or 0, 'failed': row['failed'] or 0}

    def asset_vectors(self, audio_id):
        rows = self.database.query('SELECT row,segment,start,stop FROM vectors WHERE analysis_key=? AND audio_id=? ORDER BY segment', (self.key, audio_id))
        if not rows: return [], np.zeros((0, self.dimension), np.float32)
        data = np.memmap(self.vectors_path, dtype=np.float16, mode='r').reshape(-1, self.dimension)
        return [dict(r) for r in rows], np.asarray(data[[r['row'] for r in rows]], dtype=np.float32)

    def index(self):
        provider = PROVIDERS.get(self.descriptor.get('indexProvider') or 'flat')
        if provider is None: raise CyToolError('InvalidState', 'Unknown index provider: '+str(self.descriptor.get('indexProvider')))
        state = self.database.one('SELECT next_row,generation FROM stores WHERE analysis_key=?', (self.key,))
        count = self.database.one('SELECT COUNT(*) c FROM vectors WHERE analysis_key=?', (self.key,))['c']
        signature = (self.library.id, self.key, state['next_row'], state['generation'], count)
        with _cache_lock:
            cached = _cache.get((self.library.id, self.key))
            if cached and cached.signature == signature: return cached
        built = provider.build(self, signature)
        with _cache_lock: _cache[(self.library.id, self.key)] = built
        return built

    # -- maintenance ------------------------------------------------------
    def compact(self):
        """Drop dead vector slots (modified or removed assets). Returns reclaimed row count."""
        with self._write_lock:
            rows = self.database.query('SELECT row FROM vectors WHERE analysis_key=? ORDER BY row', (self.key,))
            state = self.database.one('SELECT next_row FROM stores WHERE analysis_key=?', (self.key,))
            if not self.vectors_path.is_file() or len(rows) == state['next_row']: return 0
            data = np.memmap(self.vectors_path, dtype=np.float16, mode='r').reshape(-1, self.dimension)
            kept = np.asarray(data[[r['row'] for r in rows]]); del data
            temporary = self.vectors_path.with_suffix('.compact'); kept.tofile(temporary)
            with self.database.transaction():
                for new, row in enumerate(rows):
                    if new != row['row']: self.database.execute('UPDATE vectors SET row=? WHERE analysis_key=? AND row=?', (-new-1, self.key, row['row']))
                self.database.execute('UPDATE vectors SET row=-row-1 WHERE analysis_key=? AND row<0', (self.key,))
                self.database.execute('UPDATE stores SET next_row=?, generation=generation+1 WHERE analysis_key=?', (len(rows), self.key))
                temporary.replace(self.vectors_path)
            return state['next_row']-len(rows)

    def delete(self):
        with _cache_lock: _cache.pop((self.library.id, self.key), None)
        with self.database.transaction():
            for table in ('vectors', 'analysis', 'stores'): self.database.execute(f'DELETE FROM {table} WHERE analysis_key=?', (self.key,))
            remaining = self.database.one('SELECT COUNT(*) c FROM stores WHERE model_key=?', (self.model_key,))['c']
            if not remaining:
                self.database.execute("DELETE FROM tags WHERE source='auto' AND model_key=?", (self.model_key,))
                self.database.execute("DELETE FROM asset_categories WHERE source='auto' AND model_key=?", (self.model_key,))
                self.database.execute('DELETE FROM captions WHERE model_key=?', (self.model_key,))
        shutil.rmtree(self.directory, ignore_errors=True)


def list_stores(library, database):
    out = []
    for row in database.query('SELECT * FROM stores ORDER BY created'):
        store = EmbeddingStore(library, database, row['analysis_key'], row)
        size = store.vectors_path.stat().st_size if store.vectors_path.is_file() else 0
        out.append({'analysisKey': store.key, 'modelKey': store.model_key, 'dimension': store.dimension, 'config': store.config,
                    'model': store.descriptor, 'bytes': size, 'rows': row['next_row'], **store.progress(), 'directory': str(store.directory)})
    return out


# ---------------------------------------------------------------------------
# Index providers. 'flat' is exact cosine search; an ANN provider can be registered later
# under another name and selected per model with descriptor.indexProvider.
# ---------------------------------------------------------------------------
class FlatIndex:
    CHUNK = 65536

    def __init__(self, store, signature):
        self.signature, self.dimension = signature, store.dimension
        rows = store.database.query('SELECT row,audio_id,segment,start,stop FROM vectors WHERE analysis_key=? ORDER BY audio_id,segment', (store.key,))
        self.size = len(rows)
        self.audio_ids, self.starts = [], []
        previous = None
        for position, row in enumerate(rows):
            if row['audio_id'] != previous:
                self.audio_ids.append(row['audio_id']); self.starts.append(position); previous = row['audio_id']
        self.starts = np.asarray(self.starts, dtype=np.int64)
        self.segment = np.fromiter((r['segment'] for r in rows), np.int32, self.size)
        self.start = np.fromiter((r['start'] for r in rows), np.float32, self.size)
        self.stop = np.fromiter((r['stop'] for r in rows), np.float32, self.size)
        self.position = {audio_id: i for i, audio_id in enumerate(self.audio_ids)}
        if self.size:
            data = np.memmap(store.vectors_path, dtype=np.float16, mode='r').reshape(-1, store.dimension)
            self.matrix = np.ascontiguousarray(data[np.fromiter((r['row'] for r in rows), np.int64, self.size)])
        else: self.matrix = np.zeros((0, store.dimension), np.float16)

    def similarities(self, queries):
        """[rows, queries] cosine similarities, computed in float32 chunks."""
        queries = np.asarray(queries, dtype=np.float32)
        queries = queries/np.maximum(np.linalg.norm(queries, axis=1, keepdims=True), 1e-12)
        out = np.empty((self.size, len(queries)), np.float32)
        for begin in range(0, self.size, self.CHUNK):
            out[begin:begin+self.CHUNK] = self.matrix[begin:begin+self.CHUNK].astype(np.float32) @ queries.T
        return out

    def per_asset(self, similarities):
        """Best row of every asset for one similarity column: (scores[assets], rows[assets])."""
        if not self.size: return np.zeros(0, np.float32), np.zeros(0, np.int64)
        best = np.maximum.reduceat(similarities, self.starts)
        ends = np.append(self.starts[1:], self.size)
        rows = np.empty(len(self.starts), np.int64)
        # argmax per group without a Python loop over every asset: mark first occurrence of the maximum
        hit = similarities >= np.repeat(best, ends-self.starts)
        first = np.flatnonzero(hit); groups = np.searchsorted(self.starts, first, side='right')-1
        unique, index = np.unique(groups, return_index=True); rows[unique] = first[index]
        return best, rows


class FlatIndexProvider:
    name = 'flat'
    @staticmethod
    def build(store, signature):
        index = FlatIndex(store, signature)
        (store.directory/'Index').mkdir(parents=True, exist_ok=True)
        (store.directory/'Index'/'index.json').write_text(json.dumps({'provider': 'flat', 'metric': 'cosine', 'rows': index.size,
                                                                        'assets': len(index.audio_ids), 'built': time.time()}), 'utf-8')
        return index


PROVIDERS = {'flat': FlatIndexProvider}


def plan_segments(duration, config):
    """[(index, start, stop)] windows with overlap; short files get a single window."""
    length, overlap = config['segmentSeconds'], config['segmentOverlap']
    if not duration or duration <= length*1.15: return [(0, 0.0, float(duration or length))]
    step = max(0.5, length-overlap); segments, start = [], 0.0
    while start < duration-0.25*length or not segments:
        segments.append((len(segments), round(start, 3), round(min(duration, start+length), 3))); start += step
    limit = config['maxSegmentsPerFile']
    if len(segments) > limit:       # very long recordings: spread the windows evenly instead of truncating the end
        picks = np.linspace(0, len(segments)-1, limit).round().astype(int)
        segments = [(i, segments[p][1], segments[p][2]) for i, p in enumerate(picks)]
    return segments
