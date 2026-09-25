"""Update mechanism with fixtures: no real GitHub release exists for this Tool, so nothing here proves a public
update. What is proved: staging, identity/ABI/content checks, rejection of hostile archives, activation at start-up,
rollback, and that data/ is never touched. Everything runs in a temporary copy; the real app/ is not swapped.
"""
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import maintenance


class Updates(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix='cy-audiolib-update-'))
        self.root = self.temp/'Tool'; app = self.root/'app'
        (app/'gui').mkdir(parents=True)
        for name in ('CyTool.json', 'release.json', 'tool.py', 'worker.py', 'maintenance.py', 'engine.json', 'bootstrap.py'): shutil.copyfile(APP/name, app/name)
        shutil.copyfile(APP/'gui'/'main.py', app/'gui'/'main.py')
        (self.root/'data'/'libraries').mkdir(parents=True); (self.root/'data'/'libraries'/'keep.json').write_text('{"user": "data"}', 'utf-8')
        self.saved = {name: getattr(maintenance, name) for name in ('APP', 'ROOT', 'UPDATES', 'BACKUPS', 'SETTINGS')}
        maintenance.APP, maintenance.ROOT = app, self.root
        maintenance.UPDATES, maintenance.BACKUPS, maintenance.SETTINGS = self.root/'runtime'/'updates', self.root/'runtime'/'backups', self.root/'data'/'settings'
        maintenance.ensure_idle = lambda: None

    def tearDown(self):
        for name, value in self.saved.items(): setattr(maintenance, name, value)
        shutil.rmtree(self.temp, ignore_errors=True)

    def release(self, version='0.2.0', tool_id=None, abi=None, extra=None, drop=None):
        source = self.temp/('release-'+version); shutil.copytree(maintenance.APP, source/'app')
        data = json.loads((source/'app'/'release.json').read_text('utf-8')); data['version'] = version
        if abi: data['runtime_abi'] = abi
        (source/'app'/'release.json').write_text(json.dumps(data), 'utf-8')
        if tool_id:
            manifest = json.loads((source/'app'/'CyTool.json').read_text('utf-8')); manifest['id'] = tool_id
            (source/'app'/'CyTool.json').write_text(json.dumps(manifest), 'utf-8')
        if drop: (source/'app'/drop).unlink()
        archive = self.temp/(version+'.zip')
        with zipfile.ZipFile(archive, 'w') as bundle:
            for path in source.rglob('*'):
                if path.is_file(): bundle.write(path, path.relative_to(source).as_posix())
            for name, content in (extra or {}).items(): bundle.writestr(name, content)
        return archive, hashlib.sha256(archive.read_bytes()).hexdigest()

    def test_stage_activate_and_rollback_preserve_data(self):
        archive, digest = self.release('0.2.0')
        self.assertEqual(maintenance.stage_archive(archive, digest), '0.2.0')
        self.assertEqual(json.loads((maintenance.APP/'release.json').read_text('utf-8'))['version'], '0.1.0', 'staging must not touch the active application')
        self.assertEqual(maintenance.apply_pending(), '0.2.0')
        self.assertEqual(json.loads((maintenance.APP/'release.json').read_text('utf-8'))['version'], '0.2.0')
        self.assertEqual((self.root/'runtime'/'bootstrap.py').read_bytes(), (maintenance.APP/'bootstrap.py').read_bytes(),
                         'the start-up script outside app/ is installed from the activated release')
        self.assertEqual((self.root/'data'/'libraries'/'keep.json').read_text('utf-8'), '{"user": "data"}')
        backups = list((maintenance.BACKUPS/'app').iterdir()); self.assertEqual(len(backups), 1)
        self.assertIsNone(maintenance.apply_pending())
        maintenance.rollback_tool(); self.assertEqual(maintenance.apply_pending(), '0.1.0')
        self.assertEqual(json.loads((maintenance.APP/'release.json').read_text('utf-8'))['version'], '0.1.0')
        self.assertEqual((self.root/'data'/'libraries'/'keep.json').read_text('utf-8'), '{"user": "data"}')

    def test_hostile_or_wrong_archives_are_rejected(self):
        cases = {'other tool': dict(tool_id='cy.tool.other'), 'other abi': dict(abi='cpython399-other'), 'incomplete': dict(drop='worker.py'),
                 'traversal': dict(extra={'../escape.txt': 'x'}), 'absolute': dict(extra={'/abs.txt': 'x'}), 'drive': dict(extra={'C:/x.txt': 'x'}),
                 'data folder': dict(extra={'app/data/settings/x.json': '{}'})}
        for number, (name, options) in enumerate(cases.items()):
            with self.subTest(name):
                archive, digest = self.release('0.3.'+str(number), **options)
                with self.assertRaises(Exception): maintenance.stage_archive(archive, digest)
                self.assertFalse((maintenance.SETTINGS/'tool-pending.json').is_file(), name+' became pending')
                self.assertFalse((self.temp/'escape.txt').exists())
        self.assertEqual(json.loads((maintenance.APP/'release.json').read_text('utf-8'))['version'], '0.1.0')

    def test_symlink_entry_is_rejected(self):
        archive, _ = self.release('0.4.0')
        with zipfile.ZipFile(archive, 'a') as bundle:
            info = zipfile.ZipInfo('app/link'); info.external_attr = (0o120777 << 16); bundle.writestr(info, '../../data')
        with self.assertRaises(ValueError): maintenance.safe_extract(archive, self.temp/'out')

    def published(self, repository):
        path = maintenance.APP/'release.json'
        data = json.loads(path.read_text('utf-8'))
        if repository: data['repository'] = repository
        else: data.pop('repository', None)
        path.write_text(json.dumps(data), 'utf-8')

    def test_no_repository_is_invented(self):
        self.published(None)        # a release that declares no repository, and nothing entered
        with self.assertRaises(RuntimeError) as error: maintenance.check_tool()
        self.assertIn('No GitHub repository is configured', str(error.exception))
        with self.assertRaises(ValueError): maintenance.save_update_settings({'tool_repository': 'not a repository!'})
        self.assertEqual(maintenance.save_update_settings({'tool_repository': 'https://github.com/owner/name.git'})['tool_repository'], 'owner/name')

    def test_published_repository_is_the_default_and_a_fork_overrides_it(self):
        self.published('Publisher/Tool')
        self.assertEqual(maintenance.configured_repository(), 'Publisher/Tool')
        self.assertEqual(maintenance.save_update_settings({'tool_repository': 'https://github.com/Someone/Fork'})['tool_repository'], 'Someone/Fork')
        self.assertEqual(maintenance.configured_repository(), 'Someone/Fork')
        # saving the published one again is not an override: the default keeps following release.json
        self.assertEqual(maintenance.save_update_settings({'tool_repository': 'Publisher/Tool'})['tool_repository'], '')
        self.published('Publisher/Moved')
        self.assertEqual(maintenance.configured_repository(), 'Publisher/Moved')

    def test_missing_private_and_empty_repositories_are_told_apart(self):
        self.published('Publisher/Tool')
        saved = maintenance.github
        try:
            def private(path): raise RuntimeError('Repository or release not found on GitHub.')
            maintenance.github = private
            with self.assertRaises(RuntimeError) as error: maintenance.check_tool()
            self.assertIn('private', str(error.exception))
            def empty(path):
                if path.endswith('/releases/latest'): raise RuntimeError('Repository or release not found on GitHub.')
                return {'full_name': 'Publisher/Tool'}
            maintenance.github = empty
            with self.assertRaises(RuntimeError) as error: maintenance.check_tool()
            self.assertIn('No release is published', str(error.exception))
            maintenance.github = lambda path: {'tag_name': 'v0.2.0', 'html_url': 'https://github.com/Publisher/Tool/releases/v0.2.0', 'assets': []}
            state = maintenance.check_tool()
            self.assertEqual((state['repository'], state['update_available']), ('Publisher/Tool', True))
        finally:
            maintenance.github = saved


if __name__ == '__main__':
    unittest.main()
