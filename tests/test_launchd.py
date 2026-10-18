import importlib.util
import json
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


adapter = module('adapter', ROOT / 'templates/launchd/service.py')
generator = module('generator', ROOT / 'scripts/scaffold-launchd.py')


class FakeLaunchd:
    def __init__(self, plist):
        self.plist = plist
        self.loaded = True
        self.pid = 123
        self.calls = []
        self.health = True
        self.fail_query = False
        self.fail_action = False

    def __call__(self, args):
        self.calls.append(args)
        code, out, err = 0, '', ''
        if args[1] == 'print':
            if self.fail_query:
                code, err = 1, 'Could not find domain'
            elif not self.loaded:
                code, err = 113, 'Could not find service "test" in domain'
            else:
                out = 'path = {}\npid = {}\n'.format(self.plist, self.pid) if self.pid else 'path = {}\n'.format(self.plist)
        elif args[0] == '/usr/sbin/lsof':
            out = 'p123\nn127.0.0.1:45678\n'
        elif args[1] == 'health':
            code = 0 if self.health else 1
            out = json.dumps({'result': 'ok' if self.health else 'failed',
                              **{key: {'ok': self.health} for key in ('healthz', 'readyz', 'control_plane_poll')}})
        elif self.fail_action:
            code = 1
        elif args[1] == 'bootout':
            self.loaded, self.pid = False, 0
        elif args[1] in ('bootstrap', 'kickstart'):
            self.loaded, self.pid = True, 124
        else:
            raise AssertionError(args)
        return subprocess.CompletedProcess(args, code, out, err)


class LaunchdTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plist = self.root / 'test.plist'
        self.plist.write_bytes(plistlib.dumps({'Label': 'test.tunnel', 'KeepAlive': True,
            'ProgramArguments': ['/path with spaces/tunnel-client', 'run', '--profile', 'test']}))
        self.fake = FakeLaunchd(self.plist)
        self.config = {'label': 'test.tunnel', 'plist': str(self.plist),
                       'probe': {'type': 'tunnel-client', 'profile': 'test'}}
        self.service = adapter.Service(self.config, self.fake)

    def test_running_start_is_idempotent_and_readiness_is_separate(self):
        self.service.start()
        self.assertFalse(any(call[1] in ('bootstrap', 'kickstart') for call in self.fake.calls))
        result, code = self.service.status()
        self.assertEqual((result['status'], result['readiness'], code), ('running', 'ready', 0))
        self.assertIn(['--pid', '123'], [call[i:i+2] for call in self.fake.calls for i in range(len(call)-1)])
        self.fake.health = False
        result, code = self.service.status()
        self.assertEqual((result['status'], result['readiness'], code), ('running', 'unready', 0))

    def test_keepalive_stop_unloads_and_is_idempotent_then_bootstraps(self):
        self.service.stop()
        self.service.stop()
        self.assertEqual(sum(call[1] == 'bootout' for call in self.fake.calls), 1)
        self.assertEqual(self.service.status()[1], 1)
        self.service.start()
        self.assertEqual(sum(call[1] == 'bootstrap' for call in self.fake.calls), 1)
        self.assertEqual(self.fake.pid, 124)

    def test_loaded_stopped_job_kickstarts_without_bootstrap(self):
        self.fake.pid = 0
        self.service.start()
        self.assertTrue(any(call[1] == 'kickstart' for call in self.fake.calls))
        self.assertFalse(any(call[1] == 'bootstrap' for call in self.fake.calls))

    def test_query_failure_and_wrong_job_never_mutate(self):
        self.fake.fail_query = True
        with self.assertRaises(RuntimeError):
            self.service.start()
        self.fake.fail_query = False
        self.fake.plist = self.root / 'someone-else.plist'
        with self.assertRaises(ValueError):
            self.service.stop()
        self.assertTrue(all(call[1] == 'print' for call in self.fake.calls))

    def test_action_failure_is_reported(self):
        self.fake.fail_action = True
        with self.assertRaises(RuntimeError):
            self.service.stop()

    def test_profile_or_label_mismatch_is_rejected(self):
        for key, value in [('label', 'wrong.label'), ('probe', {'type': 'tunnel-client', 'profile': 'other'})]:
            with self.assertRaises(ValueError):
                adapter.Service({**self.config, key: value}, self.fake)
        self.assertEqual(self.fake.calls, [])

    def test_health_timeout_does_not_hide_running_process(self):
        def run(args):
            if args[1] == 'health':
                raise subprocess.TimeoutExpired(args, 5)
            return self.fake(args)
        result, code = adapter.Service(self.config, run).status()
        self.assertEqual((result['status'], result['readiness'], code), ('running', 'unknown', 0))

    def test_generator_preserves_parent_and_refuses_overwrite_or_escape(self):
        manifest = self.root / 'control-panel.json'
        manifest.write_text(json.dumps({'name': 'Parent', 'id': 'parent', 'startCommand': './start.sh',
                                        'children': [{'path': 'existing', 'role': 'api'}]}))
        dest = generator.scaffold(self.root, 'tooling/tunnel', 'Parent Tunnel', 'test.tunnel', 'test')
        parent = json.loads(manifest.read_text())
        self.assertEqual(parent['startCommand'], './start.sh')
        self.assertEqual(parent['children'][0]['role'], 'api')
        self.assertEqual(parent['children'][1]['path'], 'tooling/tunnel')
        child = json.loads((dest / 'control-panel.json').read_text())
        self.assertEqual(child['processMode'], 'external')
        for action in ('start', 'stop', 'status', 'restart'):
            script = dest / child[action + 'Command']
            self.assertTrue(script.stat().st_mode & 0o111)
            subprocess.run(['/bin/bash', '-n', str(script)], check=True)
        before = manifest.read_bytes()
        with self.assertRaises(ValueError):
            generator.scaffold(self.root, 'tooling/tunnel', 'Other', 'test.tunnel')
        with self.assertRaises(ValueError):
            generator.scaffold(self.root, '../escape', 'Other', 'test.tunnel')
        outside = self.root.parent / 'outside'
        (self.root / 'escape').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            generator.scaffold(self.root, 'escape/tunnel', 'Other', 'test.tunnel')
        self.assertEqual(manifest.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
