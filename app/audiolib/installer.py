"""Guided model installation: pinned revision, resume, size and SHA-256 checks, receipts.

Downloads go through CyToolsCore DownloadManager (HTTPS only, .part files, ETag/Range resume,
shared SHA-256 cache when the user enabled it). A model is reported Installed only after
every file of its receipt was verified. A Hugging Face token, when one is needed, is read
from the operating-system credential store inside this process: it never travels in argv,
job parameters, the manifest or a log.
"""
import os
import shutil
import time
import zipfile
from pathlib import Path

from config import SETTINGS, read_json, write_json
from cytools_core import CyToolError
from cytools_core.downloads import DownloadManager
from .registry import file_sha256, write_receipt

SERVICE = 'CyTools_AudioLibrary'
STATE_DIR = SETTINGS/'install-state'
MAX_ARCHIVE_BYTES = 8*1024**3


def token():
    try:
        import keyring
        return keyring.get_password(SERVICE, 'huggingface') or ''
    except Exception: return ''


def state_path(descriptor): return STATE_DIR/(descriptor.key.replace('@', '__')+'.json')


def set_state(descriptor, state, **fields):
    write_json(state_path(descriptor), {'modelKey': descriptor.key, 'state': state, 'updated': time.time(), **fields})


def blocks_of(descriptor):
    source = descriptor.get('source') or {}
    return ([source] if source else [])+list(descriptor.get('auxiliary', []))


def planned_files(descriptor):
    """[(block, relative target path, url, size, sha256)] for every file fetched over HTTPS."""
    files = []
    for block in blocks_of(descriptor):
        if block.get('kind') == 'huggingface':
            for item in block['files']:
                target = (block.get('target', '')+'/' if block.get('target') else '')+item['path']
                url = f"https://huggingface.co/{block['repo']}/resolve/{block['revision']}/{item['path']}"
                files.append((block, target, url, item.get('size'), item.get('sha256') or None))
        elif block.get('kind') == 'url-archive':
            files.append((block, '_download/'+block['url'].rsplit('/', 1)[1], block['url'], block.get('size'), block.get('sha256') or None))
    return files


def model_status(descriptor):
    """Structured state for the UI and for AI clients; presence of a folder alone is never 'Installed'."""
    base = {'modelKey': descriptor.key, 'displayName': descriptor['displayName'], 'license': descriptor.get('license', {}),
            'repository': descriptor.get('repository', ''), 'integrated': bool(descriptor.get('adapter')), 'custom': descriptor.custom,
            'installPath': str(descriptor.install_dir)}
    if descriptor.installed: return {**base, 'state': 'Installed', 'modelHash': descriptor.model_hash}
    if descriptor.custom: return {**base, 'state': 'Missing', 'message': 'The registered local files are no longer present or changed size'}
    if not descriptor.get('adapter'): return {**base, 'state': 'NotIntegrated', 'message': descriptor.get('validation', '')}
    files = planned_files(descriptor)
    total = sum(size or 0 for *_, size, _ in files)
    present = 0
    for _, target, _, size, _ in files:
        path = descriptor.install_dir/target
        if path.is_file(): present += path.stat().st_size
        elif path.with_name(path.name+'.part').is_file(): present += path.with_name(path.name+'.part').stat().st_size
    recorded = read_json(state_path(descriptor))
    state = recorded.get('state') if recorded.get('state') in ('Downloading', 'Verifying', 'Failed', 'AccessRequired', 'LicenseAcceptanceRequired', 'Cancelled') else None
    if state in ('Downloading', 'Verifying') and time.time()-recorded.get('updated', 0) > 30: state = 'Interrupted'
    return {**base, 'state': state or ('Partial' if present else 'NotInstalled'), 'downloadBytes': total, 'presentBytes': present,
            'message': recorded.get('message', ''), 'gated': any(b.get('gated') for b in blocks_of(descriptor))}


def safe_extract(archive, destination, cancellation=None):
    destination = Path(destination).resolve()
    with zipfile.ZipFile(archive) as bundle:
        if sum(info.file_size for info in bundle.infolist()) > MAX_ARCHIVE_BYTES: raise CyToolError('IntegrityFailure', 'Archive is larger than expected')
        for info in bundle.infolist():
            name = info.filename
            if name.startswith('/') or '\\' in name or '..' in Path(name).parts or Path(name).is_absolute() or ':' in name:
                raise CyToolError('IntegrityFailure', 'Unsafe path in archive: '+name)
            if (info.external_attr >> 16) & 0o170000 == 0o120000: raise CyToolError('IntegrityFailure', 'Symbolic links are not allowed in a model archive')
            if not (destination/name).resolve().is_relative_to(destination): raise CyToolError('IntegrityFailure', 'Archive entry escapes the model folder')
        for info in bundle.infolist():
            if cancellation: cancellation.check()
            bundle.extract(info, destination)
    return [p for p in destination.rglob('*') if p.is_file()]


