"""Analysis queue: what is missing, per asset and per model, and the loop that fills it.

The queue is derived, not stored: an asset is pending for a model when no Ready row exists
for the current analysis key of that model. Adding a model, or moving to a new version,
therefore analyses exactly the missing (asset, model) pairs and nothing else. Pause/resume
is a flag in the Library database, so the UI, the CLI and an MCP client share it.
"""
import os
import time

import numpy as np

from cytools_core import CyToolError
from .embeddings import EmbeddingStore, list_stores, plan_segments
from .registry import analysis_config, analysis_key, get_model
from .search import resolve_models
from .taxonomy import categorize

BATCH_SECONDS = 240.0
BATCH_FILES = 24
FAILURE_STREAK = 24


def queue_state(database): return database.control('analysis', 'running')


def set_queue_state(database, state):
    if state not in ('running', 'paused'): raise CyToolError('InvalidParameters', 'state must be running or paused')
    database.set_control('analysis', state); return state


def _wait_if_paused(database, cancelled, progress, percent):
    announced = False
    while queue_state(database) == 'paused':
        if cancelled(): return
        if not announced: progress(percent, currentStep='Paused', statusMessage='Analysis queue paused; resume to continue'); announced = True
        time.sleep(0.5)


def analyze_models(library, database, pool, registry, model_keys=None, *, progress=None, cancelled=None, log=None, retry_failed=False,
                   device=None, audio_ids=None, auto_label=True):
    progress = progress or (lambda *a, **k: None); cancelled = cancelled or (lambda: False); log = log or (lambda *a, **k: None)
    descriptors = resolve_models(library, registry, model_keys)
    if not descriptors:
        raise CyToolError('InvalidState', 'No embedding model selected: enable at least one installed model for this Library', recoverable=True)
    plans = []
    for descriptor in descriptors:
        if not descriptor.installed:
            raise CyToolError('ModelNotInstalled', descriptor['displayName']+' is not installed', recoverable=True,
                              suggested_action='Install the model from the Installation tab first')
        store = EmbeddingStore.for_model(library, database, descriptor, create=True)
        plans.append((descriptor, store, store.pending(retry_failed, audio_ids)))
    total = sum(len(p[2]) for p in plans) or 1
    done, failed, reports, started = 0, 0, [], time.monotonic()
    library.temporary.mkdir(parents=True, exist_ok=True)
    for descriptor, store, pending in plans:
        report = {'modelKey': descriptor.key, 'analysisKey': store.key, 'queued': len(pending), 'analyzed': 0, 'failed': 0}
        reports.append(report)
        if not pending: continue
        host = pool.host(descriptor)
        log(f'{descriptor.key}: {len(pending)} file(s) to analyze (analysis key {store.key})')
        position, fresh, streak = 0, [], 0
        while position < len(pending):
            _wait_if_paused(database, cancelled, progress, 100*done/total)
            if cancelled(): break
            batch, seconds = [], 0.0
            while position < len(pending) and len(batch) < BATCH_FILES and (not batch or seconds < BATCH_SECONDS):
                row = pending[position]; position += 1
                batch.append(row); seconds += min(row['duration'] or 0, store.config['segmentSeconds']*store.config['maxSegmentsPerFile'])
            items = [{'id': r['audio_id'], 'path': r['absolute_path'], 'segments': plan_segments(r['duration'], store.config)} for r in batch]
            output = library.temporary/f'embed-{os.getpid()}-{store.key}.npz'
            remaining = total-done
            eta = (time.monotonic()-started)/done*remaining if done else None
            fields = {'currentStep': 'Embedding with '+descriptor['displayName'], 'currentStepIndex': done+1, 'stepCount': total,
                      'currentFile': batch[0]['filename'], 'statusMessage': f'{remaining} remaining'}
            if eta is not None: fields['etaSeconds'] = round(eta, 1)
            progress(100*done/total, **fields)
            try: results = host.embed_audio(descriptor, items, output, device, cancelled)
            except CyToolError as exc:
                if exc.code == 'Cancelled': break
                raise
            with np.load(output) as arrays:
                for result in results:
                    if result['ok']:
                        store.add(result['id'], [tuple(s) for s in result['segments']], arrays[result['id']])
                        report['analyzed'] += 1; fresh.append(result['id'])
                    else:
                        store.mark(result['id'], 'Failed', result['error']); report['failed'] += 1; failed += 1
                        log(f"{descriptor.key}: {result['id']} failed: {result['error']}", level='Warning')
                    streak = 0 if result['ok'] else streak+1
                    if streak >= FAILURE_STREAK and not report['analyzed']:
                        # Nothing ever succeeded: this is an engine/adapter problem, not bad audio files. Stop instead of failing the whole Library.
                        raise CyToolError('EngineError', f"{descriptor['displayName']} failed on {streak} files in a row: {result['error']}", recoverable=True,
                                          suggested_action='Check data/logs/model-worker-*.log, repair the model or the engine, then run analyze_library with retryFailed=true')
            try: output.unlink()
            except OSError: pass
            done += len(batch)
        if auto_label and fresh and descriptor.has('ZeroShotTagging') and not cancelled():
            progress(100*done/total, currentStep='Categorizing with '+descriptor['displayName'])
            report['labels'] = categorize(library, database, pool, descriptor, fresh, device, cancelled)
    return {'models': reports, 'analyzed': sum(r['analyzed'] for r in reports), 'failed': failed, 'cancelled': bool(cancelled()),
            'seconds': round(time.monotonic()-started, 2)}


