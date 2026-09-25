"""Secondary tabs: analysis queue, guided installation (engine + models) and updates."""
import time
import webbrowser
from pathlib import Path

from imgui_bundle import imgui as ig
from ui_common import imgui, tr

from audiolib import installer, registry

GOOD, WARN, BAD, GREY = (0.45, 0.85, 0.5, 1), (0.95, 0.8, 0.3, 1), (0.95, 0.4, 0.4, 1), (0.6, 0.6, 0.6, 1)
STATE_COLOUR = {'Installed': GOOD, 'Downloading': WARN, 'Verifying': WARN, 'Partial': WARN, 'Interrupted': WARN, 'Cancelled': WARN,
                'Failed': BAD, 'AccessRequired': BAD, 'Missing': BAD, 'LicenseAcceptanceRequired': WARN}


def gigabytes(value): return f'{(value or 0)/1e9:.2f} GB'


class QueuePanel:
    def __init__(self, app): self.app, self.retry = app, False

    def start(self, retry=False, library_id=None):
        app = self.app
        library_id = library_id or app.library_id()
        if not library_id: return
        def done(job): app.refresh()
        app.submit('analyze_library', {'libraryId': library_id, 'retryFailed': retry}, done, 'Analysis')

    def draw(self):
        app, status = self.app, self.app.browser.status
        if not status: ig.text_wrapped(tr('Create a Library first.')); return
        ig.text(tr('Analysis Queue')); ig.separator()
        running = app.jobs.running('analyze_library')
        paused = status['queueState'] == 'paused'
        if running:
            progress = running[0].get('progress') or {}
            ig.text(f"{progress.get('statusMessage', '')}     "+tr('File')+f" {progress.get('currentStepIndex', 0)}/{progress.get('stepCount', 0)}")
            ig.text(tr('Current: ')+progress.get('currentFile', '-')); ig.text(tr('Step: ')+tr(progress.get('currentStep', '-')))
            if progress.get('etaSeconds') is not None: ig.text(tr('Remaining time: ')+time.strftime('%H:%M:%S', time.gmtime(progress['etaSeconds'])))
            ig.progress_bar(progress.get('percent', 0)/100, (-1, 0))
        else: ig.text_disabled(tr('No analysis is running.'))
        ig.begin_disabled(bool(running))
        if imgui.button('Start Analysis'): self.start()
        ig.same_line()
        if imgui.button('Retry Failed'): self.start(retry=True)
        ig.end_disabled()
        ig.same_line()
        if imgui.button('Resume' if paused else 'Pause'):
            app.submit('control_analysis', {'libraryId': app.library_id(), 'action': 'resume' if paused else 'pause'}, lambda job: app.browser.refresh_status(), 'Queue')
        ig.same_line()
        ig.begin_disabled(not running)
        if imgui.button('Cancel'): app.jobs.cancel('analyze_library')
        ig.end_disabled()
        if paused: ig.same_line(); ig.text_colored(WARN, tr('Queue paused'))
        ig.separator()
        ig.text(f"{status['files']:,} ".replace(',', ' ')+tr('files')+f"    {status['totalSeconds']/3600:.1f} h    {gigabytes(status['totalBytes'])}")
        if ig.begin_table('##states', 5, ig.TableFlags_.row_bg | ig.TableFlags_.borders_inner_v):
            for name in ('Stage', 'Ready', 'Failed', 'Pending', 'Progress'): ig.table_setup_column(tr(name))
            ig.table_headers_row()
            lines = [(tr('Metadata'), status['metadata']['ready'], status['metadata']['failed'], None, status['metadata']['percent']),
                     (tr('Waveforms'), status['waveforms']['ready'], status['waveforms']['failed'], None, status['waveforms']['percent'])]
            lines += [(m.get('displayName', m['modelKey']), m['ready'], m['failed'], m['pending'], m['percent']) for m in status['models']]
            for name, ready, failed, pending, percent in lines:
                ig.table_next_row()
                for column, value in enumerate((name, ready, failed, '-' if pending is None else pending)):
                    ig.table_set_column_index(column); ig.text(str(value))
                ig.table_set_column_index(4); ig.progress_bar(percent/100, (-1, 0), f'{percent:.0f}%')
            ig.end_table()
        if status.get('failureReasons'):
            ig.text_colored(BAD, f"{status['metadata']['failed']} "+tr('files could not be read'))
            for reason in status['failureReasons']: ig.bullet_text(f"{reason['count']} x {reason['error']}")
            ig.text_disabled(tr('Unreadable files are kept in the list (filter: Show failed files) and skipped by the analysis. Retry Failed re-reads them after a repair.'))
        ig.separator(); ig.text(tr('Analysis data kept in the cache'))
        ig.text_wrapped(tr('One store per model version and analysis settings. A new model version never overwrites the previous data; delete a store only when you no longer need it.'))
        for store in status['stores']:
            ig.push_id(store['analysisKey'])
            label = f"{store['modelKey']}   {store['analysisKey']}   {store['ready']} "+tr('files')+f"   {gigabytes(store['bytes'])}   "+(tr('current') if store['current'] else tr('previous version or settings'))
            ig.text_colored(GOOD if store['current'] else GREY, label)
            ig.same_line()
            if imgui.small_button('Delete this data'):
                app.submit('remove_model_data', {'libraryId': app.library_id(), 'analysisKey': store['analysisKey']}, lambda job: app.refresh(), 'Remove data')
            ig.pop_id()
        self.draw_taxonomy()
        ig.separator()
        if imgui.button('Recompute categories and tags'): app.submit('categorize_library', {'libraryId': app.library_id()}, lambda job: app.refresh(), 'Categorize')
        ig.same_line()
        if imgui.button('Find exact duplicates'): app.submit('find_duplicates', {'libraryId': app.library_id(), 'mode': 'exact'}, lambda job: app.refresh(), 'Duplicates')
        ig.same_line()
        if imgui.button('Find probable duplicates'): app.submit('find_duplicates', {'libraryId': app.library_id(), 'mode': 'probable'}, lambda job: app.refresh(), 'Duplicates')
        ig.text_disabled(tr('Duplicates are only grouped and reported. Nothing is ever deleted automatically.'))


    def draw_taxonomy(self):
        """Small editor of the Library taxonomy: categories (with parent and English prompts) and the tag vocabulary."""
        import copy
        from audiolib.library import flatten_taxonomy
        app, library = self.app, self.app.browser.library
        import sys
        if any(a.startswith('--ui-test-tab=') for a in sys.argv): ig.set_next_item_open(True, ig.Cond_.once)
        if not imgui.collapsing_header('Edit categories and tag vocabulary'): return
        state = self.__dict__.setdefault('taxonomy_form', {'name': '', 'prompts': '', 'parent': 0, 'remove': 0, 'tag': ''})
        nodes = flatten_taxonomy(library.taxonomy)
        def save(taxonomy): app.submit('update_library', {'libraryId': library.id, 'taxonomy': taxonomy}, lambda job: app.refresh(), 'Taxonomy')
        def find(items, identifier):
            for item in items:
                if item['id'] == identifier: return items, item
                found = find(item.get('children', []), identifier)
                if found: return found
        _, state['name'] = imgui.input_text('Category name', state['name'])
        _, state['prompts'] = imgui.input_text('English descriptions (comma separated)', state['prompts'])
        _, state['parent'] = ig.combo(tr('Parent category'), state['parent'], [tr('(top level)')]+[('  '*len(n[2]))+n[1] for n in nodes])
        if imgui.button('Add category') and state['name'].strip():
            taxonomy = copy.deepcopy(library.taxonomy); name = state['name'].strip()
            identifier = ''.join(c if c.isalnum() else '-' for c in name.lower()).strip('-') or 'category'
            parent = nodes[state['parent']-1][0] if state['parent'] else ''
            identifier = (parent+'.' if parent else '')+identifier
            if identifier in {n[0] for n in nodes}: app.jobs.message = tr('This category already exists.')
            else:
                node = {'id': identifier, 'name': name, 'prompts': [t.strip() for t in state['prompts'].split(',') if t.strip()] or [name.lower()]}
                target = find(taxonomy['categories'], parent)[1].setdefault('children', []) if parent else taxonomy['categories']
                target.append(node); save(taxonomy); state['name'] = state['prompts'] = ''
        if nodes:
            _, state['remove'] = ig.combo(tr('Category to remove'), min(state['remove'], len(nodes)-1), [('  '*len(n[2]))+n[1] for n in nodes])
            if imgui.button('Remove category (its sub-categories too)'):
                taxonomy = copy.deepcopy(library.taxonomy); siblings, node = find(taxonomy['categories'], nodes[state['remove']][0])
                siblings.remove(node); save(taxonomy); state['remove'] = 0
        _, state['tag'] = imgui.input_text('Tag for the automatic vocabulary', state['tag'])
        if imgui.button('Add tag to vocabulary') and state['tag'].strip():
            taxonomy = copy.deepcopy(library.taxonomy); taxonomy['tags'] = sorted(set(taxonomy.get('tags', []))|{state['tag'].strip().lower()}); save(taxonomy); state['tag'] = ''
        ig.same_line()
        if imgui.button('Remove tag from vocabulary') and state['tag'].strip():
            taxonomy = copy.deepcopy(library.taxonomy); taxonomy['tags'] = [t for t in taxonomy.get('tags', []) if t != state['tag'].strip().lower()]; save(taxonomy); state['tag'] = ''
        ig.text_disabled(tr('Then use Recompute categories and tags: no audio is decoded again, and user tags are untouched.'))


