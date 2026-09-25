"""The only two functions of this Tool that change the user's original audio files.

Everything else opens audio read-only. These two are explicit operations (a tab in the interface, a `confirm`
flag for the CLI/MCP), never background work:

* rename: inside the same folder, never overwrites, keeps the extension, journalled so the last batch can be
  undone. The AudioId, tags, waveform and embeddings follow the file (the database row is updated in place).
* write metadata: tags are written into a temporary copy, the decoded audio of the copy is compared with the
  original sample for sample, and only then does the copy replace the original. A backup of the untouched file
  goes to the cache (not next to the audio) unless the caller turns it off. The database identity (size, date,
  hashes) is refreshed so that the next scan does not treat the file as modified and embeddings stay valid.
"""
import hashlib
import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path

from cytools_core import CyToolError
from .audiofile import blocks, probe
from .database import fetch_rows
from .library import flatten_taxonomy
from .scanner import fast_hash

RESERVED = {'con', 'prn', 'aux', 'nul', *(f'com{i}' for i in range(1, 10)), *(f'lpt{i}' for i in range(1, 10))}
FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
GENERIC = re.compile(r'^(sound|audio|track|untitled|new|recording|record|rec|file|sample|sfx|clip|take|export|bounce|mix|output|render|voice|memo|'
                     r'sans[ _-]?titre|nouveau|nouvel|enregistrement|piste|son)[\s_\-.]*(\(?\d+\)?)?$', re.I)
RECORDER = re.compile(r'^(zoom|ste|dr|mvi|vid|img|tascam|ls|h\dn?|wav|t)[-_ ]?\d{2,}', re.I)
HEXLIKE = re.compile(r'^[0-9a-f]{8,}(-[0-9a-f]{4,})*$', re.I)
ID3_FORMATS = ('.mp3', '.wav', '.aif', '.aiff', '.aifc')
VORBIS_FORMATS = ('.flac', '.ogg', '.oga', '.opus')
MP4_FORMATS = ('.m4a', '.mp4', '.aac')
FIELDS = ('description', 'tags', 'categories', 'rating', 'audioId')


def operations_dir(library):
    folder = library.cache/'Common'/'FileOperations'; folder.mkdir(parents=True, exist_ok=True)
    return folder


# ---------------------------------------------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------------------------------------------
def name_problem(stem):
    """Reason why a file name says nothing about its content, or '' when the name looks descriptive."""
    clean = stem.strip()
    letters = sum(c.isalpha() for c in clean)
    if len(clean) < 4: return 'very short name'
    if letters < max(3, len(clean)*0.35): return 'mostly digits'
    if GENERIC.match(clean): return 'generic name'
    if RECORDER.match(clean): return 'recorder or camera numbering'
    if HEXLIKE.match(clean): return 'identifier instead of a name'
    return ''


def words(text):
    return [w for w in re.split(r'[^0-9A-Za-zÀ-ÖØ-öø-ÿ]+', text) if w]


def build_stem(asset, category_names, template, max_tags):
    ordered = [c for c in asset['categories'] if c in category_names]
    leaf = max(ordered, key=lambda c: c.count('.'), default='')          # deepest category says the most
    tags = list(dict.fromkeys(asset['userTags']+asset['autoTags']))
    category_words = words(category_names.get(leaf, ''))
    stem_of = lambda word: word.lower().rstrip('s')                      # Explosions / explosion, Birds / bird
    seen = {stem_of(c) for c in category_words}; tag_words = []
    for word in (w for tag in tags for w in words(tag)):
        if stem_of(word) not in seen and ''.join(category_words).lower().find(stem_of(word)) < 0: seen.add(stem_of(word)); tag_words.append(word)
    tag_words = tag_words[:max_tags]
    values = {'category': ''.join(w.capitalize() for w in category_words), 'tags': '_'.join(w.capitalize() for w in tag_words),
              'original': '_'.join(words(Path(asset['filename']).stem)), 'duration': f"{(asset['duration'] or 0):.1f}s"}
    try: stem = template.format(**values)
    except (KeyError, IndexError, ValueError) as exc: raise CyToolError('InvalidParameters', 'Unknown field in the name template: '+str(exc)) from exc
    stem = re.sub(r'_+', '_', FORBIDDEN.sub('', stem)).strip('_ .-')
    return stem[:90]


