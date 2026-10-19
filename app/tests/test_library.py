"""End-to-end tests through the real CyToolsCore runtime, with synthetic audio and the
deterministic test adapter (real worker process and protocol, no PyTorch, no weights).

    runtime/python/Scripts/python.exe -m unittest discover -s app/tests -v
"""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

TEMP = Path(tempfile.mkdtemp(prefix='cy-audiolib-test-'))
os.environ['CYTOOLS_AUDIOLIBRARY_DATA'] = str(TEMP/'data')
os.environ['CYTOOLS_SETTINGS_DIR'] = str(TEMP/'shared-settings')
APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP)); sys.path.insert(0, str(APP/'tests'))

import fixtures
from audiolib import registry
from cytools_core import CyToolError
from tool import create_runtime


def listing(folder):
    return sorted((str(p.relative_to(folder)), p.stat().st_size, p.stat().st_mtime_ns) for p in Path(folder).rglob('*') if p.is_file())


class LibraryFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audio = TEMP/'Audio Library é'; cls.second = TEMP/'Second'; cls.cache = TEMP/'External Cache'
        fixtures.build_library(cls.audio); cls.second.mkdir()
        import soundfile
        soundfile.write(str(cls.second/'second_folder_tone.wav'), fixtures.tone(200, 1.0), 22050)
        cls.runtime = create_runtime(TEMP/'jobs'); cls.runtime.start()
        cls.actor = cls.runtime.authenticate(cls.runtime.create_client('tests')['token'])
        cls.session = cls.runtime.create_session(cls.actor, temporary=False)['sessionId']
        cls.models = fixtures.register_test_models(TEMP/'custom-models', registry)
        cls.state = {}

    @classmethod
    def tearDownClass(cls):
        cls.runtime.close()
        shutil.rmtree(TEMP, ignore_errors=True)

    def run_job(self, operation, parameters, expect='Completed', timeout=300):
        job = self.runtime.submit(self.actor, self.session, operation, parameters)
        job = self.runtime.wait(self.actor, job['jobId'], timeout=timeout)
        self.assertEqual(job['state'], expect, job.get('error'))
        return job['outputs'] if expect == 'Completed' else job['error']

    def test_01_create_scan_and_keep_sources_clean(self):
        before = listing(self.audio)
        library = self.run_job('create_library', {'name': 'Test SFX', 'cacheLocation': str(self.cache), 'folders': [str(self.audio), str(self.second)]})
        self.state['library'] = library['libraryId']
        self.assertEqual(len(library['rootFolders']), 2)
        summary = self.run_job('scan_library', {'libraryId': library['libraryId']})
        self.assertEqual(summary['new'], 12); self.assertEqual(summary['unreadable'], 0)
        self.assertEqual(summary['common']['failed'], 0, summary)
        self.assertEqual(summary['duplicateGroups'], 1)
        self.assertEqual(before, listing(self.audio), 'the Tool wrote into an audio folder')
        self.assertTrue((self.cache/('Library_'+library['libraryId'])/'Common'/'Database'/'library.sqlite').is_file())
        status = self.run_job('library_status', {'libraryId': library['libraryId']})
        self.assertEqual(status['files'], 12); self.assertEqual(status['metadata']['percent'], 100.0); self.assertEqual(status['waveforms']['percent'], 100.0)

    def test_02_metadata_per_format(self):
        page = self.run_job('browse_assets', {'libraryId': self.state['library'], 'limit': 100})
        by_name = {a['filename']: a for a in page['assets']}
        self.assertEqual(by_name['low_tone_90_24bit.wav']['bit_depth'], 24); self.assertEqual(by_name['low_tone_110.wav']['bit_depth'], 16)
        self.assertEqual(by_name['high_tone_5000_stereo.wav']['channels'], 2); self.assertEqual(by_name['high_tone_4000.flac']['sample_rate'], 48000)
        for name in ('mid_tone_1000.mp3', 'mid_tone_800.m4a', 'white noise burst.ogg', 'clicks.aiff'):
            self.assertAlmostEqual(by_name[name]['duration'], {'mid_tone_1000.mp3': 1.5, 'mid_tone_800.m4a': 1.5, 'white noise burst.ogg': 1.0, 'clicks.aiff': 2.0}[name], delta=0.08, msg=name)
            self.assertEqual(by_name[name]['metadata_state'], 'Ready')
        self.assertAlmostEqual(by_name['low_tone_110.wav']['peak_db'], -6.02, delta=0.1)
        self.assertAlmostEqual(by_name['low_tone_110.wav']['rms_db'], -9.03, delta=0.1)
        self.assertIsNotNone(by_name['low_tone_90_24bit.wav']['lufs'])
        self.assertIsNotNone(by_name['noise_copy_a.wav']['duplicate_group'])
        self.state['assets'] = by_name
        filtered = self.run_job('browse_assets', {'libraryId': self.state['library'], 'filters': {'extensions': ['wav'], 'maxDuration': 1.6, 'channels': 1}})
        self.assertTrue(all(a['extension'] == '.wav' and a['duration'] <= 1.6 for a in filtered['assets'])); self.assertGreaterEqual(filtered['total'], 3)

    def test_03_waveform_pyramid(self):
        long = self.state['assets']['long_recording_with_noise_at_14s.wav']
        whole = self.run_job('get_waveform', {'libraryId': self.state['library'], 'audioId': long['audio_id'], 'columns': 64})
        self.assertGreaterEqual(len(whole['levels']), 2); self.assertEqual(len(whole['max']), 64)
        self.assertGreater(max(whole['max'][28:36]), max(whole['max'][:20])+0.1, 'the noise burst is not visible in the coarse level')
        zoom = self.run_job('get_waveform', {'libraryId': self.state['library'], 'audioId': long['audio_id'], 'start': 14.0, 'stop': 14.5, 'columns': 2000})
        self.assertGreater(len(zoom['max']), 50)

    def test_04_incremental_rescan(self):
        library = self.state['library']
        again = self.run_job('scan_library', {'libraryId': library})
        self.assertEqual((again['unchanged'], again['new'], again['modified'], again['missing']), (12, 0, 0, 0))
        moved_id = self.state['assets']['clicks.aiff']['audio_id']
        (self.audio/'Moved').mkdir(); os.replace(self.audio/'Noise éàü'/'clicks.aiff', self.audio/'Moved'/'renamed clicks.aiff')
        import soundfile
        soundfile.write(str(self.audio/'Tones'/'Low'/'low_tone_110.wav'), fixtures.tone(120, 1.0), fixtures.RATE)       # modified content
        (self.audio/'Tones'/'mid_tone_1000.mp3').unlink()                                                               # missing
        soundfile.write(str(self.audio/'Tones'/'new_high_tone_6000.wav'), fixtures.tone(6000, 1.0), fixtures.RATE)     # new
        result = self.run_job('scan_library', {'libraryId': library})
        self.assertEqual((result['moved'], result['modified'], result['missing'], result['new']), (1, 1, 1, 1), result)
        self.assertEqual(result['common']['processed'], 2)      # only the new and the modified file were analysed again
        moved = self.run_job('get_asset', {'libraryId': library, 'audioId': moved_id})
        self.assertEqual(moved['filename'], 'renamed clicks.aiff'); self.assertEqual(moved['status'], 'present')

    def test_05_multi_model_analysis(self):
        library = self.state['library']
        self.run_job('update_library', {'libraryId': library, 'enabledModels': self.models[:2], 'settings': {'segmentSeconds': 4.0, 'segmentOverlap': 1.0}})
        result = self.run_job('analyze_library', {'libraryId': library, 'device': 'cpu'})
        self.assertEqual(result['failed'], 0, result); self.assertEqual(len(result['models']), 2)
        status = result['status']
        self.assertTrue(all(m['percent'] == 100.0 for m in status['models']), status['models'])
        self.assertEqual(sorted(s['dimension'] for s in status['stores']), [24, 40])     # independent stores, never merged
        self.assertEqual(len({s['directory'] for s in status['stores']}), 2)
        again = self.run_job('analyze_library', {'libraryId': library, 'device': 'cpu'})
        self.assertEqual(again['analyzed'], 0, 'existing embeddings were recomputed')

    def test_06_text_search_fusion_and_segments(self):
        library = self.state['library']
        result = self.run_job('search_sounds', {'libraryId': library, 'text': 'low tone', 'llmAssist': 'off', 'topK': 5})
        self.assertEqual(result['fusion']['method'], 'ReciprocalRankFusion'); self.assertEqual(len(result['fusion']['weights']), 2)
        top = [r['filename'] for r in result['results'][:3]]
        self.assertTrue(any('low_tone' in name for name in top), top)
        self.assertEqual(set(result['results'][0]['models']), set(self.models[:2]))
        self.assertTrue(Path(result['file']).is_file())
        noise = self.run_job('search_sounds', {'libraryId': library, 'text': 'noise', 'llmAssist': 'off', 'topK': 8})
        long = next(r for r in noise['results'] if r['filename'].startswith('long_recording'))
        self.assertIn('matchedSegment', long); self.assertTrue(11.0 <= long['matchedSegment']['start'] <= 17.0, long['matchedSegment'])
        only_flac = self.run_job('search_sounds', {'libraryId': library, 'text': 'high tone', 'llmAssist': 'off', 'filters': {'extensions': ['flac']}})
        self.assertEqual([r['filename'] for r in only_flac['results']], ['high_tone_4000.flac'])
        single = self.run_job('search_sounds', {'libraryId': library, 'text': 'click', 'llmAssist': 'off', 'models': [self.models[1]], 'weights': {self.models[1]: 2.0}})
        self.assertEqual(list(single['fusion']['weights'].items()), [(self.models[1], 2.0)])
        self.assertEqual(single['results'][0]['filename'], 'renamed clicks.aiff')

    def test_07_similar_and_selection(self):
        library = self.state['library']
        page = self.run_job('browse_assets', {'libraryId': library, 'limit': 100}); names = {a['filename']: a['audio_id'] for a in page['assets']}
        similar = self.run_job('search_sounds', {'libraryId': library, 'similarTo': names['high_tone_4000.flac'], 'topK': 3})
        self.assertNotIn('high_tone_4000.flac', [r['filename'] for r in similar['results']])
        self.assertIn('high_tone', similar['results'][0]['filename'])
        selection = self.run_job('search_sounds', {'libraryId': library, 'similarTo': names['long_recording_with_noise_at_14s.wav'], 'selectionStart': 14.5, 'selectionEnd': 17.5, 'topK': 4})
        self.assertEqual(selection['mode'], 'selection')
        self.assertTrue(any('noise' in r['filename'] for r in selection['results'][:3]), [r['filename'] for r in selection['results']])

    def test_08_llm_assist_and_fallback(self):
        library = self.state['library']
        understood = self.run_job('understand_query', {'text': 'un son grave sans bruit', 'llmAssist': 'always', 'llmModel': self.models[2]})
        self.assertTrue(understood['llm']['used']); self.assertEqual(understood['structured']['exclude'], ['noise'])
        result = self.run_job('search_sounds', {'libraryId': library, 'text': 'un son grave sans bruit', 'llmAssist': 'always', 'llmModel': self.models[2], 'topK': 3})
        low = ('low_tone', 'second_folder_tone', 'long_recording')      # every fixture dominated by a tone below 300 Hz
        self.assertTrue(all(any(k in r['filename'] for k in low) for r in result['results']), [r['filename'] for r in result['results']])
        parsed = self.run_job('understand_query', {'text': 'forest wind without birds', 'llmAssist': 'off'})
        self.assertEqual(parsed['structured']['exclude'], ['birds']); self.assertFalse(parsed['llm']['used'])

    def test_09_user_tags_survive_reanalysis(self):
        library = self.state['library']
        page = self.run_job('browse_assets', {'libraryId': library, 'limit': 100}); asset = next(a for a in page['assets'] if a['filename'] == 'high_tone_4000.flac')
        self.run_job('update_assets', {'libraryId': library, 'audioIds': [asset['audio_id']], 'setTags': ['My Tag', 'keeper'], 'favorite': True, 'rating': 4, 'notes': 'manual note'})
        taxonomy = {'categories': [{'id': 'tones', 'name': 'Tones', 'prompts': ['tone'], 'children': [{'id': 'tones.high', 'name': 'High', 'prompts': ['high tone']},
                    {'id': 'tones.low', 'name': 'Low', 'prompts': ['low tone']}]}, {'id': 'noise', 'name': 'Noise', 'prompts': ['noise']}], 'tags': ['noise', 'click', 'low', 'high']}
        self.run_job('update_library', {'libraryId': library, 'taxonomy': taxonomy, 'settings': {'categoryThreshold': 0.6, 'autoTagThreshold': 0.6}})
        self.run_job('categorize_library', {'libraryId': library})
        self.run_job('analyze_library', {'libraryId': library, 'retryFailed': True, 'device': 'cpu'})
        details = self.run_job('get_asset', {'libraryId': library, 'audioId': asset['audio_id']})
        self.assertEqual(details['userTags'], ['keeper', 'My Tag']); self.assertTrue(details['favorite']); self.assertEqual(details['rating'], 4)
        self.assertIn('tones.high', details['categories']); self.assertIn('tones', details['categories']); self.assertIn('high', details['autoTags'])
        self.assertTrue(all(t['modelKey'] for t in details['tagDetails'] if t['source'] == 'auto'))
        by_category = self.run_job('browse_assets', {'libraryId': library, 'filters': {'categories': ['noise']}})
        self.assertTrue(by_category['total'] >= 2 and all('tone' not in a['filename'] for a in by_category['assets']), [a['filename'] for a in by_category['assets']])

    def test_10_model_versions_coexist(self):
        library = self.state['library']
        before = self.run_job('library_status', {'libraryId': library})
        source = Path(registry.get_model(self.models[0])['localPath'])
        copy = TEMP/'custom-models'/'test-embed-a-v2'; shutil.copytree(source, copy)
        (copy/'adapter.py').write_text(fixtures.ADAPTER % {'dim': 24, 'salt': 'a-v2', 'delay': 0.0}, 'utf-8')
        registered = self.run_job('register_model', {'modelId': 'test-embed-a', 'version': 'v2-custom', 'displayName': 'Test A v2', 'modelType': 'AudioTextEmbedding',
                                                     'adapter': 'file:'+str(copy/'adapter.py'), 'localPath': str(copy), 'engine': 'base', 'embeddingDimension': 24,
                                                     'requiredSampleRate': 16000, 'preferredChunkDuration': 4.0, 'capabilities': ['AudioEmbedding', 'TextEmbedding', 'ZeroShotTagging']})
        self.assertNotEqual(registered['modelHash'], registry.get_model(self.models[0]).model_hash)
        self.run_job('update_library', {'libraryId': library, 'enabledModels': self.models[:2]+[registered['modelKey']]})
        result = self.run_job('analyze_library', {'libraryId': library, 'device': 'cpu'})
        analysed = {m['modelKey']: m['analyzed'] for m in result['models']}
        self.assertEqual(analysed[self.models[0]], 0); self.assertEqual(analysed[self.models[1]], 0); self.assertGreater(analysed[registered['modelKey']], 0)
        after = result['status']
        self.assertEqual(len(after['stores']), len(before['stores'])+1)
        old = next(s for s in after['stores'] if s['modelKey'] == self.models[0])
        self.assertEqual(old['rows'], next(s for s in before['stores'] if s['modelKey'] == self.models[0])['rows'])
        removed = self.run_job('remove_model', {'modelKey': registered['modelKey'], 'deleteAnalysis': True})
        self.assertEqual(len(removed['analysisDeleted']), 1); self.assertTrue((copy/'adapter.py').is_file(), 'custom model files must never be deleted')
        self.run_job('update_library', {'libraryId': library, 'enabledModels': self.models[:2]})

    def test_11_pause_resume_and_cancel(self):
        library = self.state['library']
        import soundfile
        for index in range(30): soundfile.write(str(self.second/f'batch_{index:02d}.wav'), fixtures.tone(300+index*20, 0.6), 22050)
        self.run_job('scan_library', {'libraryId': library})
        self.run_job('control_analysis', {'libraryId': library, 'action': 'pause'})
        job = self.runtime.submit(self.actor, self.session, 'analyze_library', {'libraryId': library, 'device': 'cpu'})
        deadline = time.monotonic()+60
        while time.monotonic() < deadline:
            current = self.runtime.get_job(self.actor, job['jobId'])
            if current['progress'].get('currentStep') == 'Paused': break
            time.sleep(0.1)
        self.assertEqual(current['progress'].get('currentStep'), 'Paused', current)
        self.assertEqual(self.run_job('library_status', {'libraryId': library})['queueState'], 'paused')
        busy = self.run_job('scan_library', {'libraryId': library}, expect='Failed')      # one maintenance job per Library
        self.assertEqual(busy['code'], 'Busy')
        self.run_job('control_analysis', {'libraryId': library, 'action': 'resume'})
        finished = self.runtime.wait(self.actor, job['jobId'], timeout=300)
        self.assertEqual(finished['state'], 'Completed', finished.get('error')); self.assertEqual(finished['outputs']['failed'], 0)
        # cancellation in the middle of a model request: the engine worker must really be gone before the job reports Cancelled
        self.run_job('update_library', {'libraryId': library, 'enabledModels': self.models[:2]+[self.models[3]]})
        job = self.runtime.submit(self.actor, self.session, 'analyze_library', {'libraryId': library, 'device': 'cpu', 'models': [self.models[3]]})
        while not self.runtime.get_job(self.actor, job['jobId'])['progress'].get('currentStep', '').startswith('Embedding'): time.sleep(0.05)
        host = self.runtime.model_pool.hosts['base']
        while host.state != 'Busy': time.sleep(0.02)
        time.sleep(0.4); pid = host.health()['pid']
        self.assertTrue(pid)
        self.runtime.cancel(self.actor, job['jobId'])
        cancelled = self.runtime.wait(self.actor, job['jobId'], timeout=60)
        self.assertEqual(cancelled['state'], 'Cancelled')
        import psutil
        self.assertFalse(psutil.pid_exists(pid), 'the job reported Cancelled while its worker process was still alive')
        self.assertEqual(host.health()['state'], 'Stopped')
        resumed = self.run_job('analyze_library', {'libraryId': library, 'device': 'cpu', 'models': [self.models[3]]})      # the queue resumes where it stopped
        self.assertGreater(resumed['analyzed'], 0)
        self.assertTrue(all(m['percent'] == 100.0 for m in resumed['status']['models']), resumed['status']['models'])
        self.run_job('update_library', {'libraryId': library, 'enabledModels': self.models[:2]})

    def test_12_errors_and_isolation(self):
        library = self.state['library']
        with self.assertRaises(CyToolError) as invalid: self.runtime.submit(self.actor, self.session, 'search_sounds', {'libraryId': 'nothex!!'})
        self.assertEqual(invalid.exception.code, 'InvalidParameters')
        error = self.run_job('search_sounds', {'libraryId': library}, expect='Failed'); self.assertEqual(error['code'], 'InvalidParameters')
        error = self.run_job('library_status', {'libraryId': '0123abcd'}, expect='Failed'); self.assertEqual(error['code'], 'NotFound')
        error = self.run_job('install_model', {'modelKey': 'm2d-clap@2025'}, expect='Failed'); self.assertEqual(error['code'], 'LicenseAcceptanceRequired')
        error = self.run_job('install_model', {'modelKey': 'audio-flamingo-3@hf', 'acceptLicense': True}, expect='Failed'); self.assertEqual(error['code'], 'NotImplemented')
        error = self.run_job('search_sounds', {'libraryId': library, 'text': 'x', 'llmAssist': 'off', 'models': ['m2d-clap@2025']}, expect='Failed')
        self.assertEqual(error['code'], 'NotAnalyzed')
        job = self.runtime.submit(self.actor, self.session, 'library_status', {'libraryId': library})
        other = self.runtime.authenticate(self.runtime.create_client('other')['token'])
        with self.assertRaises(CyToolError) as denied: self.runtime.get_job(other, job['jobId'])
        self.assertIn(denied.exception.code, ('AccessDenied', 'NotFound'))
        with self.assertRaises(CyToolError): self.runtime.cancel(other, job['jobId'])

    def test_13_move_cache_and_duplicates(self):
        library = self.state['library']
        target = TEMP/'Moved Cache'
        moved = self.run_job('move_cache', {'libraryId': library, 'cacheLocation': str(target)})
        self.assertTrue(moved['moved']); self.assertTrue(Path(moved['previous']).is_dir(), 'the previous cache must be kept')
        result = self.run_job('search_sounds', {'libraryId': library, 'text': 'noise', 'llmAssist': 'off', 'topK': 3})
        self.assertTrue(result['results'])
        error = self.run_job('move_cache', {'libraryId': library, 'cacheLocation': str(self.audio/'inside')}, expect='Failed'); self.assertEqual(error['code'], 'InvalidParameters')
        exact = self.run_job('find_duplicates', {'libraryId': library, 'mode': 'exact'})
        self.assertEqual(exact['groups'], 1); self.assertEqual(len(exact['duplicates'][0]['files']), 2)
        probable = self.run_job('find_duplicates', {'libraryId': library, 'mode': 'probable', 'model': self.models[0], 'threshold': 0.99})
        self.assertGreaterEqual(probable['groups'], 1)
        self.assertTrue((self.audio/'Noise éàü'/'noise_copy_a.wav').is_file() and (self.audio/'Noise éàü'/'noise_copy_b.wav').is_file())

    def test_14_background_check_is_read_only_and_detects_changes(self):
        library = self.state['library']
        import soundfile
        clean = self.run_job('check_library', {'libraryId': library})
        self.assertFalse(clean['changed'], clean)
        before = self.run_job('browse_assets', {'libraryId': library, 'limit': 1})['total']
        added = self.second/'added_while_closed.wav'; soundfile.write(str(added), fixtures.tone(700, 0.5), 22050)
        removed = self.second/'batch_00.wav'; removed.unlink()
        soundfile.write(str(self.second/'batch_01.wav'), fixtures.tone(1500, 0.9), 22050)       # content changed
        report = self.run_job('check_library', {'libraryId': library})
        self.assertEqual((report['new'], report['missing'], report['modified']), (1, 1, 1), report); self.assertTrue(report['changed'])
        self.assertIn(str(added), report['examples']['new'])
        self.assertEqual(self.run_job('browse_assets', {'libraryId': library, 'limit': 1})['total'], before, 'check_library wrote to the database')
        scan = self.run_job('scan_library', {'libraryId': library})
        self.assertEqual((scan['new'], scan['missing'], scan['modified']), (1, 1, 1), scan)
        self.assertEqual(self.run_job('browse_assets', {'libraryId': library, 'limit': 1})['total'], before)      # +1 new, -1 hidden as missing
        self.assertFalse(self.run_job('check_library', {'libraryId': library})['changed'])
        settings = self.run_job('update_library', {'libraryId': library, 'settings': {'autoSync': 'ask', 'autoSyncIntervalSeconds': 60, 'autoAnalyze': False}})['settings']
        self.assertEqual((settings['autoSync'], settings['autoSyncIntervalSeconds'], settings['autoAnalyze']), ('ask', 60, False))
        with self.assertRaises(CyToolError): self.runtime.submit(self.actor, self.session, 'update_library', {'libraryId': library, 'settings': {'autoSync': 'sometimes'}})

    def test_14b_macos_junk_is_never_indexed(self):
        library = self.state['library']
        junk = self.second/'__MACOSX'/'Pack'; junk.mkdir(parents=True)
        (junk/'._real_sound.wav').write_bytes(b'\x00\x05\x16\x07'+b'\x00'*508)        # AppleDouble header, 512 bytes
        (self.second/'._loose.wav').write_bytes(b'\x00\x05\x16\x07'+b'\x00'*508)
        (self.second/'.DS_Store').write_bytes(b'\x00'*64)
        before = self.run_job('browse_assets', {'libraryId': library, 'limit': 1})['total']
        check = self.run_job('check_library', {'libraryId': library}); self.assertFalse(check['changed'], check)
        scan = self.run_job('scan_library', {'libraryId': library})
        self.assertEqual((scan['new'], scan['unreadable'], scan['common']['failed']), (0, 0, 0), scan)
        self.assertEqual(self.run_job('browse_assets', {'libraryId': library, 'limit': 1})['total'], before)
        self.assertEqual(self.run_job('library_status', {'libraryId': library})['metadata']['failed'], 0)
        fixtures.write_av(self.second/'video.mp4', fixtures.tone(500, 0.5), 44100, 'aac'); self.run_job('scan_library', {'libraryId': library})
        self.assertEqual(self.run_job('browse_assets', {'libraryId': library, 'filters': {'extensions': ['mp4']}})['total'], 0, 'video containers must not be indexed')
        long = self.state['assets']['long_recording_with_noise_at_14s.wav']
        details = self.run_job('get_asset', {'libraryId': library, 'audioId': long['audio_id']})
        self.assertTrue(any(len([s for s in v if s['index'] >= 0]) > 3 for v in details['segments'].values()), details['segments'])

    def test_15_search_without_library_id_covers_every_library(self):
        import soundfile
        other = TEMP/'Other Library'; other.mkdir(exist_ok=True)
        soundfile.write(str(other/'other_low_tone_100.wav'), fixtures.tone(100, 1.0), 22050)
        empty = self.run_job('create_library', {'name': 'Not analyzed yet', 'folders': [str(other)], 'cacheLocation': str(TEMP/'External Cache')})
        second = self.run_job('create_library', {'name': 'Second SFX', 'folders': [str(other)], 'cacheLocation': str(TEMP/'External Cache')})
        self.run_job('scan_library', {'libraryId': second['libraryId']})
        self.run_job('update_library', {'libraryId': second['libraryId'], 'enabledModels': self.models[:2]})
        self.run_job('analyze_library', {'libraryId': second['libraryId'], 'device': 'cpu'})
        result = self.run_job('search_sounds', {'text': 'low tone', 'llmAssist': 'off', 'topK': 6})
        self.assertEqual({l['name'] for l in result['libraries']}, {'Test SFX', 'Second SFX'})
        self.assertEqual([s['name'] for s in result['skippedLibraries']], ['Not analyzed yet'])
        self.assertLessEqual(len(result['results']), 6)
        self.assertTrue(any(r['libraryName'] == 'Second SFX' and r['filename'] == 'other_low_tone_100.wav' for r in result['results']), [r['filename'] for r in result['results']])
        self.assertTrue(all(Path(r['path']).is_absolute() and 'libraryId' in r for r in result['results']))
        error = self.run_job('search_sounds', {'similarTo': '0'*32}, expect='Failed'); self.assertEqual(error['code'], 'InvalidParameters')
        self.run_job('delete_library', {'libraryId': empty['libraryId']}); self.run_job('delete_library', {'libraryId': second['libraryId']})


    def test_16_rename_keeps_identity_and_can_be_undone(self):
        library = self.state['library']
        from audiolib import fileops
        self.assertTrue(all(fileops.name_problem(n) for n in ('sound_01', 'ZOOM0012', 'Untitled', '0042', 'a1', 'Sans titre 3', 'c0ffee12-ab34')))
        self.assertFalse(any(fileops.name_problem(n) for n in ('MetalDoor_Slam_04', 'forest wind', 'Explosion_Heavy')))
        import soundfile
        bad = self.second/'sound_01.wav'; soundfile.write(str(bad), fixtures.tone(95, 1.0), 22050)
        self.run_job('scan_library', {'libraryId': library}); self.run_job('analyze_library', {'libraryId': library, 'device': 'cpu'})
        plan = self.run_job('suggest_names', {'libraryId': library})['plan']
        entry = next(p for p in plan if p['currentName'] == 'sound_01.wav')
        self.assertTrue(entry['proposedName'].endswith('.wav') and entry['proposedName'] != 'sound_01.wav', entry)
        self.assertNotIn('high_tone_4000.flac', [p['currentName'] for p in plan])       # a descriptive name is left alone
        self.assertTrue(bad.is_file(), 'suggest_names renamed a file')
        with self.assertRaises(CyToolError): self.runtime.submit(self.actor, self.session, 'rename_files', {'libraryId': library, 'renames': [{'audioId': entry['audioId'], 'newName': entry['proposedName']}]})
        before = self.run_job('get_asset', {'libraryId': library, 'audioId': entry['audioId']})
        done = self.run_job('rename_files', {'libraryId': library, 'confirm': True, 'renames': [
            {'audioId': entry['audioId'], 'newName': entry['proposedName']},
            {'audioId': entry['audioId'], 'newName': 'other.flac'}, {'audioId': entry['audioId'], 'newName': 'a/b.wav'}, {'audioId': entry['audioId'], 'newName': 'aux.wav'}]})
        self.assertEqual((done['renamed'], done['failed']), (1, 3), done)
        self.assertFalse(bad.exists()); self.assertTrue((self.second/entry['proposedName']).is_file())
        after = self.run_job('get_asset', {'libraryId': library, 'audioId': entry['audioId']})
        self.assertEqual(after['filename'], entry['proposedName']); self.assertEqual(after['analysis'], before['analysis'])      # embeddings follow the file
        check = self.run_job('check_library', {'libraryId': library}); self.assertFalse(check['changed'], check)                 # the scanner sees nothing to redo
        clash = self.run_job('rename_files', {'libraryId': library, 'confirm': True, 'renames': [{'audioId': entry['audioId'], 'newName': 'second_folder_tone.wav'}]})
        self.assertEqual(clash['renamed'], 0); self.assertTrue((self.second/'second_folder_tone.wav').is_file())               # never overwrites
        undone = self.run_job('undo_rename', {'libraryId': library, 'confirm': True})
        self.assertEqual(undone['restored'], 1); self.assertTrue(bad.is_file())
        self.assertEqual(self.run_job('get_asset', {'libraryId': library, 'audioId': entry['audioId']})['filename'], 'sound_01.wav')
        self.assertEqual(self.run_job('undo_rename', {'libraryId': library, 'confirm': True}, expect='Failed')['code'], 'NotFound')

    def test_17_write_metadata_leaves_audio_identical(self):
        library = self.state['library']
        from audiolib import fileops
        fixtures.write_av(self.second/'tag_me.mp3', fixtures.tone(600, 1.0), 44100, 'mp3'); self.run_job('scan_library', {'libraryId': library})
        page = self.run_job('browse_assets', {'libraryId': library, 'limit': 1000})['assets']
        wanted = {'tag_me.mp3': None, 'low_tone_90_24bit.wav': None, 'high_tone_4000.flac': None, 'mid_tone_800.m4a': None, 'white noise burst.ogg': None, 'renamed clicks.aiff': None}
        for asset in page:
            if asset['filename'] in wanted: wanted[asset['filename']] = asset
        self.assertTrue(all(wanted.values()), [k for k, v in wanted.items() if not v])
        ids = [a['audio_id'] for a in wanted.values()]
        self.run_job('update_assets', {'libraryId': library, 'audioIds': ids, 'addTags': ['Écrit dans le fichier'], 'description': 'Test description é', 'rating': 5})
        digests = {a['filename']: fileops.audio_digest(a['absolute_path']) for a in wanted.values()}
        states = {a['audio_id']: self.run_job('get_asset', {'libraryId': library, 'audioId': a['audio_id']})['analysis'] for a in wanted.values()}
        with self.assertRaises(CyToolError): self.runtime.submit(self.actor, self.session, 'write_metadata', {'libraryId': library, 'audioIds': ids})       # confirm is mandatory
        result = self.run_job('write_metadata', {'libraryId': library, 'audioIds': ids, 'confirm': True})
        self.assertEqual((result['written'], result['failed']), (6, 0), result)
        for asset in wanted.values():
            tags = fileops.read_tags(asset['absolute_path']); flat = ' '.join(tags.values())
            self.assertIn('Écrit dans le fichier', flat, asset['filename']); self.assertIn('Test description é', flat, asset['filename']); self.assertIn(asset['audio_id'], flat)
            self.assertEqual(fileops.audio_digest(asset['absolute_path']), digests[asset['filename']], 'audio changed in '+asset['filename'])
            self.assertEqual(self.run_job('get_asset', {'libraryId': library, 'audioId': asset['audio_id']})['analysis'], states[asset['audio_id']])
        self.assertTrue(all(Path(r['backup']).is_file() and str(self.audio) not in r['backup'] for r in result['results']))      # backups live in the cache
        self.assertFalse([p for p in self.audio.rglob('.*cytools-*')], 'a temporary file was left in the audio folder')
        rescan = self.run_job('scan_library', {'libraryId': library})
        self.assertEqual((rescan['modified'], rescan['new'], rescan['missing']), (0, 0, 0), rescan)     # tagging must not trigger a re-analysis
        unsupported = self.second/'plain.au'; import soundfile; soundfile.write(str(unsupported), fixtures.tone(300, 0.5), 22050, format='AU')
        self.run_job('scan_library', {'libraryId': library})
        target = next(a for a in self.run_job('browse_assets', {'libraryId': library, 'limit': 1000})['assets'] if a['filename'] == 'plain.au')
        self.run_job('update_assets', {'libraryId': library, 'audioIds': [target['audio_id']], 'addTags': ['x']})
        refused = self.run_job('write_metadata', {'libraryId': library, 'audioIds': [target['audio_id']], 'confirm': True})
        self.assertEqual(refused['results'][0]['code'], 'UnsupportedFormat'); self.assertEqual(unsupported.stat().st_size, target['file_size'])


    def test_18_folder_tree_and_batch_edits(self):
        library = self.state['library']
        listing = self.run_job('list_folders', {'libraryId': library, 'maxDepth': 0})
        main = next(r for r in listing['roots'] if Path(r['rootPath']).resolve() == self.audio.resolve())
        folders = {f['path']: f for f in main['folders']}
        self.assertIn('Tones', folders); self.assertIn('Tones/Low', folders)
        self.assertEqual(folders['Tones']['subfolders'], 1)
        self.assertEqual(folders['Tones']['files'], folders['Tones']['directFiles']+folders['Tones/Low']['files'])
        self.assertNotIn('notes.txt', ''.join(folders), 'a file is not a folder')
        for path, folder in folders.items():      # the tree and the filter agree: a folder count is what processing it would touch
            page = self.run_job('browse_assets', {'libraryId': library, 'filters': {'rootIds': [main['rootId']], 'folderPrefix': path}, 'limit': 1})
            self.assertEqual(page['total'], folder['files'], path)
        shallow = self.run_job('list_folders', {'libraryId': library, 'rootId': main['rootId'], 'maxDepth': 1})['roots'][0]['folders']
        self.assertNotIn('Tones/Low', [f['path'] for f in shallow])
        below = self.run_job('list_folders', {'libraryId': library, 'rootId': main['rootId'], 'folderPrefix': 'Tones', 'maxDepth': 0})
        self.assertEqual([f['path'] for f in below['roots'][0]['folders']], ['Tones/Low'])
        self.assertEqual(self.run_job('list_folders', {'libraryId': library, 'rootId': 'nope'}, expect='Failed')['code'], 'NotFound')

        from audiolib.library import flatten_taxonomy, get_library
        first, second = [node[0] for node in flatten_taxonomy(get_library(library).taxonomy)][:2]
        scope = {'rootIds': [main['rootId']], 'folderPrefix': 'Tones'}
        inside = {a['audio_id'] for a in self.run_job('browse_assets', {'libraryId': library, 'filters': scope, 'limit': 1000})['assets']}
        everything = {a['audio_id'] for a in self.run_job('browse_assets', {'libraryId': library, 'limit': 1000})['assets']}
        self.assertTrue(inside and everything-inside)
        noted = sorted(inside)[0]
        self.run_job('update_assets', {'libraryId': library, 'audioIds': [noted], 'notes': 'first line'})

        out = self.run_job('update_assets', {'libraryId': library, 'filters': scope, 'addTags': ['folder tag'],
                                             'addCategories': [first, second], 'appendNotes': 'batch line'})
        self.assertEqual((out['updated'], out['matched']), (len(inside), len(inside)))
        rows = {a['audio_id']: a for a in self.run_job('browse_assets', {'libraryId': library, 'limit': 1000})['assets']}
        for audio_id, row in rows.items():
            self.assertEqual('folder tag' in row['userTags'], audio_id in inside, row['relative_path'])
        self.assertEqual(self.run_job('get_asset', {'libraryId': library, 'audioId': noted})['notes'], 'first line\nbatch line')
        user_categories = lambda audio_id: {c['categoryId'] for c in self.run_job('get_asset', {'libraryId': library, 'audioId': audio_id})['categoryDetails'] if c['source'] == 'user'}
        self.assertEqual(user_categories(noted), {first, second})
        outside = sorted(everything-inside)[0]
        self.assertFalse({first, second} & user_categories(outside))

        self.run_job('update_assets', {'libraryId': library, 'audioIds': sorted(inside), 'removeCategories': [first], 'removeTags': ['folder tag']})
        self.assertEqual(user_categories(noted), {second}, 'removing one category keeps the others')
        self.assertFalse(any('folder tag' in a['userTags'] for a in self.run_job('browse_assets', {'libraryId': library, 'limit': 1000})['assets']))

        # a batch edit needs a target: an empty filter would silently mean "the whole Library"
        self.assertEqual(self.run_job('update_assets', {'libraryId': library, 'filters': {}, 'addTags': ['x']}, expect='Failed')['code'], 'InvalidParameters')
        self.assertEqual(self.run_job('update_assets', {'libraryId': library, 'addTags': ['x']}, expect='Failed')['code'], 'InvalidParameters')
        self.assertEqual(self.run_job('update_assets', {'libraryId': library, 'audioIds': [noted], 'addCategories': ['no-such-category']},
                                      expect='Failed')['code'], 'InvalidParameters')

    def test_19_bundle_copies_without_touching_the_library(self):
        import hashlib
        from audiolib.library import get_library
        library = self.state['library']
        sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
        before = listing(self.audio)
        assets = sorted(self.run_job('browse_assets', {'libraryId': library, 'limit': 1000})['assets'], key=lambda a: a['filename'])[:3]
        ids = [a['audio_id'] for a in assets]
        bundle = TEMP/'Bundle for the engine'

        first = self.run_job('export_bundle', {'libraryId': library, 'audioIds': ids, 'destination': str(bundle)})
        self.assertEqual((first['copied'], first['identical'], first['renamed'], first['missing']), (3, 0, 0, 0))
        for asset in assets:
            self.assertEqual(sha(bundle/asset['filename']), sha(asset['absolute_path']), 'a copy must be the same file')
        manifest = json.loads((bundle/'bundle.json').read_text(encoding='utf-8'))
        self.assertEqual(sorted(e['audioId'] for e in manifest['files']), sorted(ids))
        self.assertFalse(list(bundle.glob('*.part')), 'no temporary file is left behind')

        again = self.run_job('export_bundle', {'libraryId': library, 'audioIds': ids, 'destination': str(bundle)})
        self.assertEqual((again['copied'], again['identical']), (0, 3), 'exporting twice copies nothing twice')
        self.assertEqual(len(json.loads((bundle/'bundle.json').read_text(encoding='utf-8'))['files']), 3)

        other = assets[0]
        (bundle/other['filename']).write_bytes(b'a different file with the same name')      # someone changed the copy in the bundle
        renamed = self.run_job('export_bundle', {'libraryId': library, 'audioIds': [other['audio_id']], 'destination': str(bundle)})
        self.assertEqual(renamed['renamed'], 1)
        self.assertEqual((bundle/other['filename']).read_bytes(), b'a different file with the same name', 'never overwritten')
        self.assertEqual(sha(bundle/renamed['files'][0]['file']), sha(other['absolute_path']))
        self.assertIn(' (2)', renamed['files'][0]['file'])

        folders = TEMP/'Bundle with folders'
        scope = {'rootIds': [r['rootId'] for r in get_library(library).roots if Path(r['path']).resolve() == self.audio.resolve()], 'folderPrefix': 'Tones'}
        by_folder = self.run_job('export_bundle', {'libraryId': library, 'filters': scope, 'destination': str(folders), 'layout': 'folders', 'manifest': False})
        inside = self.run_job('browse_assets', {'libraryId': library, 'filters': scope, 'limit': 1000})['total']
        self.assertEqual(by_folder['copied'], inside)
        self.assertTrue(all(f['file'].startswith(self.audio.name+'/Tones/') for f in by_folder['files']), by_folder['files'][:2])
        self.assertFalse((folders/'bundle.json').exists())

        for unsafe in (self.audio/'Exports', get_library(library).cache/'Exports', 'relative/folder'):
            error = self.run_job('export_bundle', {'libraryId': library, 'audioIds': ids, 'destination': str(unsafe)}, expect='Failed')
            self.assertEqual(error['code'], 'InvalidParameters', unsafe)
        self.assertFalse((self.audio/'Exports').exists(), 'a refused export creates nothing')
        self.assertEqual(self.run_job('export_bundle', {'libraryId': library, 'filters': {}, 'destination': str(bundle)}, expect='Failed')['code'], 'InvalidParameters')
        self.assertEqual(before, listing(self.audio), 'the Library folder was modified by an export')

    def test_20_sort_by_category_tags_and_state(self):
        from audiolib.library import flatten_taxonomy, get_library
        library = self.state['library']
        names = {identifier: name for identifier, name, _, _ in flatten_taxonomy(get_library(library).taxonomy)}
        def shown(sort, descending=False):
            return self.run_job('browse_assets', {'libraryId': library, 'sort': sort, 'descending': descending, 'limit': 1000})['assets']
        everything = {a['audio_id'] for a in shown('name')}
        for sort in ('category', 'tags', 'state'):
            for descending in (False, True):
                assets = shown(sort, descending)
                self.assertEqual({a['audio_id'] for a in assets}, everything, (sort, 'a sort never drops a sound'))
        def first_category(asset): return names.get(asset['categories'][0], asset['categories'][0]).casefold() if asset['categories'] else None
        def first_tag(asset): return (asset['userTags'] or asset['autoTags'] or [None])[0]
        for sort, value in (('category', first_category), ('tags', first_tag)):
            values = [value(a) for a in shown(sort)]
            present = [v.casefold() for v in values if v is not None]
            self.assertEqual(present, sorted(present), sort)
            self.assertEqual(values[len(present):], [None]*(len(values)-len(present)), (sort, 'sounds without a value come last'))
            self.assertEqual([v.casefold() for v in (value(a) for a in shown(sort, True)) if v is not None], sorted(present, reverse=True), sort)
        with self.assertRaises(CyToolError) as refused: self.runtime.submit(self.actor, self.session, 'browse_assets', {'libraryId': library, 'sort': 'nope'})
        self.assertEqual(refused.exception.code, 'InvalidParameters')