class FileToolsPanel:
    """Rename and write-metadata: the only actions that change original files. Explicit, previewed, confirmed each session."""
    def __init__(self, app):
        self.app = app
        self.scope, self.only_bad, self.template, self.max_tags = 1, True, '{category}_{tags}', 3
        self.plan, self.note = [], ''
        self.confirm_rename = self.confirm_write = False          # never pre-ticked, never saved
        self.fields = {'description': True, 'tags': True, 'categories': True, 'rating': True, 'audioId': True}
        self.include_auto, self.backup, self.report = True, True, None

    def targets(self):
        browser = self.app.browser
        if self.scope == 0: return browser.targets()[:5000]     # the multi-selection of the list, or the current sound
        return list(browser.ids[:5000])

    def draw(self):
        app = self.app
        if not app.browser.library: ig.text_wrapped(tr('Create a Library first.')); return
        ig.text_colored(WARN, tr('These two tools change your original audio files. Everything else in this application only reads them.'))
        _, self.scope = imgui.combo('Apply to', self.scope, ['The selected sounds', 'All sounds of the current list'])
        count = len(self.targets())
        ig.same_line(); ig.text_disabled(f'{count} '+tr('files')+(tr(' (limited to 5000 per run)') if count >= 5000 else ''))
        busy = bool(app.jobs.running('suggest_names', 'rename_files', 'undo_rename', 'write_metadata'))

        ig.spacing(); ig.text(tr('Rename badly named files')); ig.separator()
        ig.text_wrapped(tr('Proposes a name from the category and the tags of each sound (run the analysis first). Files stay in their folder, keep their extension, and nothing is ever overwritten. Tags, waveform and embeddings follow the renamed file.'))
        _, self.only_bad = imgui.checkbox('Only files with a meaningless name (sound_01, ZOOM0012, Untitled...)', self.only_bad)
        ig.set_next_item_width(260); _, self.template = imgui.input_text('Name template', self.template)
        ig.same_line(); ig.set_next_item_width(90); _, self.max_tags = imgui.input_int('Tags in the name', self.max_tags, 0); self.max_tags = max(0, min(8, self.max_tags))
        ig.text_disabled(tr('Template fields: {category} {tags} {original} {duration}'))
        ig.begin_disabled(busy or not count)
        if imgui.button('Suggest names'):
            def planned(job):
                if job['state'] != 'Completed': return
                self.plan = [dict(item, checked=True, edited=item['proposedName']) for item in job['outputs']['plan']]
                self.note = f"{len(self.plan)} "+tr('proposals')+(f"  |  {job['outputs']['withoutLabels']} "+tr('without category or tag: analyze them first') if job['outputs']['withoutLabels'] else '')
            app.submit('suggest_names', {'libraryId': app.library_id(), 'audioIds': self.targets(), 'onlyBadlyNamed': self.only_bad, 'template': self.template, 'maxTags': self.max_tags}, planned, 'Names')
        ig.end_disabled()
        if self.note: ig.same_line(); ig.text_disabled(self.note)
        if self.plan and ig.begin_table('##rename-plan', 4, ig.TableFlags_.scroll_y | ig.TableFlags_.row_bg | ig.TableFlags_.resizable | ig.TableFlags_.borders_inner_v, (0, 230)):
            for name, width in ((' ', 28), ('Current name', 0), ('New name', 0), ('Why', 190)):
                ig.table_setup_column(tr(name), ig.TableColumnFlags_.width_fixed if width else ig.TableColumnFlags_.width_stretch, width)
            ig.table_setup_scroll_freeze(0, 1); ig.table_headers_row()
            clipper = ig.ListClipper(); clipper.begin(len(self.plan))
            while clipper.step():
                for index in range(clipper.display_start, clipper.display_end):
                    item = self.plan[index]; ig.table_next_row(); ig.push_id(index)
                    ig.table_set_column_index(0); _, item['checked'] = ig.checkbox('##use', item['checked'])
                    ig.table_set_column_index(1); ig.text(item['currentName'])
                    if ig.is_item_hovered(): ig.set_tooltip(item['folder'])
                    ig.table_set_column_index(2); ig.set_next_item_width(-1); _, item['edited'] = ig.input_text('##new', item['edited'])
                    ig.table_set_column_index(3); ig.text_disabled(tr(item['reason']))
                    ig.pop_id()
            ig.end_table()
        chosen = [p for p in self.plan if p['checked'] and p['edited'].strip()]
        _, self.confirm_rename = imgui.checkbox('I understand that this renames the original files on disk', self.confirm_rename)
        ig.begin_disabled(busy or not chosen or not self.confirm_rename)
        if imgui.button('Rename the checked files'):
            def renamed(job):
                if job['state'] != 'Completed': return
                out = job['outputs']; failed = {r['audioId']: r['error'] for r in out['results'] if not r['ok']}
                self.plan = [dict(p, reason=failed[p['audioId']]) for p in self.plan if p['audioId'] in failed]
                self.note = f"{out['renamed']} "+tr('renamed')+f", {out['failed']} "+tr('refused'); self.confirm_rename = False; app.refresh()
            app.submit('rename_files', {'libraryId': app.library_id(), 'confirm': True, 'renames': [{'audioId': p['audioId'], 'newName': p['edited'].strip()} for p in chosen]}, renamed, 'Rename')
        ig.end_disabled()
        ig.same_line()
        ig.begin_disabled(busy or not self.confirm_rename)
        if imgui.button('Undo the last rename'):
            def undone(job):
                if job['state'] == 'Completed': self.note = f"{job['outputs']['restored']} "+tr('names restored'); self.confirm_rename = False; app.refresh()
            app.submit('undo_rename', {'libraryId': app.library_id(), 'confirm': True}, undone, 'Undo rename')
        ig.end_disabled()

        ig.spacing(); ig.text(tr('Write the tags into the files')); ig.separator()
        ig.text_wrapped(tr('Writes the description, tags, categories, rating and AudioId inside each file (ID3 for WAV, AIFF and MP3; Vorbis comments for FLAC, OGG and Opus; MP4 atoms for M4A), so other software can read them. Each file is rewritten through a verified copy: the decoded audio must be identical, otherwise the original is left untouched.'))
        for key, title in (('description', 'Description'), ('tags', 'Tags'), ('categories', 'Categories'), ('rating', 'Rating'), ('audioId', 'AudioId')):
            _, self.fields[key] = imgui.checkbox(title+'##field', self.fields[key]); ig.same_line()
        ig.new_line()
        _, self.include_auto = imgui.checkbox('Include the automatic tags (not only mine)', self.include_auto)
        _, self.backup = imgui.checkbox('Keep a backup of each original file in the Library cache', self.backup)
        _, self.confirm_write = imgui.checkbox('I understand that this rewrites the original files', self.confirm_write)
        ig.begin_disabled(busy or not count or not self.confirm_write or not any(self.fields.values()))
        if imgui.button('Write into the files'):
            def written(job):
                if job['state'] == 'Completed': self.report = job['outputs']; self.confirm_write = False; app.refresh()
            app.submit('write_metadata', {'libraryId': app.library_id(), 'audioIds': self.targets(), 'confirm': True, 'fields': [k for k, v in self.fields.items() if v],
                                          'includeAutoTags': self.include_auto, 'backup': self.backup}, written, 'Write metadata')
        ig.end_disabled()
        for job in app.jobs.running('write_metadata'):
            progress = job.get('progress') or {}
            ig.progress_bar(progress.get('percent', 0)/100, (-1, 0), f"{progress.get('currentStepIndex', 0)}/{progress.get('stepCount', 0)}  {progress.get('currentFile', '')}")
            if imgui.button('Cancel##write'): app.jobs.cancel('write_metadata')
        if self.report:
            ig.text(f"{self.report['written']} "+tr('files written')+f", {self.report['failed']} "+tr('refused'))
            if self.report.get('backups'): ig.text_disabled(tr('Backups: ')+self.report['backups'])
            for result in [r for r in self.report['results'] if not r['ok']][:12]: ig.text_colored(BAD, f"{result.get('code', '')}: {result['error']}")
        if app.jobs.message: ig.text_colored(BAD, app.jobs.message)