def install_model(descriptor, *, accept_license=False, progress=None, cancellation=None, log=None, repair=False):
    progress = progress or (lambda *a, **k: None); log = log or (lambda *a, **k: None)
    if descriptor.custom: raise CyToolError('InvalidState', 'Custom models are registered in place; nothing to download')
    if not descriptor.get('adapter'): raise CyToolError('NotImplemented', descriptor['displayName']+' has no adapter in this version: it cannot be installed yet')
    license_info = descriptor.get('license', {})
    if license_info.get('requiresAcceptance') and not accept_license:
        set_state(descriptor, 'LicenseAcceptanceRequired', message=license_info.get('name', ''))
        raise CyToolError('LicenseAcceptanceRequired', 'Read and accept the licence of '+descriptor['displayName']+' before installing: '+license_info.get('url', ''),
                          recoverable=True, suggested_action='Open '+license_info.get('url', '')+', then call install_model with acceptLicense=true (your own decision)')
    target_root = descriptor.install_dir
    target_root.mkdir(parents=True, exist_ok=True)
    files = planned_files(descriptor)
    total = sum(size or 0 for *_, size, _ in files) or 1
    missing = sum((size or 0) for _, target, _, size, _ in files if not (target_root/target).is_file())
    extra = sum(b.get('size') or 0 for b in blocks_of(descriptor) if b.get('kind') == 'url-archive')
    free = shutil.disk_usage(target_root).free
    if free < (missing+extra)*1.05+512*1024**2:
        set_state(descriptor, 'Failed', message='Insufficient disk space')
        raise CyToolError('InsufficientDisk', f'{(missing+extra)/1e9:.1f} GB needed, {free/1e9:.1f} GB free on the models drive', recoverable=True)
    credential = token()
    done, receipt_files = 0, []
    try:
        for block, target, url, size, sha in files:
            if cancellation: cancellation.check()
            path = target_root/target
            path.parent.mkdir(parents=True, exist_ok=True)
            manager = DownloadManager(path.parent)
            headers = {'Authorization': 'Bearer '+credential} if credential and url.startswith('https://huggingface.co/') else None
            extracted_marker = target_root/'.extracted'
            if block.get('kind') == 'url-archive' and extracted_marker.is_file() and not repair:
                done += size or 0; continue
            if repair and path.is_file() and sha and file_sha256(path) != sha:
                log('Repair: '+target+' is corrupted, downloading it again'); manager.remove(path.name)
            base = done
            def report(received, expected, base=base, name=path.name):
                set_state(descriptor, 'Downloading', bytes=base+received, total=total, file=name)
                progress(min(99.0, 100*(base+received)/total), currentStep='Downloading', currentFile=name,
                         statusMessage=f'{(base+received)/1e9:.2f} / {total/1e9:.2f} GB')
            report.calls = 0
            def throttled(received, expected, report=report):
                report.calls += 1
                if report.calls % 64 == 1: report(received, expected)
            log('Downloading '+url.replace(credential, '***') if credential else 'Downloading '+url)
            try:
                manager.download(path.name, url, sha256=sha, size=size, headers=headers, cancellation=cancellation, progress=throttled,
                                 revision=block.get('revision') or descriptor.get('revision'))
            except CyToolError as exc:
                if exc.code == 'AuthenticationRequired':
                    page = 'https://huggingface.co/'+block['repo'] if block.get('repo') else descriptor.get('repository', '')
                    set_state(descriptor, 'AccessRequired', message=exc.message, page=page)
                    raise CyToolError('AccessRequired', f'{exc.message} for {page}. The provider refused access: sign in, accept the model terms on its '
                                      'official page if it is gated, store a read token from the Installation tab, then retry.', recoverable=True,
                                      suggested_action='Open '+page) from exc
                raise
            done += size or path.stat().st_size
            if block.get('kind') == 'url-archive':
                set_state(descriptor, 'Verifying', message='Extracting '+path.name)
                progress(min(99.0, 100*done/total), currentStep='Extracting', currentFile=path.name)
                for item in safe_extract(path, target_root, cancellation):
                    if '_download' not in item.relative_to(target_root).parts and item.name not in ('receipt.json', '.extracted'):
                        receipt_files.append(item)
                extracted_marker.write_text(block.get('sha256') or '', 'utf-8')
                manager.remove(path.name)         # the verified archive is not needed once extracted
            else: receipt_files.append(path)
            if block.get('thinkerOnly') and path.name == 'model.safetensors.index.json': _keep_thinker(path)
        if (target_root/'.extracted').is_file():
            receipt_files += [p for p in target_root.rglob('*') if p.is_file() and p not in receipt_files and '_download' not in p.relative_to(target_root).parts
                              and p.name not in ('receipt.json', '.extracted') and not p.name.endswith(('.installed.json', '.download.json', '.part', '.orig'))]
        set_state(descriptor, 'Verifying', message='Hashing files')
        known = {target: sha for _, target, _, _, sha in files if sha}
        entries = []
        for index, path in enumerate(dict.fromkeys(receipt_files)):
            if cancellation: cancellation.check()
            relative = path.relative_to(target_root).as_posix()
            progress(99.0, currentStep='Verifying', currentFile=path.name, currentStepIndex=index+1, stepCount=len(receipt_files))
            digest = known.get(relative) if (relative in known and not repair and relative != 'backbone/model.safetensors.index.json') else file_sha256(path)
            entries.append((relative, path.stat().st_size, digest))
        receipt = write_receipt(descriptor, entries)
        set_state(descriptor, 'Installed', modelHash=receipt['modelHash'])
        return {'modelKey': descriptor.key, 'state': 'Installed', 'modelHash': receipt['modelHash'], 'files': len(entries),
                'bytes': sum(e[1] for e in entries), 'path': str(target_root)}
    except CyToolError as exc:
        if exc.code == 'Cancelled': set_state(descriptor, 'Cancelled', message='Partial files are kept: Resume continues where it stopped')
        elif exc.code not in ('AccessRequired',): set_state(descriptor, 'Failed', message=exc.code+': '+exc.message)
        raise


