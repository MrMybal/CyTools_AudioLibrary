"""SQLite store of one Library (WAL, shared by the UI, the CLI and an MCP process).

Assets are keyed by a stable AudioId, never by their path. User data (tags, categories,
notes, rating) and AI data are stored apart so that a re-analysis never erases manual work.
"""
import json
import sqlite3
import threading
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS assets(
  audio_id TEXT PRIMARY KEY, root_id TEXT NOT NULL, relative_path TEXT NOT NULL, absolute_path TEXT NOT NULL,
  filename TEXT NOT NULL, extension TEXT NOT NULL, file_size INTEGER NOT NULL,
  created_time REAL, modified_time REAL NOT NULL, fast_hash TEXT NOT NULL, content_hash TEXT,
  duration REAL, channels INTEGER, sample_rate INTEGER, bit_depth INTEGER, codec TEXT, container TEXT, bitrate INTEGER,
  peak_db REAL, rms_db REAL, lufs REAL, embedded TEXT,
  status TEXT NOT NULL DEFAULT 'present', metadata_state TEXT NOT NULL DEFAULT 'Pending',
  waveform_state TEXT NOT NULL DEFAULT 'Pending', error TEXT,
  description TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', favorite INTEGER NOT NULL DEFAULT 0,
  rating INTEGER NOT NULL DEFAULT 0, added_time REAL NOT NULL, last_played REAL, duplicate_group TEXT);