class ModelsPanel:
    def __init__(self, app):
        self.app = app
        self.accepted = {}          # modelKey -> ticked by the user in this window; never pre-ticked, never saved
        self.engine, self.engine_checked = None, 0.0
        self.token, self.delete_analysis, self.form = '', {}, {'modelId': '', 'version': 'v1', 'displayName': '', 'localPath': '', 'adapter': 0, 'type': 0,
                                                             'dimension': 512, 'rate': 16000, 'chunk': 10.0, 'license': ''}
        self.message = ''

    def refresh_engine(self):
        def done(job):
            if job['state'] == 'Completed': self.engine = job['outputs']
        self.app.submit('engine_status', {}, done, 'Engine'); self.engine_checked = time.monotonic()

    def draw(self):
        app = self.app
        if self.engine is None and time.monotonic()-self.engine_checked > 5: self.refresh_engine()
        ig.text(tr('AI engine')); ig.separator()
        engine = (self.engine or {}).get('engine', {})
        if engine.get('installed'):
            report = engine.get('report', {})
            ig.text_colored(GOOD, tr('Installed')+f"   PyTorch {report.get('torch', '?')}   {report.get('device', '')}")
        else:
            ig.text_colored(WARN, tr('Not installed'))
            ig.text_wrapped(tr('The AI engine is a private PyTorch environment created in runtime/engines (several GB). It is needed for embedding models and LLMs; browsing, waveforms and playback work without it.'))
        installing = app.jobs.running('install_engine')
        ig.begin_disabled(bool(installing))
        if imgui.button('Install or repair the AI engine (GPU)'): app.submit('install_engine', {'cpuOnly': False}, lambda job: self.refresh_engine(), 'Engine installation')
        ig.same_line()
        if imgui.button('Install CPU-only engine'): app.submit('install_engine', {'cpuOnly': True}, lambda job: self.refresh_engine(), 'Engine installation')
        ig.end_disabled()
        if installing:
            ig.same_line()
            if imgui.button('Cancel##engine'): app.jobs.cancel('install_engine')
            ig.text_wrapped((installing[0].get('progress') or {}).get('statusMessage', ''))
        from config import save_settings, settings
        devices = ('auto', 'gpu', 'cpu'); current = settings()['device']
        ig.set_next_item_width(220)
        changed, index = imgui.combo('Compute device', devices.index(current) if current in devices else 0, ['Auto (GPU when available)', 'GPU (CUDA) only', 'CPU only'])
        if changed: save_settings({'device': devices[index]}); app.submit('release_models', {}, lambda job: self.refresh_engine(), 'Release')
        ig.text_disabled(tr('Applies to analysis, search and the LLM. Changing it unloads the models; CPU mode reserves RAM and no VRAM.'))
        for name, worker in ((self.engine or {}).get('workers') or {}).items():
            ig.text_disabled(f"worker {name}: {worker['state']}   "+', '.join(f"{k} ({v['device']}, {v.get('vramBytes', 0)/2**30:.1f} GiB)" for k, v in worker['loadedModels'].items()))
            measured = worker.get('measured') or {}
            if measured.get('peakVramBytes'): ig.text_disabled(tr('Peak VRAM of this worker: ')+f"{measured['peakVramBytes']/2**30:.1f} GiB")
        ig.set_next_item_width(220)
        idle = int(settings()['idleUnloadSeconds'])//60
        changed, minutes = imgui.slider_int('Unload models after (minutes of inactivity)', max(1, idle) if idle else 0, 0, 60, tr('never') if False else '%d')
        if changed: save_settings({'idleUnloadSeconds': minutes*60})
        ig.text_disabled(tr('0 = keep the models loaded until you close the application. Loaded models keep their VRAM (see below); the next search is then instant.'))
        if imgui.button('Unload models now'): app.submit('release_models', {}, lambda job: self.refresh_engine(), 'Release')
        ig.spacing(); ig.text(tr('Models')); ig.separator()
        for descriptor in registry.load_registry().values():
            self.draw_model(descriptor)
        ig.spacing(); ig.text(tr('Hugging Face access (only for gated or private models)')); ig.separator()
        ig.text_wrapped(tr('The token is sent to the operating-system credential store through a private pipe. It never appears in job parameters, command lines or logs.'))
        ig.set_next_item_width(320); _, self.token = ig.input_text('##token', self.token, ig.InputTextFlags_.password)
        ig.same_line()
        if imgui.button('Store token') and self.token:
            self.message = app.updates.task.start('login', secret=self.token) and tr('Token sent to the credential store.') or tr('Another maintenance action is running.'); self.token = ''
        ig.same_line()
        if imgui.button('Forget token'): app.updates.task.start('logout')
        ig.same_line()
        if imgui.button('Create a read token'): webbrowser.open('https://huggingface.co/settings/tokens')
        if self.message: ig.text_wrapped(self.message)
        self.draw_custom_form()

    def draw_model(self, descriptor):
        app = self.app
        status = installer.model_status(descriptor)
        ig.push_id(descriptor.key)
        import sys
        if '--ui-test-tab=Installation' in sys.argv and descriptor.key in ('m2d-clap@2025', 'm2d-clap@2024'): ig.set_next_item_open(True, ig.Cond_.once)
        if ig.collapsing_header(f"{descriptor['displayName']}   [{tr(status['state'])}]###header"):
            ig.text_colored(STATE_COLOUR.get(status['state'], GREY), tr(status['state']))
            ig.same_line(); ig.text_disabled(f"{descriptor.key}   {descriptor.get('modelType')}   "+', '.join(descriptor.get('capabilities', [])))
            if status.get('downloadBytes'): ig.text(tr('Download size: ')+gigabytes(status['downloadBytes'])+'    '+tr('already present: ')+gigabytes(status.get('presentBytes')))
            if status['state'] == 'Installed': ig.text_disabled(tr('Model hash: ')+status.get('modelHash', '')[:24]+'   '+tr('revision: ')+str(descriptor.receipt().get('revision', '')))
            if status.get('message'): ig.text_wrapped(status['message'])
            if descriptor.get('validation'): ig.text_wrapped(tr('Validation: ')+descriptor['validation'])
            if descriptor.get('adapter') and status['state'] == 'Installed':
                from config import save_settings, settings
                per_model = settings().get('modelDevices', {}); choices = ('', 'gpu', 'cpu')
                ig.set_next_item_width(260)
                changed, index = imgui.combo('Device for this model', choices.index(per_model.get(descriptor.key, '')) if per_model.get(descriptor.key, '') in choices else 0,
                                             ['Same as the global setting', 'GPU (CUDA)', 'CPU (no VRAM, slower)'])
                if changed:
                    per_model = dict(per_model); per_model.pop(descriptor.key, None)
                    if choices[index]: per_model[descriptor.key] = choices[index]
                    save_settings({'modelDevices': per_model})
                resources = descriptor.get('resources') or {}
                if resources.get('vramBytes'): ig.text_disabled(tr('Estimated VRAM on GPU: ')+f"{resources['vramBytes']/2**30:.1f} GiB"+tr('. On CPU a search query takes a few seconds; indexing a Library on CPU is much slower.'))
            license_info = descriptor.get('license', {})
            ig.text_wrapped(tr('Licence: ')+str(license_info.get('name', 'Not declared')))
            if license_info.get('notes'): ig.text_wrapped(license_info['notes'])
            if license_info.get('url') and imgui.button('Open licence'): webbrowser.open(license_info['url'])
            if descriptor.get('repository'):
                ig.same_line()
                if imgui.button('Official page'): webbrowser.open(descriptor['repository'])
            running = [j for j in app.jobs.running('install_model') if j['parameters'].get('modelKey') == descriptor.key]
            if status['state'] == 'NotIntegrated': pass
            elif descriptor.custom:
                if imgui.button('Unregister (files are kept)'): app.submit('remove_model', {'modelKey': descriptor.key}, None, 'Unregister')
            else:
                needs = bool(license_info.get('requiresAcceptance')) and status['state'] != 'Installed'
                if needs:
                    _, self.accepted[descriptor.key] = imgui.checkbox('I have read this licence and I accept it personally', self.accepted.get(descriptor.key, False))
                ig.begin_disabled(bool(running) or (needs and not self.accepted.get(descriptor.key, False)))
                label = 'Repair' if status['state'] == 'Installed' else ('Resume' if status.get('presentBytes') else 'Download')
                if imgui.button(label):
                    app.submit('install_model', {'modelKey': descriptor.key, 'acceptLicense': bool(self.accepted.get(descriptor.key, False)), 'repair': status['state'] == 'Installed'},
                               lambda job: app.refresh(), 'Model installation')
                ig.end_disabled()
                if running:
                    ig.same_line()
                    if imgui.button('Cancel##install'):
                        for job in running: app.jobs.runtime.cancel(app.jobs.actor, job['jobId'])
                    progress = running[0].get('progress') or {}
                    ig.progress_bar(progress.get('percent', 0)/100, (-1, 0), f"{tr(progress.get('currentStep', ''))}  {progress.get('currentFile', '')}  {progress.get('statusMessage', '')}")
                if status['state'] in ('Installed', 'Partial', 'Interrupted', 'Cancelled', 'Failed'):
                    ig.same_line()
                    if imgui.button('Verify files') and status['state'] == 'Installed': app.submit('verify_model', {'modelKey': descriptor.key}, self.verified, 'Verify')
                    _, self.delete_analysis[descriptor.key] = imgui.checkbox('Also delete its analysis data in every Library', self.delete_analysis.get(descriptor.key, False))
                    ig.same_line()
                    if imgui.button('Remove Model'):
                        app.submit('remove_model', {'modelKey': descriptor.key, 'deleteAnalysis': self.delete_analysis.get(descriptor.key, False)}, lambda job: app.refresh(), 'Remove model')
        ig.pop_id()

    def verified(self, job):
        if job['state'] == 'Completed':
            out = job['outputs']; self.message = tr('Verified files: ')+str(out['files'])+('' if out['verified'] else '   '+tr('problems: ')+str(out['problems']))

    def draw_custom_form(self):
        ig.spacing(); ig.text(tr('Add a custom model or another version')); ig.separator()
        ig.text_wrapped(tr('Local models are referenced in place. Use a new version label for a fine-tuned or updated model: each version keeps its own embeddings.'))
        form = self.form
        adapters, kinds = list(registry.BUILTIN_ADAPTERS), ['AudioTextEmbedding', 'AudioEmbedding', 'LLM']
        _, form['modelId'] = imgui.input_text('Model id', form['modelId']); _, form['version'] = imgui.input_text('Version', form['version'])
        _, form['displayName'] = imgui.input_text('Display name', form['displayName']); _, form['localPath'] = imgui.input_text('Folder or weight file', form['localPath'])
        _, form['adapter'] = imgui.combo('Adapter', form['adapter'], adapters); ig.text_disabled(registry.BUILTIN_ADAPTERS[adapters[form['adapter']]])
        _, form['type'] = imgui.combo('Model type', form['type'], kinds)
        if kinds[form['type']] != 'LLM':
            _, form['dimension'] = imgui.input_int('Embedding dimension', form['dimension']); _, form['rate'] = imgui.input_int('Required sample rate', form['rate'])
            _, form['chunk'] = imgui.input_float('Preferred chunk (s)', form['chunk'])
        _, form['license'] = imgui.input_text('Licence name', form['license'])
        if imgui.button('Register model'):
            kind = kinds[form['type']]
            parameters = {'modelId': form['modelId'].strip(), 'version': form['version'].strip(), 'displayName': form['displayName'].strip() or form['modelId'].strip(),
                          'modelType': kind, 'adapter': adapters[form['adapter']], 'localPath': form['localPath'].strip(), 'licenseName': form['license'].strip(),
                          'capabilities': ['QueryUnderstanding', 'StructuredOutput'] if kind == 'LLM' else ['AudioEmbedding']+(['TextEmbedding', 'ZeroShotTagging'] if kind == 'AudioTextEmbedding' else [])}
            if kind != 'LLM': parameters.update(embeddingDimension=int(form['dimension']), requiredSampleRate=int(form['rate']), preferredChunkDuration=float(form['chunk']))
            self.app.submit('register_model', parameters, lambda job: self.app.refresh(), 'Register model')


