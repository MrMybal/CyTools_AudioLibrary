"""Generate CyTool.json. The manifest is the single contract of the UI, the CLI, JSONL/HTTP and MCP.

    runtime/python/Scripts/python.exe app/build_manifest.py
"""
import json
from pathlib import Path

APP = Path(__file__).resolve().parent
MIB, GIB = 1024**2, 1024**3
VERSION = '0.1.0'

LIBRARY = {'type': 'string', 'pattern': '^[0-9a-f]{8}$', 'description': 'LibraryId returned by create_library or list_libraries'}
AUDIO_ID = {'type': 'string', 'pattern': '^[0-9a-f]{32}$', 'description': 'Stable AudioId of an asset (survives renames and moves)'}
MODEL_KEY = {'type': 'string', 'pattern': '^[A-Za-z][A-Za-z0-9_.-]{0,63}@[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$', 'description': 'modelId@version from list_models'}
MODELS = {'type': 'array', 'items': MODEL_KEY, 'uniqueItems': True, 'maxItems': 16,
          'description': 'Embedding models to use. Empty or absent = every model enabled for the Library. Each model retrieves independently.'}
DEVICE = {'type': 'string', 'enum': ['auto', 'gpu', 'cpu'], 'default': 'auto',
          'description': 'auto = CUDA GPU when the engine sees one, else CPU. gpu fails when CUDA is unavailable. cpu reserves RAM only.'}
PATH = lambda text: {'type': 'string', 'minLength': 1, 'description': text+' Absolute path on the machine running the Tool.', 'x-cy-kind': 'Directory'}
FILTERS = {
    'type': 'object', 'additionalProperties': False, 'description': 'Classic filters, combined with AND. They also restrict a semantic search.',
    'properties': {
        'text': {'type': 'string', 'description': 'Words that must appear in the file name, relative path, description or a tag'},
        'rootIds': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Restrict to these folders of the Library'},
        'folderPrefix': {'type': 'string', 'description': 'Relative sub-folder inside the selected root(s), e.g. "Doors/Metal"'},
        'extensions': {'type': 'array', 'items': {'type': 'string'}, 'description': 'File types, e.g. ["wav", "flac"]'},
        'minDuration': {'type': 'number', 'minimum': 0, 'description': 'Seconds'}, 'maxDuration': {'type': 'number', 'minimum': 0, 'description': 'Seconds'},
        'minSampleRate': {'type': 'integer', 'minimum': 0, 'description': 'Hz, e.g. 48000'}, 'maxSampleRate': {'type': 'integer', 'minimum': 0},
        'minBitDepth': {'type': 'integer', 'minimum': 0}, 'channels': {'type': 'integer', 'minimum': 1, 'maximum': 64, 'description': '1 = mono, 2 = stereo'},
        'categories': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Category ids (user or auto); all must match'},
        'tags': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Tags (user or auto); all must match'},
        'favorite': {'type': 'boolean'}, 'minRating': {'type': 'integer', 'minimum': 0, 'maximum': 5},
        'duplicatesOnly': {'type': 'boolean'}, 'recent': {'type': 'boolean', 'description': 'Only sounds that were played'},
        'status': {'type': 'string', 'enum': ['present', 'missing', 'any'], 'default': 'present'},
        'metadataState': {'type': 'string', 'enum': ['Ready', 'Failed', 'Pending'], 'description': 'Files whose metadata/waveform pass is in this state (Failed = unreadable)'},
        'analysisKey': {'type': 'string'}, 'analysisState': {'type': 'string', 'enum': ['Ready', 'Failed', 'NotAnalyzed']}}}
OBJECT = lambda **properties: {'type': 'object', 'properties': properties, 'additionalProperties': True}
ANY_OBJECT = {'type': 'object', 'additionalProperties': True}