def library_status(library, database, registry):
    """Global figures of the explorer header: files, metadata %, waveform %, one line per model."""
    counts = database.counts()
    present = counts['present'] or 0
    ready_for_models = database.one("SELECT COUNT(*) c FROM assets WHERE status='present' AND metadata_state='Ready'")['c']
    models, current = [], set()
    for key in library.enabled_models:
        descriptor = registry.get(key)
        if descriptor is None:
            models.append({'modelKey': key, 'state': 'Unregistered', 'ready': 0, 'failed': 0, 'pending': 0, 'percent': 0.0}); continue
        config = analysis_config(descriptor, library.settings)
        identifier, _ = analysis_key(descriptor, config)
        current.add(identifier)
        row = database.one("""SELECT SUM(s.state='Ready') ready, SUM(s.state='Failed') failed FROM analysis s JOIN assets a
            ON a.audio_id=s.audio_id AND a.status='present' WHERE s.analysis_key=?""", (identifier,))
        ready, bad = row['ready'] or 0, row['failed'] or 0
        models.append({'modelKey': key, 'displayName': descriptor['displayName'], 'analysisKey': identifier, 'installed': descriptor.installed,
                       'ready': ready, 'failed': bad, 'pending': max(0, ready_for_models-ready-bad),
                       'percent': round(100*ready/ready_for_models, 1) if ready_for_models else 0.0,
                       'state': 'Ready' if ready_for_models and ready >= ready_for_models else ('NotInstalled' if not descriptor.installed else 'Pending')})
    stores = list_stores(library, database)
    for store in stores: store['current'] = store['analysisKey'] in current
    reasons = [{'error': (r['error'] or '')[:160], 'count': r['c']} for r in database.query(
        "SELECT SUBSTR(error, 1, INSTR(error||':', ':')) error, COUNT(*) c FROM assets WHERE status='present' AND metadata_state='Failed' GROUP BY 1 ORDER BY c DESC LIMIT 6")]
    percent = lambda value: round(100*value/present, 1) if present else 0.0
    return {'libraryId': library.id, 'name': library.name, 'files': present, 'missing': counts['missing'], 'totalSeconds': counts['seconds'],
            'totalBytes': counts['bytes'], 'favorites': counts['favorites'],
            'metadata': {'ready': counts['metadata_ready'], 'failed': counts['metadata_failed'], 'percent': percent(counts['metadata_ready'])},
            'waveforms': {'ready': counts['waveform_ready'], 'failed': counts['waveform_failed'], 'percent': percent(counts['waveform_ready'])},
            'failureReasons': reasons,
            'models': models, 'stores': stores, 'queueState': queue_state(database), 'cache': str(library.cache),
            'folders': [{**root, 'available': os.path.isdir(root['path'])} for root in library.roots]}


