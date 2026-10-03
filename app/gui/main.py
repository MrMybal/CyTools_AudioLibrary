"""CyTools_AudioLibrary: Dear ImGui interface. English source strings, French through the catalogue.

Explorer layout: left = libraries, folders, categories, tags, favourites, recent, models;
centre = search bar, filters and the virtualised asset table; bottom = player with the
interactive waveform, asset information and AI results. Every action is a job of the same
CyToolsCore runtime used by the CLI and MCP.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent
sys.path.insert(0, str(APP)); sys.path.insert(0, str(APP/'gui'))

from imgui_bundle import hello_imgui, imgui as ig, portable_file_dialogs as pfd
from ui_common import configure_generation, imgui, run, tr

from audiolib.database import list_ids, user_tag_counts
from audiolib.library import flatten_taxonomy, list_libraries
from audiolib.waveform import Pyramid, waveform_path
from config import DATA, save_settings, settings
from panels import FileToolsPanel, ModelsPanel, QueuePanel, UpdatesPanel
from player import Player
from state import MAINTENANCE, Browser, Jobs, initial_library
import dragdrop
from tool import create_runtime
from waveform_view import WaveformView, clock

FOLDER_NODE = ig.TreeNodeFlags_.open_on_arrow | ig.TreeNodeFlags_.open_on_double_click | ig.TreeNodeFlags_.span_avail_width

VIEW_MODES = ('List', 'Compact', 'Large Row')
LLM_MODES = ('off', 'auto', 'always')
STATE_COLOURS = {'Ready': (0.45, 0.85, 0.5, 1), 'Pending': (0.95, 0.8, 0.3, 1), 'Failed': (0.95, 0.4, 0.4, 1), 'Not Analyzed': (0.6, 0.6, 0.6, 1)}


def open_in_explorer(path):
    path = Path(path)
    if os.name == 'nt': subprocess.Popen(['explorer', '/select,', str(path)] if path.is_file() else ['explorer', str(path)])
    else: subprocess.Popen(['xdg-open', str(path if path.is_dir() else path.parent)])


def size_text(value):
    value = float(value or 0)
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if value < 1024 or unit == 'TB': return f'{value:.0f} {unit}' if unit == 'B' else f'{value:.1f} {unit}'
        value /= 1024


class App:
    def __init__(self, runtime, actor, session):
        self.jobs = Jobs(runtime, actor, session)
        self.browser, self.player, self.wave = Browser(), Player(), WaveformView()
        self.queue, self.models, self.updates, self.file_tools = QueuePanel(self), ModelsPanel(self), UpdatesPanel(self), FileToolsPanel(self)
        preferences = settings()
        self.query, self.llm_mode, self.llm_model = '', preferences['llmAssist'], preferences['llmModel']
        self.search_models = list(preferences['searchModels'])
        self.top_k, self.rrf_k = preferences['topK'], preferences['rrfK']
        self.auto_preview, self.view_mode = preferences['autoPreview'], 0
        self.new_library, self.new_cache, self.cache_target = '', '', ''
        self.dialog, self.dialog_purpose = None, ''
        self.loaded_id, self.tag_input, self.details = None, '', None
        # notes typed in the details panel: saved without a button, when the field loses focus, after a pause, or
        # before another sound is shown; always to the sound they were typed for (notes_owner), never to the next one
        self.notes_owner, self.notes_buffer, self.description_buffer, self.notes_dirty, self.notes_changed = None, '', '', False, 0.0
        self.note_line, self.category_choice, self.batch_counts, self.batch_key = '', 0, {}, None
        # bundle export (a copy of the chosen sounds in a folder) and drag out of the list (copies only)
        self.bundle_layout, self.bundle_manifest, self.bundle_targets, self.bundle_report = 0, True, [], None
        self.pending_drag, self.drag_note = None, ''
        self.duration_min, self.duration_max, self.channels, self.extension, self.rate_min = 0.0, 0.0, 0, '', 0
        self.frames, self.last_status = 0, 0.0
        self.sync = {}       # libraryId -> background synchronisation state
        self.thumbs = {}     # audioId -> small waveform for the list
        self.browser.open(initial_library())

    # -- helpers ----------------------------------------------------------------
    def submit(self, operation, parameters, callback=None, label=''):
        return self.jobs.submit(operation, parameters, callback, label)

    def library_id(self): return self.browser.library.id if self.browser.library else ''

    def refresh(self, job=None):
        self.browser.reload(keep_search=False); self.loaded_id = None; self.thumbs.clear()

    def apply_filters(self):
        filters = {k: v for k, v in self.browser.filters.items() if k in ('rootIds', 'folderPrefix', 'categories', 'tags', 'favorite', 'recent', 'duplicatesOnly', 'status', 'metadataState')}
        if self.duration_min > 0: filters['minDuration'] = self.duration_min
        if self.duration_max > 0: filters['maxDuration'] = self.duration_max
        if self.channels: filters['channels'] = self.channels
        if self.extension.strip(): filters['extensions'] = [e.strip().lstrip('.') for e in self.extension.replace(';', ',').split(',') if e.strip()]
        if self.rate_min: filters['minSampleRate'] = int(self.rate_min)
        self.browser.filters = filters

    def search_parameters(self):
        parameters = {'libraryId': self.library_id(), 'text': self.query.strip(), 'llmAssist': self.llm_mode, 'llmModel': self.llm_model,
                      'topK': int(self.top_k), 'rrfK': int(self.rrf_k), 'device': settings()['device']}
        if self.search_models: parameters['models'] = list(self.search_models)
        self.apply_filters()
        filters = {k: v for k, v in self.browser.filters.items() if v not in (None, '', [], False)}
        if filters: parameters['filters'] = filters
        return parameters

    def run_search(self, **override):
        if not self.library_id(): return
        parameters = {**self.search_parameters(), **override}
        if override.get('similarTo'): parameters.pop('text', None)
        elif not parameters['text']:
            self.apply_filters(); self.browser.reload(); return
        save_settings({'llmAssist': self.llm_mode, 'llmModel': self.llm_model, 'searchModels': self.search_models, 'topK': int(self.top_k), 'rrfK': int(self.rrf_k)})
        def done(job):
            if job['state'] == 'Completed': self.browser.show_search(job['outputs']); self.loaded_id = None
        self.submit('search_sounds', parameters, done, 'Search')

    def select(self, index, play=None):
        if not self.browser.ids: return
        self.browser.selected = max(0, min(len(self.browser.ids)-1, index))
        row = self.browser.current()
        if not row or row['audio_id'] == self.loaded_id: return
        self.flush_notes()
        self.notes_owner, self.notes_buffer, self.description_buffer = row['audio_id'], row.get('notes') or '', row.get('description') or ''
        self.loaded_id, self.details = row['audio_id'], None
        self.wave.set_file(waveform_path(self.browser.library, row['audio_id']))
        start = 0.0
        match = (self.browser.scores.get(row['audio_id']) or {}).get('matchedSegment')
        if match:       # a search hit inside a long recording: show it and start playback there
            self.wave.marker = (match['start'], match['stop']); self.wave.focus(match['start'], match['stop']); start = match['start']
        autoplay = self.auto_preview if play is None else play
        if row['status'] == 'present': self.player.load(row['absolute_path'], row['duration'], autoplay=autoplay, start=start)
        def loaded(job):
            if job['state'] == 'Completed' and job['outputs']['audio_id'] == self.loaded_id: self.details = job['outputs']
        self.submit('get_asset', {'libraryId': self.library_id(), 'audioId': row['audio_id']}, loaded, 'Asset details')

    def edit_asset(self, audio_id, **changes):
        self.edit_targets([audio_id], **changes)

    def edit_targets(self, audio_ids, **changes):
        """One job per 10 000 sounds (the operation's limit). The list, the left panel counts and the details follow
        each job; the player is left alone, so editing never interrupts what is playing."""
        audio_ids = list(audio_ids)
        def done(job, chunk):
            self.browser.invalidate(chunk); self.batch_key = None
            if job['state'] == 'Completed': self.browser.refresh_status()
            current = self.browser.current()
            if current and current['audio_id'] in chunk: self.refresh_details()
        for begin in range(0, len(audio_ids), 10000):
            chunk = audio_ids[begin:begin+10000]
            self.submit('update_assets', {'libraryId': self.library_id(), 'audioIds': chunk, **changes}, lambda job, chunk=chunk: done(job, chunk), 'Edit')

    def refresh_details(self):
        row = self.browser.current()
        if not row: return
        def loaded(job):
            if job['state'] == 'Completed' and job['outputs']['audio_id'] == self.loaded_id: self.details = job['outputs']
        self.submit('get_asset', {'libraryId': self.library_id(), 'audioId': row['audio_id']}, loaded, 'Asset details')

    def flush_notes(self):
        if self.notes_dirty and self.notes_owner:
            self.edit_targets([self.notes_owner], notes=self.notes_buffer, description=self.description_buffer)
        self.notes_dirty = False

    def ask_bundle(self, targets):
        self.bundle_targets = list(targets)
        if self.bundle_targets: self.ask_folder('bundle', 'Choose the bundle folder (copies go there)')

    def export_bundle(self, folder):
        """Copies of the chosen sounds in `folder`: one job per 10 000 sounds, the operation's limit."""
        targets, self.bundle_targets = self.bundle_targets, []
        def done(job):
            if job['state'] == 'Completed': self.bundle_report = job['outputs']
        for begin in range(0, len(targets), 10000):
            self.submit('export_bundle', {'libraryId': self.library_id(), 'audioIds': targets[begin:begin+10000], 'destination': folder,
                                          'layout': ('flat', 'folders')[self.bundle_layout], 'manifest': self.bundle_manifest}, done, 'Bundle')

    def draw_bundle_options(self, targets, key):
        if imgui.small_button('Create Bundle...##'+key): self.ask_bundle(targets)
        if ig.is_item_hovered(): ig.set_tooltip(tr('Copy these sounds into a folder you choose. The originals are not moved or changed, nothing is overwritten.'))
        ig.same_line(); ig.set_next_item_width(130)
        _, self.bundle_layout = imgui.combo('##bundle-layout-'+key, self.bundle_layout, ['Flat', 'Keep folders'])
        ig.same_line(); _, self.bundle_manifest = imgui.checkbox('bundle.json##'+key, self.bundle_manifest)
        if ig.is_item_hovered(): ig.set_tooltip(tr('A list of the copied files with their source, tags and categories. Untick it to import the folder into a game engine without it.'))

    def start_drag(self, index, row):
        """Dragging a row carries the selection when the row is part of it, otherwise that sound alone."""
        ids = self.browser.targets() if row['audio_id'] in self.browser.marked else [row['audio_id']]
        self.pending_drag = self.browser.paths_of(ids)

    def finish_drag(self):
        paths, self.pending_drag = self.pending_drag, None
        result = dragdrop.drag_files(paths)
        ig.get_io().add_mouse_button_event(ig.MouseButton_.left, False)     # the drop consumed the release: tell ImGui
        self.drag_note = '' if result in ('copied', 'cancelled') else result

    def show_folder(self, root_id, prefix):
        """Show one folder of one root, sub-folders included. prefix '' = the whole root, None = every folder again."""
        browser = self.browser
        browser.filters.pop('folderPrefix', None)
        browser.filters['rootIds'] = None if prefix is None else [root_id]
        if prefix: browser.filters['folderPrefix'] = prefix
        self.apply_filters(); browser.reload()

    def folder_menu(self, root, path):
        """Right-click menu of a root folder (path '') or of one of its sub-folders."""
        library = self.browser.library
        where = os.path.join(root['path'], *path.split('/')) if path else root['path']
        scope = {'rootIds': [root['rootId']], **({'folderPrefix': path} if path else {})}
        if imgui.menu_item('Show This Folder', '', False)[0]: self.show_folder(root['rootId'], path)
        if imgui.menu_item('Select Every Sound In This Folder', '', False)[0]:
            self.show_folder(root['rootId'], path); self.browser.mark_all()
            if self.browser.ids: self.select(0, play=False)
        if imgui.menu_item('Analyze This Folder', '', False)[0]:
            ids = list_ids(self.browser.database, scope)
            if ids: self.submit('analyze_library', {'libraryId': library.id, 'audioIds': ids}, self.refresh, 'Analysis')
        if imgui.menu_item('Open Folder', '', False)[0]: open_in_explorer(where)
        if not path:
            if imgui.menu_item('Rescan Folder', '', False)[0]: self.submit('scan_library', {'libraryId': library.id, 'rootIds': [root['rootId']]}, self.refresh, 'Scan')
            if imgui.menu_item('Remove Folder', '', False)[0]: self.submit('remove_folder', {'libraryId': library.id, 'rootId': root['rootId']}, self.refresh, 'Remove folder')

    def draw_folder_children(self, root, node, path):
        """Sub-folders of an opened folder. Only opened levels are built, so a deep library costs nothing while closed."""
        browser = self.browser
        active = browser.filters.get('folderPrefix') if browser.filters.get('rootIds') == [root['rootId']] else None
        for name in sorted(node['children'], key=str.casefold):
            child = node['children'][name]
            child_path = f'{path}/{name}' if path else name
            flags = FOLDER_NODE | (ig.TreeNodeFlags_.selected if active == child_path else 0) | (0 if child['children'] else ig.TreeNodeFlags_.leaf)
            opened = ig.tree_node_ex(f"{name}  ({child['files']})##{child_path}", flags)
            if ig.is_item_clicked() and not ig.is_item_toggled_open(): self.show_folder(root['rootId'], '' if active == child_path else child_path)
            if ig.begin_popup_context_item('##menu-'+child_path): self.folder_menu(root, child_path); ig.end_popup()
            if opened:
                if child['children']: self.draw_folder_children(root, child, child_path)
                ig.tree_pop()

    # -- background synchronisation ---------------------------------------------------------------------------
    SYNC_MODES = ('auto', 'ask', 'off')

    def auto_sync(self):
        """Every Library is checked in the background (read-only job). 'auto' updates by itself, 'ask' shows a button.

        One step at a time and never while a scan, an analysis or a cache move is running, so the watcher cannot pile up
        jobs. Everything goes through the runtime: the window never blocks, and the CLI/MCP see the same jobs.
        """
        if self.jobs.running('check_library', *MAINTENANCE): return
        now = time.monotonic()
        for library in list_libraries():
            settings_ = library.settings
            if settings_['autoSync'] == 'off': continue
            state = self.sync.setdefault(library.id, {'last': -1e9, 'pending': None, 'dismissed': None, 'note': ''})
            if now-state['last'] < max(30, settings_['autoSyncIntervalSeconds']): continue
            state['last'] = now
            def checked(job, library=library, state=state):
                if job['state'] != 'Completed': return
                report = job['outputs']; signature = (report['new'], report['modified'], report['missing'], report['restored'], report['pendingMetadata'])
                state['note'] = time.strftime('%H:%M:%S')+'  '+self.sync_text(report)
                if not report['changed']:
                    state['pending'] = None
                    if library.settings['autoAnalyze'] and library.settings['autoSync'] == 'auto' and not self.jobs.running('analyze_library'):
                        # scanned (by hand or earlier) but not yet embedded with an installed enabled model
                        from audiolib.analysis import library_status
                        from audiolib.database import open_database
                        lines = library_status(library, open_database(library), self.browser.registry)['models']
                        if any(m.get('installed') and m['pending'] > 0 for m in lines): self.queue.start(library_id=library.id)
                    return
                if library.settings['autoSync'] == 'auto': self.start_sync(library.id)
                elif signature != state['dismissed']: state['pending'] = dict(report, signature=signature)
            self.submit('check_library', {'libraryId': library.id}, checked, 'Check')
            return      # one Library per pass

    def sync_text(self, report):
        parts = [f"{report[key]} {tr(label)}" for key, label in (('new', 'new'), ('modified', 'modified'), ('missing', 'missing'), ('restored', 'restored')) if report[key]]
        if report['unavailableFolders']: parts.append(tr('folder unavailable: ')+', '.join(report['unavailableFolders']))
        return ', '.join(parts) or tr('up to date')

    def start_sync(self, library_id):
        state = self.sync.setdefault(library_id, {'last': time.monotonic(), 'pending': None, 'dismissed': None, 'note': ''})
        state['pending'] = None
        def scanned(job):
            if job['state'] != 'Completed': return
            summary = job['outputs']
            if library_id == self.library_id(): self.refresh()
            library = next((l for l in list_libraries() if l.id == library_id), None)
            ready = library and [k for k in library.enabled_models if k in self.browser.registry and self.browser.registry[k].installed]
            if library and library.settings['autoAnalyze'] and ready and (summary['new'] or summary['modified']): self.queue.start(library_id=library_id)
        self.submit('scan_library', {'libraryId': library_id}, scanned, 'Automatic update')

    def draw_sync_banner(self):
        names = {l.id: l.name for l in list_libraries()}
        for library_id, state in self.sync.items():
            report = state.get('pending')
            if not report or library_id not in names: continue
            ig.push_id('sync-'+library_id)
            ig.text_colored(STATE_COLOURS['Pending'], names[library_id]+': '+tr('changes detected in the folders')+'  ('+self.sync_text(report)+')')
            ig.same_line()
            if imgui.button('Update now'): self.start_sync(library_id)
            ig.same_line()
            if imgui.button('Ignore'): state['dismissed'], state['pending'] = report['signature'], None
            ig.pop_id()

    def draw_sync_settings(self, library):
        if not imgui.collapsing_header('Automatic update'): return
        settings_ = library.settings
        changed, index = imgui.combo('Watch folders', self.SYNC_MODES.index(settings_['autoSync']), ['Update automatically', 'Ask me first', 'Off'])
        if changed: self.submit('update_library', {'libraryId': library.id, 'settings': {'autoSync': self.SYNC_MODES[index]}}, self.refresh, 'Settings')
        ig.set_next_item_width(90)
        minutes = max(1, settings_['autoSyncIntervalSeconds']//60)
        edited, minutes = imgui.input_int('Check every (minutes)', minutes, 0)
        if edited and ig.is_item_deactivated_after_edit() or (edited and minutes != max(1, settings_['autoSyncIntervalSeconds']//60) and not ig.is_item_active()):
            self.submit('update_library', {'libraryId': library.id, 'settings': {'autoSyncIntervalSeconds': max(1, min(1440, minutes))*60}}, self.refresh, 'Settings')
        changed, value = imgui.checkbox('Also analyze new files with the enabled models', bool(settings_['autoAnalyze']))
        if changed: self.submit('update_library', {'libraryId': library.id, 'settings': {'autoAnalyze': value}}, self.refresh, 'Settings')
        if imgui.button('Check now'): self.sync.setdefault(library.id, {'last': 0, 'pending': None, 'dismissed': None, 'note': ''}).update(last=-1e9, dismissed=None)
        note = self.sync.get(library.id, {}).get('note')
        if note: ig.text_disabled(tr('Last check: ')+note)
        ig.text_disabled(tr('Missing files are hidden and kept in the database (a moved file keeps its tags); nothing is deleted.'))

    # -- dialogs ------------------------------------------------------------------
    def ask_folder(self, purpose, title):
        self.dialog, self.dialog_purpose = pfd.select_folder(tr(title), str(Path.home())), purpose

    def poll_dialog(self):
        if self.dialog is None or not self.dialog.ready(): return
        folder, purpose = self.dialog.result(), self.dialog_purpose
        self.dialog = None
        if not folder: return
        if purpose == 'add-folder': self.submit('add_folder', {'libraryId': self.library_id(), 'path': folder}, self.refresh, 'Add folder')
        elif purpose == 'new-cache': self.new_cache = folder
        elif purpose == 'move-cache': self.cache_target = folder
        elif purpose == 'bundle': self.export_bundle(folder)

    # -- left panel ---------------------------------------------------------------
    def draw_left(self):
        browser = self.browser
        libraries = list_libraries()
        names = [l.name for l in libraries] or [tr('(no Library)')]
        index = next((i for i, l in enumerate(libraries) if l.id == self.library_id()), 0)
        ig.set_next_item_width(-1)
        changed, index = ig.combo('##library', index, names)
        if changed and libraries: browser.open(libraries[index].id); self.loaded_id = None
        if imgui.collapsing_header('New Library'):
            _, self.new_library = imgui.input_text('Name##new-library', self.new_library)
            _, self.new_cache = imgui.input_text('Cache folder##new-library', self.new_cache)
            if imgui.button('Browse##new-cache'): self.ask_folder('new-cache', 'Choose the cache folder')
            ig.text_wrapped(tr('Empty = data/cache of this Tool. The cache holds the database, waveforms and embeddings; nothing is written in your audio folders.'))
            if imgui.button('Create Library') and self.new_library.strip():
                def created(job):
                    if job['state'] == 'Completed': browser.open(job['outputs']['libraryId']); self.new_library = ''
                self.submit('create_library', {'name': self.new_library.strip(), 'cacheLocation': self.new_cache.strip()}, created, 'Create Library')
        if not browser.library: return
        library = browser.library
        if imgui.collapsing_header('Folders', ig.TreeNodeFlags_.default_open):
            if imgui.button('Add Folder'): self.ask_folder('add-folder', 'Add an audio folder')
            ig.same_line()
            if imgui.button('Rescan All'): self.submit('scan_library', {'libraryId': library.id}, self.refresh, 'Scan')
            for root in library.roots:
                ig.push_id(root['rootId'])
                changed, enabled = ig.checkbox('##enabled', root['enabled'])
                if changed: self.submit('set_folder_enabled', {'libraryId': library.id, 'rootId': root['rootId'], 'enabled': enabled}, self.refresh, 'Folder')
                ig.same_line()
                count = (browser.facets or {}).get('roots', {}).get(root['rootId'], 0)
                selected = browser.filters.get('rootIds') == [root['rootId']] and not browser.filters.get('folderPrefix')
                tree = browser.folders.get(root['rootId']) or {'children': {}}
                flags = FOLDER_NODE | (ig.TreeNodeFlags_.selected if selected else 0) | (0 if tree['children'] else ig.TreeNodeFlags_.leaf)
                if '--ui-test-open-folders' in sys.argv: ig.set_next_item_open(True, ig.Cond_.once)     # rendering proof of the tree
                opened = ig.tree_node_ex(f"{Path(root['path']).name or root['path']}  ({count})##root", flags)
                if ig.is_item_hovered(): ig.set_tooltip(root['path'])
                if ig.is_item_clicked() and not ig.is_item_toggled_open(): self.show_folder(root['rootId'], None if selected else '')
                if ig.begin_popup_context_item('##folder-menu'): self.folder_menu(root, ''); ig.end_popup()
                if opened:
                    if tree['children']: self.draw_folder_children(root, tree, '')
                    ig.tree_pop()
                ig.pop_id()
            ig.push_style_color(ig.Col_.text, ig.get_style_color_vec4(ig.Col_.text_disabled))
            ig.text_wrapped(tr('Arrow: open a folder. Click: show it. Right-click: select, analyze, open, rescan.'))
            ig.pop_style_color()
        if imgui.collapsing_header('Categories', ig.TreeNodeFlags_.default_open):
            counts = (browser.facets or {}).get('categories', {})
            active = (browser.filters.get('categories') or [None])[0]
            for identifier, name, parents, _ in flatten_taxonomy(library.taxonomy):
                ig.indent(12.0*len(parents)+0.01)
                clicked, _ = ig.selectable(f'{name}  ({counts.get(identifier, 0)})##category-{identifier}', active == identifier)
                if clicked:
                    browser.filters['categories'] = None if active == identifier else [identifier]; self.apply_filters(); browser.reload()
                ig.unindent(12.0*len(parents)+0.01)
        if imgui.collapsing_header('Tags'):
            active = (browser.filters.get('tags') or [None])[0]
            for tag in ((browser.facets or {}).get('tags') or [])[:150]:
                clicked, _ = ig.selectable(f"{tag['tag']}  ({tag['count']}){' *' if tag['user'] else ''}##tag-{tag['tag']}", active == tag['tag'])
                if clicked:
                    browser.filters['tags'] = None if active == tag['tag'] else [tag['tag']]; self.apply_filters(); browser.reload()
            ig.text_disabled(tr('* = contains user tags'))
        for label, key in (('Favorites', 'favorite'), ('Recent', 'recent'), ('Duplicates', 'duplicatesOnly')):
            changed, value = imgui.checkbox(label, bool(browser.filters.get(key)))
            if changed: browser.filters[key] = value; self.apply_filters(); browser.reload()
        if imgui.collapsing_header('Models', ig.TreeNodeFlags_.default_open):
            lines = {m['modelKey']: m for m in (browser.status or {}).get('models', [])}
            for descriptor in browser.registry.values():
                if not descriptor.is_embedding or not descriptor.get('adapter'): continue
                enabled = descriptor.key in library.enabled_models
                ig.begin_disabled(not descriptor.installed and not enabled)
                changed, value = ig.checkbox(descriptor['displayName']+'##enable-'+descriptor.key, enabled)
                ig.end_disabled()
                if changed:
                    models = [k for k in library.enabled_models if k != descriptor.key]+([descriptor.key] if value else [])
                    self.submit('update_library', {'libraryId': library.id, 'enabledModels': models}, self.refresh, 'Models')
                line = lines.get(descriptor.key)
                if line: ig.same_line(); ig.text_colored(STATE_COLOURS['Ready' if line['percent'] >= 100 else 'Pending'], f"{line['percent']:.0f}%")
                elif not descriptor.installed: ig.same_line(); ig.text_disabled(tr('not installed'))
            if imgui.button('Analyze Library'): self.queue.start()
        self.draw_sync_settings(library)
        if imgui.collapsing_header('Cache'):
            ig.text_wrapped(str(library.cache))
            _, self.cache_target = imgui.input_text('New location##cache', self.cache_target)
            if imgui.button('Browse##move-cache'): self.ask_folder('move-cache', 'Choose the new cache folder')
            ig.same_line()
            if imgui.button('Move Cache') and self.cache_target.strip():
                self.submit('move_cache', {'libraryId': library.id, 'cacheLocation': self.cache_target.strip()}, self.refresh, 'Move cache')
            if imgui.button('Open Cache Folder'): open_in_explorer(library.cache)

    # -- centre: search, filters, table -------------------------------------------------
    def draw_search(self):
        browser = self.browser
        ig.set_next_item_width(max(200.0, ig.get_content_region_avail().x-560))
        entered, self.query = ig.input_text_with_hint('##query', tr('Describe the sound you are looking for, in any language'), self.query, ig.InputTextFlags_.enter_returns_true)
        ig.same_line()
        searching = bool(self.jobs.running('search_sounds'))
        if (imgui.button('Search') or entered) and not searching: self.run_search()
        ig.same_line()
        if imgui.button('Clear'): self.query = ''; browser.filters.pop('metadataState', None); browser.reload()
        ig.same_line(); ig.set_next_item_width(110)
        changed, mode = imgui.combo('LLM Search Assist', LLM_MODES.index(self.llm_mode), ['Off', 'Auto', 'Always'])
        if changed: self.llm_mode = LLM_MODES[mode]
        if imgui.collapsing_header('Search models and filters'):
            embedding = [d for d in browser.registry.values() if d.is_embedding and browser.library and d.key in browser.library.enabled_models]
            if imgui.radio_button('All Enabled Models', not self.search_models): self.search_models = []
            for descriptor in embedding:
                ig.same_line()
                changed, value = ig.checkbox(descriptor['displayName']+'##search-'+descriptor.key, descriptor.key in self.search_models)
                if changed: self.search_models = [k for k in self.search_models if k != descriptor.key]+([descriptor.key] if value else [])
            llms = [d for d in browser.registry.values() if d.is_llm and d.installed]
            keys = ['']+[d.key for d in llms]
            ig.set_next_item_width(220)
            changed, index = imgui.combo('LLM', keys.index(self.llm_model) if self.llm_model in keys else 0, [tr('Default')]+[d['displayName'] for d in llms])
            if changed: self.llm_model = keys[index]
            ig.same_line(); ig.set_next_item_width(90); _, self.top_k = imgui.input_int('Top K', int(self.top_k), 0); self.top_k = max(1, min(2000, self.top_k))
            ig.same_line(); ig.set_next_item_width(90); _, self.rrf_k = imgui.input_int('RRF K', int(self.rrf_k), 0); self.rrf_k = max(1, min(1000, self.rrf_k))
            ig.set_next_item_width(90); c1, self.duration_min = imgui.input_float('Min duration (s)', self.duration_min, 0, 0, '%.1f')
            ig.same_line(); ig.set_next_item_width(90); c2, self.duration_max = imgui.input_float('Max duration (s)', self.duration_max, 0, 0, '%.1f')
            ig.same_line(); ig.set_next_item_width(110); c3, channel = imgui.combo('Channels', {0: 0, 1: 1, 2: 2}.get(self.channels, 0), ['Any', 'Mono', 'Stereo']); self.channels = channel
            ig.same_line(); ig.set_next_item_width(110); c4, self.extension = imgui.input_text('Types (wav,flac)', self.extension)
            ig.same_line(); ig.set_next_item_width(110); c5, self.rate_min = imgui.input_int('Min sample rate', int(self.rate_min), 0)
            if (c1 or c2 or c3 or c5 or (c4 and ig.is_item_deactivated_after_edit())) and not browser.search: self.apply_filters(); browser.reload()
        if browser.search:
            info = browser.search['query'].get('llm') or {}
            line = tr('Results: ')+str(len(browser.ids))+'  |  '+tr('fusion: ')+', '.join(f"{k} x{v:g}" for k, v in browser.search['fusion']['weights'].items())
            if info.get('used'): line += '  |  LLM '+info['modelKey']+f" ({info['seconds']} s)"
            elif info.get('fallback'): line += '  |  '+info['fallback']
            hints = browser.search['query'].get('hints') or {}
            if hints.get('boostedCandidates'): line += '  |  '+tr('category hints: ')+str(hints['boostedCandidates'])+' '+tr('results reordered')
            ig.text_disabled(line)
            structured = browser.search['query'].get('structured')
            if structured and ig.is_item_hovered():
                detail = [f'{key}: {", ".join(structured[key])}' for key in
                          ('queries', 'events', 'properties', 'environment', 'exclude', 'temporal', 'categories', 'tags') if structured.get(key)]
                if hints.get('ignoredCategories'):
                    detail.append(tr('Not in this Library, ignored: ')+', '.join(hints['ignoredCategories']))
                if detail: ig.set_tooltip('\n'.join(detail))

    def draw_header(self):
        status = self.browser.status
        if not status: ig.text_wrapped(tr('Create a Library, add folders, then scan.')); return
        parts = [f"{status['files']:,} ".replace(',', ' ')+tr('files'), tr('Metadata')+f": {status['metadata']['percent']:.0f}%", tr('Waveforms')+f": {status['waveforms']['percent']:.0f}%"]
        parts += [f"{m.get('displayName', m['modelKey'])}: {m['percent']:.0f}%" for m in status['models']]
        if status['missing']: parts.append(f"{status['missing']} "+tr('missing'))
        ig.text_wrapped('   '.join(parts))      # one entry per enabled model: it wraps instead of running under the view controls
        failed = status['metadata']['failed']
        if failed:
            ig.text_colored(STATE_COLOURS['Failed'], f'{failed} '+tr('files could not be read'))
            if ig.is_item_hovered(): ig.set_tooltip('\n'.join(f"{r['count']} x {r['error']}" for r in status.get('failureReasons', []))+'\n'+tr('Select a file: the AI Analysis tab shows the exact error.'))
            ig.same_line()
            if imgui.small_button('Show failed files'):
                self.browser.filters['status'] = 'present'; self.browser.filters['metadataState'] = 'Failed'; self.apply_filters(); self.browser.reload()
        prefix, marked = self.browser.filters.get('folderPrefix'), len(self.browser.marked)
        if prefix:
            ig.text_colored(STATE_COLOURS['Pending'], tr('Folder: ')+prefix); ig.same_line()
            if imgui.small_button('Show All Folders'): self.show_folder('', None)
            ig.same_line()
        if marked > 1:
            ig.text(f'{marked} '+tr('sounds selected')); ig.same_line()
            if imgui.small_button('Clear Selection##header'): self.browser.clear_marks()
        else: ig.text_disabled(tr('Ctrl+click or Shift+click selects several sounds, Ctrl+A the whole list. Drag them out to copy them.'))
        report = self.bundle_report
        if report:
            ig.text_colored(STATE_COLOURS['Ready'], tr('Bundle: ')+f"{report['copied']+report['renamed']} "+tr('copied')+
                            f", {report['identical']} "+tr('already there')+(f", {report['missing']} "+tr('missing') if report['missing'] else '')+
                            '  ->  '+report['destination'])
            ig.same_line()
            if imgui.small_button('Open Bundle Folder'): open_in_explorer(report['destination'])
            ig.same_line()
            if ig.small_button('x##bundle-report'): self.bundle_report = None
        if self.drag_note: ig.text_colored(STATE_COLOURS['Failed'], self.drag_note)
        ig.set_next_item_width(120)
        changed, self.view_mode = imgui.combo('View', self.view_mode, list(VIEW_MODES))
        ig.same_line()
        changed, self.auto_preview = imgui.checkbox('Auto Preview', self.auto_preview)
        if changed: save_settings({'autoPreview': self.auto_preview})

    def thumbnail(self, audio_id, duration):
        """64 (min, max) pairs from the coarsest level of the cached pyramid: one small file read per visible row, then cached."""
        if audio_id in self.thumbs: return self.thumbs[audio_id]
        if len(self.thumbs) > 6000: self.thumbs.clear()
        value = None
        try:
            path = waveform_path(self.browser.library, audio_id)
            if path.is_file():
                pyramid = Pyramid(path); value = pyramid.read(0.0, pyramid.duration, 64)
        except (OSError, ValueError): value = None
        self.thumbs[audio_id] = value
        return value

    def draw_thumbnail(self, audio_id, duration, height, playing):
        width = max(24.0, ig.get_content_region_avail().x)
        origin = ig.get_cursor_screen_pos(); ig.dummy((width, height))
        peaks = self.thumbnail(audio_id, duration)
        if peaks is None or not len(peaks[0]): return
        low, high = peaks; draw = ig.get_window_draw_list()
        middle, half = origin.y+height/2, height/2-1
        colour = ig.get_color_u32((0.98, 0.62, 0.2, 1) if playing else (0.36, 0.72, 0.95, 0.9))
        step = width/len(low)
        for index in range(len(low)):
            x = origin.x+(index+0.5)*step
            top, bottom = middle-float(high[index])*half, middle-float(low[index])*half
            draw.add_line((x, top), (x, max(bottom, top+1.0)), colour, max(1.0, step-0.5))
        if playing and duration:
            x = origin.x+width*min(1.0, self.player.position/duration)
            draw.add_line((x, origin.y), (x, origin.y+height), ig.get_color_u32((1, 1, 1, 1)), 1.0)

    def play_row(self, index):
        """Play/stop button of a row: selecting the row loads it; the same row toggles play/pause."""
        row = self.browser.row(index)
        if not row: return
        if index == self.browser.selected and row['audio_id'] == self.loaded_id: self.player.toggle()
        else: self.select(index, play=True)

    def draw_table(self, height):
        browser = self.browser
        searching = browser.search is not None
        models = list(browser.search['fusion']['weights']) if searching else []
        columns = ['', 'Play', 'Name', 'Waveform', 'Duration', 'Type', 'Category', 'Tags', 'Folder', 'Analysis State']+(['Final']+models if searching else [])
        column = {name: position for position, name in enumerate(columns)}
        flags = ig.TableFlags_.scroll_y | ig.TableFlags_.row_bg | ig.TableFlags_.resizable | ig.TableFlags_.borders_inner_v | ig.TableFlags_.sortable | ig.TableFlags_.hideable
        if not ig.begin_table('##assets', len(columns), flags, (0, height)): return
        ig.table_setup_scroll_freeze(0, 1)
        widths = {'': 26, 'Play': 46, 'Waveform': 150, 'Duration': 78, 'Type': 52, 'Final': 60, 'Analysis State': 120}
        sort_keys = {column['Name']: 'name', column['Duration']: 'duration', column['Type']: 'type', column['Folder']: 'folder'}
        for position, name in enumerate(columns):
            column_flags = ig.TableColumnFlags_.width_fixed if name in widths or name in models else ig.TableColumnFlags_.width_stretch
            if position not in sort_keys or searching: column_flags |= ig.TableColumnFlags_.no_sort
            ig.table_setup_column(tr(name) if name and name not in models else name, column_flags, widths.get(name, 70 if name in models else 0))
        ig.table_headers_row()
        specs = ig.table_get_sort_specs()
        if specs and specs.specs_dirty and not searching:
            if specs.specs_count:
                spec = specs.get_specs(0)
                browser.sort = sort_keys.get(spec.column_index, 'name'); browser.descending = spec.get_sort_direction() == ig.SortDirection.descending
                browser.reload()
            specs.specs_dirty = False
        category_names = {identifier: name for identifier, name, _, _ in flatten_taxonomy(browser.library.taxonomy)} if browser.library else {}
        large = VIEW_MODES[self.view_mode] == 'Large Row'
        row_height = ig.get_text_line_height_with_spacing()*(2 if large else 1)+(0 if VIEW_MODES[self.view_mode] == 'Compact' else 4)
        clipper = ig.ListClipper(); clipper.begin(len(browser.ids), row_height)     # only visible rows are built, whatever the Library size
        while clipper.step():
            for index in range(clipper.display_start, clipper.display_end):
                row = browser.row(index)
                if not row: continue
                playing = self.player.playing and row['audio_id'] == self.loaded_id
                ig.table_next_row(0, row_height); ig.push_id(index)
                ig.table_set_column_index(column[''])
                if ig.small_button(('*' if row['favorite'] else '-')+'##favorite'): self.edit_asset(row['audio_id'], favorite=not row['favorite'])
                ig.table_set_column_index(column['Play'])
                if ig.small_button((tr('Stop') if playing else tr('Play'))+'##play'): self.play_row(index)
                ig.table_set_column_index(column['Name'])
                marked = index == browser.selected if not browser.marked else row['audio_id'] in browser.marked
                clicked, _ = ig.selectable(row['filename']+'##row', marked, ig.SelectableFlags_.span_all_columns | ig.SelectableFlags_.allow_overlap, (0, row_height-4))
                if clicked:
                    io = ig.get_io()
                    if io.key_shift: browser.mark_range(index, extend=io.key_ctrl)
                    elif io.key_ctrl: browser.toggle_mark(index)
                    else: browser.mark_only(index)
                    self.select(index)
                if clicked and ig.is_mouse_double_clicked(ig.MouseButton_.left): self.player.play()
                if ig.is_item_active() and ig.is_mouse_dragging(ig.MouseButton_.left, 12.0) and self.pending_drag is None and dragdrop.AVAILABLE:
                    self.start_drag(index, row)
                if ig.begin_popup_context_item('##row-menu'):
                    if imgui.menu_item('Play', '', False)[0]: self.select(index, play=True)
                    if imgui.menu_item('Find Similar Sounds', '', False)[0]: self.run_search(similarTo=row['audio_id'])
                    if imgui.menu_item('Show in Folder', '', False)[0]: open_in_explorer(row['absolute_path'])
                    folder = os.path.dirname(row['relative_path']).replace('\\', '/')
                    if imgui.menu_item('Show Only This Folder', '', False)[0]: self.show_folder(row['root_id'], folder)
                    if len(browser.marked) > 1 and imgui.menu_item('Clear Selection', '', False)[0]: browser.clear_marks()
                    if imgui.menu_item('Create Bundle...', '', False)[0]:
                        self.ask_bundle(browser.targets() if row['audio_id'] in browser.marked else [row['audio_id']])
                    ig.end_popup()
                ig.table_set_column_index(column['Waveform']); self.draw_thumbnail(row['audio_id'], row['duration'], row_height-6, playing)
                ig.table_set_column_index(column['Duration']); ig.text(clock(row['duration'] or 0) if row['duration'] else '-')
                ig.table_set_column_index(column['Type']); ig.text(row['extension'].lstrip('.').upper())
                ig.table_set_column_index(column['Category']); ig.text(', '.join(category_names.get(c, c) for c in row['categories'][:3]))
                ig.table_set_column_index(column['Tags'])
                tags = row['userTags']+[t for t in row['autoTags'] if t not in row['userTags']]
                ig.text(', '.join(tags[:8 if large else 4]))
                ig.table_set_column_index(column['Folder']); ig.text(os.path.dirname(row['relative_path']) or '.')
                ig.table_set_column_index(column['Analysis State'])
                ready = sum(1 for a in row['analysis'].values() if a['state'] == 'Ready'); failed = sum(1 for a in row['analysis'].values() if a['state'] == 'Failed')
                state = 'Failed' if row['metadata_state'] == 'Failed' or failed else ('Pending' if row['metadata_state'] != 'Ready' or ready < len(browser.library.enabled_models) else 'Ready')
                ig.text_colored(STATE_COLOURS[state], tr(state)+(f' ({ready}/{len(browser.library.enabled_models)})' if browser.library.enabled_models else ''))
                if state == 'Failed' and ig.is_item_hovered():
                    problems = [row['error']] if row.get('error') else []
                    problems += [a['error'] for a in row['analysis'].values() if a['state'] == 'Failed' and a.get('error')]
                    ig.set_tooltip('\n'.join(p[:300] for p in problems) or tr('Failed'))
                if searching:
                    hit = browser.scores.get(row['audio_id'], {})
                    ig.table_set_column_index(column['Final']); ig.text(f"{hit.get('finalScore', 0):.0f}%")
                    for offset, key in enumerate(models):
                        ig.table_set_column_index(column['Final']+1+offset); score = hit.get('models', {}).get(key)
                        ig.text(f"{score['score']:.0f}%" if score else '-')
                ig.pop_id()
        ig.end_table()

    # -- bottom: player, waveform, details ------------------------------------------------
    def draw_player(self):
        player, row = self.player, self.browser.current()
        if not row: ig.text_disabled(tr('Select a sound to see its waveform and play it.')); return
        if imgui.button('Pause' if player.playing else 'Play'): player.toggle()
        ig.same_line()
        if imgui.button('Stop'): player.stop()
        ig.same_line(); _, player.loop = imgui.checkbox('Loop', player.loop)
        ig.same_line(); ig.set_next_item_width(120); _, player.volume = imgui.slider_float('Volume', player.volume, 0.0, 1.5, '%.2f')
        ig.same_line()
        if imgui.button('Reset Zoom'): self.wave.reset_zoom()
        ig.same_line()
        if imgui.button('Show in Folder'): open_in_explorer(row['absolute_path'])
        if ig.is_item_hovered(): ig.set_tooltip(row['absolute_path'])
        ig.same_line(); ig.text(row['filename'])
        if player.loading: ig.same_line(); ig.text_disabled(tr('decoding...'))
        if player.error: ig.text_colored(STATE_COLOURS['Failed'], player.error)
        if row['status'] != 'present': ig.text_colored(STATE_COLOURS['Failed'], tr('This file is missing from its folder.'))
        events = self.wave.draw(player, 150.0, tr)
        if 'seek' in events: player.seek(events['seek'])
        if player.playing and self.frames % 120 == 0: self.browser.database.execute('UPDATE assets SET last_played=? WHERE audio_id=?', (time.time(), row['audio_id']))
        if player.selection:
            a, b = player.selection
            ig.text(tr('Start: ')+clock(a)+'   '+tr('End: ')+clock(b)+'   '+tr('Length: ')+f'{b-a:.3f} s')
            ig.same_line()
            if imgui.button('Loop Selection'): player.loop = True; player.seek(a); player.play()
            ig.same_line()
            if imgui.button('Find Sounds Similar To Selection'): self.run_search(similarTo=row['audio_id'], selectionStart=a, selectionEnd=b)
        else: ig.text_disabled(tr('Wheel: zoom   Shift+wheel or middle drag: pan   Click: seek   Drag: select   Double-click: clear selection'))

    def category_choices(self):
        nodes = flatten_taxonomy(self.browser.library.taxonomy)
        return [node[0] for node in nodes], ['  '*len(node[2])+node[1] for node in nodes], {node[0]: node[1] for node in nodes}

    def draw_category_picker(self, targets):
        ids, labels, _ = self.category_choices()
        if not ids: return
        self.category_choice = min(self.category_choice, len(ids)-1)
        ig.text_disabled(tr('Category')); ig.same_line(120)
        ig.set_next_item_width(max(120.0, min(220.0, ig.get_content_region_avail().x-250)))    # the two buttons always fit beside it
        _, self.category_choice = ig.combo('##category-choice', self.category_choice, labels)
        ig.same_line()
        if imgui.small_button('Add Category'): self.edit_targets(targets, addCategories=[ids[self.category_choice]])
        ig.same_line()
        if imgui.small_button('Remove Category'): self.edit_targets(targets, removeCategories=[ids[self.category_choice]])

    def draw_user_data(self, row, details):
        """One sound: your tags, categories, rating, description and notes. Automatic data is shown, never edited."""
        ig.text_disabled(tr('User Tags')); ig.same_line(120)
        for tag in list(row['userTags']):
            if ig.small_button(tag+'  x##user-'+tag): self.edit_asset(row['audio_id'], removeTags=[tag])
            ig.same_line()
        ig.set_next_item_width(140)
        entered, self.tag_input = ig.input_text_with_hint('##new-tag', tr('add a tag'), self.tag_input, ig.InputTextFlags_.enter_returns_true)
        if entered and self.tag_input.strip(): self.edit_asset(row['audio_id'], addTags=[self.tag_input.strip()]); self.tag_input = ''
        ig.text_disabled(tr('Auto Tags')); ig.same_line(120); ig.text_wrapped(', '.join(row['autoTags']) or '-')
        ig.text_disabled(tr('Rating')); ig.same_line(120)
        for stars in range(6):
            if ig.radio_button(f'{stars}##rating', row['rating'] == stars): self.edit_asset(row['audio_id'], rating=stars)
            ig.same_line()
        ig.new_line()
        self.draw_category_picker([row['audio_id']])
        _, _, names = self.category_choices()
        for item in details.get('categoryDetails', []):
            source = tr('user') if item['source'] == 'user' else item['modelKey']+(f" {100*item['score']:.0f}%" if item['score'] is not None else '')
            ig.bullet_text(names.get(item['categoryId'], item['categoryId'])+'   ['+source+']')
            if item['source'] == 'user':
                ig.same_line()
                if ig.small_button('x##user-category-'+item['categoryId']): self.edit_asset(row['audio_id'], removeCategories=[item['categoryId']])
        if self.notes_owner == row['audio_id']:
            ig.text_disabled(tr('Description')); ig.same_line(120); ig.set_next_item_width(-1)
            changed, self.description_buffer = ig.input_text_with_hint('##description', tr('one line, searchable'), self.description_buffer)
            saved = ig.is_item_deactivated_after_edit()
            if changed: self.notes_dirty, self.notes_changed = True, time.monotonic()
            ig.text_disabled(tr('Notes'))
            changed, self.notes_buffer = ig.input_text_multiline('##notes', self.notes_buffer, (-1, 70))
            saved = saved or ig.is_item_deactivated_after_edit()
            if changed: self.notes_dirty, self.notes_changed = True, time.monotonic()
            if self.notes_dirty and (saved or time.monotonic()-self.notes_changed > 1.5): self.flush_notes()
            ig.text_disabled(tr('Saved automatically.') if not self.notes_dirty else tr('Saving...'))
        ig.text_disabled(tr('A re-analysis never removes user tags or user categories.'))

    def draw_batch_editor(self, targets):
        """Several sounds: every change applies to all of them. Removing works on what they have in common or not."""
        ig.text_colored(STATE_COLOURS['Pending'], f'{len(targets)} '+tr('sounds selected: every change below applies to all of them.'))
        key = (len(targets), targets[0], targets[-1], self.browser.refreshed)
        if key != self.batch_key: self.batch_counts, self.batch_key = user_tag_counts(self.browser.database, targets), key
        ig.text_disabled(tr('User Tags')); ig.same_line(120)
        for tag, count in list(self.batch_counts.items())[:40]:
            if ig.small_button(f'{tag} ({count}/{len(targets)})  x##batch-tag-{tag}'): self.edit_targets(targets, removeTags=[tag])
            if ig.is_item_hovered(): ig.set_tooltip(tr('Remove this tag from every selected sound'))
            ig.same_line()
        ig.set_next_item_width(160)
        entered, self.tag_input = ig.input_text_with_hint('##batch-tag', tr('add a tag to all'), self.tag_input, ig.InputTextFlags_.enter_returns_true)
        if entered and self.tag_input.strip(): self.edit_targets(targets, addTags=[self.tag_input.strip()]); self.tag_input = ''
        self.draw_category_picker(targets)
        ig.text_disabled(tr('Rating')); ig.same_line(120)
        for stars in range(6):
            if ig.radio_button(f'{stars}##batch-rating', False): self.edit_targets(targets, rating=stars)
            ig.same_line()
        ig.new_line()
        ig.text_disabled(tr('Favourite')); ig.same_line(120)
        if imgui.small_button('Mark as Favourite'): self.edit_targets(targets, favorite=True)
        ig.same_line()
        if imgui.small_button('Remove from Favourites'): self.edit_targets(targets, favorite=False)
        ig.text_disabled(tr('Notes')); ig.same_line(120); ig.set_next_item_width(-110)
        entered, self.note_line = ig.input_text_with_hint('##batch-note', tr('a line added to the notes of each sound'), self.note_line, ig.InputTextFlags_.enter_returns_true)
        ig.same_line()
        if (imgui.small_button('Add to Notes') or entered) and self.note_line.strip():
            self.edit_targets(targets, appendNotes=self.note_line.strip()); self.note_line = ''
        ig.separator()
        if imgui.small_button('Analyze These Sounds'): self.submit('analyze_library', {'libraryId': self.library_id(), 'audioIds': targets}, self.refresh, 'Analysis')
        self.draw_bundle_options(targets, 'batch')
        ig.push_style_color(ig.Col_.text, ig.get_style_color_vec4(ig.Col_.text_disabled))
        ig.text_wrapped(tr('Rename them or write their tags into the files: File Tools tab, "The selected sounds".'))
        ig.pop_style_color()

    def draw_details(self):
        row = self.browser.current()
        if not row: return
        details = self.details or row
        if not ig.begin_tab_bar('##details'): return
        if imgui.begin_tab_item('Asset Info')[0]:
            db = lambda value, unit='dB': f'{value:.1f} {unit}' if value is not None and value > -190 else '-'
            for label, value in (('Filename', row['filename']), ('Path', row['absolute_path']), ('Duration', clock(row['duration'] or 0)),
                                 ('Sample Rate', f"{row['sample_rate']} Hz" if row['sample_rate'] else '-'), ('Channels', str(row['channels'] or '-')),
                                 ('Bit Depth', str(row['bit_depth'] or '-')), ('Codec', f"{row['codec'] or '-'} / {row['container'] or '-'}"),
                                 ('File Size', size_text(row['file_size'])), ('Peak Level', db(row['peak_db'], 'dBFS')), ('RMS', db(row['rms_db'], 'dBFS')),
                                 ('LUFS', db(row['lufs'], 'LUFS')), ('AudioId', row['audio_id'])):
                ig.text_disabled(tr(label)); ig.same_line(120); ig.text_wrapped(str(value))
            if imgui.button('Show in Folder##info'): open_in_explorer(row['absolute_path'])
            ig.same_line()
            if imgui.button('Copy path'): ig.set_clipboard_text(row['absolute_path'])
            if row.get('duplicate_group'): ig.text_colored(STATE_COLOURS['Pending'], tr('Duplicate group: ')+row['duplicate_group'])
            ig.end_tab_item()
        targets = self.browser.targets()
        # one tab identity (###tags-tab) whether one or several sounds are selected, so ImGui keeps it open when the count changes
        title = tr('Tags and Categories') if len(targets) < 2 else tr('Selection')+f' ({len(targets)})'
        forced = '--ui-test-details=Tags' in sys.argv and self.frames < 400
        if ig.begin_tab_item(title+'###tags-tab', None, ig.TabItemFlags_.set_selected if forced else 0)[0]:
            if len(targets) > 1: self.draw_batch_editor(targets)
            else: self.draw_user_data(row, details)
            ig.end_tab_item()
        wanted_tab = next((a.partition('=')[2] for a in sys.argv if a.startswith('--ui-test-details=')), '')
        if imgui.begin_tab_item('AI Analysis', None, ig.TabItemFlags_.set_selected if wanted_tab == 'AI Analysis' and self.frames < 400 else 0)[0]:
            names = {identifier: name for identifier, name, _, _ in flatten_taxonomy(self.browser.library.taxonomy)}
            lines = details.get('states', [])
            for line in lines[:2]:       # Metadata, Waveform
                ig.text(tr(line['name'])); ig.same_line(220); ig.text_colored(STATE_COLOURS.get(line['state'], STATE_COLOURS['Not Analyzed']), tr(line['state']))
            ig.separator()
            if not lines[2:]: ig.text_disabled(tr('No model is enabled for this Library.'))
            for line in lines[2:]:       # one block per enabled model: everything this model produced for this file
                key = line.get('modelKey', '')
                ig.push_id(key)
                colour = STATE_COLOURS.get(line['state'], STATE_COLOURS['Not Analyzed'])
                ig.text_colored(colour, line['name']); ig.same_line(); ig.text_disabled(key)
                ig.same_line(); ig.text_colored(colour, tr(line['state']))
                if line.get('error'): ig.text_wrapped('    '+line['error'])
                if line['state'] == 'Ready':
                    store = next((s for s in (self.browser.status or {}).get('stores', []) if s['modelKey'] == key and s['current']), None)
                    segments = details.get('segments', {}).get(store['analysisKey'], []) if store else []
                    windows = [s for s in segments if s['index'] >= 0]
                    ig.indent(12)
                    if store: ig.text_disabled(tr('Embedding')+f": {store['dimension']} "+tr('dimensions')+f", {len(windows)} "+tr('segments')+(' + '+tr('whole clip') if any(s['index'] < 0 for s in segments) else ''))
                    if len(windows) > 1 and ig.tree_node(tr('Segments')+f' ({len(windows)})##segments'):
                        for segment in windows[:200]:
                            if ig.small_button(clock(segment['start'])+' > '+clock(segment['stop'])+'##seg%d' % segment['index']):
                                self.wave.marker = (segment['start'], segment['stop']); self.wave.focus(segment['start'], segment['stop']); self.player.seek(segment['start']); self.player.play()
                            if segment['index'] % 4 != 3: ig.same_line()
                        ig.new_line(); ig.tree_pop()
                    categories = [c for c in details.get('categoryDetails', []) if c['source'] == 'auto' and c['modelKey'] == key]
                    tags = [t for t in details.get('tagDetails', []) if t['source'] == 'auto' and t['modelKey'] == key]
                    ig.text(tr('Categories')); ig.same_line(140)
                    ig.text_wrapped(', '.join(f"{names.get(c['categoryId'], c['categoryId'])} {100*(c['score'] or 0):.0f}%" for c in categories) or tr('none above the threshold'))
                    ig.text(tr('Tags')); ig.same_line(140)
                    ig.text_wrapped(', '.join(f"{t['tag']} {100*(t['score'] or 0):.0f}%" for t in tags) or tr('none above the threshold'))
                    for caption in [c for c in details.get('captions', []) if c['modelKey'] == key]:
                        ig.text(tr('Caption')); ig.same_line(140); ig.text_wrapped(caption['text'])
                    ig.unindent(12)
                ig.pop_id(); ig.spacing()
            ig.separator()
            ig.text_disabled(tr('Percentages are zero-shot probabilities over the taxonomy of this Library, relative to the other labels. Thresholds: Library settings.'))
            ig.end_tab_item()
        hit = self.browser.scores.get(row['audio_id'])
        if not hit and imgui.begin_tab_item('Search Match')[0]:
            ig.text_wrapped(tr('This tab shows how a search matched the selected sound: final score, score of each model, matching time segment and recognised concepts. It fills in when the sound comes from a search.'))
            if imgui.button('Find Similar Sounds##match'): self.run_search(similarTo=row['audio_id'])
            if self.player.selection:
                ig.same_line()
                if imgui.button('Find Sounds Similar To Selection##match'): self.run_search(similarTo=row['audio_id'], selectionStart=self.player.selection[0], selectionEnd=self.player.selection[1])
            ig.text_disabled(tr('Or type a description in the search bar above.'))
            ig.end_tab_item()
        if hit and imgui.begin_tab_item('Search Match')[0]:
            ig.text(tr('Final')+f"   {hit['finalScore']:.0f}%     RRF {hit['rrf']:.5f}")
            for key, entry in hit['models'].items():
                segment = entry['segment']
                ig.text(f"{key}   {entry['score']:.0f}%   cos {entry['similarity']:.3f}   "+tr('rank')+f" {entry['rank'] or '-'}")
                if segment['index'] >= 0:
                    ig.same_line()
                    if ig.small_button(clock(segment['start'])+' > '+clock(segment['stop'])+'##go-'+key):
                        self.wave.marker = (segment['start'], segment['stop']); self.wave.focus(segment['start'], segment['stop']); self.player.seek(segment['start']); self.player.play()
            if hit.get('matchedConcepts'):
                ig.text_disabled(tr('Matched concepts')); ig.text_wrapped(', '.join(f"{c['concept']} ({c['score']:.0f}%)" for c in hit['matchedConcepts']))
            ig.text_disabled(tr('Order comes from rank fusion; percentages are each model\'s calibrated similarity.'))
            ig.end_tab_item()
        ig.end_tab_bar()

    # -- keyboard -------------------------------------------------------------------------
    def keyboard(self):
        if ig.get_io().want_text_input or not self.browser.ids: return
        io = ig.get_io()
        if ig.is_key_pressed(ig.Key.space, False): self.player.toggle()
        for key, step in ((ig.Key.down_arrow, 1), (ig.Key.up_arrow, -1)):
            if ig.is_key_pressed(key):
                target = max(0, min(len(self.browser.ids)-1, self.browser.selected+step))
                if io.key_shift: self.browser.mark_range(target, extend=True)
                else: self.browser.mark_only(target)
                self.select(target)
        if io.key_ctrl and ig.is_key_pressed(ig.Key.a, False): self.browser.mark_all()
        if ig.is_key_pressed(ig.Key.escape, False): self.browser.clear_marks()

    def draw_library_tab(self):
        available = ig.get_content_region_avail()
        ig.begin_child('##left', (270, 0), ig.ChildFlags_.borders | ig.ChildFlags_.resize_x); self.draw_left(); ig.end_child()
        ig.same_line()
        ig.begin_child('##main', (0, 0))
        self.draw_search(); self.draw_header()
        if self.jobs.message: ig.text_colored(STATE_COLOURS['Failed'], self.jobs.message)
        self.draw_sync_banner()
        for job in self.jobs.running('scan_library', 'analyze_library', 'search_sounds', 'move_cache'):
            progress = job.get('progress') or {}
            ig.progress_bar(progress.get('percent', 0)/100, (-1, 0), f"{tr(progress.get('currentStep', job['operationId']))}  {progress.get('currentFile', '')}  {progress.get('statusMessage', '')}")
        if self.browser.library:
            bottom = 330.0
            self.draw_table(max(120.0, ig.get_content_region_avail().y-bottom-8))
            ig.begin_child('##player', (max(300.0, ig.get_content_region_avail().x*0.58), 0), ig.ChildFlags_.borders); self.draw_player(); ig.end_child()
            ig.same_line()
            ig.begin_child('##details-panel', (0, 0), ig.ChildFlags_.borders); self.draw_details(); ig.end_child()
        ig.end_child()

    def draw(self):
        self.frames += 1
        self.jobs.poll(); self.poll_dialog(); self.keyboard()
        if not any(a.startswith('--ui-test') or a == '--smoke-test' for a in sys.argv) or '--ui-test-sync' in sys.argv: self.auto_sync()
        if self.browser.library and time.monotonic()-self.last_status > (2.0 if self.jobs.running(*('scan_library', 'analyze_library')) else 30.0):
            self.browser.refresh_status(); self.last_status = time.monotonic()
        wanted = next((a.partition('=')[2] for a in sys.argv if a.startswith('--ui-test-tab=')), '')      # rendering proof of one tab
        flag = lambda name: ig.TabItemFlags_.set_selected if wanted == name and self.frames < 5 else 0
        if imgui.begin_tab_bar('##tabs'):
            if imgui.begin_tab_item('Library', None, flag('Library'))[0]: self.draw_library_tab(); imgui.end_tab_item()
            if imgui.begin_tab_item('Analysis Queue', None, flag('Analysis Queue'))[0]: self.queue.draw(); imgui.end_tab_item()
            if imgui.begin_tab_item('File Tools', None, flag('File Tools'))[0]: self.file_tools.draw(); imgui.end_tab_item()
            if imgui.begin_tab_item('Installation', None, flag('Installation'))[0]: self.models.draw(); imgui.end_tab_item()
            if imgui.begin_tab_item('Updates', None, flag('Updates'))[0]: self.updates.draw(); imgui.end_tab_item()
            imgui.end_tab_bar()       # the facade appends Application log, Advanced and Options here
        if self.pending_drag: self.finish_drag()


def main():
    from branding import configure as configure_branding
    configure_branding('Cyberalien.CyTools_AudioLibrary')
    runner = hello_imgui.RunnerParams()
    runner.app_window_params.window_title = 'CyTools AudioLibrary'
    runner.app_window_params.window_geometry.size = (1500, 920)
    (DATA/'settings').mkdir(parents=True, exist_ok=True)
    runner.ini_filename = str(DATA/'settings'/'imgui.ini')
    runner.fps_idling.enable_idling = False       # the playhead must move while the mouse is still
    # A second window (tests, or a user who wants two instances) needs its own job directory: one runtime per data dir.
    jobs = next((a.partition('=')[2] for a in sys.argv if a.startswith('--jobs-dir=')), '') or DATA/'jobs'
    with create_runtime(Path(jobs)) as runtime:
        actor = runtime.authenticate(runtime.create_client('ImGui')['token'])
        session = runtime.create_session(actor, temporary=False)['sessionId']
        app = App(runtime, actor, session)
        def capture(): return {'operationId': 'search_sounds', 'parameters': app.search_parameters()}
        def restore(value):
            parameters = value['parameters']
            app.query, app.llm_mode, app.llm_model = parameters.get('text', ''), parameters.get('llmAssist', 'auto'), parameters.get('llmModel', '')
            app.search_models, app.top_k, app.rrf_k = list(parameters.get('models', [])), parameters.get('topK', 50), parameters.get('rrfK', 60)
            filters = parameters.get('filters', {})
            app.duration_min, app.duration_max = filters.get('minDuration', 0.0), filters.get('maxDuration', 0.0)
            app.channels, app.rate_min = filters.get('channels', 0), filters.get('minSampleRate', 0)
            app.extension = ','.join(filters.get('extensions', []))
            if parameters.get('libraryId') and parameters['libraryId'] != app.library_id():
                try: app.browser.open(parameters['libraryId'])
                except Exception: pass
        configure_generation(runtime, capture, restore)
        test = next((a for a in sys.argv if a.startswith('--ui-test-library')), '')
        probe = {'searched': False, 'done_at': 0}
        def gui():
            app.draw()
            if '--smoke-test' in sys.argv and app.frames > 30: runner.app_shall_exit = True
            if any(a.startswith('--ui-test-tab=') for a in sys.argv) and app.frames > 150: runner.app_shall_exit = True
            if test:      # rendering proof: real Library, optional real search, first result selected, screenshot on exit
                text = test.partition('=')[2]
                if app.frames == 20 and text: app.query = text; app.run_search(); probe['searched'] = True
                ready = not app.jobs.running('search_sounds') and app.frames > 40
                if ready and not probe['done_at']:
                    app.select(0, play=False); probe['done_at'] = app.frames
                    marked = int(next((a.partition('=')[2] for a in sys.argv if a.startswith('--ui-test-select=')), '0') or 0)
                    if marked: app.browser.marked = set(app.browser.ids[:marked])      # rendering proof of the batch editor
                if probe['done_at'] and app.frames > probe['done_at']+90 and not app.player.loading: runner.app_shall_exit = True
        runner.callbacks.show_gui = gui
        try: run(runner)
        finally: app.player.close()
        tab = next((a.partition('=')[2] for a in sys.argv if a.startswith('--ui-test-tab=')), '')
        if tab:
            from standalone_log import save_screenshot
            from ui_common import preferences
            (DATA/'reports').mkdir(parents=True, exist_ok=True)
            save_screenshot(DATA/'reports'/('tab-'+tab.lower().replace(' ', '-')+'-'+preferences.values['language']+'.png'), hello_imgui.final_app_window_screenshot())
        if test:
            from standalone_log import save_screenshot
            from ui_common import preferences
            reports = DATA/'reports'; reports.mkdir(parents=True, exist_ok=True)
            name = 'library-'+('search-' if probe['searched'] else '')+preferences.values['language']
            save_screenshot(reports/(name+'.png'), hello_imgui.final_app_window_screenshot())
            import json
            current = app.browser.current() or {}
            (reports/(name+'.json')).write_text(json.dumps({'frames': app.frames, 'rows': len(app.browser.ids), 'selected': current.get('filename'),
                'waveformLoaded': app.wave.pyramid is not None, 'decodedFrames': int(len(app.player.audio)), 'detailsLoaded': app.details is not None,
                'searchResults': len(app.browser.scores), 'message': app.jobs.message,
                'backgroundSync': {key: value.get('note') for key, value in app.sync.items()}}, indent=1), 'utf-8')


if __name__ == '__main__':
    main()