def operation(identifier, name, description, properties, required=(), output=None, *, ram=64*MIB, progress=False, outputs=None, seconds=None, defs=None):
    value = {'id': identifier, 'name': name, 'description': description,
             'inputSchema': {'type': 'object', 'properties': properties, 'required': list(required), 'additionalProperties': False, **({'$defs': defs} if defs else {})},
             'outputSchema': output or ANY_OBJECT, 'resourceRequirements': {'ramBytes': ram}, 'supportedBackends': [], 'permissions': [],
             'canRunAsync': True, 'canCancel': True, 'supportsProgress': progress}
    if outputs: value['outputs'] = outputs
    if seconds: value['estimatedDurationSeconds'] = seconds
    return value


LIBRARY_SETTINGS = {
    'type': 'object', 'additionalProperties': False, 'description': 'Library settings. Changing segmentation creates a new analysis key: previous embeddings are kept.',
    'properties': {
        'segmentSeconds': {'type': 'number', 'minimum': 1, 'maximum': 120, 'description': 'Window length in seconds for long files (a model may impose its own)'},
        'segmentOverlap': {'type': 'number', 'minimum': 0, 'maximum': 60, 'description': 'Overlap between consecutive windows, seconds'},
        'maxSegmentsPerFile': {'type': 'integer', 'minimum': 1, 'maximum': 5000},
        'computeLoudness': {'type': 'boolean', 'description': 'Integrated LUFS (ITU-R BS.1770) during the metadata pass'},
        'autoTagThreshold': {'type': 'number', 'minimum': 0, 'maximum': 1}, 'autoTagsPerFile': {'type': 'integer', 'minimum': 0, 'maximum': 30},
        'categoryThreshold': {'type': 'number', 'minimum': 0, 'maximum': 1}, 'categoriesPerFile': {'type': 'integer', 'minimum': 0, 'maximum': 10},
        'modelWeights': {'type': 'object', 'additionalProperties': {'type': 'number', 'minimum': 0, 'maximum': 10}, 'description': 'Rank-fusion weight per modelKey (default 1.0)'},
        'excludePenalty': {'type': 'number', 'minimum': 0, 'maximum': 3, 'description': 'Strength of the penalty for excluded sounds'},
        'autoSync': {'type': 'string', 'enum': ['auto', 'ask', 'off'], 'description': 'Standalone background synchronisation: auto = check the folders and update by itself (default); ask = check, then show an Update button; off'},
        'autoSyncIntervalSeconds': {'type': 'integer', 'minimum': 30, 'maximum': 86400, 'description': 'Seconds between two background checks'},
        'autoAnalyze': {'type': 'boolean', 'description': 'After an automatic scan, embed new/modified files with the enabled models'}}}
CATEGORY = {'type': 'object', 'required': ['id', 'name'], 'additionalProperties': False, 'properties': {
    'id': {'type': 'string', 'minLength': 1}, 'name': {'type': 'string', 'minLength': 1},
    'prompts': {'type': 'array', 'items': {'type': 'string'}, 'description': 'English descriptions used for zero-shot classification'},
    'children': {'type': 'array', 'items': {'$ref': '#/$defs/category'}}}}