def _keep_thinker(index_path):
    """Drop talker/token2wav entries whose shard is not downloaded; the original index is kept as .orig."""
    import json
    data = json.loads(index_path.read_text('utf-8'))
    kept = {k: v for k, v in data['weight_map'].items() if k.startswith('thinker.')}
    if len(kept) == len(data['weight_map']): return
    original = index_path.with_name(index_path.name+'.orig')
    if not original.is_file(): shutil.copyfile(index_path, original)
    data['weight_map'] = kept
    index_path.write_text(json.dumps(data), 'utf-8')


def verify_model(descriptor, cancellation=None, progress=None):
    receipt = descriptor.receipt()
    if not receipt.get('files'): raise CyToolError('ModelNotInstalled', descriptor['displayName']+' has no installation receipt')
    problems = []
    for index, item in enumerate(receipt['files']):
        path = descriptor.install_dir/item['path']
        if progress: progress(100*index/len(receipt['files']), currentStep='Verifying', currentFile=item['path'])
        if not path.is_file(): problems.append({'path': item['path'], 'problem': 'missing'})
        elif path.stat().st_size != item['size']: problems.append({'path': item['path'], 'problem': 'size'})
        elif item.get('sha256') and file_sha256(path, (lambda: cancellation.event.is_set()) if cancellation is not None else None) != item['sha256']:
            problems.append({'path': item['path'], 'problem': 'sha256'})
    return {'modelKey': descriptor.key, 'verified': not problems, 'files': len(receipt['files']), 'problems': problems}


def remove_model(descriptor):
    """Delete the installed weights of an official model. Analysis data in Library caches is a separate choice."""
    if descriptor.custom: raise CyToolError('InvalidState', 'Custom model files are never deleted by the Tool; unregister the model instead')
    folder = descriptor.install_dir
    from config import MODELS
    if not folder.resolve().is_relative_to(MODELS.resolve()): raise CyToolError('AccessDenied', 'Model folder is outside data/models')
    size = sum(p.stat().st_size for p in folder.rglob('*') if p.is_file()) if folder.is_dir() else 0
    shutil.rmtree(folder, ignore_errors=True)
    path = state_path(descriptor)
    if path.is_file(): path.unlink()
    return {'modelKey': descriptor.key, 'freedBytes': size}