def asset_states(library, database, registry, audio_id):
    """Per-asset state lines: Metadata, Waveform, then one line per enabled model."""
    asset = database.asset(audio_id)
    if not asset: raise CyToolError('NotFound', 'Unknown asset: '+str(audio_id))
    lines = [{'name': 'Metadata', 'state': asset['metadata_state']}, {'name': 'Waveform', 'state': asset['waveform_state']}]
    for key in library.enabled_models:
        descriptor = registry.get(key)
        if descriptor is None: lines.append({'name': key, 'state': 'Unregistered'}); continue
        identifier, _ = analysis_key(descriptor, analysis_config(descriptor, library.settings))
        row = database.one('SELECT state,segments,error FROM analysis WHERE audio_id=? AND analysis_key=?', (audio_id, identifier))
        lines.append({'name': descriptor['displayName'], 'modelKey': key, 'state': row['state'] if row else 'Not Analyzed',
                      'segments': row['segments'] if row else 0, 'error': row['error'] if row else None})
    return lines


def probable_duplicates(library, database, registry, model_key=None, threshold=0.985, duration_tolerance=0.02, cancelled=None, limit=20000):
    """Group sounds that are very close in one embedding space and nearly equal in length. Reports only."""
    descriptors = resolve_models(library, registry, [model_key] if model_key else None)
    if not descriptors: raise CyToolError('InvalidState', 'No embedding model enabled')
    descriptor = descriptors[0]
    store = EmbeddingStore.for_model(library, database, descriptor)
    if store is None: raise CyToolError('InvalidState', 'Library is not analyzed with '+descriptor.key)
    index = store.index()
    if len(index.audio_ids) > limit:
        raise CyToolError('TooLarge', f'Probable-duplicate detection is limited to {limit} analyzed files per run in this version')
    matrix = index.matrix[index.starts].astype(np.float32)
    durations = {r['audio_id']: r['duration'] or 0 for r in database.query('SELECT audio_id,duration FROM assets')}
    lengths = np.array([durations.get(a, 0) for a in index.audio_ids], np.float32)
    parent = list(range(len(matrix)))
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for begin in range(0, len(matrix), 2048):
        if cancelled and cancelled(): break
        block = matrix[begin:begin+2048] @ matrix.T
        close = np.argwhere(block >= threshold)
        for i, j in close:
            i += begin
            if i < j and abs(lengths[i]-lengths[j]) <= duration_tolerance*max(lengths[i], lengths[j], 0.05): parent[find(i)] = find(j)
    groups = {}
    for i in range(len(matrix)): groups.setdefault(find(i), []).append(index.audio_ids[i])
    groups = [members for members in groups.values() if len(members) > 1]
    with database.transaction():
        database.execute("UPDATE assets SET duplicate_group=NULL WHERE duplicate_group LIKE 'sim:%'")
        for number, members in enumerate(groups):
            database.execute("UPDATE assets SET duplicate_group=? WHERE duplicate_group IS NULL AND audio_id IN (%s)" % ','.join('?'*len(members)),
                             ['sim:%05d' % number]+members)
    return {'modelKey': descriptor.key, 'groups': len(groups), 'files': sum(len(g) for g in groups), 'threshold': threshold,
            'note': 'Similarity groups are suggestions; exact duplicates keep their hash group. Nothing is deleted.'}