class Configurations(unittest.TestCase):
    """Save/Load of the search form: exact parameters, no secret, loading never starts a job, replay through the runtime."""
    def test_roundtrip_and_replay(self):
        import generation_config
        runtime = LibraryFlow.runtime if hasattr(LibraryFlow, 'runtime') else None
        own = runtime is None or runtime._closed
        if own:
            runtime = create_runtime(Path(tempfile.mkdtemp(prefix='cy-audiolib-config-'))/'jobs'); runtime.start()
        try:
            parameters = {'libraryId': '0123abcd', 'text': 'porte métallique qui claque', 'llmAssist': 'always', 'llmModel': '', 'topK': 25, 'rrfK': 30,
                          'models': ['m2d-clap@2025'], 'filters': {'maxDuration': 5.0, 'channels': 2, 'extensions': ['wav'], 'minSampleRate': 48000}}
            value = generation_config.recipe(runtime.descriptor, 'search_sounds', parameters, ui_state={'widgets': {'##token': 'should-not-matter'}})
            self.assertTrue(value['validParameters']); self.assertEqual(value['toolId'], 'cy.tool.audiolibrary')
            path = Path(tempfile.mkdtemp(prefix='cy-audiolib-config-'))/'search.json'
            generation_config.save(path, value)
            before = len(runtime._jobs)
            loaded = generation_config.load(path, runtime.descriptor)
            restored = loaded['parameters']      # the Core re-validates on load and fills declared defaults (device, filters.status)
            self.assertEqual({k: restored[k] for k in parameters if k != 'filters'}, {k: v for k, v in parameters.items() if k != 'filters'})
            self.assertEqual({k: restored['filters'][k] for k in parameters['filters']}, parameters['filters'])
            self.assertEqual(set(restored)-set(parameters), {'device'}); self.assertEqual(loaded['operationId'], 'search_sounds')
            self.assertEqual(len(runtime._jobs), before, 'loading a configuration started a job')
            self.assertNotIn('token', json.dumps(json.loads(path.read_text('utf-8'))['parameters']).lower())
            draft = generation_config.recipe(runtime.descriptor, 'search_sounds', {'libraryId': 'bad id'})
            self.assertFalse(draft['validParameters'])       # an incomplete form is saved as a draft, not rejected
            actor = runtime.authenticate(runtime.create_client('replay')['token']); session = runtime.create_session(actor, temporary=False)['sessionId']
            job = generation_config.submit_config(runtime, actor, session, path)
            job = runtime.wait(actor, job['jobId'], timeout=60)
            self.assertEqual(job['state'], 'Failed'); self.assertEqual(job['error']['code'], 'NotFound')      # replay reached the handler: that Library does not exist here
        finally:
            if own: runtime.close()


if __name__ == '__main__':
    unittest.main()
