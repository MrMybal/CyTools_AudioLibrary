"""Incremental Library scan and model-independent analysis (metadata, waveform, loudness).

Identity is (size, fast hash), never the path alone, so a renamed or moved file keeps its
AudioId together with its waveform, embeddings, tags and notes. Only new and modified files
are handed to the analysis stages; missing files are flagged, never deleted automatically.
"""
import hashlib
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from . import AUDIO_EXTENSIONS
from .audiofile import LoudnessMeter, blocks, probe
from .waveform import PyramidBuilder, waveform_path

HASH_CHUNK = 65536
# Never audio: AppleDouble resource forks ('._name.wav', 512 bytes) and the __MACOSX folders of zips made on macOS,
# plus desktop metadata files. They carry audio extensions and used to appear as thousands of 'Failed' files.
JUNK_DIRS = {'__macosx', '.git', '.svn', '$recycle.bin', 'system volume information'}
JUNK_PREFIXES = ('._',)
JUNK_NAMES = {'.ds_store', 'thumbs.db', 'desktop.ini'}


def is_junk(name):
    lower = name.lower()
    return lower.startswith(JUNK_PREFIXES) or lower in JUNK_NAMES


def fast_hash(path, size=None):
    """SHA-1 of the size and of three 64 KiB windows: cheap on large files, stable across moves."""
    size = os.path.getsize(path) if size is None else size
    digest = hashlib.sha1(str(size).encode())
    with open(path, 'rb') as handle:
        for offset in sorted({0, max(0, size//2-HASH_CHUNK//2), max(0, size-HASH_CHUNK)}):
            handle.seek(offset); digest.update(handle.read(HASH_CHUNK))
    return digest.hexdigest()


def content_hash(path, cancelled=None):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        while True:
            if cancelled and cancelled(): return None
            chunk = handle.read(1 << 20)
            if not chunk: break
            digest.update(chunk)
    return digest.hexdigest()


def walk(folder, cancelled=None):
    """Recursive listing of audio files; directory symlinks are not followed (no loops)."""
    stack = [str(folder)]
    while stack:
        if cancelled and cancelled(): return
        current = stack.pop()
        try: entries = list(os.scandir(current))
        except OSError: continue
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    if entry.name.lower() not in JUNK_DIRS: stack.append(entry.path)
                elif entry.is_file() and entry.name.lower().endswith(AUDIO_EXTENSIONS) and not is_junk(entry.name):
                    yield entry.path, entry.stat()
            except OSError: continue


def check(library, database, root_ids=None, cancelled=None, examples=8):
    """Read-only difference between the folders and the database: nothing is hashed, nothing is written.

    Cheap enough to run in the background every few minutes (one directory walk, size and mtime only).
    A moved file shows up here as one new + one missing; scan_library recognises it by its content hash.
    An unplugged drive is reported as unavailable, never as thousands of missing files.
    """
    cancelled = cancelled or (lambda: False)
    fold = (lambda text: text.casefold()) if os.name == 'nt' else (lambda text: text)
    roots = [r for r in library.roots if r['enabled'] and (not root_ids or r['rootId'] in root_ids)]
    known = {(row['root_id'], fold(row['relative_path'])): row
             for row in database.query('SELECT root_id,relative_path,file_size,modified_time,status FROM assets')}
    report = {'new': 0, 'modified': 0, 'missing': 0, 'restored': 0, 'unchanged': 0, 'unavailableFolders': [],
              'examples': {'new': [], 'modified': [], 'missing': []}}
    seen, scanned = set(), set()
    for root in roots:
        base = Path(root['path'])
        if not base.is_dir(): report['unavailableFolders'].append(root['path']); continue
        scanned.add(root['rootId'])
        for path, stat in walk(base, cancelled):
            key = (root['rootId'], fold(os.path.relpath(path, base).replace('\\', '/')))
            seen.add(key); row = known.get(key)
            if row is None: kind = 'new'
            elif row['file_size'] != stat.st_size or abs(row['modified_time']-stat.st_mtime) >= 0.002: kind = 'modified'
            elif row['status'] != 'present': kind = 'restored'
            else: report['unchanged'] += 1; continue
            report[kind] += 1
            if kind in report['examples'] and len(report['examples'][kind]) < examples: report['examples'][kind].append(path)
    if cancelled(): return dict(report, cancelled=True, changed=False)
    for key, row in known.items():
        if key[0] in scanned and key not in seen and row['status'] == 'present':
            report['missing'] += 1
            if len(report['examples']['missing']) < examples: report['examples']['missing'].append(row['relative_path'])
    pending = database.one("SELECT COUNT(*) c FROM assets WHERE status='present' AND (metadata_state='Pending' OR waveform_state='Pending')")['c']
    report.update(pendingMetadata=pending, changed=bool(report['new'] or report['modified'] or report['missing'] or report['restored'] or pending))
    return report


def forget_analysis(database, audio_ids):
    """Content changed: derived data of these assets is stale. User data is preserved."""
    connection = database.connection()
    for audio_id in audio_ids:
        connection.execute('DELETE FROM analysis WHERE audio_id=?', (audio_id,))
        connection.execute('DELETE FROM vectors WHERE audio_id=?', (audio_id,))
        connection.execute("DELETE FROM tags WHERE audio_id=? AND source='auto'", (audio_id,))
        connection.execute("DELETE FROM asset_categories WHERE audio_id=? AND source='auto'", (audio_id,))
        connection.execute('DELETE FROM captions WHERE audio_id=?', (audio_id,))
    connection.execute("UPDATE stores SET generation=generation+1")


def scan(library, database, root_ids=None, progress=None, cancelled=None, threads=6):
    progress = progress or (lambda *a, **k: None)
    cancelled = cancelled or (lambda: False)
    roots = [r for r in library.roots if r['enabled'] and (not root_ids or r['rootId'] in root_ids)]
    summary = {'unchanged': 0, 'new': 0, 'modified': 0, 'moved': 0, 'missing': 0, 'restored': 0, 'unreadable': 0,
               'folders': len(roots), 'unavailableFolders': []}
    # Rows created by an earlier version for junk files are removed: they were never audio (no user data can exist on them
    # that is worth keeping, and they would otherwise turn into thousands of 'missing' entries).
    junk = [r['audio_id'] for r in database.query("SELECT audio_id,filename,relative_path,extension FROM assets")
            if is_junk(r['filename']) or r['extension'] not in AUDIO_EXTENSIONS or any(part.lower() in JUNK_DIRS for part in r['relative_path'].split('/')[:-1])]
    if junk:
        with database.transaction():
            forget_analysis(database, junk)
            for audio_id in junk:
                for table in ('tags', 'asset_categories', 'assets'): database.execute(f'DELETE FROM {table} WHERE audio_id=?', (audio_id,))
        for audio_id in junk:
            try: waveform_path(library, audio_id).unlink()
            except OSError: pass
    summary['junkRemoved'] = len(junk)
    known = {}
    for row in database.query('SELECT audio_id,root_id,relative_path,file_size,modified_time,fast_hash,status FROM assets'):
        known[(row['root_id'], row['relative_path'].casefold() if os.name == 'nt' else row['relative_path'])] = row
    seen, to_hash = set(), []
    now = time.time()
    for index, root in enumerate(roots):
        base = Path(root['path'])
        if not base.is_dir():
            # An unplugged drive must not flag thousands of files as missing.
            summary['unavailableFolders'].append(root['path'])
            seen.update(key for key in known if key[0] == root['rootId'])
            continue
        count = 0
        for path, stat in walk(base, cancelled):
            relative = os.path.relpath(path, base).replace('\\', '/')
            key = (root['rootId'], relative.casefold() if os.name == 'nt' else relative)
            row = known.get(key); seen.add(key); count += 1
            if row is not None and row['file_size'] == stat.st_size and abs(row['modified_time']-stat.st_mtime) < 0.002:
                if row['status'] != 'present':
                    database.execute("UPDATE assets SET status='present' WHERE audio_id=?", (row['audio_id'],)); summary['restored'] += 1
                else: summary['unchanged'] += 1
            else: to_hash.append((root, path, relative, stat, row))
            if count % 500 == 0: progress(5*(index+count/(count+2000))/max(1, len(roots)), currentStep='Listing '+root['path'], statusMessage=f'{count} files')
        root['lastScan'] = now
    if cancelled(): return dict(summary, cancelled=True)

    def hashed(item):
        root, path, relative, stat, row = item
        try: return item, fast_hash(path, stat.st_size)
        except OSError: return item, None
    results = []
    with ThreadPoolExecutor(max_workers=max(1, threads)) as pool:
        futures = [pool.submit(hashed, item) for item in to_hash]
        for done, future in enumerate(as_completed(futures), 1):
            if cancelled():
                for other in futures: other.cancel()
                return dict(summary, cancelled=True)
            results.append(future.result())
            if done % 200 == 0 or done == len(futures):
                progress(5+85*done/len(futures), currentStep='Identifying files', currentStepIndex=done, stepCount=len(futures))

    scanned_roots = {r['rootId'] for r in roots}
    vanished = {}
    for key, row in known.items():
        if key not in seen and key[0] in scanned_roots or row['status'] == 'missing' and key not in seen:
            vanished.setdefault((row['file_size'], row['fast_hash']), []).append(row)
    modified_ids = []
    with database.transaction():
        connection = database.connection()
        for (root, path, relative, stat, row), digest in results:
            if digest is None: summary['unreadable'] += 1; continue
            filename = os.path.basename(path); extension = os.path.splitext(filename)[1].lower()
            created = getattr(stat, 'st_birthtime', None) or stat.st_ctime
            if row is not None:
                if row['fast_hash'] == digest and row['file_size'] == stat.st_size:      # touched, same content
                    connection.execute("UPDATE assets SET modified_time=?, status='present' WHERE audio_id=?", (stat.st_mtime, row['audio_id']))
                    summary['unchanged'] += 1
                else:
                    connection.execute("""UPDATE assets SET file_size=?, modified_time=?, fast_hash=?, content_hash=NULL, status='present',
                        metadata_state='Pending', waveform_state='Pending', error=NULL, duplicate_group=NULL WHERE audio_id=?""",
                        (stat.st_size, stat.st_mtime, digest, row['audio_id']))
                    modified_ids.append(row['audio_id']); summary['modified'] += 1
                continue
            candidates = vanished.get((stat.st_size, digest))
            if candidates:
                moved = candidates.pop()
                connection.execute("""UPDATE assets SET root_id=?, relative_path=?, absolute_path=?, filename=?, extension=?, modified_time=?,
                    status='present' WHERE audio_id=?""", (root['rootId'], relative, path, filename, extension, stat.st_mtime, moved['audio_id']))
                summary['moved'] += 1
                continue
            connection.execute("""INSERT INTO assets(audio_id,root_id,relative_path,absolute_path,filename,extension,file_size,created_time,
                modified_time,fast_hash,added_time) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (uuid.uuid4().hex, root['rootId'], relative, path, filename, extension, stat.st_size, created, stat.st_mtime, digest, now))
            summary['new'] += 1
        for rows in vanished.values():
            for row in rows:
                if row['status'] == 'present':
                    connection.execute("UPDATE assets SET status='missing' WHERE audio_id=?", (row['audio_id'],)); summary['missing'] += 1
        forget_analysis(database, modified_ids)
        connection.execute('INSERT INTO scans(time,summary) VALUES(?,?)', (now, __import__('json').dumps(summary)))
    library.save()
    progress(92, currentStep='Looking for duplicates')
    summary['duplicateGroups'] = find_exact_duplicates(database, cancelled)
    progress(100, currentStep='Scan complete')
    return summary


def find_exact_duplicates(database, cancelled=None):
    """Group byte-identical files. Candidates share size and fast hash; SHA-256 confirms. Nothing is deleted."""
    groups = database.query("""SELECT file_size, fast_hash FROM assets WHERE status='present'
        GROUP BY file_size, fast_hash HAVING COUNT(*)>1""")
    database.execute("UPDATE assets SET duplicate_group=NULL WHERE duplicate_group IS NOT NULL AND duplicate_group NOT LIKE 'sim:%'")
    count = 0
    for group in groups:
        if cancelled and cancelled(): break
        rows = database.query("SELECT audio_id,absolute_path,content_hash FROM assets WHERE status='present' AND file_size=? AND fast_hash=?",
                              (group['file_size'], group['fast_hash']))
        by_hash = {}
        for row in rows:
            digest = row['content_hash']
            if not digest:
                try: digest = content_hash(row['absolute_path'], cancelled)
                except OSError: digest = None
                if digest: database.execute('UPDATE assets SET content_hash=? WHERE audio_id=?', (digest, row['audio_id']))
            if digest: by_hash.setdefault(digest, []).append(row['audio_id'])
        for digest, members in by_hash.items():
            if len(members) > 1:
                count += 1
                database.execute('UPDATE assets SET duplicate_group=? WHERE audio_id IN (%s)' % ','.join('?'*len(members)), [digest[:16]]+members)
    return count


def analyze_file(path, target, loudness=True):
    """One decoding pass: technical metadata, level statistics and the waveform pyramid."""
    info = probe(path)
    meter = builder = None
    frames = 0
    for block, rate in blocks(path):
        if meter is None:
            meter = LoudnessMeter(rate, block.shape[1], gated=loudness); builder = PyramidBuilder(rate, block.shape[1])
        meter.feed(block); builder.feed(block); frames += len(block)
    if not frames: raise ValueError('No audio samples decoded')
    info.update(meter.result())
    info['duration'] = frames/info['sample_rate']        # decoded length is authoritative
    info['waveform'] = builder.write(target)
    return info


def analyze_common(library, database, progress=None, cancelled=None, threads=6, retry_failed=False, audio_ids=None):
    """Metadata + waveform for assets that lack them. Existing results are never recomputed."""
    import json
    progress = progress or (lambda *a, **k: None)
    cancelled = cancelled or (lambda: False)
    states = ("'Pending','Failed'" if retry_failed else "'Pending'")
    sql = f"SELECT audio_id,absolute_path,filename FROM assets WHERE status='present' AND (metadata_state IN ({states}) OR waveform_state IN ({states}))"
    rows = database.query(sql)
    if audio_ids is not None:
        wanted = set(audio_ids); rows = [r for r in rows if r['audio_id'] in wanted]
    total, done, failed = len(rows), 0, 0
    loudness = library.settings['computeLoudness']

    def work(row):
        try: return row, analyze_file(row['absolute_path'], waveform_path(library, row['audio_id']), loudness), None
        except Exception as exc: return row, None, (type(exc).__name__+': '+str(exc))[:500]
    pending = []
    with ThreadPoolExecutor(max_workers=max(1, threads)) as pool:
        iterator = iter(rows); active = set()
        def refill():
            while len(active) < threads*2:
                row = next(iterator, None)
                if row is None: return
                active.add(pool.submit(work, row))
        refill()
        while active:
            if cancelled():
                for future in active: future.cancel()
                break
            finished = next(as_completed(active)); active.discard(finished); refill()
            row, info, error = finished.result(); done += 1
            pending.append((row, info, error)); failed += bool(error)
            if len(pending) >= 50 or not active:
                with database.transaction():
                    for item, value, problem in pending:
                        if problem:
                            database.execute("UPDATE assets SET metadata_state='Failed', waveform_state='Failed', error=? WHERE audio_id=?", (problem, item['audio_id']))
                        else:
                            database.execute("""UPDATE assets SET duration=?,channels=?,sample_rate=?,bit_depth=?,codec=?,container=?,bitrate=?,
                                peak_db=?,rms_db=?,lufs=?,embedded=?,metadata_state='Ready',waveform_state='Ready',error=NULL WHERE audio_id=?""",
                                (value['duration'], value['channels'], value['sample_rate'], value['bit_depth'], value['codec'], value['container'],
                                 value['bitrate'], value['peak_db'], value['rms_db'], value['lufs'], json.dumps(value.get('embedded') or {}), item['audio_id']))
                pending.clear()
            progress(100*done/max(1, total), currentStep='Metadata and waveform', currentStepIndex=done, stepCount=total, currentFile=row['filename'])
    return {'processed': done, 'failed': failed, 'remaining': total-done, 'cancelled': bool(cancelled())}
