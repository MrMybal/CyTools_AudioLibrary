"""Real-model validation on real audio, through the same runtime as the UI, the CLI and MCP.

    runtime/python/Scripts/python.exe app/scripts/validate_real.py --models m2d-clap@2025 [--llm qwen3-1.7b@2025-04] --report NAME

Folders are referenced read-only. The five Clotho clips shipped with the pinned
Omni-Embed-Audio source have human captions: they give a small ground truth (caption ->
expected file). Everything else is reported as observed, not as a benchmark.
"""
import argparse
import json
import sys
import time
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from config import DATA, ENGINE_SOURCES, REPORTS
from tool import create_runtime

QUERIES = ['dog barking', 'water flowing in a stream', 'a short notification chime', 'heavy metal impact with long reverb',
           'gros impact métallique très lourd avec une longue réverbération', 'ambiance de forêt avec vent mais sans oiseaux',
           'moteur diesel qui démarre difficilement']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', nargs='+', required=True); parser.add_argument('--llm', default='')
    parser.add_argument('--folders', nargs='*', default=[]); parser.add_argument('--report', default='real-validation')
    parser.add_argument('--library', default='Real validation'); parser.add_argument('--device', default='auto')
    args = parser.parse_args()
    clotho = ENGINE_SOURCES/'Omni-Embed-Audio'/'examples'/'data'/'clotho_samples'
    folders = [str(clotho)]+args.folders
    report = {'date': time.strftime('%Y-%m-%d %H:%M:%S'), 'models': args.models, 'llm': args.llm, 'folders': folders, 'steps': {}}
    with create_runtime(DATA/'jobs-validation') as runtime:
        actor = runtime.authenticate(runtime.create_client('validation')['token'])
        session = runtime.create_session(actor, temporary=False)['sessionId']
        def run(operation, parameters, timeout=7200):
            began = time.monotonic()
            job = runtime.wait(actor, runtime.submit(actor, session, operation, parameters)['jobId'], timeout=timeout)
            if job['state'] != 'Completed': raise SystemExit(f"{operation} -> {job['state']}: {json.dumps(job.get('error'))}")
            return job['outputs'], round(time.monotonic()-began, 2)
        existing = [l for l in run('list_libraries', {})[0]['libraries'] if l['name'] == args.library]
        library = existing[0] if existing else run('create_library', {'name': args.library, 'folders': folders, 'enableDefaultModels': False})[0]
        identifier = library['libraryId']
        for folder in folders:
            if folder not in [r['path'] for r in library['rootFolders']]: run('add_folder', {'libraryId': identifier, 'path': folder})
        scan, seconds = run('scan_library', {'libraryId': identifier})
        report['steps']['scan'] = {'seconds': seconds, **{k: v for k, v in scan.items() if k != 'common'}, 'common': scan.get('common')}
        run('update_library', {'libraryId': identifier, 'enabledModels': args.models})
        analysis, seconds = run('analyze_library', {'libraryId': identifier, 'device': args.device, 'retryFailed': True})
        if not analysis['status']['models'] or any(m['ready'] == 0 for m in analysis['status']['models']): raise SystemExit('Analysis produced no embeddings: '+json.dumps(analysis['models']))
        report['steps']['analyze'] = {'seconds': seconds, 'models': analysis['models'], 'failed': analysis['failed']}
        report['status'] = {k: analysis['status'][k] for k in ('files', 'metadata', 'waveforms', 'models')}
        report['engine'] = run('engine_status', {})[0]['workers']
        truth = [json.loads(line) for line in (clotho/'captions.jsonl').read_text('utf-8').splitlines() if line.strip()]
        hits, details = 0, []
        for entry in truth:
            result, seconds = run('search_sounds', {'libraryId': identifier, 'text': entry['captions'][0], 'llmAssist': 'off', 'topK': 5})
            names = [r['filename'] for r in result['results']]
            rank = names.index(entry['file'])+1 if entry['file'] in names else None
            hits += rank == 1
            details.append({'caption': entry['captions'][0], 'expected': entry['file'], 'rank': rank, 'seconds': seconds, 'top3': names[:3]})
        report['captionRetrieval'] = {'top1': hits, 'of': len(truth), 'details': details}
        report['queries'] = []
        for text in QUERIES:
            mode = 'auto' if args.llm else 'off'
            result, seconds = run('search_sounds', {'libraryId': identifier, 'text': text, 'llmAssist': mode, 'llmModel': args.llm, 'topK': 5})
            report['queries'].append({'text': text, 'seconds': seconds, 'llm': result['query']['llm'], 'structured': result['query']['structured'],
                                      'results': [{'file': r['filename'], 'final': r['finalScore'], 'models': {k: v['score'] for k, v in r['models'].items()},
                                                   'segment': r.get('matchedSegment'), 'concepts': r.get('matchedConcepts')} for r in result['results']]})
        first = run('browse_assets', {'libraryId': identifier, 'limit': 1, 'filters': {'text': 'water'}})[0]['assets']
        if first:
            similar, seconds = run('search_sounds', {'libraryId': identifier, 'similarTo': first[0]['audio_id'], 'topK': 4})
            report['similar'] = {'reference': first[0]['filename'], 'seconds': seconds, 'results': [r['filename'] for r in similar['results']]}
            details_asset = run('get_asset', {'libraryId': identifier, 'audioId': first[0]['audio_id']})[0]
            report['assetExample'] = {k: details_asset[k] for k in ('filename', 'duration', 'sample_rate', 'channels', 'bit_depth', 'codec', 'peak_db', 'rms_db', 'lufs',
                                                                    'categories', 'autoTags', 'states')}
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS/(args.report+'.json')).write_text(json.dumps(report, indent=1, ensure_ascii=False), 'utf-8')
    print(json.dumps({'scan': report['steps']['scan']['seconds'], 'analyze': report['steps']['analyze'], 'captionTop1': report['captionRetrieval']['top1'],
                      'of': report['captionRetrieval']['of']}, indent=1))
    for query in report['queries']:
        print(f"\n{query['text']}  ({query['seconds']} s, llm={query['llm'].get('used')})")
        for item in query['results'][:4]: print(f"   {item['final']:5.1f}%  {item['file']}  {item['models']}")


if __name__ == '__main__':
    main()