def validate_name(name, extension):
    if not name or name != name.strip() or FORBIDDEN.search(name) or name.endswith('.'): raise CyToolError('InvalidParameters', 'Invalid file name: '+repr(name))
    if Path(name).stem.lower() in RESERVED: raise CyToolError('InvalidParameters', 'Reserved Windows name: '+name)
    if Path(name).suffix.lower() != extension.lower(): raise CyToolError('InvalidParameters', f'The extension must stay {extension}: {name}')
    if len(name) > 200: raise CyToolError('InvalidParameters', 'File name too long')


def suggest_names(library, database, audio_ids=None, only_badly_named=True, template='{category}_{tags}', max_tags=3, limit=500):
    """A plan, nothing is renamed. Files without any category or tag get no proposal (nothing to build a name from)."""
    names = {identifier: name for identifier, name, _, _ in flatten_taxonomy(library.taxonomy)}
    if audio_ids is None:
        audio_ids = [r['audio_id'] for r in database.query("SELECT audio_id FROM assets WHERE status='present' ORDER BY relative_path")]
    plan, skipped, taken = [], 0, {}
    for begin in range(0, len(audio_ids), 500):
        rows = fetch_rows(database, audio_ids[begin:begin+500])
        for audio_id in audio_ids[begin:begin+500]:
            asset = rows.get(audio_id)
            if not asset or asset['status'] != 'present': continue
            path = Path(asset['absolute_path']); reason = name_problem(path.stem)
            if only_badly_named and not reason: continue
            stem = build_stem(asset, names, template, max_tags)
            if not stem: skipped += 1; continue
            folder = taken.setdefault(str(path.parent).lower(), {p.name.lower() for p in path.parent.iterdir()} if path.parent.is_dir() else set())
            candidate, counter = stem+path.suffix, 1
            while candidate.lower() in folder and candidate.lower() != path.name.lower():
                counter += 1; candidate = f'{stem}_{counter:02d}{path.suffix}'
            if candidate == path.name: continue
            folder.add(candidate.lower())
            plan.append({'audioId': audio_id, 'currentName': path.name, 'proposedName': candidate, 'folder': str(path.parent), 'reason': reason or 'requested'})
            if len(plan) >= limit: return {'plan': plan, 'withoutLabels': skipped, 'truncated': True}
    return {'plan': plan, 'withoutLabels': skipped, 'truncated': False}


def rename_files(library, database, renames, cancelled=None):
    batch, journal = uuid.uuid4().hex[:12], operations_dir(library)/'renames.jsonl'
    results = []
    for item in renames:
        if cancelled and cancelled(): break
        asset = database.asset(item['audioId'])
        try:
            if not asset or asset['status'] != 'present': raise CyToolError('NotFound', 'Unknown or missing asset')
            source = Path(asset['absolute_path'])
            if not source.is_file(): raise CyToolError('NotFound', 'The file is no longer there; rescan the Library')
            validate_name(item['newName'], source.suffix)
            target = source.with_name(item['newName'])
            if target.name == source.name: raise CyToolError('InvalidParameters', 'Same name')
            if target.exists() and target.name.lower() != source.name.lower(): raise CyToolError('Conflict', 'A file with this name already exists; nothing is overwritten')
            os.rename(source, target)
            relative = (Path(asset['relative_path']).parent/target.name).as_posix()
            if relative.startswith('./'): relative = relative[2:]
            try:
                database.execute('UPDATE assets SET absolute_path=?, relative_path=?, filename=? WHERE audio_id=?', (str(target), relative, target.name, asset['audio_id']))
            except Exception:
                os.rename(target, source); raise
            with journal.open('a', encoding='utf-8') as handle:
                handle.write(json.dumps({'batch': batch, 'time': time.time(), 'audioId': asset['audio_id'], 'from': str(source), 'to': str(target)}, ensure_ascii=False)+'\n')
            results.append({'audioId': asset['audio_id'], 'ok': True, 'from': source.name, 'to': target.name, 'path': str(target)})
        except (CyToolError, OSError) as exc:
            results.append({'audioId': item['audioId'], 'ok': False, 'error': getattr(exc, 'message', str(exc))})
    return {'batch': batch, 'renamed': sum(r['ok'] for r in results), 'failed': sum(not r['ok'] for r in results), 'results': results}