# The Core resolves $ref from the root of an operation inputSchema: $defs is attached there (see update_library).
TAXONOMY = {'type': 'object', 'required': ['categories'], 'additionalProperties': False,
            'properties': {'categories': {'type': 'array', 'items': {'$ref': '#/$defs/category'}},
                           'tags': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Vocabulary of automatic tags'}}}

OPERATIONS = [
    operation('list_libraries', 'List Libraries', 'Libraries known to this Tool with their folders, cache location and enabled models.', {}),
    operation('create_library', 'Create Library', 'Create a virtual Library. Folders are referenced, never copied or modified. The cache can live on any drive.',
              {'name': {'type': 'string', 'minLength': 1, 'maxLength': 120},
               'cacheLocation': {'type': 'string', 'description': 'Absolute folder for all derived data (database, waveforms, embeddings). Empty = data/cache of the Tool.', 'x-cy-kind': 'Directory'},
               'folders': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Absolute audio folders to add immediately'},
               'enableDefaultModels': {'type': 'boolean', 'default': True, 'description': 'Enable the installed default embedding models'}}, ['name']),
    operation('update_library', 'Update Library', 'Rename a Library, change its settings, its enabled models or its taxonomy.',
              {'libraryId': LIBRARY, 'name': {'type': 'string', 'minLength': 1, 'maxLength': 120}, 'settings': LIBRARY_SETTINGS,
               'enabledModels': MODELS, 'taxonomy': TAXONOMY}, ['libraryId'], defs={'category': CATEGORY}),
    operation('delete_library', 'Delete Library', 'Forget a Library. Audio files are never touched; the cache is deleted only on request.',
              {'libraryId': LIBRARY, 'deleteCache': {'type': 'boolean', 'default': False}}, ['libraryId']),
    operation('add_folder', 'Add Folder', 'Reference one more audio folder (recursive). Run scan_library afterwards.',
              {'libraryId': LIBRARY, 'path': PATH('Audio folder.')}, ['libraryId', 'path']),
    operation('remove_folder', 'Remove Folder', 'Stop referencing a folder. Its assets become missing and keep their analysis until purge_missing.',
              {'libraryId': LIBRARY, 'rootId': {'type': 'string'}}, ['libraryId', 'rootId']),
    operation('set_folder_enabled', 'Enable or Disable Folder', 'A disabled folder is skipped by scans and hidden from browsing; nothing is deleted.',
              {'libraryId': LIBRARY, 'rootId': {'type': 'string'}, 'enabled': {'type': 'boolean'}}, ['libraryId', 'rootId', 'enabled']),
    operation('move_cache', 'Move Cache', 'Copy the whole cache of a Library to another location, verify it, then switch. The previous copy is kept.',
              {'libraryId': LIBRARY, 'cacheLocation': PATH('New cache root.')}, ['libraryId', 'cacheLocation'], progress=True, ram=256*MIB),
    operation('scan_library', 'Scan Library', 'Incremental recursive scan: new, unchanged, modified, moved, missing and duplicate files, then metadata, loudness and waveform cache for new/modified files only.',
              {'libraryId': LIBRARY, 'rootIds': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Rescan only these folders'},
               'analyzeCommon': {'type': 'boolean', 'default': True, 'description': 'Also compute metadata + waveform for pending files'},
               'retryFailed': {'type': 'boolean', 'default': False}, 'threads': {'type': 'integer', 'minimum': 1, 'maximum': 32}},
              ['libraryId'], progress=True, ram=1*GIB, seconds=60),
    operation('check_library', 'Check Library For Changes', 'Read-only and fast: compares the folders with the database (size and date only) and reports new, modified, missing and restored files, without writing anything. Call scan_library when changed is true.',
              {'libraryId': LIBRARY, 'rootIds': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Check only these folders'}}, ['libraryId'], ram=256*MIB),
    operation('analyze_library', 'Analyze Library', 'Compute the missing embeddings (whole clip + overlapping segments) for each selected model, then automatic categories and tags. Existing waveforms, metadata and other models\' embeddings are never recomputed.',
              {'libraryId': LIBRARY, 'models': MODELS, 'retryFailed': {'type': 'boolean', 'default': False}, 'device': DEVICE,
               'audioIds': {'type': 'array', 'items': AUDIO_ID, 'description': 'Restrict to these assets'},
               'autoLabel': {'type': 'boolean', 'default': True, 'description': 'Categorize and tag newly analyzed files'}},
              ['libraryId'], progress=True, ram=2*GIB, seconds=600),
    operation('control_analysis', 'Pause or Resume Analysis', 'Pause or resume the analysis queue of a Library (shared by the UI, CLI and MCP). Use cancel_job to cancel it.',
              {'libraryId': LIBRARY, 'action': {'type': 'string', 'enum': ['pause', 'resume']}}, ['libraryId', 'action']),
    operation('library_status', 'Library Status', 'Global figures: files, metadata %, waveforms %, one line per model, stores kept from previous versions, queue state.',
              {'libraryId': LIBRARY}, ['libraryId']),
    operation('browse_assets', 'Browse Assets', 'One page of assets with classic filters and sorting (virtualised: only the requested window is materialised).',
              {'libraryId': LIBRARY, 'filters': FILTERS,
               'sort': {'type': 'string', 'enum': ['name', 'duration', 'type', 'folder', 'size', 'modified', 'added', 'rating', 'played', 'sampleRate', 'channels'], 'default': 'name'},
               'descending': {'type': 'boolean', 'default': False}, 'offset': {'type': 'integer', 'minimum': 0, 'default': 0},
               'limit': {'type': 'integer', 'minimum': 1, 'maximum': 1000, 'default': 100}}, ['libraryId']),
    operation('get_asset', 'Asset Details', 'Metadata, levels, user and automatic tags/categories with the model that produced them, captions and per-model analysis states.',
              {'libraryId': LIBRARY, 'audioId': AUDIO_ID}, ['libraryId', 'audioId']),
    operation('get_waveform', 'Waveform Peaks', 'Min/max peaks of a time range from the cached pyramid (no decoding).',
              {'libraryId': LIBRARY, 'audioId': AUDIO_ID, 'start': {'type': 'number', 'minimum': 0, 'default': 0, 'description': 'Seconds'},
               'stop': {'type': 'number', 'minimum': 0, 'description': 'Seconds; absent = end of file'},
               'columns': {'type': 'integer', 'minimum': 16, 'maximum': 8192, 'default': 1024}}, ['libraryId', 'audioId']),
    operation('update_assets', 'Edit Assets', 'User data (tags, categories, rating, favourite, description, notes) of one asset, a selection '
              '(audioIds) or every asset a filter matches, for instance one folder: filters {"rootIds": [rootId], "folderPrefix": "Impacts/Metal"}. '
              'Only the Library database changes; audio files are never written here. Automatic tags and categories are stored apart and never '
              'overwritten by this operation, nor user data by a re-analysis.',
              {'libraryId': LIBRARY, 'audioIds': {'type': 'array', 'items': AUDIO_ID, 'minItems': 1, 'maxItems': 10000},
               'filters': {**FILTERS, 'description': 'Every asset these filters match is edited too (same filters as browse_assets). Must not be empty.'},
               'setTags': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Replace the user tags'},
               'addTags': {'type': 'array', 'items': {'type': 'string'}}, 'removeTags': {'type': 'array', 'items': {'type': 'string'}},
               'setCategories': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Replace the user categories (category ids)'},
               'addCategories': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Add user categories (category ids), keeping the others'},
               'removeCategories': {'type': 'array', 'items': {'type': 'string'}, 'description': 'Remove these user categories (category ids)'},
               'favorite': {'type': 'boolean'}, 'rating': {'type': 'integer', 'minimum': 0, 'maximum': 5},
               'description': {'type': 'string', 'maxLength': 4000}, 'notes': {'type': 'string', 'maxLength': 20000, 'description': 'Replace the notes'},
               'appendNotes': {'type': 'string', 'maxLength': 4000, 'description': 'Add this line after the existing notes of every target, never replacing them'}},
              ['libraryId'], progress=True),
    operation('list_folders', 'List Folders', 'Folder structure of a Library as its audio files describe it: every folder with its recursive '
              'and direct file counts, per root folder. Use a path from here as filters.folderPrefix (with rootIds) in browse_assets, '
              'update_assets, or to collect audioIds for analyze_library, suggest_names and write_metadata.',
              {'libraryId': LIBRARY, 'rootId': {'type': 'string', 'description': 'Only this root folder'},
               'folderPrefix': {'type': 'string', 'description': "Start below this folder, relative to the root, '/' separated"},
               'maxDepth': {'type': 'integer', 'minimum': 0, 'maximum': 64, 'default': 2, 'description': 'Levels below the start; 0 = all'}},
              ['libraryId']),
    operation('search_sounds', 'Search Sounds', 'Find sounds in the user\'s local audio Libraries from a free-text description in any language (or sounds similar to a known asset). Omit libraryId to search every Library at once. Each result gives the absolute path of the original file, duration, tags, categories, a 0-100 score per model and, for long recordings, the matching time segment: enough to propose sounds to the user. Each model retrieves from its own index; ranks are fused with weighted Reciprocal Rank Fusion. The job is asynchronous: poll cy_get_job and read outputs.results when Completed.',
              {'libraryId': {**LIBRARY, 'description': 'Optional. Absent = search all Libraries (results carry libraryId and libraryName). Required with similarTo.'}, 'text': {'type': 'string', 'maxLength': 1000, 'description': 'Free text in any language, e.g. "gros impact métallique très lourd avec une longue réverbération"', 'x-cy-kind': 'MultilineString'},
               'similarTo': {**AUDIO_ID, 'description': 'Find sounds similar to this asset (its stored embedding is the query)'},
               'selectionStart': {'type': 'number', 'minimum': 0, 'description': 'With similarTo: start of the time selection used as the audio query, seconds'},
               'selectionEnd': {'type': 'number', 'minimum': 0, 'description': 'With similarTo: end of the time selection, seconds'},
               'models': MODELS, 'filters': FILTERS, 'topK': {'type': 'integer', 'minimum': 1, 'maximum': 2000, 'default': 50},
               'llmAssist': {'type': 'string', 'enum': ['off', 'auto', 'always'], 'default': 'auto', 'description': 'Small local LLM for query understanding. auto = only for long, non-English, negated or sequential requests.'},
               'llmModel': {'type': 'string', 'default': '', 'description': 'modelKey of the LLM; empty = the model chosen in the '
                             'application settings, which is what the interface uses too'},
               'weights': {'type': 'object', 'additionalProperties': {'type': 'number', 'minimum': 0, 'maximum': 10}, 'description': 'Rank-fusion weight per modelKey for this search'},
               'rrfK': {'type': 'integer', 'minimum': 1, 'maximum': 1000, 'default': 60, 'description': 'K of Reciprocal Rank Fusion'}, 'device': DEVICE},
              [], progress=True, ram=1*GIB,
              outputs=[{'id': 'results', 'name': 'Search results', 'type': 'File', 'mimeType': 'application/json',
                        'description': 'outputs/search-results.json: same content as the job outputs, paths are absolute paths of the original audio files'}]),
    operation('understand_query', 'Understand Query', 'Turn a free-form request into the stable structured query (events, properties, environment, exclude, temporal, queries) without searching.',
              {'text': {'type': 'string', 'minLength': 1, 'maxLength': 1000}, 'llmAssist': {'type': 'string', 'enum': ['off', 'auto', 'always'], 'default': 'always'},
               'llmModel': {'type': 'string', 'default': ''}, 'device': DEVICE}, ['text'], ram=1*GIB),
    operation('categorize_library', 'Categorize Library', 'Recompute automatic categories and tags from stored embeddings with the current taxonomy. No audio decoding; user tags untouched.',
              {'libraryId': LIBRARY, 'models': MODELS, 'device': DEVICE}, ['libraryId'], progress=True, ram=1*GIB),
    operation('find_duplicates', 'Find Duplicates', 'Group exact duplicates (size + hash, confirmed by SHA-256) or probable duplicates (embedding similarity + duration). Reports and groups only: nothing is deleted.',
              {'libraryId': LIBRARY, 'mode': {'type': 'string', 'enum': ['exact', 'probable'], 'default': 'exact'}, 'model': MODEL_KEY,
               'threshold': {'type': 'number', 'minimum': 0.8, 'maximum': 1.0, 'default': 0.985, 'description': 'Cosine similarity for probable duplicates'}},
              ['libraryId'], progress=True, ram=2*GIB),
    operation('purge_missing', 'Purge Missing Assets', 'Delete the database rows and analysis of assets whose file is missing. Explicit; original files are not concerned.',
              {'libraryId': LIBRARY, 'confirm': {'type': 'boolean', 'const': True}}, ['libraryId', 'confirm']),
    operation('suggest_names', 'Suggest File Names', 'Read-only. Proposes descriptive names (category + tags) for badly named files such as sound_01.wav or ZOOM0012.wav. Returns a plan; nothing is renamed.',
              {'libraryId': LIBRARY, 'audioIds': {'type': 'array', 'items': AUDIO_ID, 'maxItems': 10000, 'description': 'Absent = whole Library'},
               'onlyBadlyNamed': {'type': 'boolean', 'default': True, 'description': 'false = propose a name for every listed file'},
               'template': {'type': 'string', 'default': '{category}_{tags}', 'maxLength': 120, 'description': 'Fields: {category} {tags} {original} {duration}'},
               'maxTags': {'type': 'integer', 'minimum': 0, 'maximum': 8, 'default': 3}, 'limit': {'type': 'integer', 'minimum': 1, 'maximum': 5000, 'default': 500}}, ['libraryId'], ram=256*MIB),
    operation('rename_files', 'Rename Files', 'CHANGES ORIGINAL FILES. Renames files on disk inside their folder (never overwrites, extension kept). AudioId, tags, waveform and embeddings follow the file. Journalled: undo_rename reverses the last batch.',
              {'libraryId': LIBRARY, 'renames': {'type': 'array', 'minItems': 1, 'maxItems': 5000, 'items': {'type': 'object', 'required': ['audioId', 'newName'], 'additionalProperties': False,
                   'properties': {'audioId': AUDIO_ID, 'newName': {'type': 'string', 'minLength': 1, 'maxLength': 200, 'description': 'File name with the same extension, no folder'}}}},
               'confirm': {'type': 'boolean', 'const': True, 'description': 'Must be true. This operation changes the user\'s original files: an AI client must show the plan to the user and obtain an explicit yes first.'}}, ['libraryId', 'renames', 'confirm']),
    operation('undo_rename', 'Undo Last Rename', 'CHANGES ORIGINAL FILES. Restores the names of the most recent rename batch that was not undone yet.',
              {'libraryId': LIBRARY, 'confirm': {'type': 'boolean', 'const': True, 'description': 'Must be true. This operation changes the user\'s original files: an AI client must show the plan to the user and obtain an explicit yes first.'}}, ['libraryId', 'confirm']),
    operation('write_metadata', 'Write Metadata Into Files', 'CHANGES ORIGINAL FILES. Writes description, tags, categories, rating and AudioId into the files themselves (ID3 for WAV/AIFF/MP3, Vorbis comments for FLAC/OGG/Opus, MP4 atoms for M4A). Tags are written into a copy, the decoded audio is verified identical, then the copy replaces the original; a backup goes to the Library cache by default. Embeddings stay valid.',
              {'libraryId': LIBRARY, 'audioIds': {'type': 'array', 'items': AUDIO_ID, 'minItems': 1, 'maxItems': 5000},
               'fields': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'enum': ['description', 'tags', 'categories', 'rating', 'audioId']}, 'description': 'Absent = all'},
               'includeAutoTags': {'type': 'boolean', 'default': True, 'description': 'false = user tags only'},
               'backup': {'type': 'boolean', 'default': True, 'description': 'Keep the untouched original in <cache>/Common/FileOperations/Backups'},
               'confirm': {'type': 'boolean', 'const': True, 'description': 'Must be true. This operation changes the user\'s original files: an AI client must show the plan to the user and obtain an explicit yes first.'}}, ['libraryId', 'audioIds', 'confirm'], progress=True, ram=512*MIB),
    operation('list_models', 'List Models', 'Model registry: embedding models, LLMs and declared extension points, with version, revision, hash, capabilities, licence, size and installation state.', {}),
    operation('install_model', 'Install Model', 'Download (with resume), verify and register a catalogue model. Licences that require it must be accepted personally with acceptLicense=true. Credentials are never parameters.',
              {'modelKey': MODEL_KEY, 'acceptLicense': {'type': 'boolean', 'default': False, 'description': 'Your own acceptance of the model licence shown by list_models'},
               'repair': {'type': 'boolean', 'default': False, 'description': 'Re-hash every file and download corrupted ones again'}},
              ['modelKey'], progress=True, ram=512*MIB, seconds=600),
    operation('verify_model', 'Verify Model', 'Re-hash the installed files of a model against its receipt.', {'modelKey': MODEL_KEY}, ['modelKey'], progress=True, ram=256*MIB),
    operation('remove_model', 'Remove Model', 'Uninstall the weights of a catalogue model, or unregister a custom model (its files are never deleted). Analysis data of each Library is kept unless deleteAnalysis is true.',
              {'modelKey': MODEL_KEY, 'deleteAnalysis': {'type': 'boolean', 'default': False, 'description': 'Also delete the embeddings/indexes of this model in every Library'}}, ['modelKey']),
    operation('register_model', 'Register Custom Model', 'Register a local model, a fine-tuned variant or another version, in place. Several versions of one modelId coexist; each keeps its own embeddings.',
              {'modelId': {'type': 'string', 'pattern': '^[A-Za-z][A-Za-z0-9_.-]{0,63}$'}, 'version': {'type': 'string', 'pattern': '^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$'},
               'displayName': {'type': 'string', 'minLength': 1}, 'modelType': {'type': 'string', 'enum': ['AudioTextEmbedding', 'AudioEmbedding', 'LLM', 'AudioUnderstanding']},
               'adapter': {'type': 'string', 'description': 'm2d_clap | hf_clap | omni_embed | hf_causal_lm | file:<absolute adapter.py>'},
               'localPath': {'type': 'string', 'description': 'Absolute folder or weight file; referenced in place, never copied'},
               'capabilities': {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'enum': ['AudioEmbedding', 'TextEmbedding', 'ZeroShotTagging', 'Tagging', 'Classification', 'Captioning', 'Reranking', 'QuestionAnswering', 'QueryUnderstanding', 'QueryExpansion', 'Translation', 'StructuredOutput']}},
               'embeddingDimension': {'type': 'integer', 'minimum': 1, 'maximum': 16384}, 'requiredSampleRate': {'type': 'integer', 'minimum': 8000, 'maximum': 192000},
               'maximumAudioDuration': {'type': 'number', 'minimum': 0.1}, 'preferredChunkDuration': {'type': 'number', 'minimum': 0.5, 'maximum': 600},
               'revision': {'type': 'string'}, 'family': {'type': 'string'}, 'provider': {'type': 'string'}, 'repository': {'type': 'string'},
               'licenseName': {'type': 'string'}, 'licenseUrl': {'type': 'string'}, 'engine': {'type': 'string', 'enum': ['torch', 'base'], 'default': 'torch'},
               'similarityRange': {'type': 'array', 'items': {'type': 'number'}, 'minItems': 2, 'maxItems': 2, 'description': 'Cosine range mapped to 0..100 % for display'},
               'promptProfile': {'type': 'string', 'enum': ['generic', 'caption'], 'default': 'generic',
                                 'description': 'Which prompt this model was trained for. "generic" is the built-in instruction with its '
                                                'few-shot examples; "caption" is the clap_prompt/variations/suggested_* schema. A model is '
                                                'never recognised by its name, it declares its profile here.'}},
              ['modelId', 'version', 'displayName', 'modelType', 'adapter', 'localPath', 'capabilities'], ram=256*MIB),
    operation('remove_model_data', 'Remove Analysis Data', 'Delete one embedding store (analysis key) of a Library, e.g. the data of a previous model version. Other models and versions are untouched.',
              {'libraryId': LIBRARY, 'analysisKey': {'type': 'string', 'pattern': '^[0-9a-f]{16}$'}}, ['libraryId', 'analysisKey']),
    operation('engine_status', 'Engine Status', 'State of the private AI engine environment, its pinned sources and the models currently loaded in the worker.', {}),
    operation('install_engine', 'Install AI Engine', 'Create the private PyTorch environment at its final path and fetch the pinned engine sources. Long: several GB.',
              {'cpuOnly': {'type': 'boolean', 'default': False}}, [], progress=True, ram=1*GIB, seconds=1200),
    operation('release_models', 'Release Models', 'Unload every model and stop the engine worker now (frees RAM/VRAM). Refused while an analysis or search is running.', {}),
]


def main():
    catalog = json.loads((APP/'models'/'catalog.json').read_text('utf-8'))
    models = []
    for entry in catalog:
        license_info = entry.get('license', {})
        resources = dict(entry.get('resources', {}))
        if 'vramBytes' in resources: resources['vramBytes'] = {'auto': resources['vramBytes']}
        entry = {**entry, 'resources': resources}
        models.append({'id': (entry['modelId']+'-'+entry['version']).replace('@', '-'), 'name': entry['displayName'], 'version': entry['version'],
                       'source': entry.get('repository', ''), 'license': license_info.get('name', 'Not declared'), 'licenseUrl': license_info.get('url', ''),
                       'location': 'Local', 'runsLocally': True, 'capabilities': entry['capabilities'],
                       'computeBackends': ['CUDA', 'CPU'], 'resourceRequirements': entry.get('resources', {})})
    windows = {'os': 'Windows', 'architecture': 'x64', 'status': 'Experimental', 'computeBackends': ['CPU', 'CUDA'], 'tested': [],
               'notes': 'Filled from data/reports after real runs; see app/Docs/AudioLibrary-Validation.md'}
    tested = APP/'platform-tested.json'
    if tested.is_file():
        windows.update(json.loads(tested.read_text('utf-8')))
    manifest = {
        'schemaVersion': 1, 'protocolVersion': '1.0', 'id': 'cy.tool.audiolibrary', 'name': 'CyTools_AudioLibrary', 'version': VERSION,
        'description': 'Management, analysis, categorization and intelligent search in large local audio libraries, with several embedding models and small local LLMs.',
        'vendor': 'Cyberalien', 'author': 'Cyberalien', 'license': 'GPL-3.0-only (Tool code, see LICENSE). Engines and model weights '
        'keep their own licences: see app/licenses.json.', 'executable': 'runtime/python/Scripts/python.exe app/tool.py',
        'categories': ['audio', 'search', 'library'], 'tags': ['audio', 'sfx', 'embeddings', 'clap', 'semantic-search', 'waveform'],
        'capabilities': ['jobs', 'cancellation', 'progress', 'models', 'downloads'],
        'backends': [{'id': 'torch-engine', 'name': 'Private PyTorch engine (model worker)', 'version': '2.8.0',
                      'source': 'https://pytorch.org', 'license': 'BSD-3-Clause', 'shareableModelInstance': True, 'threadSafe': False,
                      'concurrentInference': False, 'models': models}],
        'platforms': [windows,
                      {'os': 'Linux', 'architecture': 'x64', 'status': 'Unknown', 'computeBackends': ['CPU', 'CUDA'], 'notes': 'Launcher and install script provided, never executed.'},
                      {'os': 'macOS', 'architecture': 'ARM64', 'status': 'Unknown', 'computeBackends': ['CPU'], 'notes': 'Not tested.'}],
        'interfaces': ['Native', 'CLI', 'JSONL', 'HTTP', 'MCP', 'ImGui'],
        'runtimeRequirements': [{'id': 'python', 'version': '>=3.11', 'required': False, 'source': 'https://www.python.org/downloads/',
                                 'notes': 'Private environments in runtime/ are created from a system Python on the tested machine'},
                                {'id': 'git', 'required': False, 'source': 'https://git-scm.com/downloads', 'notes': 'Only to fetch the pinned engine sources'}],
        'concurrency': {'policy': 'Concurrent', 'maxWorkers': 8},
        'operations': OPERATIONS, 'standaloneExecutable': 'CyTools_AudioLibrary.exe',
        'distributionStatus': 'Standalone installation validated on the development machine only; see app/Docs/AudioLibrary-Validation.md'}
    (APP/'CyTool.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print(len(OPERATIONS), 'operations written')


if __name__ == '__main__':
    main()