class UpdatesPanel:
    def __init__(self, app):
        from maintenance import Task, configured_repository, update_settings
        self.app, self.task = app, Task()
        self.settings = update_settings()
        try: self.repository = configured_repository()      # what the checks will actually use
        except ValueError: self.repository = self.settings.get('tool_repository', '')
        if self.settings.get('auto_check'): self.task.start('auto-download' if self.settings.get('auto_download') else 'auto-check')

    def draw(self):
        from maintenance import save_update_settings, update_state
        log = self.task.poll(); state = update_state()
        busy = self.task.busy or bool(self.app.jobs.running('analyze_library', 'scan_library', 'install_model', 'install_engine'))
        ig.text_wrapped(tr('Application, engine sources and model weights are three separate update streams. Updates are staged in runtime/updates, verified, activated at the next start, and can be rolled back. The data folder is never part of an update.'))
        ig.separator(); ig.text(tr('Application')+'   '+tr('installed: ')+str(state['application']['installed']))
        _, self.repository = imgui.input_text('GitHub repository (owner/name)', self.repository)
        ig.text_disabled(tr('Updates come from the repository this application is published from. Change it only to follow a fork.'))
        changed_a, auto_check = imgui.checkbox('Check for updates at startup', bool(self.settings.get('auto_check')))
        ig.same_line(); changed_b, auto_download = imgui.checkbox('Download updates automatically', bool(self.settings.get('auto_download')))
        if imgui.button('Save update settings') or changed_a or changed_b:
            self.settings = save_update_settings({'tool_repository': self.repository.strip(), 'auto_check': auto_check, 'auto_download': auto_download})
        ig.begin_disabled(busy)
        for label, action in (('Check application', 'tool-check'), ('Download and verify', 'tool-fetch'), ('Roll back application', 'tool-rollback')):
            if imgui.button(label): self.task.start(action)
            ig.same_line()
        ig.new_line()
        if state['application'].get('pending'): ig.text_colored(WARN, tr('Version ready, activated at next start: ')+str(state['application']['pending']))
        ig.separator(); ig.text(tr('Engine sources (pinned revisions)'))
        for name, source in state['engine'].items():
            ig.text(f"{name}   {tr('active: ')}{source['active'][:12]}   {tr('pinned: ')}{source['pinned'][:12]}"+(f"   {tr('available: ')}{source['available'][:12]}" if source.get('available') else ''))
        for label, action in (('Check engine sources', 'engine-check'), ('Stage newest revision', 'engine-fetch'), ('Activate staged engine', 'engine-apply'), ('Roll back engine', 'engine-rollback')):
            if imgui.button(label): self.task.start(action)
            ig.same_line()
        ig.new_line(); ig.end_disabled()
        ig.text_disabled(tr('Model weights are updated from the Installation tab, with their own versions and licences.'))
        if busy and not self.task.busy: ig.text_colored(WARN, tr('Updates are disabled while an analysis or an installation is running.'))
        if self.task.busy and imgui.button('Cancel##maintenance'): self.task.cancel()
        ig.text(self.task.status)
        ig.input_text_multiline('##maintenance-log', log, (-1, 220), ig.InputTextFlags_.read_only)
