"""Interface state shared by the panels: runtime session, job tracking and the asset list.

The interface never schedules work itself. Every operation goes through Runtime.submit with
the authenticated principal of this window, exactly like the CLI and MCP; this module only
remembers which jobs it started and what to do with their outputs. Reading the Library
database to display rows is a read-only query, not an operation.
"""
import time

from audiolib import registry
from audiolib.analysis import library_status
from audiolib.database import facet_counts, fetch_rows, folder_tree, list_ids, open_database
from audiolib.library import get_library, list_libraries
from config import save_settings, settings
from cytools_core import CyToolError

TERMINAL = ('Completed', 'Failed', 'Cancelled')
MAINTENANCE = ('scan_library', 'analyze_library', 'move_cache', 'categorize_library', 'find_duplicates')


class Jobs:
    def __init__(self, runtime, actor, session):
        self.runtime, self.actor, self.session = runtime, actor, session
        self.active = {}        # jobId -> {'operation', 'callback', 'label'}
        self.last = {}          # operation -> last known job dict
        self.message = ''       # last error, already human readable

    def submit(self, operation, parameters, callback=None, label=''):
        try:
            job = self.runtime.submit(self.actor, self.session, operation, parameters)
        except CyToolError as exc:
            self.message = f'{exc.code}: {exc.message}'; return None
        self.active[job['jobId']] = {'operation': operation, 'callback': callback, 'label': label or operation}
        self.last[operation] = job; self.message = ''
        return job['jobId']

    def cancel(self, operation):
        for job_id, info in self.active.items():
            if info['operation'] == operation:
                try: self.runtime.cancel(self.actor, job_id)
                except CyToolError as exc: self.message = f'{exc.code}: {exc.message}'

    def running(self, *operations):
        return [self.last[i['operation']] for i in self.active.values() if not operations or i['operation'] in operations]

    def poll(self):
        for job_id in list(self.active):
            info = self.active[job_id]
            try: job = self.runtime.get_job(self.actor, job_id)
            except CyToolError: self.active.pop(job_id); continue
            self.last[info['operation']] = job
            if job['state'] in TERMINAL:
                self.active.pop(job_id)
                if job['state'] == 'Failed':
                    error = job.get('error') or {}
                    self.message = f"{info['label']}: {error.get('code', 'Error')} - {error.get('message', '')}"
                    if error.get('suggestedAction'): self.message += ' | '+error['suggestedAction']
                if info['callback']:
                    try: info['callback'](job)
                    except Exception as exc: self.message = f"{info['label']}: {exc}"


class Browser:
    """Virtualised asset list: all matching ids (a few bytes each) + a small cache of display rows."""
    WINDOW = 256

    def __init__(self):
        self.library = None; self.database = None
        self.ids, self.rows, self.scores = [], {}, {}
        self.filters, self.sort, self.descending = {}, 'name', False
        self.search = None          # last search_sounds output, or None when browsing
        self.selected = -1
        self.marked, self.anchor = set(), -1     # the multi-selection, by AudioId so it survives reloads and scrolling
        self.folders, self.folder_signature = {}, None
        self.status, self.facets, self.refreshed = None, None, 0.0
        self.registry = registry.load_registry()

    def open(self, library_id):
        self.library = get_library(library_id) if library_id else None
        self.database = open_database(self.library) if self.library else None
        self.search, self.selected = None, -1
        self.marked, self.anchor, self.folder_signature = set(), -1, None
        save_settings({'activeLibrary': library_id or ''})
        self.reload()

    def reload(self, keep_search=False):
        self.rows.clear()
        self.registry = registry.load_registry()
        if not self.library: self.ids, self.status, self.facets = [], None, None; return
        self.library = get_library(self.library.id)
        if not (keep_search and self.search):
            filters = dict(self.filters)
            if not filters.get('rootIds'): filters['rootIds'] = [r['rootId'] for r in self.library.roots if r['enabled']]
            self.ids = list_ids(self.database, filters, self.sort, self.descending); self.search, self.scores = None, {}
        self.keep_visible_marks()
        self.folder_signature = None       # an explicit reload also rebuilds the folder tree (a rename changes paths, not counts)
        self.refresh_status()

    def refresh_status(self):
        if not self.library: return
        self.status = library_status(self.library, self.database, self.registry)
        self.facets = facet_counts(self.database); self.refreshed = time.monotonic()
        signature = tuple(sorted(self.facets.get('roots', {}).items()))
        if signature != self.folder_signature:      # one indexed read, only when files appeared, moved or vanished
            self.folders, self.folder_signature = folder_tree(self.database), signature

    def show_search(self, outputs):
        self.search = outputs
        self.ids = [r['audioId'] for r in outputs['results']]
        self.scores = {r['audioId']: r for r in outputs['results']}
        self.rows.clear(); self.selected = 0 if self.ids else -1
        self.keep_visible_marks()

    def row(self, index):
        audio_id = self.ids[index]
        if audio_id not in self.rows:
            begin = max(0, index-self.WINDOW//4)
            if len(self.rows) > self.WINDOW*8: self.rows.clear()
            self.rows.update(fetch_rows(self.database, self.ids[begin:begin+self.WINDOW]))
        return self.rows.get(audio_id)

    def current(self):
        return self.row(self.selected) if 0 <= self.selected < len(self.ids) else None

    def invalidate(self, audio_ids):
        for audio_id in audio_ids: self.rows.pop(audio_id, None)

    # -- multi-selection ----------------------------------------------------------------------------------------
    def keep_visible_marks(self):
        """A selection only ever holds sounds the list shows: an edit never reaches a file the user cannot see."""
        if self.marked: self.marked &= set(self.ids)
        self.anchor = -1

    def mark_only(self, index):
        self.marked = {self.ids[index]} if 0 <= index < len(self.ids) else set(); self.anchor = index

    def toggle_mark(self, index):
        audio_id = self.ids[index]
        if audio_id in self.marked: self.marked.discard(audio_id)
        else: self.marked.add(audio_id)
        self.anchor = index

    def mark_range(self, index, extend=False):
        """Shift+click: from the last clicked row to this one. Ctrl+Shift+click adds the range to the selection."""
        start = self.anchor if 0 <= self.anchor < len(self.ids) else index
        low, high = sorted((start, index))
        chosen = set(self.ids[low:high+1])
        self.marked = (self.marked | chosen) if extend else chosen
        if self.anchor < 0: self.anchor = index

    def mark_all(self):
        self.marked = set(self.ids)

    def clear_marks(self):
        self.marked, self.anchor = set(), -1

    def targets(self):
        """What an edit applies to: the marked sounds in list order, or the current one when nothing is marked."""
        if self.marked: return [audio_id for audio_id in self.ids if audio_id in self.marked]
        row = self.current()
        return [row['audio_id']] if row else []


def initial_library():
    wanted = settings().get('activeLibrary')
    libraries = list_libraries()
    if any(l.id == wanted for l in libraries): return wanted
    return libraries[0].id if libraries else ''