CREATE INDEX IF NOT EXISTS assets_path ON assets(root_id, relative_path);
CREATE INDEX IF NOT EXISTS assets_identity ON assets(file_size, fast_hash);
CREATE INDEX IF NOT EXISTS assets_name ON assets(filename COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS assets_status ON assets(status);
CREATE TABLE IF NOT EXISTS tags(
  audio_id TEXT NOT NULL, tag TEXT NOT NULL COLLATE NOCASE, source TEXT NOT NULL, model_key TEXT NOT NULL DEFAULT '',
  score REAL, PRIMARY KEY(audio_id, tag, source, model_key));
CREATE INDEX IF NOT EXISTS tags_tag ON tags(tag);
CREATE TABLE IF NOT EXISTS asset_categories(
  audio_id TEXT NOT NULL, category_id TEXT NOT NULL, source TEXT NOT NULL, model_key TEXT NOT NULL DEFAULT '',
  score REAL, PRIMARY KEY(audio_id, category_id, source, model_key));
CREATE INDEX IF NOT EXISTS categories_category ON asset_categories(category_id);
CREATE TABLE IF NOT EXISTS analysis(
  audio_id TEXT NOT NULL, analysis_key TEXT NOT NULL, model_key TEXT NOT NULL, state TEXT NOT NULL,
  segments INTEGER NOT NULL DEFAULT 0, error TEXT, updated REAL NOT NULL, PRIMARY KEY(audio_id, analysis_key));
CREATE INDEX IF NOT EXISTS analysis_key ON analysis(analysis_key, state);
CREATE TABLE IF NOT EXISTS vectors(
  analysis_key TEXT NOT NULL, row INTEGER NOT NULL, audio_id TEXT NOT NULL, segment INTEGER NOT NULL,
  start REAL NOT NULL, stop REAL NOT NULL, PRIMARY KEY(analysis_key, row));
CREATE INDEX IF NOT EXISTS vectors_asset ON vectors(analysis_key, audio_id);
CREATE TABLE IF NOT EXISTS stores(
  analysis_key TEXT PRIMARY KEY, model_key TEXT NOT NULL, descriptor TEXT NOT NULL, config TEXT NOT NULL,
  dimension INTEGER NOT NULL, next_row INTEGER NOT NULL DEFAULT 0, generation INTEGER NOT NULL DEFAULT 0,
  relative_dir TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS captions(
  audio_id TEXT NOT NULL, model_key TEXT NOT NULL, text TEXT NOT NULL, updated REAL NOT NULL, PRIMARY KEY(audio_id, model_key));
CREATE TABLE IF NOT EXISTS scans(scan_id INTEGER PRIMARY KEY AUTOINCREMENT, time REAL NOT NULL, summary TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS control(key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""
ASSET_COLUMNS = ('audio_id', 'root_id', 'relative_path', 'absolute_path', 'filename', 'extension', 'file_size',
                 'created_time', 'modified_time', 'fast_hash', 'content_hash', 'duration', 'channels', 'sample_rate',
                 'bit_depth', 'codec', 'container', 'bitrate', 'peak_db', 'rms_db', 'lufs', 'embedded', 'status',
                 'metadata_state', 'waveform_state', 'error', 'description', 'notes', 'favorite', 'rating',
                 'added_time', 'last_played', 'duplicate_group')
SORTS = {'name': 'a.filename COLLATE NOCASE', 'duration': 'a.duration', 'type': 'a.extension', 'folder': 'a.relative_path COLLATE NOCASE',
         'size': 'a.file_size', 'modified': 'a.modified_time', 'added': 'a.added_time', 'rating': 'a.rating',
         'played': 'a.last_played', 'sampleRate': 'a.sample_rate', 'channels': 'a.channels'}
_databases = {}
_guard = threading.Lock()


class Database:
    """Thread-safe wrapper: one connection per thread, every write in a short transaction."""
    def __init__(self, path):
        self.path = str(path)
        self._local = threading.local()
        self._all = []
        self.connection().executescript(SCHEMA)

    def connection(self):
        connection = getattr(self._local, 'connection', None)
        if connection is None:
            connection = sqlite3.connect(self.path, timeout=60, isolation_level=None, check_same_thread=False)
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA journal_mode=WAL'); connection.execute('PRAGMA synchronous=NORMAL')
            connection.execute('PRAGMA busy_timeout=60000')
            self._local.connection = connection
            with _guard: self._all.append(connection)
        return connection

    def execute(self, sql, parameters=()): return self.connection().execute(sql, parameters)
    def query(self, sql, parameters=()): return self.connection().execute(sql, parameters).fetchall()
    def one(self, sql, parameters=()): return self.connection().execute(sql, parameters).fetchone()

    def transaction(self):
        database = self
        class Transaction:
            def __enter__(self): database.execute('BEGIN IMMEDIATE'); return database
            def __exit__(self, kind, value, trace):
                database.execute('ROLLBACK' if kind else 'COMMIT'); return False
        return Transaction()

    def close(self):
        with _guard:
            for connection in self._all:
                try: connection.close()
                except sqlite3.Error: pass
            self._all.clear()
        self._local = threading.local()

    # -- control flags (pause/resume of the analysis queue, across processes) ----
    def control(self, key, default=''):
        row = self.one('SELECT value FROM control WHERE key=?', (key,))
        return row['value'] if row else default

    def set_control(self, key, value):
        self.execute('INSERT INTO control(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, str(value)))

    # -- assets ---------------------------------------------------------
    def asset(self, audio_id):
        row = self.one('SELECT * FROM assets WHERE audio_id=?', (audio_id,))
        return asset_dict(row) if row else None

    def counts(self):
        row = self.one("""SELECT COUNT(*) total, SUM(status='present') present, SUM(status='missing') missing,
            SUM(status='present' AND metadata_state='Ready') metadata_ready, SUM(status='present' AND metadata_state='Failed') metadata_failed,
            SUM(status='present' AND waveform_state='Ready') waveform_ready, SUM(status='present' AND waveform_state='Failed') waveform_failed,
            SUM(CASE WHEN status='present' THEN duration ELSE 0 END) seconds, SUM(CASE WHEN status='present' THEN file_size ELSE 0 END) bytes,
            SUM(favorite) favorites FROM assets""")
        return {key: (row[key] or 0) for key in row.keys()}


def asset_dict(row):
    value = {key: row[key] for key in row.keys()}
    value['favorite'] = bool(value.get('favorite'))
    if 'embedded' in value:
        try: value['embedded'] = json.loads(value['embedded']) if value['embedded'] else {}
        except ValueError: value['embedded'] = {}
    return value


def open_database(library):
    with _guard:
        database = _databases.get(library.id)
        if database is not None and database.path == str(library.database_path): return database
    library.ensure_cache()
    database = Database(library.database_path)
    with _guard: _databases[library.id] = database
    return database


def close_database(library):
    with _guard: database = _databases.pop(library.id, None)
    if database: database.close()


# ---------------------------------------------------------------------------
# Browsing: filters are compiled once into SQL; the UI only materialises visible rows.
# ---------------------------------------------------------------------------
def build_filter(filters):
    """Translate the portable filter object into (where clause, parameters)."""
    filters = filters or {}
    clauses, values = [], []
    status = filters.get('status', 'present')
    if status != 'any': clauses.append('a.status=?'); values.append(status)
    text = str(filters.get('text') or '').strip()
    for word in text.split()[:8]:
        like = '%'+word.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')+'%'
        clauses.append("(a.filename LIKE ? ESCAPE '\\' OR a.relative_path LIKE ? ESCAPE '\\' OR a.description LIKE ? ESCAPE '\\'"
                       " OR EXISTS(SELECT 1 FROM tags t WHERE t.audio_id=a.audio_id AND t.tag LIKE ? ESCAPE '\\'))")
        values += [like, like, like, like]
    if filters.get('rootIds'):
        clauses.append('a.root_id IN (%s)' % ','.join('?'*len(filters['rootIds']))); values += list(filters['rootIds'])
    if filters.get('folderPrefix'):
        prefix = str(filters['folderPrefix']).replace('\\', '/').strip('/')
        clauses.append("(a.relative_path LIKE ? ESCAPE '\\')")
        values.append(prefix.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')+'/%')
    if filters.get('extensions'):
        extensions = [e.lower() if e.startswith('.') else '.'+e.lower() for e in filters['extensions']]
        clauses.append('a.extension IN (%s)' % ','.join('?'*len(extensions))); values += extensions
    for key, column, operator in (('minDuration', 'a.duration', '>='), ('maxDuration', 'a.duration', '<='),
                                  ('minSampleRate', 'a.sample_rate', '>='), ('maxSampleRate', 'a.sample_rate', '<='),
                                  ('minRating', 'a.rating', '>='), ('minBitDepth', 'a.bit_depth', '>=')):
        if filters.get(key) is not None: clauses.append(f'{column} {operator} ?'); values.append(filters[key])
    if filters.get('channels') is not None: clauses.append('a.channels=?'); values.append(int(filters['channels']))
    if filters.get('favorite'): clauses.append('a.favorite=1')
    if filters.get('duplicatesOnly'): clauses.append('a.duplicate_group IS NOT NULL')
    if filters.get('recent'): clauses.append('a.last_played IS NOT NULL')
    for category in filters.get('categories') or []:
        clauses.append('EXISTS(SELECT 1 FROM asset_categories c WHERE c.audio_id=a.audio_id AND c.category_id=?)'); values.append(category)
    for tag in filters.get('tags') or []:
        clauses.append('EXISTS(SELECT 1 FROM tags t WHERE t.audio_id=a.audio_id AND t.tag=?)'); values.append(tag)
    if filters.get('metadataState'): clauses.append('a.metadata_state=?'); values.append(filters['metadataState'])
    state = filters.get('analysisState')
    if state and filters.get('analysisKey'):
        if state == 'NotAnalyzed':
            clauses.append('NOT EXISTS(SELECT 1 FROM analysis s WHERE s.audio_id=a.audio_id AND s.analysis_key=?)'); values.append(filters['analysisKey'])
        else:
            clauses.append('EXISTS(SELECT 1 FROM analysis s WHERE s.audio_id=a.audio_id AND s.analysis_key=? AND s.state=?)')
            values += [filters['analysisKey'], state]
    return (' WHERE '+' AND '.join(clauses)) if clauses else '', values


# Sorts on what the list shows but no single column holds: computed per asset, then applied in Python.
DERIVED_SORTS = ('category', 'tags', 'state')


def list_ids(database, filters=None, sort='name', descending=False, category_names=None, enabled_models=0):
    """All matching AudioIds in display order: a few bytes per asset, even for 100 000 files.
    category = the first category shown (user ones first, then by score), by its name; tags = the first tag shown;
    state = failed, then pending, then ready (and by the number of models done)."""
    where, values = build_filter(filters)
    if sort in DERIVED_SORTS:
        ids = [row[0] for row in database.query('SELECT a.audio_id FROM assets a'+where+' ORDER BY '+SORTS['name']+', a.audio_id', values)]
        return order_ids(ids, sort_values(database, ids, sort, category_names, enabled_models), descending)
    order = SORTS.get(sort, SORTS['name'])+(' DESC' if descending else ' ASC')+', a.audio_id'
    return [row[0] for row in database.query('SELECT a.audio_id FROM assets a'+where+' ORDER BY '+order, values)]


def order_ids(ids, values, descending=False):
    """Stable sort of `ids` by `values` (id -> value); assets without a value always come last."""
    present = [i for i in ids if values.get(i) is not None]
    return sorted(present, key=values.get, reverse=descending)+[i for i in ids if values.get(i) is None]


def sort_values(database, audio_ids, sort, category_names=None, enabled_models=0):
    """id -> the value the list is sorted by, for a column of the database or a derived one (DERIVED_SORTS)."""
    wanted = set(audio_ids)
    if not wanted: return {}
    if sort == 'category':
        names, out = category_names or {}, {}
        for row in database.query('SELECT audio_id,category_id FROM asset_categories GROUP BY audio_id,category_id ORDER BY source DESC, MAX(score) DESC'):
            if row['audio_id'] in wanted and row['audio_id'] not in out: out[row['audio_id']] = str(names.get(row['category_id'], row['category_id'])).casefold()
        return out
    if sort == 'tags':
        user, auto = {}, {}
        for row in database.query('SELECT audio_id,tag,source FROM tags GROUP BY audio_id,tag,source ORDER BY MAX(score) DESC'):
            if row['audio_id'] in wanted: (user if row['source'] == 'user' else auto).setdefault(row['audio_id'], row['tag'].casefold())
        return {**auto, **user}
    if sort == 'state':
        ready, failed = {}, set()
        for row in database.query('SELECT audio_id,state FROM analysis'):
            if row['state'] == 'Ready': ready[row['audio_id']] = ready.get(row['audio_id'], 0)+1
            elif row['state'] == 'Failed': failed.add(row['audio_id'])
        out = {}
        for row in database.query('SELECT audio_id,metadata_state FROM assets'):
            audio_id = row['audio_id']
            if audio_id not in wanted: continue
            done = ready.get(audio_id, 0)
            rank = 0 if row['metadata_state'] == 'Failed' or audio_id in failed else (1 if row['metadata_state'] != 'Ready' or done < enabled_models else 2)
            out[audio_id] = (rank, done)
        return out
    column, out = SORTS.get(sort, SORTS['name']).replace(' COLLATE NOCASE', ''), {}
    ids = list(wanted)
    for begin in range(0, len(ids), 900):
        chunk = ids[begin:begin+900]
        for row in database.query('SELECT a.audio_id,%s FROM assets a WHERE a.audio_id IN (%s)' % (column, ','.join('?'*len(chunk))), chunk):
            value = row[1]
            out[row[0]] = value.casefold() if isinstance(value, str) else value
    return out


def fetch_rows(database, audio_ids):
    """Display rows for a small window of ids, with their tags, categories and analysis states."""
    if not audio_ids: return {}
    marks = ','.join('?'*len(audio_ids))
    rows = {row['audio_id']: asset_dict(row) for row in database.query('SELECT * FROM assets WHERE audio_id IN (%s)' % marks, audio_ids)}
    for row in rows.values(): row.update(userTags=[], autoTags=[], categories=[], analysis={})
    for tag in database.query('SELECT audio_id,tag,source,MAX(score) score FROM tags WHERE audio_id IN (%s) GROUP BY audio_id,tag,source ORDER BY score DESC' % marks, audio_ids):
        rows[tag['audio_id']]['userTags' if tag['source'] == 'user' else 'autoTags'].append(tag['tag'])
    for item in database.query('SELECT audio_id,category_id,source,MAX(score) score FROM asset_categories WHERE audio_id IN (%s) GROUP BY audio_id,category_id ORDER BY source DESC, score DESC' % marks, audio_ids):
        rows[item['audio_id']]['categories'].append(item['category_id'])
    for item in database.query('SELECT audio_id,analysis_key,model_key,state,segments,error FROM analysis WHERE audio_id IN (%s)' % marks, audio_ids):
        rows[item['audio_id']]['analysis'][item['analysis_key']] = {'modelKey': item['model_key'], 'state': item['state'],
                                                                   'segments': item['segments'], 'error': item['error']}
    return rows


def asset_details(database, audio_id):
    row = fetch_rows(database, [audio_id]).get(audio_id)
    if not row: return None
    row['tagDetails'] = [dict(r) for r in database.query('SELECT tag,source,model_key modelKey,score FROM tags WHERE audio_id=? ORDER BY source DESC, score DESC', (audio_id,))]
    row['categoryDetails'] = [dict(r) for r in database.query('SELECT category_id categoryId,source,model_key modelKey,score FROM asset_categories WHERE audio_id=? ORDER BY source DESC, score DESC', (audio_id,))]
    row['captions'] = [dict(r) for r in database.query('SELECT model_key modelKey,text FROM captions WHERE audio_id=?', (audio_id,))]
    row['segments'] = {}
    for item in database.query('SELECT analysis_key,segment,start,stop FROM vectors WHERE audio_id=? ORDER BY analysis_key,segment', (audio_id,)):
        row['segments'].setdefault(item['analysis_key'], []).append({'index': item['segment'], 'start': item['start'], 'stop': item['stop']})
    return row


# -- user data: never touched by an AI re-analysis ---------------------------
def set_user_tags(database, audio_id, tags):
    clean = sorted({str(t).strip() for t in tags if str(t).strip()}, key=str.casefold)
    with database.transaction():
        database.execute("DELETE FROM tags WHERE audio_id=? AND source='user'", (audio_id,))
        database.connection().executemany("INSERT OR IGNORE INTO tags(audio_id,tag,source,model_key,score) VALUES(?,?,'user','',NULL)", [(audio_id, t) for t in clean])
    return clean


def set_user_categories(database, audio_id, categories):
    clean = sorted({str(c) for c in categories if str(c)})
    with database.transaction():
        database.execute("DELETE FROM asset_categories WHERE audio_id=? AND source='user'", (audio_id,))
        database.connection().executemany("INSERT OR IGNORE INTO asset_categories(audio_id,category_id,source,model_key,score) VALUES(?,?,'user','',NULL)", [(audio_id, c) for c in clean])
    return clean


def update_user_fields(database, audio_id, values):
    allowed = {'description': str, 'notes': str, 'favorite': lambda v: int(bool(v)), 'rating': lambda v: max(0, min(5, int(v)))}
    pairs = [(key, allowed[key](value)) for key, value in values.items() if key in allowed]
    if pairs:
        database.execute('UPDATE assets SET '+','.join(k+'=?' for k, _ in pairs)+' WHERE audio_id=?', [v for _, v in pairs]+[audio_id])


def replace_auto_labels(database, model_key, labels):
    """labels: {audio_id: {'tags': [(tag, score)], 'categories': [(id, score)]}}; only this model's auto rows change."""
    with database.transaction():
        connection = database.connection()
        for audio_id, value in labels.items():
            connection.execute("DELETE FROM tags WHERE audio_id=? AND source='auto' AND model_key=?", (audio_id, model_key))
            connection.execute("DELETE FROM asset_categories WHERE audio_id=? AND source='auto' AND model_key=?", (audio_id, model_key))
            connection.executemany("INSERT OR REPLACE INTO tags VALUES(?,?,'auto',?,?)", [(audio_id, t, model_key, float(s)) for t, s in value.get('tags', [])])
            connection.executemany("INSERT OR REPLACE INTO asset_categories VALUES(?,?,'auto',?,?)", [(audio_id, c, model_key, float(s)) for c, s in value.get('categories', [])])


def facet_counts(database):
    """Counts for the left panel; grouped queries stay fast on indexed columns."""
    tags = [dict(r) for r in database.query("""SELECT t.tag, COUNT(DISTINCT t.audio_id) count, MAX(t.source='user') user FROM tags t
        JOIN assets a ON a.audio_id=t.audio_id AND a.status='present' GROUP BY t.tag ORDER BY count DESC LIMIT 500""")]
    categories = {r['category_id']: r['count'] for r in database.query("""SELECT c.category_id, COUNT(DISTINCT c.audio_id) count FROM asset_categories c
        JOIN assets a ON a.audio_id=c.audio_id AND a.status='present' GROUP BY c.category_id""")}
    roots = {r['root_id']: r['count'] for r in database.query("SELECT root_id, COUNT(*) count FROM assets WHERE status='present' GROUP BY root_id")}
    return {'tags': tags, 'categories': categories, 'roots': roots}


def folder_tree(database, root_ids=None):
    """{rootId: node}, node = {'files': recursive count, 'direct': files right here, 'children': {name: node}}.

    Built from the paths already in the database, so it costs one indexed read and never touches the disk:
    a folder that holds no audio file does not appear, which is what a sound library view wants.
    """
    where, values = "WHERE status='present'", []
    if root_ids:
        where += ' AND root_id IN (%s)' % ','.join('?'*len(root_ids)); values = list(root_ids)
    trees = {}
    for row in database.query('SELECT root_id, relative_path FROM assets '+where, values):
        node = trees.setdefault(row['root_id'], {'files': 0, 'direct': 0, 'children': {}})
        node['files'] += 1
        parts = str(row['relative_path']).replace('\\', '/').split('/')[:-1]
        for part in parts:
            node = node['children'].setdefault(part, {'files': 0, 'direct': 0, 'children': {}})
            node['files'] += 1
        node['direct'] += 1
    return trees


def flatten_folders(tree, prefix='', max_depth=None):
    """Depth-first list of the folders under `prefix` (a '/' separated path relative to the root)."""
    node = tree
    for part in [p for p in prefix.replace('\\', '/').strip('/').split('/') if p]:
        node = node['children'].get(part)
        if node is None: return []
    out = []
    def visit(current, path, depth):
        for name in sorted(current['children'], key=str.casefold):
            child = current['children'][name]
            child_path = f'{path}/{name}' if path else name
            out.append({'path': child_path, 'name': name, 'depth': depth, 'files': child['files'],
                        'directFiles': child['direct'], 'subfolders': len(child['children'])})
            if max_depth is None or depth < max_depth: visit(child, child_path, depth+1)
    visit(node, prefix.replace('\\', '/').strip('/'), 1)
    return out


def user_tag_counts(database, audio_ids):
    """{tag: number of the given assets carrying it as a user tag}, read in chunks so any selection size works."""
    counts = {}
    ids = list(audio_ids)
    for begin in range(0, len(ids), 500):
        chunk = ids[begin:begin+500]
        for row in database.query("SELECT tag, COUNT(DISTINCT audio_id) count FROM tags WHERE source='user' AND audio_id IN (%s) GROUP BY tag"
                                  % ','.join('?'*len(chunk)), chunk):
            counts[row['tag']] = counts.get(row['tag'], 0)+row['count']
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold())))


def user_category_ids(database, audio_id):
    return [r['category_id'] for r in database.query("SELECT category_id FROM asset_categories WHERE audio_id=? AND source='user'", (audio_id,))]


def touch_played(database, audio_id):
    database.execute('UPDATE assets SET last_played=? WHERE audio_id=?', (time.time(), audio_id))
