"""Scale check with synthetic files: scan, metadata + waveform, embeddings through the real worker protocol
(deterministic test adapter, no PyTorch), then browse and vector-search timings. Proves the data path at size;
it says nothing about model quality or GPU throughput.

    runtime/python/Scripts/python.exe app/scripts/scale_test.py --files 20000
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

parser = argparse.ArgumentParser(); parser.add_argument('--files', type=int, default=20000); parser.add_argument('--keep', action='store_true')
args = parser.parse_args()
TEMP = Path(tempfile.mkdtemp(prefix='cy-audiolib-scale-'))
os.environ['CYTOOLS_AUDIOLIBRARY_DATA'] = str(TEMP/'data'); os.environ['CYTOOLS_SETTINGS_DIR'] = str(TEMP/'shared')
APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP)); sys.path.insert(0, str(APP/'tests'))
import numpy as np
import soundfile
import fixtures
from audiolib import registry
from audiolib.database import fetch_rows, list_ids, open_database
from audiolib.library import get_library
from tool import create_runtime

REPORT = APP.parent/'data'/'reports'/'scale-test.json'


def main():
    report = {'files': args.files, 'date': time.strftime('%Y-%m-%d %H:%M:%S')}
    began = time.monotonic(); rng = np.random.default_rng(0); audio = TEMP/'audio'
    for index in range(args.files):
        folder = audio/f'pack_{index//500:03d}'; folder.mkdir(parents=True, exist_ok=True)
        kind = index % 3
        wave = fixtures.tone(80+rng.integers(0, 6000), 0.25, 22050) if kind else fixtures.noise(0.25, 22050, seed=index)
        soundfile.write(str(folder/f'sound_{index:06d}.wav'), wave, 22050, subtype='PCM_16')
    report['generateSeconds'] = round(time.monotonic()-began, 1)
    runtime = create_runtime(TEMP/'jobs'); runtime.start()
    try:
        actor = runtime.authenticate(runtime.create_client('scale')['token']); session = runtime.create_session(actor, temporary=False)['sessionId']
        def run(operation, parameters):
            start = time.monotonic(); job = runtime.wait(actor, runtime.submit(actor, session, operation, parameters)['jobId'], timeout=36000)
            assert job['state'] == 'Completed', job.get('error'); return job['outputs'], round(time.monotonic()-start, 2)
        models = fixtures.register_test_models(TEMP/'models', registry)[:2]
        library, _ = run('create_library', {'name': 'Scale', 'folders': [str(audio)], 'cacheLocation': str(TEMP/'cache')})
        identifier = library['libraryId']
        scan, seconds = run('scan_library', {'libraryId': identifier}); report['scan'] = {'seconds': seconds, 'new': scan['new'], 'failed': scan['common']['failed']}
        rescan, seconds = run('scan_library', {'libraryId': identifier}); report['rescan'] = {'seconds': seconds, 'unchanged': rescan['unchanged'], 'new': rescan['new']}
        run('update_library', {'libraryId': identifier, 'enabledModels': models})
        analysis, seconds = run('analyze_library', {'libraryId': identifier, 'device': 'cpu', 'autoLabel': False})
        report['analyze'] = {'seconds': seconds, 'analyzed': analysis['analyzed'], 'failed': analysis['failed'], 'models': len(models)}
        database = open_database(get_library(identifier))
        start = time.monotonic(); ids = list_ids(database, {}, 'name'); report['listIdsSeconds'] = round(time.monotonic()-start, 3)
        start = time.monotonic(); fetch_rows(database, ids[len(ids)//2:len(ids)//2+256]); report['fetch256RowsSeconds'] = round(time.monotonic()-start, 3)
        start = time.monotonic(); filtered = list_ids(database, {'text': 'sound_0199', 'maxDuration': 1.0}, 'duration', True); report['filteredListSeconds'] = round(time.monotonic()-start, 3); report['filteredCount'] = len(filtered)
        first, seconds = run('search_sounds', {'libraryId': identifier, 'text': 'low tone', 'llmAssist': 'off', 'topK': 50}); report['firstSearchSeconds'] = seconds
        timings = []
        for text in ('noise', 'high tone', 'click', 'mid tone', 'low tone'):
            _, seconds = run('search_sounds', {'libraryId': identifier, 'text': text, 'llmAssist': 'off', 'topK': 50}); timings.append(seconds)
        report['warmSearchSeconds'] = {'min': min(timings), 'max': max(timings)}; report['rowsSearched'] = [m['searched'] for m in first['models']]
        similar, seconds = run('search_sounds', {'libraryId': identifier, 'similarTo': ids[0], 'topK': 50}); report['similarSearchSeconds'] = seconds
        cache = Path(library['cache']); report['cacheBytes'] = sum(p.stat().st_size for p in cache.rglob('*') if p.is_file())
        report['audioFolderUntouched'] = not any(p.suffix != '.wav' for p in audio.rglob('*') if p.is_file())
    finally:
        runtime.close()
    REPORT.parent.mkdir(parents=True, exist_ok=True); REPORT.write_text(json.dumps(report, indent=1), 'utf-8'); print(json.dumps(report, indent=1))
    if not args.keep: shutil.rmtree(TEMP, ignore_errors=True)


if __name__ == '__main__':
    main()