def undo_rename(library, database):
    """Reverse the most recent batch that has not been undone yet."""
    journal = operations_dir(library)/'renames.jsonl'
    entries = [json.loads(line) for line in journal.read_text('utf-8').splitlines() if line.strip()] if journal.is_file() else []
    undone = {e['undoes'] for e in entries if e.get('undoes')}
    batches = [e['batch'] for e in entries if not e.get('undoes') and e['batch'] not in undone]
    if not batches: raise CyToolError('NotFound', 'No rename to undo')
    batch, results = batches[-1], []
    for entry in reversed([e for e in entries if e['batch'] == batch and not e.get('undoes')]):
        source, target = Path(entry['to']), Path(entry['from'])
        try:
            if not source.is_file(): raise CyToolError('NotFound', 'Renamed file not found: '+source.name)
            if target.exists(): raise CyToolError('Conflict', 'The original name is taken again: '+target.name)
            os.rename(source, target)
            asset = database.asset(entry['audioId'])
            if asset:
                relative = (Path(asset['relative_path']).parent/target.name).as_posix()
                database.execute('UPDATE assets SET absolute_path=?, relative_path=?, filename=? WHERE audio_id=?', (str(target), relative[2:] if relative.startswith('./') else relative, target.name, entry['audioId']))
            results.append({'audioId': entry['audioId'], 'ok': True, 'restored': target.name})
        except (CyToolError, OSError) as exc: results.append({'audioId': entry['audioId'], 'ok': False, 'error': getattr(exc, 'message', str(exc))})
    with journal.open('a', encoding='utf-8') as handle: handle.write(json.dumps({'batch': uuid.uuid4().hex[:12], 'undoes': batch, 'time': time.time()})+'\n')
    return {'undoneBatch': batch, 'restored': sum(r['ok'] for r in results), 'failed': sum(not r['ok'] for r in results), 'results': results}


# ---------------------------------------------------------------------------------------------------------------
# Embedded metadata
# ---------------------------------------------------------------------------------------------------------------
def audio_digest(path):
    """Hash of the decoded samples: proves that writing tags did not touch the audio itself."""
    digest, frames = hashlib.sha256(), 0
    for block, rate in blocks(path):
        digest.update(block.tobytes()); frames += len(block)
    return digest.hexdigest(), frames


def metadata_values(asset, category_names, fields, include_auto):
    tags = list(asset['userTags'])+([t for t in asset['autoTags'] if t not in asset['userTags']] if include_auto else [])
    categories = [category_names.get(c, c) for c in asset['categories'] if '.' not in c or c in category_names]
    values = {}
    if 'description' in fields and asset.get('description'): values['description'] = asset['description']
    if 'tags' in fields and tags: values['keywords'] = tags
    if 'categories' in fields and categories: values['genre'] = categories[0]; values['categories'] = categories
    if 'rating' in fields and asset.get('rating'): values['rating'] = str(asset['rating'])
    if 'audioId' in fields: values['audioId'] = asset['audio_id']
    return values


def apply_tags(path, values):
    import mutagen
    from mutagen.id3 import COMM, TCON, TXXX
    suffix = Path(path).suffix.lower()
    if suffix in ID3_FORMATS:
        audio = mutagen.File(str(path))
        if audio is None: raise CyToolError('UnsupportedFormat', 'This file cannot carry ID3 tags')
        if audio.tags is None: audio.add_tags()
        tags = audio.tags
        if 'description' in values: tags.delall('COMM'); tags.add(COMM(encoding=3, lang='eng', desc='', text=[values['description']]))
        if 'genre' in values: tags.delall('TCON'); tags.add(TCON(encoding=3, text=[values['genre']]))
        for key, name in (('keywords', 'KEYWORDS'), ('categories', 'CATEGORIES'), ('rating', 'RATING'), ('audioId', 'CYTOOLS_AUDIOID')):
            if key in values:
                tags.delall('TXXX:'+name); value = values[key]
                tags.add(TXXX(encoding=3, desc=name, text=['; '.join(value) if isinstance(value, list) else value]))
        audio.save()
    elif suffix in VORBIS_FORMATS:
        audio = mutagen.File(str(path))
        if audio is None: raise CyToolError('UnsupportedFormat', 'This file cannot carry Vorbis comments')
        if audio.tags is None: audio.add_tags()
        for key, name in (('description', 'DESCRIPTION'), ('genre', 'GENRE'), ('keywords', 'KEYWORDS'), ('categories', 'CATEGORIES'), ('rating', 'RATING'), ('audioId', 'CYTOOLS_AUDIOID')):
            if key in values: audio[name] = values[key] if isinstance(values[key], list) else [values[key]]
        audio.save()
    elif suffix in MP4_FORMATS:
        from mutagen.mp4 import MP4, MP4FreeForm
        audio = MP4(str(path))
        if 'description' in values: audio['\xa9cmt'] = [values['description']]
        if 'genre' in values: audio['\xa9gen'] = [values['genre']]
        for key, name in (('keywords', 'KEYWORDS'), ('categories', 'CATEGORIES'), ('rating', 'RATING'), ('audioId', 'CYTOOLS_AUDIOID')):
            if key in values:
                value = '; '.join(values[key]) if isinstance(values[key], list) else values[key]
                audio['----:com.apple.iTunes:'+name] = [MP4FreeForm(value.encode('utf-8'))]
        audio.save()
    else: raise CyToolError('UnsupportedFormat', f'Writing tags into {suffix} files is not supported (supported: WAV, AIFF, MP3, FLAC, OGG, Opus, M4A)')


