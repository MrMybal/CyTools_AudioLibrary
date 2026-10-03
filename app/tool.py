"""CyTools_AudioLibrary: operation handlers.

CyToolsCore owns validation, jobs, sessions, workspaces, events, the scheduler, the resource
ledger and every transport (CLI, JSONL, HTTP, MCP, native). This file only binds the
operations of CyTool.json to the business layer in audiolib/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from installation_ui import configure as configure_storage
configure_storage()
import json
import os
import subprocess

from cytools_core import CyToolError, Runtime, load_manifest
from cytools_core.transports.cli import run_cli

from audiolib import analysis, bundle, fileops, installer, llm, registry, scanner, search as searching, taxonomy
from audiolib.database import (asset_details, fetch_rows, flatten_folders, folder_tree, list_ids, open_database, set_user_categories,
                               set_user_tags, update_user_fields, user_category_ids)
from audiolib.embeddings import EmbeddingStore, list_stores
from audiolib.library import create_library, delete_library, get_library, list_libraries, lock_for
from audiolib.modelhost import HostPool
from audiolib.waveform import Pyramid, waveform_path
from config import APP, DATA, ROOT, configure_tls, device_for, runtime_python, settings

MIB, GIB = 1024**2, 1024**3


def library_view(library):
    return {'libraryId': library.id, 'name': library.name, 'rootFolders': library.roots, 'cacheLocation': str(library.cache_root),
            'cache': str(library.cache), 'settings': library.settings, 'enabledModels': library.enabled_models,
            'taxonomy': library.taxonomy, 'definitionFile': str(library.path)}


def exclusive(library):
    """One maintenance job per Library; a second one fails fast instead of corrupting the queue."""
    lock = lock_for(library.id)
    if not lock.acquire(blocking=False):
        raise CyToolError('Busy', 'Another scan, analysis or cache move is running for this Library', recoverable=True,
                          suggested_action='Wait for it, or cancel it, then retry')
    return lock


def create_runtime(data_dir, **options):
    runtime = Runtime(load_manifest(APP/'CyTool.json'), data_dir, **options)
    # No operation takes an input *file* to copy: Libraries reference folders in place, read-only.
    runtime.configure_inputs(DATA/'inputs', fields={})
    pool = HostPool(runtime)
    runtime.model_pool = pool
    def cancelled(context):
        """Callable for the business layer: true once the job is cancelled or its execution deadline has passed."""
        token = context.cancellation
        def test():
            try: token.check(); return False
            except CyToolError: return True
        return test

    def opened(parameters):
        library = get_library(parameters['libraryId'])
        return library, open_database(library)

    # -- estimates -------------------------------------------------------
    def model_estimate(parameters, backend, model):
        """RAM/VRAM of the models this job may have to load; models already resident are held by the worker reservation."""
        reg = registry.load_registry()
        keys = list(parameters.get('models') or [])
        if not keys and parameters.get('libraryId'):
            try: keys = get_library(parameters['libraryId']).enabled_models
            except CyToolError: keys = []
        if parameters.get('modelKey'): keys = [parameters['modelKey']]
        loaded = {key for host in pool.hosts.values() for key in host.loaded}
        ram, vram = 1*GIB, 0
        for key in keys:
            descriptor = reg.get(key)
            if descriptor is None or key in loaded: continue
            resources = descriptor.get('resources') or {}
            device = device_for(key, parameters.get('device'))
            if device == 'cpu': ram += resources.get('ramBytes', 0)+resources.get('vramBytes', 0)
            else: ram += resources.get('ramBytes', 0)//2; vram = max(vram, resources.get('vramBytes', 0))
        estimate = {'ramBytes': int(ram)}
        if vram: estimate['vramBytes'] = {'auto': int(vram)}
        return estimate

    # -- libraries ---------------------------------------------------------
    def op_list_libraries(context, parameters):
        return {'libraries': [library_view(library) for library in list_libraries()]}

    def op_create_library(context, parameters):
        library = create_library(parameters['name'], parameters.get('cacheLocation', ''))
        for folder in parameters.get('folders', []): library.add_root(folder)
        if parameters.get('enableDefaultModels', True):
            for descriptor in registry.load_registry().values():
                if descriptor.get('defaultEnabled') and descriptor.installed: library.set_model_enabled(descriptor.key, True)
        open_database(library)
        return library_view(library)

    def op_update_library(context, parameters):
        library, _ = opened(parameters)
        if 'name' in parameters: library.data['name'] = parameters['name'].strip(); library.save()
        if 'settings' in parameters: library.update_settings(parameters['settings'])
        if 'enabledModels' in parameters:
            reg = registry.load_registry()
            for key in parameters['enabledModels']:
                if not registry.get_model(key, reg).is_embedding: raise CyToolError('InvalidParameters', key+' is not an audio embedding model')
            library.data['enabledModels'] = list(parameters['enabledModels']); library.save()
        if 'taxonomy' in parameters: library.set_taxonomy(parameters['taxonomy'])
        return library_view(library)

    def op_delete_library(context, parameters): return delete_library(parameters['libraryId'], parameters.get('deleteCache', False))

    def op_add_folder(context, parameters):
        library, _ = opened(parameters)
        return {'folder': library.add_root(parameters['path']), 'library': library_view(library)}

    def op_remove_folder(context, parameters):
        library, database = opened(parameters)
        library.remove_root(parameters['rootId'])
        changed = database.execute("UPDATE assets SET status='missing' WHERE root_id=? AND status='present'", (parameters['rootId'],)).rowcount
        return {'removed': parameters['rootId'], 'assetsMarkedMissing': changed, 'library': library_view(library)}

    def op_set_folder_enabled(context, parameters):
        library, _ = opened(parameters)
        library.set_root_enabled(parameters['rootId'], parameters['enabled'])
        return library_view(library)

    def op_move_cache(context, parameters):
        library, _ = opened(parameters)
        lock = exclusive(library)
        try:
            from audiolib.database import close_database
            close_database(library)
            return library.move_cache(parameters['cacheLocation'], lambda percent, name: context.progress(min(99, percent), currentStep='Copying cache', currentFile=name), cancelled(context))
        finally: lock.release()

    # -- scanning and analysis ----------------------------------------------
    def op_scan_library(context, parameters):
        library, database = opened(parameters)
        lock = exclusive(library)
        try:
            threads = parameters.get('threads') or settings()['scanThreads']
            share = 0.35 if parameters.get('analyzeCommon', True) else 1.0
            summary = scanner.scan(library, database, parameters.get('rootIds'), lambda p, **f: context.progress(p*share, **f), cancelled(context), threads)
            context.log('Scan: '+json.dumps({k: v for k, v in summary.items() if isinstance(v, int)}))
            if parameters.get('analyzeCommon', True) and not summary.get('cancelled'):
                summary['common'] = scanner.analyze_common(library, database, lambda p, **f: context.progress(35+p*0.65, **f), cancelled(context),
                                                           threads, parameters.get('retryFailed', False))
            context.cancellation.check()
            return summary
        finally: lock.release()

    def op_check_library(context, parameters):
        library, database = opened(parameters)
        report = scanner.check(library, database, parameters.get('rootIds'), cancelled(context))
        context.cancellation.check()
        return {'libraryId': library.id, 'name': library.name, **report}

    def op_analyze_library(context, parameters):
        library, database = opened(parameters)
        lock = exclusive(library)
        try:
            common = scanner.analyze_common(library, database, lambda p, **f: context.progress(p*0.1, **f), cancelled(context), settings()['scanThreads'],
                                            parameters.get('retryFailed', False), parameters.get('audioIds'))
            result = analysis.analyze_models(library, database, pool, registry.load_registry(), parameters.get('models'),
                                             progress=lambda p, **f: context.progress(10+p*0.9, **f), cancelled=cancelled(context), log=context.log,
                                             retry_failed=parameters.get('retryFailed', False), device=parameters.get('device'),
                                             audio_ids=parameters.get('audioIds'), auto_label=parameters.get('autoLabel', True))
            context.cancellation.check()
            return {'common': common, **result, 'status': analysis.library_status(library, database, registry.load_registry())}
        finally: lock.release()

    def op_control_analysis(context, parameters):
        _, database = opened(parameters)
        return {'queueState': analysis.set_queue_state(database, 'paused' if parameters['action'] == 'pause' else 'running')}

    def op_library_status(context, parameters):
        library, database = opened(parameters)
        return analysis.library_status(library, database, registry.load_registry())

    # -- browsing --------------------------------------------------------------
    def visible_filters(library, filters):
        filters = dict(filters or {})
        if not filters.get('rootIds'): filters['rootIds'] = [r['rootId'] for r in library.roots if r['enabled']]
        return filters

    def op_browse_assets(context, parameters):
        library, database = opened(parameters)
        ids = list_ids(database, visible_filters(library, parameters.get('filters')), parameters.get('sort', 'name'), parameters.get('descending', False))
        window = ids[parameters.get('offset', 0):parameters.get('offset', 0)+parameters.get('limit', 100)]
        rows = fetch_rows(database, window)
        return {'total': len(ids), 'offset': parameters.get('offset', 0), 'assets': [rows[i] for i in window if i in rows]}

    def op_get_asset(context, parameters):
        library, database = opened(parameters)
        details = asset_details(database, parameters['audioId'])
        if not details: raise CyToolError('NotFound', 'Unknown asset: '+parameters['audioId'])
        details['states'] = analysis.asset_states(library, database, registry.load_registry(), parameters['audioId'])
        return details

    def op_get_waveform(context, parameters):
        library, database = opened(parameters)
        asset = database.asset(parameters['audioId'])
        if not asset: raise CyToolError('NotFound', 'Unknown asset: '+parameters['audioId'])
        path = waveform_path(library, asset['audio_id'])
        if not path.is_file(): raise CyToolError('NotReady', 'Waveform not computed yet: run scan_library', recoverable=True)
        pyramid = Pyramid(path)
        stop = parameters.get('stop', pyramid.duration)
        low, high = pyramid.read(parameters.get('start', 0), stop, parameters.get('columns', 1024))
        return {'audioId': asset['audio_id'], 'duration': pyramid.duration, 'sampleRate': pyramid.sample_rate, 'start': parameters.get('start', 0),
                'stop': min(stop, pyramid.duration), 'levels': pyramid.header['levels'], 'min': [round(float(v), 4) for v in low], 'max': [round(float(v), 4) for v in high]}

    def targets_of(library, database, parameters):
        """audioIds, plus every asset the filters match. The runtime fills schema defaults in, so an empty filter
        arrives as {"status": "present"}: a filter is judged by what it restricts, otherwise "no filter" would
        silently mean "the whole Library"."""
        filters = {k: v for k, v in (parameters.get('filters') or {}).items()
                   if v not in (None, '', [], False) and not (k == 'status' and v == 'present')}
        if 'audioIds' not in parameters and not filters:
            raise CyToolError('InvalidParameters', 'Give audioIds, or filters that restrict something, such as {"rootIds": [...], "folderPrefix": "..."}')
        targets = list(parameters.get('audioIds') or [])
        if filters: targets += list_ids(database, visible_filters(library, parameters['filters']))
        return list(dict.fromkeys(targets))

    def op_export_bundle(context, parameters):
        """Copies of a selection, or of everything a filter matches, gathered in a folder: originals are only read."""
        library, database = opened(parameters)
        return bundle.export_bundle(library, database, targets_of(library, database, parameters), parameters['destination'],
                                    parameters.get('layout', 'flat'), parameters.get('manifest', True), cancelled(context),
                                    lambda percent, name: context.progress(min(99, percent), currentStep='Copying into the bundle', currentFile=str(name)))

    def op_update_assets(context, parameters):
        """User data of one file, a selection (audioIds) or everything a filter matches, e.g. one folder.

        Only the database is written: the audio files are never touched here (write_metadata does that,
        with its own confirmation). Automatic tags and categories live apart and are never changed.
        """
        library, database = opened(parameters)
        targets = targets_of(library, database, parameters)
        fields = {k: parameters[k] for k in ('favorite', 'rating', 'description', 'notes') if k in parameters}
        category_keys = ('setCategories', 'addCategories', 'removeCategories')
        if any(k in parameters for k in category_keys):
            from audiolib.library import flatten_taxonomy
            known = {node[0] for node in flatten_taxonomy(library.taxonomy)}
            unknown = sorted({c for k in category_keys for c in parameters.get(k, []) if c not in known})
            if unknown: raise CyToolError('InvalidParameters', 'Unknown category ids: '+', '.join(unknown))
        note = str(parameters.get('appendNotes') or '').strip()
        updated = 0
        for position, audio_id in enumerate(targets):
            context.cancellation.check()
            if position % 200 == 0 and len(targets) > 200: context.progress(100*position/len(targets), currentStep='Editing')
            asset = database.asset(audio_id)
            if not asset: continue
            values = dict(fields)
            if note:          # never replaces what is already written: the line is added after it
                existing = (values.get('notes', asset['notes']) or '').rstrip()
                values['notes'] = (existing+'\n' if existing else '')+note
            if values: update_user_fields(database, audio_id, values)
            if any(k in parameters for k in ('setTags', 'addTags', 'removeTags')):
                current = [r['tag'] for r in database.query("SELECT tag FROM tags WHERE audio_id=? AND source='user'", (audio_id,))]
                tags = list(parameters['setTags']) if 'setTags' in parameters else current
                tags += parameters.get('addTags', [])
                removed = {t.casefold() for t in parameters.get('removeTags', [])}
                set_user_tags(database, audio_id, [t for t in tags if t.casefold() not in removed])
            if any(k in parameters for k in category_keys):
                categories = list(parameters['setCategories']) if 'setCategories' in parameters else user_category_ids(database, audio_id)
                categories += parameters.get('addCategories', [])
                removed = set(parameters.get('removeCategories', []))
                set_user_categories(database, audio_id, [c for c in categories if c not in removed])
            updated += 1
        return {'updated': updated, 'matched': len(targets)}

    def op_list_folders(context, parameters):
        """The folder structure of a Library, as its files describe it: counts per folder, recursive and direct."""
        library = get_library(parameters['libraryId'])
        database = open_database(library)
        roots = [r for r in library.roots if not parameters.get('rootId') or r['rootId'] == parameters['rootId']]
        if parameters.get('rootId') and not roots: raise CyToolError('NotFound', 'Unknown rootId: '+parameters['rootId'])
        trees = folder_tree(database, [r['rootId'] for r in roots])
        prefix, depth = str(parameters.get('folderPrefix') or ''), parameters.get('maxDepth', 2)
        out = []
        for root in roots:
            tree = trees.get(root['rootId'], {'files': 0, 'direct': 0, 'children': {}})
            folders = flatten_folders(tree, prefix, None if depth == 0 else depth)
            out.append({'rootId': root['rootId'], 'rootPath': root['path'], 'enabled': root['enabled'], 'files': tree['files'],
                        'directFiles': tree['direct'], 'folders': folders})
        return {'roots': out, 'folderPrefix': prefix, 'maxDepth': depth,
                'hint': 'Process one folder with filters {"rootIds": [rootId], "folderPrefix": path} in browse_assets or update_assets.'}

    # -- search ------------------------------------------------------------------
    def op_search_sounds(context, parameters):
        if parameters.get('libraryId'): targets = [get_library(parameters['libraryId'])]
        else:       # an AI client that only wants "a sound of X" does not need to know the Libraries first
            if parameters.get('similarTo'): raise CyToolError('InvalidParameters', 'similarTo needs the libraryId of that asset')
            targets = list_libraries()
            if not targets:
                raise CyToolError('NotFound', 'No Library exists yet', recoverable=True,
                                  suggested_action='Create one with create_library, then scan_library and analyze_library')
        selection = None
        if parameters.get('selectionStart') is not None or parameters.get('selectionEnd') is not None:
            if not parameters.get('similarTo'): raise CyToolError('InvalidParameters', 'A selection needs similarTo')
            selection = (parameters.get('selectionStart', 0.0), parameters.get('selectionEnd', 0.0))
            if selection[1]-selection[0] < 0.05: raise CyToolError('InvalidParameters', 'Selection is shorter than 50 ms')
        if parameters.get('text') and parameters.get('similarTo'): raise CyToolError('InvalidParameters', 'Use either text or similarTo')
        context.progress(5, currentStep='Understanding the query')
        result, skipped, understood = None, [], None
        for library in targets:
            try:
                found = searching.search(library, open_database(library), pool, registry.load_registry(), text=parameters.get('text', ''),
                                         similar_to=parameters.get('similarTo', ''), selection=selection, models=parameters.get('models'),
                                         filters=visible_filters(library, parameters.get('filters')), top_k=parameters.get('topK', 50),
                                         llm_mode=parameters.get('llmAssist', 'auto'), llm_model=parameters.get('llmModel', ''), weights=parameters.get('weights'),
                                         rrf_k=parameters.get('rrfK', 60), device=parameters.get('device'), cancelled=cancelled(context), understood=understood)
            except CyToolError as exc:
                if len(targets) > 1 and exc.code in ('NotAnalyzed', 'InvalidState'):      # a Library that is not indexed yet must not hide the others
                    skipped.append({'libraryId': library.id, 'name': library.name, 'reason': exc.code+': '+exc.message}); continue
                raise
            understood = (found['query']['structured'], found['query']['llm']) if found['mode'] == 'text' else None
            for item in found['results']: item.update(libraryId=library.id, libraryName=library.name)
            found['libraries'] = [{'libraryId': library.id, 'name': library.name, 'candidates': found['total']}]
            if result is None: result = found
            else:
                result['results'] += found['results']; result['total'] += found['total']; result['libraries'] += found['libraries']
                result['models'] += found['models']; result['seconds'] = round(result['seconds']+found['seconds'], 3)
        if result is None:
            raise CyToolError('NotAnalyzed', 'No Library has embeddings yet: '+'; '.join(s['name']+' ('+s['reason']+')' for s in skipped), recoverable=True,
                              suggested_action='Run analyze_library on a Library, then search again')
        if len(result['libraries']) > 1:       # each Library was ranked by its own fusion; the normalised fusion score is comparable across them
            result['results'].sort(key=lambda item: (-item['rrfNormalized'], -item['finalScore']))
            result['results'] = result['results'][:parameters.get('topK', 50)]
        result['skippedLibraries'] = skipped
        path = context.path('outputs/search-results.json')
        path.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding='utf-8')
        result['file'] = str(path)
        return result

    def op_understand_query(context, parameters):
        structured, info = llm.understand(pool, registry.load_registry(), parameters['text'].strip(), parameters.get('llmAssist', 'always'),
                                          parameters.get('llmModel', ''), parameters.get('device'), cancelled(context))
        return {'structured': structured, 'llm': info}

    def op_categorize_library(context, parameters):
        library, database = opened(parameters)
        reg = registry.load_registry()
        reports = []
        models = searching.resolve_models(library, reg, parameters.get('models'), ('AudioEmbedding', 'TextEmbedding'))
        for index, descriptor in enumerate(models):
            reports.append(taxonomy.categorize(library, database, pool, descriptor, None, parameters.get('device'), cancelled(context),
                                               lambda p, index=index: context.progress((index+p/100)*100/len(models), currentStep='Categorizing with '+descriptor['displayName'])))
        context.cancellation.check()
        return {'models': reports}

    def op_find_duplicates(context, parameters):
        library, database = opened(parameters)
        if parameters.get('mode', 'exact') == 'exact':
            groups = scanner.find_exact_duplicates(database, cancelled(context))
            result = {'mode': 'exact', 'groups': groups}
        else:
            result = {'mode': 'probable', **analysis.probable_duplicates(library, database, registry.load_registry(), parameters.get('model'),
                                                                        parameters.get('threshold', 0.985), cancelled=cancelled(context))}
        rows = database.query("SELECT duplicate_group, audio_id, absolute_path, file_size FROM assets WHERE duplicate_group IS NOT NULL AND status='present' ORDER BY duplicate_group")
        listing = {}
        for row in rows: listing.setdefault(row['duplicate_group'], []).append({'audioId': row['audio_id'], 'path': row['absolute_path'], 'fileSize': row['file_size']})
        result['duplicates'] = [{'group': key, 'kind': 'probable' if key.startswith('sim:') else 'exact', 'files': files} for key, files in list(listing.items())[:500]]
        return result

    def op_purge_missing(context, parameters):
        library, database = opened(parameters)
        ids = [r['audio_id'] for r in database.query("SELECT audio_id FROM assets WHERE status='missing'")]
        with database.transaction():
            scanner.forget_analysis(database, ids)
            for audio_id in ids:
                database.execute('DELETE FROM tags WHERE audio_id=?', (audio_id,)); database.execute('DELETE FROM asset_categories WHERE audio_id=?', (audio_id,))
                database.execute('DELETE FROM assets WHERE audio_id=?', (audio_id,))
        for audio_id in ids:
            try: waveform_path(library, audio_id).unlink()
            except OSError: pass
        return {'purged': len(ids)}

    # -- file tools: the only operations that change the original audio files ------------
    def op_suggest_names(context, parameters):
        library, database = opened(parameters)
        return fileops.suggest_names(library, database, parameters.get('audioIds'), parameters.get('onlyBadlyNamed', True),
                                     parameters.get('template', '{category}_{tags}'), parameters.get('maxTags', 3), parameters.get('limit', 500))

    def op_rename_files(context, parameters):
        library, database = opened(parameters)
        lock = exclusive(library)          # never while a scan or an analysis reads these paths
        try: return fileops.rename_files(library, database, parameters['renames'], cancelled(context))
        finally: lock.release()

    def op_undo_rename(context, parameters):
        library, database = opened(parameters)
        lock = exclusive(library)
        try: return fileops.undo_rename(library, database)
        finally: lock.release()

    def op_write_metadata(context, parameters):
        library, database = opened(parameters)
        lock = exclusive(library)
        try:
            return fileops.write_metadata(library, database, parameters['audioIds'], parameters.get('fields') or list(fileops.FIELDS),
                                          parameters.get('includeAutoTags', True), parameters.get('backup', True), cancelled(context), context.progress)
        finally: lock.release()

    # -- models ---------------------------------------------------------------------
    def op_list_models(context, parameters):
        reg = registry.load_registry()
        return {'models': [{**descriptor.public(), 'installation': installer.model_status(descriptor)} for descriptor in reg.values()],
                'adapters': registry.BUILTIN_ADAPTERS, 'capabilities': list(registry.CAPABILITIES)}

    def op_install_model(context, parameters):
        configure_tls()
        descriptor = registry.get_model(parameters['modelKey'])
        return installer.install_model(descriptor, accept_license=parameters.get('acceptLicense', False), progress=context.progress,
                                       cancellation=context.cancellation, log=context.log, repair=parameters.get('repair', False))

    def op_verify_model(context, parameters):
        return installer.verify_model(registry.get_model(parameters['modelKey']), context.cancellation, context.progress)

    def op_remove_model(context, parameters):
        descriptor = registry.get_model(parameters['modelKey'])
        for host in pool.hosts.values():
            if descriptor.key in host.loaded: host.unload(descriptor.key)
        deleted = []
        if parameters.get('deleteAnalysis'):
            for library in list_libraries():
                database = open_database(library)
                for store in list_stores(library, database):
                    if store['modelKey'] == descriptor.key:
                        EmbeddingStore.open(library, database, store['analysisKey']).delete(); deleted.append({'libraryId': library.id, 'analysisKey': store['analysisKey']})
        result = registry.unregister_custom(descriptor.key) if descriptor.custom else installer.remove_model(descriptor)
        return {**result, 'analysisDeleted': deleted, 'analysisKept': not parameters.get('deleteAnalysis')}

    def op_register_model(context, parameters):
        data = {k: v for k, v in parameters.items() if k not in ('licenseName', 'licenseUrl')}
        data['license'] = {'name': parameters.get('licenseName') or 'Not declared', 'url': parameters.get('licenseUrl', ''), 'requiresAcceptance': False}
        if 'AudioEmbedding' in data['capabilities'] and not data.get('embeddingDimension'):
            raise CyToolError('InvalidParameters', 'An embedding model needs embeddingDimension')
        descriptor = registry.register_custom(data, cancelled(context))
        return {**descriptor.public(), 'installation': installer.model_status(descriptor)}

    def op_remove_model_data(context, parameters):
        library, database = opened(parameters)
        store = EmbeddingStore.open(library, database, parameters['analysisKey'])
        size = store.vectors_path.stat().st_size if store.vectors_path.is_file() else 0
        store.delete()
        return {'analysisKey': parameters['analysisKey'], 'modelKey': store.model_key, 'freedBytes': size}

    def engine_report():
        result = subprocess.run([runtime_python(), str(APP/'setup_backend.py'), '--status'], capture_output=True, text=True,
                                creationflags=0x08000000 if os.name == 'nt' else 0, timeout=120)
        return json.loads(result.stdout) if result.returncode == 0 else {'installed': False, 'error': result.stderr[-500:]}

    def op_engine_status(context, parameters):
        return {'engine': engine_report(), 'workers': pool.status(), 'settings': settings()}

    def op_install_engine(context, parameters):
        command = [runtime_python(), str(APP/'setup_backend.py')]+(['--cpu-only'] if parameters.get('cpuOnly') else [])
        log_path = context.path('logs/install-engine.log')
        with log_path.open('w', encoding='utf-8') as handle:
            process = subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT, cwd=str(ROOT), creationflags=0x08000000 if os.name == 'nt' else 0)
            try:
                while process.poll() is None:
                    context.cancellation.sleep(1.0)
                    tail = log_path.read_text('utf-8', errors='replace')[-300:].strip().splitlines()
                    context.progress(50, currentStep='Installing the AI engine', statusMessage=tail[-1][:200] if tail else '')
            except CyToolError:
                import psutil
                family = psutil.Process(process.pid).children(recursive=True)+[psutil.Process(process.pid)]
                for member in family:
                    try: member.terminate()
                    except psutil.NoSuchProcess: pass
                psutil.wait_procs(family, timeout=15)
                raise
        if process.returncode:
            raise CyToolError('InstallFailed', 'Engine installation failed', details=log_path.read_text('utf-8', errors='replace')[-3000:], recoverable=True)
        return {'engine': engine_report(), 'log': str(log_path)}

    def op_release_models(context, parameters):
        with runtime._cv: busy = [j for j in runtime._running if runtime._jobs[j]['operationId'] in ('analyze_library', 'search_sounds', 'categorize_library', 'understand_query')]
        if busy: raise CyToolError('Busy', 'A model job is running; cancel it or wait before releasing the models', recoverable=True)
        pool.stop()
        return {'workers': pool.status()}

    handlers = {name[3:]: function for name, function in locals().items() if name.startswith('op_')}
    estimated = {'analyze_library', 'search_sounds', 'categorize_library', 'understand_query'}
    for operation in runtime.descriptor['operations']:
        identifier = operation['id']
        runtime.register(identifier, handlers[identifier], estimate=model_estimate if identifier in estimated else None)
    from cytools_core.shared_installation import register_operations
    register_operations(runtime, ROOT)
    return runtime


if __name__ == '__main__':
    argv = sys.argv[1:]
    if '--data-dir' not in argv: argv = ['--data-dir', str(ROOT/'data/jobs'), *argv]
    raise SystemExit(run_cli(create_runtime, argv))
