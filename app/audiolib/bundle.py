"""Copies of chosen sounds gathered in a folder the user picks: an import list for a game engine, a DAW, a project.

The originals are only read. A copy never overwrites anything: a file already there with the same content is
left as it is, a different one with the same name gets a numbered name. Each copy is written under a temporary
name and renamed once its size matches the source, so an interrupted export never leaves a truncated file that
looks complete.

A destination that would put a copy inside a folder of any Library, or inside a cache, is refused before anything
is copied: the next scan would otherwise index the copies as new sounds of the Library.

`bundle.json`, written next to the copies unless the caller turns it off, lists every file with its source,
AudioId, duration, tags and categories. Exporting into the same folder again adds to it: a bundle can be built in
several passes.
"""
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

from cytools_core import CyToolError
from .database import fetch_rows
from .library import flatten_taxonomy, get_library, list_libraries

LAYOUTS = ('flat', 'folders')
MANIFEST = 'bundle.json'


def digest(path):
    value = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''): value.update(block)
    return value.hexdigest()


def protected_folders():
    """[(path, reason)]: every folder of every Library, and every cache. Copies must never land there."""
    folders = []
    for summary in list_libraries():
        try: library = get_library(summary.id)
        except CyToolError: continue
        folders += [(Path(root['path']).resolve(), f"a folder of the Library '{library.name}'") for root in library.roots]
        folders.append((Path(library.cache).resolve(), f"the cache of the Library '{library.name}'"))
    return folders


def free_name(target, taken):
    """`name.wav`, else `name (2).wav`, `name (3).wav`... skipping names on disk and names already planned."""
    candidate, number = target, 2
    while candidate.exists() or str(candidate).casefold() in taken:
        candidate = target.with_name(f'{target.stem} ({number}){target.suffix}'); number += 1
    return candidate


def plan(library, database, audio_ids, destination, layout='flat'):
    """Where each sound would go, checked before anything is copied."""
    if layout not in LAYOUTS: raise CyToolError('InvalidParameters', 'layout must be one of '+', '.join(LAYOUTS))
    destination = Path(str(destination or ''))
    if not destination.is_absolute(): raise CyToolError('InvalidParameters', 'destination must be an absolute folder path')
    destination = destination.resolve()
    if destination.exists() and not destination.is_dir(): raise CyToolError('InvalidParameters', 'destination exists and is not a folder')
    roots = {root['rootId']: Path(root['path']) for root in library.roots}
    rows, items = {}, []
    ids = list(dict.fromkeys(audio_ids))
    for begin in range(0, len(ids), 500): rows.update(fetch_rows(database, ids[begin:begin+500]))
    for audio_id in ids:
        row = rows.get(audio_id)
        if not row: items.append({'audioId': audio_id, 'problem': 'unknown AudioId'}); continue
        source = Path(row['absolute_path'])
        if row['status'] != 'present' or not source.is_file():
            items.append({'audioId': audio_id, 'source': str(source), 'problem': 'missing on disk'}); continue
        if layout == 'flat': relative = Path(source.name)
        else:
            root = roots.get(row['root_id'])
            relative = Path(root.name if root and root.name else row['root_id'])/Path(str(row['relative_path']).replace('\\', '/'))
        items.append({'audioId': audio_id, 'row': row, 'source': source, 'relative': relative})
    for path, reason in protected_folders():
        for item in items:
            if 'relative' in item and (destination/item['relative']).resolve().is_relative_to(path):
                raise CyToolError('InvalidParameters', f'This destination would put copies inside {reason} ({path}). Choose a folder outside your Libraries and caches.',
                                  recoverable=True, suggested_action='Choose another destination folder')
    return destination, items


def export_bundle(library, database, audio_ids, destination, layout='flat', manifest=True, cancelled=None, progress=None):
    destination, items = plan(library, database, audio_ids, destination, layout)
    destination.mkdir(parents=True, exist_ok=True)
    names = {identifier: name for identifier, name, _, _ in flatten_taxonomy(library.taxonomy)}
    taken, entries, problems = set(), [], []
    counts = {'copied': 0, 'identical': 0, 'renamed': 0, 'missing': 0}
    copied_bytes = 0
    for position, item in enumerate(items):
        if cancelled and cancelled(): raise CyToolError('Cancelled', 'Bundle export cancelled')
        if progress: progress(100*position/max(1, len(items)), item.get('relative', ''))
        if 'problem' in item:
            counts['missing'] += 1; problems.append({k: str(v) for k, v in item.items() if k in ('audioId', 'source', 'problem')}); continue
        source, row = item['source'], item['row']
        target = destination/item['relative']
        target.parent.mkdir(parents=True, exist_ok=True)
        status = 'copied'
        if target.exists() and target.stat().st_size == source.stat().st_size and digest(target) == digest(source):
            status = 'identical'                   # already in the bundle: nothing to write
        else:
            if target.exists() or str(target).casefold() in taken:
                target = free_name(target, taken); status = 'renamed'
            partial = target.with_name(target.name+'.part')
            try:
                shutil.copy2(source, partial)
                if partial.stat().st_size != source.stat().st_size: raise OSError('size differs after copy')
                os.replace(partial, target)
            except OSError as exc:
                partial.unlink(missing_ok=True)
                raise CyToolError('IOError', f'Cannot copy {source.name} into the bundle: {exc}', recoverable=True) from None
            copied_bytes += target.stat().st_size
        taken.add(str(target).casefold())
        counts[status] += 1
        entries.append({'file': target.relative_to(destination).as_posix(), 'source': str(source), 'audioId': row['audio_id'],
                        'status': status, 'duration': row['duration'], 'sampleRate': row['sample_rate'], 'channels': row['channels'],
                        'tags': row['userTags']+[t for t in row['autoTags'] if t not in row['userTags']],
                        'categories': [names.get(c, c) for c in row['categories']], 'rating': row['rating'],
                        'description': row.get('description') or '', 'notes': row.get('notes') or ''})
    manifest_path = None
    if manifest:
        manifest_path = destination/MANIFEST
        previous = {}
        try:
            for entry in json.loads(manifest_path.read_text(encoding='utf-8')).get('files', []): previous[entry['file']] = entry
        except (OSError, ValueError, AttributeError): previous = {}
        for entry in entries: previous[entry['file']] = entry
        document = {'createdBy': 'CyTools_AudioLibrary', 'library': library.name, 'layout': layout,
                    'updated': time.strftime('%Y-%m-%dT%H:%M:%S'), 'files': sorted(previous.values(), key=lambda e: e['file'].casefold())}
        partial = manifest_path.with_name(MANIFEST+'.part')
        partial.write_text(json.dumps(document, indent=1, ensure_ascii=False)+'\n', encoding='utf-8')
        os.replace(partial, manifest_path)
    if progress: progress(100, 'Done')
    return {'destination': str(destination), 'layout': layout, **counts, 'bytesCopied': copied_bytes,
            'manifest': str(manifest_path) if manifest_path else None, 'files': entries, 'problems': problems}