def read_tags(path):
    """Flat view of what is embedded, for display and tests."""
    import mutagen
    audio = mutagen.File(str(path))
    if audio is None or audio.tags is None: return {}
    out = {}
    for key, value in audio.tags.items():
        text = getattr(value, 'text', value)
        if isinstance(text, (list, tuple)): text = '; '.join(v.decode('utf-8', 'replace') if isinstance(v, bytes) else str(v) for v in text)
        out[str(key)] = str(text)[:500]
    return out


def write_metadata(library, database, audio_ids, fields=FIELDS, include_auto=True, backup=True, cancelled=None, progress=None):
    names = {identifier: name for identifier, name, _, _ in flatten_taxonomy(library.taxonomy)}
    journal = operations_dir(library)/'metadata.jsonl'
    results = []
    for index, audio_id in enumerate(audio_ids):
        if cancelled and cancelled(): break
        asset = fetch_rows(database, [audio_id]).get(audio_id)
        temporary = None
        try:
            if not asset or asset['status'] != 'present': raise CyToolError('NotFound', 'Unknown or missing asset')
            source = Path(asset['absolute_path'])
            if progress: progress(100*index/len(audio_ids), currentStep='Writing metadata', currentFile=source.name, currentStepIndex=index+1, stepCount=len(audio_ids))
            if not source.is_file(): raise CyToolError('NotFound', 'The file is no longer there; rescan the Library')
            values = metadata_values(asset, names, fields, include_auto)
            if not [k for k in values if k != 'audioId']: raise CyToolError('NothingToWrite', 'No description, tag or category to write for this file')
            if shutil.disk_usage(source.parent).free < source.stat().st_size*1.1+64*1024**2: raise CyToolError('InsufficientDisk', 'Not enough free space next to the file for a safe rewrite')
            before, frames = audio_digest(source)
            temporary = source.with_name('.'+source.stem+'.cytools-'+uuid.uuid4().hex[:8]+source.suffix)
            shutil.copy2(source, temporary)
            apply_tags(temporary, values)
            after, frames_after = audio_digest(temporary)
            if (after, frames_after) != (before, frames): raise CyToolError('VerificationFailed', 'The audio of the tagged copy differs from the original; the original was left untouched')
            saved = ''
            if backup:
                folder = operations_dir(library)/'Backups'/audio_id; folder.mkdir(parents=True, exist_ok=True)
                saved = folder/(time.strftime('%Y%m%d-%H%M%S')+'_'+source.name); shutil.copy2(source, saved)
            os.replace(temporary, source); temporary = None
            stat = source.stat()
            database.execute('UPDATE assets SET file_size=?, modified_time=?, fast_hash=?, content_hash=NULL, embedded=? WHERE audio_id=?',
                             (stat.st_size, stat.st_mtime, fast_hash(source, stat.st_size), json.dumps(probe(source).get('embedded') or {}), audio_id))
            with journal.open('a', encoding='utf-8') as handle:
                handle.write(json.dumps({'time': time.time(), 'audioId': audio_id, 'path': str(source), 'written': sorted(values), 'backup': str(saved)}, ensure_ascii=False)+'\n')
            results.append({'audioId': audio_id, 'ok': True, 'file': source.name, 'written': sorted(values), 'backup': str(saved), 'audioVerified': True})
        except (CyToolError, OSError) as exc:
            results.append({'audioId': audio_id, 'ok': False, 'error': getattr(exc, 'message', str(exc)), 'code': getattr(exc, 'code', type(exc).__name__)})
        except Exception as exc:       # a tagging library error must never leave a half-written original
            results.append({'audioId': audio_id, 'ok': False, 'error': type(exc).__name__+': '+str(exc), 'code': 'TaggingFailed'})
        finally:
            if temporary is not None and temporary.exists(): temporary.unlink()
    return {'written': sum(r['ok'] for r in results), 'failed': sum(not r['ok'] for r in results), 'results': results,
            'backups': str(operations_dir(library)/'Backups') if backup else ''}
