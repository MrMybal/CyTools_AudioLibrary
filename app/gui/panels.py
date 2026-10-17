"""Secondary tabs: analysis queue, file tools, guided installation (engine + models) and updates."""
import time
import webbrowser
from pathlib import Path

from imgui_bundle import imgui as ig
from ui_common import imgui, tr

import cyui as cy
from audiolib import installer, registry

STATE_TONE = {'Installed': 'success', 'Downloading': 'warning', 'Verifying': 'warning', 'Partial': 'warning', 'Interrupted': 'warning',
              'Cancelled': 'warning', 'Failed': 'error', 'AccessRequired': 'error', 'Missing': 'error', 'LicenseAcceptanceRequired': 'warning'}


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
        if not status: cy.empty_state('No Library yet', 'Create a Library first.', 'library'); return
        cy.panel_header('Analysis Queue', app.browser.library.name)
        cy.space(4)
        running = app.jobs.running('analyze_library')
        paused = status['queueState'] == 'paused'
        if cy.begin_card('##queue-progress'):
            if running:
                progress = running[0].get('progress') or {}
                ig.text(f"{progress.get('statusMessage', '')}     "+tr('File')+f" {progress.get('currentStepIndex', 0)}/{progress.get('stepCount', 0)}")
                cy.text_dim(tr('Current: ')+progress.get('currentFile', '-')); cy.text_dim(tr('Step: ')+tr(progress.get('currentStep', '-')))
                if progress.get('etaSeconds') is not None: cy.text_dim(tr('Remaining time: ')+time.strftime('%H:%M:%S', time.gmtime(progress['etaSeconds'])))
                cy.progress_bar(progress.get('percent', 0)/100, (-1, 0), f"{progress.get('percent', 0):.0f}%")
            else: cy.text_faint(tr('No analysis is running.'))
            cy.space(4)
            ig.begin_disabled(bool(running))
            if cy.icon_text_button('play', 'Start Analysis', 'primary'): self.start()
            ig.same_line()
            if cy.icon_text_button('refresh', 'Retry Failed'): self.start(retry=True)
            ig.end_disabled()
            ig.same_line()
            if cy.icon_text_button('play' if paused else 'pause', 'Resume' if paused else 'Pause'):
                app.submit('control_analysis', {'libraryId': app.library_id(), 'action': 'resume' if paused else 'pause'}, lambda job: app.browser.refresh_status(), 'Queue')
            ig.same_line()
            ig.begin_disabled(not running)
            if cy.icon_text_button('stop', 'Cancel'): app.jobs.cancel('analyze_library')
            ig.end_disabled()
            if paused: ig.same_line(); cy.badge('Queue paused', 'warning')
        cy.end_card()
        cy.space(4)
        cy.text_dim(f"{status['files']:,} ".replace(',', ' ')+tr('files')+f"    {status['totalSeconds']/3600:.1f} h    {gigabytes(status['totalBytes'])}")
        if ig.begin_table('##states', 5, ig.TableFlags_.row_bg | ig.TableFlags_.borders_inner_v | ig.TableFlags_.borders_outer):
            for name in ('Stage', 'Ready', 'Failed', 'Pending'): ig.table_setup_column(tr(name), ig.TableColumnFlags_.width_stretch, 1.0)
            ig.table_setup_column(tr('Progress'), ig.TableColumnFlags_.width_stretch, 2.0)
            ig.table_headers_row()
            lines = [(tr('Metadata'), status['metadata']['ready'], status['metadata']['failed'], None, status['metadata']['percent']),
                     (tr('Waveforms'), status['waveforms']['ready'], status['waveforms']['failed'], None, status['waveforms']['percent'])]
            lines += [(m.get('displayName', m['modelKey']), m['ready'], m['failed'], m['pending'], m['percent']) for m in status['models']]
            for name, ready, failed, pending, percent in lines:
                ig.table_next_row()
                ig.table_set_column_index(0); ig.text(str(name))
                ig.table_set_column_index(1); ig.text(str(ready))
                ig.table_set_column_index(2); cy.text_coloured(cy.palette().error if failed else cy.palette().textFaint, str(failed))
                ig.table_set_column_index(3); cy.text_dim('-' if pending is None else str(pending))
                ig.table_set_column_index(4); cy.progress_bar(percent/100, (-1, ig.get_text_line_height()), f'{percent:.0f}%', 'success' if percent >= 100 else 'accent')
            ig.end_table()
        if status.get('failureReasons'):
            cy.space(4)
            cy.callout('warning', f"{status['metadata']['failed']} "+tr('files could not be read')+'\n'+
                       '\n'.join(f"{reason['count']} x {reason['error']}" for reason in status['failureReasons']))
            cy.wrapped_faint(tr('Unreadable files are kept in the list (filter: Show failed files) and skipped by the analysis. Retry Failed re-reads them after a repair.'))
        cy.space(6)
        if cy.begin_section('Analysis data kept in the cache'):
            cy.wrapped_dim(tr('One store per model version and analysis settings. A new model version never overwrites the previous data; delete a store only when you no longer need it.'))
            for store in status['stores']:
                ig.push_id(store['analysisKey'])
                cy.status_dot(cy.palette().success if store['current'] else cy.palette().textFaint); ig.same_line(0, cy.dp(4))
                label = f"{store['modelKey']}   {store['analysisKey']}   {store['ready']} "+tr('files')+f"   {gigabytes(store['bytes'])}   "+(tr('current') if store['current'] else tr('previous version or settings'))
                (ig.text_unformatted if store['current'] else cy.text_dim)(label)
                ig.same_line()
                if cy.button('Delete this data', 'danger', small=True):
                    app.submit('remove_model_data', {'libraryId': app.library_id(), 'analysisKey': store['analysisKey']}, lambda job: app.refresh(), 'Remove data')
                ig.pop_id()
            if not status['stores']: cy.text_faint(tr('No analysis data yet.'))
            cy.end_section()
        self.draw_taxonomy()
        if cy.begin_section('Categories, tags and duplicates'):
            if cy.icon_text_button('refresh', 'Recompute categories and tags'): app.submit('categorize_library', {'libraryId': app.library_id()}, lambda job: app.refresh(), 'Categorize')
            ig.same_line()
            if cy.icon_text_button('copy', 'Find exact duplicates'): app.submit('find_duplicates', {'libraryId': app.library_id(), 'mode': 'exact'}, lambda job: app.refresh(), 'Duplicates')
            ig.same_line()
            if cy.button('Find probable duplicates'): app.submit('find_duplicates', {'libraryId': app.library_id(), 'mode': 'probable'}, lambda job: app.refresh(), 'Duplicates')
            cy.wrapped_faint(tr('Duplicates are only grouped and reported. Nothing is ever deleted automatically.'))
            cy.end_section()


    def draw_taxonomy(self):
        """Small editor of the Library taxonomy: categories (with parent and English prompts) and the tag vocabulary."""
        import copy
        from audiolib.library import flatten_taxonomy
        app, library = self.app, self.app.browser.library
        import sys
        if any(a.startswith('--ui-test-tab=') for a in sys.argv): ig.set_next_item_open(True, ig.Cond_.once)
        if not cy.begin_section('Edit categories and tag vocabulary', False): return
        state = self.__dict__.setdefault('taxonomy_form', {'name': '', 'prompts': '', 'parent': 0, 'remove': 0, 'tag': ''})
        nodes = flatten_taxonomy(library.taxonomy)
        def save(taxonomy): app.submit('update_library', {'libraryId': library.id, 'taxonomy': taxonomy}, lambda job: app.refresh(), 'Taxonomy')
        def find(items, identifier):
            for item in items:
                if item['id'] == identifier: return items, item
                found = find(item.get('children', []), identifier)
                if found: return found
        cy.section_title('New category')
        if cy.begin_properties('##new-category', 240):
            cy.property('Category name'); _, state['name'] = imgui.input_text('##category-name', state['name'])
            cy.property('English descriptions (comma separated)'); _, state['prompts'] = imgui.input_text('##category-prompts', state['prompts'])
            cy.property('Parent category'); _, state['parent'] = ig.combo('##parent-category', state['parent'], [tr('(top level)')]+[('  '*len(n[2]))+n[1] for n in nodes])
            cy.end_properties()
        if cy.icon_text_button('add', 'Add category') and state['name'].strip():
            taxonomy = copy.deepcopy(library.taxonomy); name = state['name'].strip()
            identifier = ''.join(c if c.isalnum() else '-' for c in name.lower()).strip('-') or 'category'
            parent = nodes[state['parent']-1][0] if state['parent'] else ''
            identifier = (parent+'.' if parent else '')+identifier
            if identifier in {n[0] for n in nodes}: app.jobs.message = tr('This category already exists.')
            else:
                node = {'id': identifier, 'name': name, 'prompts': [t.strip() for t in state['prompts'].split(',') if t.strip()] or [name.lower()]}
                target = find(taxonomy['categories'], parent)[1].setdefault('children', []) if parent else taxonomy['categories']
                target.append(node); save(taxonomy); state['name'] = state['prompts'] = ''
        cy.space(6)
        if nodes:
            cy.section_title('Remove a category')
            if cy.begin_properties('##remove-category', 240):
                cy.property('Category to remove'); _, state['remove'] = ig.combo('##category-remove', min(state['remove'], len(nodes)-1), [('  '*len(n[2]))+n[1] for n in nodes])
                cy.end_properties()
            if cy.button('Remove category (its sub-categories too)', 'danger'):
                taxonomy = copy.deepcopy(library.taxonomy); siblings, node = find(taxonomy['categories'], nodes[state['remove']][0])
                siblings.remove(node); save(taxonomy); state['remove'] = 0
            cy.space(6)
        cy.section_title('Automatic tag vocabulary')
        if cy.begin_properties('##vocabulary', 240):
            cy.property('Tag for the automatic vocabulary'); _, state['tag'] = imgui.input_text('##vocabulary-tag', state['tag'])
            cy.end_properties()
        if cy.icon_text_button('add', 'Add tag to vocabulary') and state['tag'].strip():
            taxonomy = copy.deepcopy(library.taxonomy); taxonomy['tags'] = sorted(set(taxonomy.get('tags', []))|{state['tag'].strip().lower()}); save(taxonomy); state['tag'] = ''
        ig.same_line()
        if cy.icon_text_button('remove', 'Remove tag from vocabulary') and state['tag'].strip():
            taxonomy = copy.deepcopy(library.taxonomy); taxonomy['tags'] = [t for t in taxonomy.get('tags', []) if t != state['tag'].strip().lower()]; save(taxonomy); state['tag'] = ''
        cy.wrapped_faint(tr('Then use Recompute categories and tags: no audio is decoded again, and user tags are untouched.'))
        cy.end_section()


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
        if not app.browser.library: cy.empty_state('No Library yet', 'Create a Library first.', 'library'); return
        cy.panel_header('File Tools', tr('The only actions that change your audio files'))
        cy.space(4)
        cy.callout('warning', tr('These two tools change your original audio files. Everything else in this application only reads them.'))
        cy.space(4)
        count = len(self.targets())
        if cy.begin_properties('##file-scope', 120):
            cy.property('Apply to')
            ig.set_next_item_width(cy.dp(260))
            _, self.scope = imgui.combo('##apply-to', self.scope, ['The selected sounds', 'All sounds of the current list'])
            ig.same_line(); ig.align_text_to_frame_padding(); cy.text_dim(f'{count} '+tr('files')+(tr(' (limited to 5000 per run)') if count >= 5000 else ''))
            cy.end_properties()
        busy = bool(app.jobs.running('suggest_names', 'rename_files', 'undo_rename', 'write_metadata'))
        cy.space(4)

        if cy.begin_section('Rename badly named files'):
            cy.wrapped_dim(tr('Proposes a name from the category and the tags of each sound (run the analysis first). Files stay in their folder, keep their extension, and nothing is ever overwritten. Tags, waveform and embeddings follow the renamed file.'))
            cy.space(4)
            _, self.only_bad = imgui.checkbox('Only files with a meaningless name (sound_01, ZOOM0012, Untitled...)', self.only_bad)
            if cy.begin_properties('##rename-options', 120):
                cy.property('Name template', 'Template fields: {category} {tags} {original} {duration}')
                ig.set_next_item_width(cy.dp(260)); _, self.template = imgui.input_text('##name-template', self.template)
                cy.property('Tags in the name')
                ig.set_next_item_width(cy.dp(90)); _, self.max_tags = imgui.input_int('##tags-in-name', self.max_tags, 0); self.max_tags = max(0, min(8, self.max_tags))
                cy.end_properties()
            ig.begin_disabled(busy or not count)
            if cy.icon_text_button('rename', 'Suggest names'):
                def planned(job):
                    if job['state'] != 'Completed': return
                    self.plan = [dict(item, checked=True, edited=item['proposedName']) for item in job['outputs']['plan']]
                    self.note = f"{len(self.plan)} "+tr('proposals')+(f"  |  {job['outputs']['withoutLabels']} "+tr('without category or tag: analyze them first') if job['outputs']['withoutLabels'] else '')
                app.submit('suggest_names', {'libraryId': app.library_id(), 'audioIds': self.targets(), 'onlyBadlyNamed': self.only_bad, 'template': self.template, 'maxTags': self.max_tags}, planned, 'Names')
            ig.end_disabled()
            if self.note: ig.same_line(); ig.align_text_to_frame_padding(); cy.text_dim(self.note)
            if self.plan and ig.begin_table('##rename-plan', 4, ig.TableFlags_.scroll_y | ig.TableFlags_.row_bg | ig.TableFlags_.resizable | ig.TableFlags_.borders_inner_v | ig.TableFlags_.borders_outer, (0, cy.dp(230))):
                for name, width in ((' ', 28), ('Current name', 0), ('New name', 0), ('Why', 190)):
                    ig.table_setup_column(tr(name), ig.TableColumnFlags_.width_fixed if width else ig.TableColumnFlags_.width_stretch, cy.dp(width))
                ig.table_setup_scroll_freeze(0, 1); ig.table_headers_row()
                clipper = ig.ListClipper(); clipper.begin(len(self.plan))
                while clipper.step():
                    for index in range(clipper.display_start, clipper.display_end):
                        item = self.plan[index]; ig.table_next_row(); ig.push_id(index)
                        ig.table_set_column_index(0); _, item['checked'] = ig.checkbox('##use', item['checked'])
                        ig.table_set_column_index(1); ig.align_text_to_frame_padding(); ig.text(item['currentName'])
                        cy.tooltip(item['folder'])
                        ig.table_set_column_index(2); ig.set_next_item_width(-1); _, item['edited'] = ig.input_text('##new', item['edited'])
                        ig.table_set_column_index(3); ig.align_text_to_frame_padding(); cy.text_dim(tr(item['reason']))
                        ig.pop_id()
                ig.end_table()
            chosen = [p for p in self.plan if p['checked'] and p['edited'].strip()]
            cy.space(4)
            _, self.confirm_rename = imgui.checkbox('I understand that this renames the original files on disk', self.confirm_rename)
            ig.begin_disabled(busy or not chosen or not self.confirm_rename)
            if cy.button('Rename the checked files', 'danger'):
                def renamed(job):
                    if job['state'] != 'Completed': return
                    out = job['outputs']; failed = {r['audioId']: r['error'] for r in out['results'] if not r['ok']}
                    self.plan = [dict(p, reason=failed[p['audioId']]) for p in self.plan if p['audioId'] in failed]
                    self.note = f"{out['renamed']} "+tr('renamed')+f", {out['failed']} "+tr('refused'); self.confirm_rename = False; app.refresh()
                    cy.notify(self.note, 'success' if not out['failed'] else 'warning')
                app.submit('rename_files', {'libraryId': app.library_id(), 'confirm': True, 'renames': [{'audioId': p['audioId'], 'newName': p['edited'].strip()} for p in chosen]}, renamed, 'Rename')
            ig.end_disabled()
            ig.same_line()
            ig.begin_disabled(busy or not self.confirm_rename)
            if cy.icon_text_button('undo', 'Undo the last rename'):
                def undone(job):
                    if job['state'] == 'Completed': self.note = f"{job['outputs']['restored']} "+tr('names restored'); self.confirm_rename = False; app.refresh()
                app.submit('undo_rename', {'libraryId': app.library_id(), 'confirm': True}, undone, 'Undo rename')
            ig.end_disabled()
            cy.end_section()

        if cy.begin_section('Write the tags into the files'):
            cy.wrapped_dim(tr('Writes the description, tags, categories, rating and AudioId inside each file (ID3 for WAV, AIFF and MP3; Vorbis comments for FLAC, OGG and Opus; MP4 atoms for M4A), so other software can read them. Each file is rewritten through a verified copy: the decoded audio must be identical, otherwise the original is left untouched.'))
            cy.space(4)
            ig.align_text_to_frame_padding(); cy.text_dim(tr('Fields')); ig.same_line(cy.dp(120))
            for key, title in (('description', 'Description'), ('tags', 'Tags'), ('categories', 'Categories'), ('rating', 'Rating'), ('audioId', 'AudioId')):
                _, self.fields[key] = imgui.checkbox(title+'##field', self.fields[key]); ig.same_line()
            ig.new_line()
            _, self.include_auto = imgui.checkbox('Include the automatic tags (not only mine)', self.include_auto)
            _, self.backup = imgui.checkbox('Keep a backup of each original file in the Library cache', self.backup)
            cy.space(4)
            _, self.confirm_write = imgui.checkbox('I understand that this rewrites the original files', self.confirm_write)
            ig.begin_disabled(busy or not count or not self.confirm_write or not any(self.fields.values()))
            if cy.button('Write into the files', 'danger'):
                def written(job):
                    if job['state'] == 'Completed':
                        self.report = job['outputs']; self.confirm_write = False; app.refresh()
                        cy.notify(f"{self.report['written']} "+tr('files written'), 'success' if not self.report['failed'] else 'warning')
                app.submit('write_metadata', {'libraryId': app.library_id(), 'audioIds': self.targets(), 'confirm': True, 'fields': [k for k, v in self.fields.items() if v],
                                              'includeAutoTags': self.include_auto, 'backup': self.backup}, written, 'Write metadata')
            ig.end_disabled()
            for job in app.jobs.running('write_metadata'):
                progress = job.get('progress') or {}
                cy.progress_bar(progress.get('percent', 0)/100, (-1, 0), f"{progress.get('currentStepIndex', 0)}/{progress.get('stepCount', 0)}  {progress.get('currentFile', '')}")
                if cy.icon_text_button('stop', 'Cancel##write'): app.jobs.cancel('write_metadata')
            if self.report:
                cy.callout('success' if not self.report['failed'] else 'warning', f"{self.report['written']} "+tr('files written')+f", {self.report['failed']} "+tr('refused'))
                if self.report.get('backups'): cy.wrapped_faint(tr('Backups: ')+self.report['backups'])
                for result in [r for r in self.report['results'] if not r['ok']][:12]: cy.text_coloured(cy.palette().error, f"{result.get('code', '')}: {result['error']}")
            cy.end_section()
        if app.jobs.message: cy.callout('error', app.jobs.message)


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
        cy.panel_header('Installation', tr('AI engine, models and access'))
        cy.space(4)
        engine = (self.engine or {}).get('engine', {})
        if cy.begin_card('##engine-card', 'AI engine'):
            if engine.get('installed'):
                report = engine.get('report', {})
                cy.badge('Installed', 'success'); ig.same_line(); ig.align_text_to_frame_padding(); cy.text_dim(f"PyTorch {report.get('torch', '?')}   {report.get('device', '')}")
            else:
                cy.badge('Not installed', 'warning')
                cy.wrapped_dim(tr('The AI engine is a private PyTorch environment created in runtime/engines (several GB). It is needed for embedding models and LLMs; browsing, waveforms and playback work without it.'))
            cy.space(4)
            installing = app.jobs.running('install_engine')
            ig.begin_disabled(bool(installing))
            if cy.icon_text_button('download', 'Install or repair the AI engine (GPU)', 'secondary' if engine.get('installed') else 'primary'):
                app.submit('install_engine', {'cpuOnly': False}, lambda job: self.refresh_engine(), 'Engine installation')
            ig.same_line()
            if cy.button('Install CPU-only engine'): app.submit('install_engine', {'cpuOnly': True}, lambda job: self.refresh_engine(), 'Engine installation')
            ig.end_disabled()
            if installing:
                ig.same_line()
                if cy.icon_text_button('stop', 'Cancel##engine'): app.jobs.cancel('install_engine')
                progress = installing[0].get('progress') or {}
                cy.progress_bar(progress.get('percent', -1)/100 if progress.get('percent') is not None else -1, (-1, 0), progress.get('statusMessage', ''))
            cy.space(4)
            from config import save_settings, settings
            if cy.begin_properties('##engine-settings', 250):
                devices = ('auto', 'gpu', 'cpu'); current = settings()['device']
                cy.property('Compute device', 'Applies to analysis, search and the LLM. Changing it unloads the models; CPU mode reserves RAM and no VRAM.')
                ig.set_next_item_width(cy.dp(240))
                changed, index = imgui.combo('##compute-device', devices.index(current) if current in devices else 0, ['Auto (GPU when available)', 'GPU (CUDA) only', 'CPU only'])
                if changed: save_settings({'device': devices[index]}); app.submit('release_models', {}, lambda job: self.refresh_engine(), 'Release')
                idle = int(settings()['idleUnloadSeconds'])//60
                cy.property('Unload models after (minutes of inactivity)', '0 = keep the models loaded until you close the application. Loaded models keep their VRAM (see below); the next search is then instant.')
                ig.set_next_item_width(cy.dp(240))
                changed, minutes = ig.slider_int('##idle-unload', max(1, idle) if idle else 0, 0, 60, '%d')
                if changed: save_settings({'idleUnloadSeconds': minutes*60})
                cy.end_properties()
            for name, worker in ((self.engine or {}).get('workers') or {}).items():
                cy.text_faint(f"worker {name}: {worker['state']}   "+', '.join(f"{k} ({v['device']}, {v.get('vramBytes', 0)/2**30:.1f} GiB)" for k, v in worker['loadedModels'].items()))
                measured = worker.get('measured') or {}
                if measured.get('peakVramBytes'): cy.text_faint(tr('Peak VRAM of this worker: ')+f"{measured['peakVramBytes']/2**30:.1f} GiB")
            if cy.icon_text_button('power', 'Unload models now'): app.submit('release_models', {}, lambda job: self.refresh_engine(), 'Release')
        cy.end_card()
        cy.space(8)
        cy.heading('Models', 2)
        cy.space(2)
        for descriptor in registry.load_registry().values():
            self.draw_model(descriptor)
        cy.space(8)
        if cy.begin_section('Hugging Face access (only for gated or private models)', False):
            cy.wrapped_dim(tr('The token is sent to the operating-system credential store through a private pipe. It never appears in job parameters, command lines or logs.'))
            ig.set_next_item_width(cy.dp(320)); _, self.token = ig.input_text('##token', self.token, ig.InputTextFlags_.password)
            ig.same_line()
            if cy.icon_text_button('lock', 'Store token') and self.token:
                self.message = app.updates.task.start('login', secret=self.token) and tr('Token sent to the credential store.') or tr('Another maintenance action is running.'); self.token = ''
            ig.same_line()
            if cy.button('Forget token'): app.updates.task.start('logout')
            ig.same_line()
            if cy.icon_text_button('globe', 'Create a read token', 'ghost'): webbrowser.open('https://huggingface.co/settings/tokens')
            if self.message: cy.wrapped_dim(self.message)
            cy.end_section()
        self.draw_custom_form()

    def draw_model(self, descriptor):
        app = self.app
        status = installer.model_status(descriptor)
        ig.push_id(descriptor.key)
        import sys
        if '--ui-test-tab=Installation' in sys.argv and descriptor.key in ('m2d-clap@2025', 'm2d-clap@2024'): ig.set_next_item_open(True, ig.Cond_.once)
        tone = STATE_TONE.get(status['state'], 'neutral')
        header_start = ig.get_cursor_screen_pos()
        opened = cy.begin_section(f"{descriptor['displayName']}   [{tr(status['state'])}]###header", False)
        # a coloured dot at the end of the header row: the state at a glance, open or closed
        header_end = ig.get_item_rect_max()
        dot = (header_end[0]-cy.dp(14), (header_start[1]+header_end[1])*0.5)
        ig.get_window_draw_list().add_circle_filled(dot, cy.dp(4), cy.tone_colour(tone), 12)
        if opened:
            cy.badge(status['state'], tone)
            ig.same_line(); ig.align_text_to_frame_padding(); cy.text_faint(f"{descriptor.key}   {descriptor.get('modelType')}   "+', '.join(descriptor.get('capabilities', [])))
            if cy.begin_properties('##model-facts', 150):
                if status.get('downloadBytes'):
                    cy.property('Download size'); ig.text(gigabytes(status['downloadBytes'])+'    '+tr('already present: ')+gigabytes(status.get('presentBytes')))
                if status['state'] == 'Installed':
                    cy.property('Model hash'); cy.text_dim(status.get('modelHash', '')[:24]+'   '+tr('revision: ')+str(descriptor.receipt().get('revision', '')))
                license_info = descriptor.get('license', {})
                cy.property('Licence'); ig.text_wrapped(str(license_info.get('name', 'Not declared')))
                if descriptor.get('validation'): cy.property('Validation'); ig.text_wrapped(descriptor['validation'])
                if descriptor.get('adapter') and status['state'] == 'Installed':
                    from config import save_settings, settings
                    per_model = settings().get('modelDevices', {}); choices = ('', 'gpu', 'cpu')
                    cy.property('Device for this model')
                    ig.set_next_item_width(cy.dp(260))
                    changed, index = imgui.combo('##model-device', choices.index(per_model.get(descriptor.key, '')) if per_model.get(descriptor.key, '') in choices else 0,
                                                 ['Same as the global setting', 'GPU (CUDA)', 'CPU (no VRAM, slower)'])
                    if changed:
                        per_model = dict(per_model); per_model.pop(descriptor.key, None)
                        if choices[index]: per_model[descriptor.key] = choices[index]
                        save_settings({'modelDevices': per_model})
                cy.end_properties()
            license_info = descriptor.get('license', {})
            if status.get('message'): cy.wrapped_dim(status['message'])
            if license_info.get('notes'): cy.wrapped_faint(license_info['notes'])
            resources = descriptor.get('resources') or {}
            if descriptor.get('adapter') and status['state'] == 'Installed' and resources.get('vramBytes'):
                cy.wrapped_faint(tr('Estimated VRAM on GPU: ')+f"{resources['vramBytes']/2**30:.1f} GiB"+tr('. On CPU a search query takes a few seconds; indexing a Library on CPU is much slower.'))
            if license_info.get('url') and cy.icon_text_button('document', 'Open licence', 'ghost'): webbrowser.open(license_info['url'])
            if descriptor.get('repository'):
                ig.same_line()
                if cy.icon_text_button('globe', 'Official page', 'ghost'): webbrowser.open(descriptor['repository'])
            running = [j for j in app.jobs.running('install_model') if j['parameters'].get('modelKey') == descriptor.key]
            if status['state'] == 'NotIntegrated': pass
            elif descriptor.custom:
                if cy.button('Unregister (files are kept)'): app.submit('remove_model', {'modelKey': descriptor.key}, None, 'Unregister')
            else:
                needs = bool(license_info.get('requiresAcceptance')) and status['state'] != 'Installed'
                if needs:
                    _, self.accepted[descriptor.key] = imgui.checkbox('I have read this licence and I accept it personally', self.accepted.get(descriptor.key, False))
                ig.begin_disabled(bool(running) or (needs and not self.accepted.get(descriptor.key, False)))
                label = 'Repair' if status['state'] == 'Installed' else ('Resume' if status.get('presentBytes') else 'Download')
                if cy.icon_text_button('repair' if status['state'] == 'Installed' else 'download', label):
                    app.submit('install_model', {'modelKey': descriptor.key, 'acceptLicense': bool(self.accepted.get(descriptor.key, False)), 'repair': status['state'] == 'Installed'},
                               lambda job: app.refresh(), 'Model installation')
                ig.end_disabled()
                if running:
                    ig.same_line()
                    if cy.icon_text_button('stop', 'Cancel##install'):
                        for job in running: app.jobs.runtime.cancel(app.jobs.actor, job['jobId'])
                    progress = running[0].get('progress') or {}
                    cy.progress_bar(progress.get('percent', 0)/100, (-1, 0), f"{tr(progress.get('currentStep', ''))}  {progress.get('currentFile', '')}  {progress.get('statusMessage', '')}")
                if status['state'] in ('Installed', 'Partial', 'Interrupted', 'Cancelled', 'Failed'):
                    ig.same_line()
                    if cy.icon_text_button('check', 'Verify files') and status['state'] == 'Installed': app.submit('verify_model', {'modelKey': descriptor.key}, self.verified, 'Verify')
                    _, self.delete_analysis[descriptor.key] = imgui.checkbox('Also delete its analysis data in every Library', self.delete_analysis.get(descriptor.key, False))
                    ig.same_line()
                    if cy.icon_text_button('trash', 'Remove Model', 'danger'):
                        app.submit('remove_model', {'modelKey': descriptor.key, 'deleteAnalysis': self.delete_analysis.get(descriptor.key, False)}, lambda job: app.refresh(), 'Remove model')
            cy.end_section()
        ig.pop_id()

    def verified(self, job):
        if job['state'] == 'Completed':
            out = job['outputs']; self.message = tr('Verified files: ')+str(out['files'])+('' if out['verified'] else '   '+tr('problems: ')+str(out['problems']))
            cy.notify(self.message, 'success' if out['verified'] else 'warning')

    def draw_custom_form(self):
        if not cy.begin_section('Add a custom model or another version', False): return
        cy.wrapped_dim(tr('Local models are referenced in place. Use a new version label for a fine-tuned or updated model: each version keeps its own embeddings.'))
        form = self.form
        adapters, kinds = list(registry.BUILTIN_ADAPTERS), ['AudioTextEmbedding', 'AudioEmbedding', 'LLM']
        if cy.begin_properties('##custom-model', 170):
            cy.property('Model id'); _, form['modelId'] = imgui.input_text('##model-id', form['modelId'])
            cy.property('Version'); _, form['version'] = imgui.input_text('##model-version', form['version'])
            cy.property('Display name'); _, form['displayName'] = imgui.input_text('##model-name', form['displayName'])
            cy.property('Folder or weight file'); _, form['localPath'] = imgui.input_text('##model-path', form['localPath'])
            cy.property('Adapter', registry.BUILTIN_ADAPTERS[adapters[form['adapter']]]); _, form['adapter'] = ig.combo('##model-adapter', form['adapter'], adapters)
            cy.property('Model type'); _, form['type'] = ig.combo('##model-type', form['type'], kinds)
            if kinds[form['type']] != 'LLM':
                cy.property('Embedding dimension'); _, form['dimension'] = imgui.input_int('##model-dimension', form['dimension'])
                cy.property('Required sample rate'); _, form['rate'] = imgui.input_int('##model-rate', form['rate'])
                cy.property('Preferred chunk (s)'); _, form['chunk'] = imgui.input_float('##model-chunk', form['chunk'])
            cy.property('Licence name'); _, form['license'] = imgui.input_text('##model-licence', form['license'])
            cy.end_properties()
        if cy.icon_text_button('add', 'Register model'):
            kind = kinds[form['type']]
            parameters = {'modelId': form['modelId'].strip(), 'version': form['version'].strip(), 'displayName': form['displayName'].strip() or form['modelId'].strip(),
                          'modelType': kind, 'adapter': adapters[form['adapter']], 'localPath': form['localPath'].strip(), 'licenseName': form['license'].strip(),
                          'capabilities': ['QueryUnderstanding', 'StructuredOutput'] if kind == 'LLM' else ['AudioEmbedding']+(['TextEmbedding', 'ZeroShotTagging'] if kind == 'AudioTextEmbedding' else [])}
            if kind != 'LLM': parameters.update(embeddingDimension=int(form['dimension']), requiredSampleRate=int(form['rate']), preferredChunkDuration=float(form['chunk']))
            self.app.submit('register_model', parameters, lambda job: self.app.refresh(), 'Register model')
        cy.end_section()


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
        cy.panel_header('Updates', tr('installed: ')+str(state['application']['installed']))
        cy.space(4)
        cy.wrapped_dim(tr('Application, engine sources and model weights are three separate update streams. Updates are staged in runtime/updates, verified, activated at the next start, and can be rolled back. The data folder is never part of an update.'))
        if busy and not self.task.busy: cy.callout('warning', tr('Updates are disabled while an analysis or an installation is running.'))
        cy.space(4)
        changed_a = changed_b = False
        auto_check, auto_download = bool(self.settings.get('auto_check')), bool(self.settings.get('auto_download'))
        if cy.begin_card('##application-updates', 'Application'):
            if cy.begin_properties('##update-settings', 220):
                cy.property('GitHub repository (owner/name)', 'Updates come from the repository this application is published from. Change it only to follow a fork.')
                _, self.repository = imgui.input_text('##repository', self.repository)
                cy.property('Check for updates at startup')
                changed_a, auto_check = cy.toggle_switch('##auto-check', auto_check)
                cy.property('Download updates automatically')
                changed_b, auto_download = cy.toggle_switch('##auto-download', auto_download)
                cy.end_properties()
            if cy.icon_text_button('save', 'Save update settings') or changed_a or changed_b:
                self.settings = save_update_settings({'tool_repository': self.repository.strip(), 'auto_check': auto_check, 'auto_download': auto_download})
            cy.space(4)
            ig.begin_disabled(busy)
            for label, action, icon_name in (('Check application', 'tool-check', 'refresh'), ('Download and verify', 'tool-fetch', 'download'), ('Roll back application', 'tool-rollback', 'back')):
                if cy.icon_text_button(icon_name, label): self.task.start(action)
                ig.same_line()
            ig.new_line(); ig.end_disabled()
            if state['application'].get('pending'): cy.callout('info', tr('Version ready, activated at next start: ')+str(state['application']['pending']))
        cy.end_card()
        cy.space(6)
        if cy.begin_card('##engine-updates', 'Engine sources (pinned revisions)'):
            for name, source in state['engine'].items():
                cy.text_mono(f"{name}   {tr('active: ')}{source['active'][:12]}   {tr('pinned: ')}{source['pinned'][:12]}"+(f"   {tr('available: ')}{source['available'][:12]}" if source.get('available') else ''))
            ig.begin_disabled(busy)
            for label, action in (('Check engine sources', 'engine-check'), ('Stage newest revision', 'engine-fetch'), ('Activate staged engine', 'engine-apply'), ('Roll back engine', 'engine-rollback')):
                if cy.button(label): self.task.start(action)
                ig.same_line()
            ig.new_line(); ig.end_disabled()
            cy.wrapped_faint(tr('Model weights are updated from the Installation tab, with their own versions and licences.'))
        cy.end_card()
        cy.space(6)
        if self.task.busy:
            cy.progress_bar(-1, (-1, cy.dp(4)))
            if cy.icon_text_button('stop', 'Cancel##maintenance'): self.task.cancel()
        if self.task.status: cy.text_dim(self.task.status)
        with cy.Font(cy.mono_font()):
            ig.input_text_multiline('##maintenance-log', log, (-1, cy.dp(220)), ig.InputTextFlags_.read_only)
