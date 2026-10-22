import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

TEMPLATE = Path(__file__).resolve().parents[1] / 'templates/release/adapter.py'

class ReleaseTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='release-contract-')
        self.root = Path(self.temporary.name) / 'source'
        self.root.mkdir()
        self.store = Path(self.temporary.name) / 'releases'
        self.env = {**os.environ, 'PROJECT_RELEASE_STORE': str(self.store), 'PYTHONDONTWRITEBYTECODE': '1'}
        self.call(['git', 'init', '-q'])
        destination = self.root / 'tooling/release'
        destination.mkdir(parents=True)
        shutil.copy2(TEMPLATE, destination / 'adapter.py')
        (self.root / '.gitignore').write_text('data/\n.runtime/\n')
        (self.root / 'worker.py').write_text('import time\nwhile True: time.sleep(1)\n')
        (self.root / 'lifecycle.py').write_text('''
import os,sys,json,subprocess,signal,time
from pathlib import Path
root=Path.cwd();handle=root/'.runtime/handle.json';action=sys.argv[1]
def alive(pid):
 try: os.kill(pid,0);return True
 except ProcessLookupError:return False
record=json.loads(handle.read_text()) if handle.exists() else None
if action=='start':
 handle.parent.mkdir(exist_ok=True)
 child=subprocess.Popen([sys.executable,str(root/'worker.py')],cwd=root,start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 handle.write_text(json.dumps({'pid':child.pid}))
 (root/'data/activated').write_text('yes')
elif action=='status':sys.exit(0 if record and alive(record['pid']) else 1)
elif action=='stop':
 if (root/'refuse-stop').exists():sys.exit(9)
 if record and alive(record['pid']):os.kill(record['pid'],signal.SIGTERM);time.sleep(.25)
 handle.unlink(missing_ok=True)
''')
        self.config = dict(legacy={a:[sys.executable,'lifecycle.py',a] for a in ['start','stop','status']},
                           prepare=[[sys.executable,'-c',"from pathlib import Path; Path('built.txt').write_text('built')"]],
                           outputs=['built.txt'],persistent=['data'],runtimeFiles=['.env'],toolchain=[])
        self.save_config()

    def tearDown(self):
        # Stop only workers created in this test's private immutable artifacts.
        for file in self.store.glob('*/active.json'):
            record=json.loads(file.read_text())
            for proc in record['processes']:
                try:os.kill(proc['pid'],signal.SIGTERM)
                except ProcessLookupError:pass
        self.temporary.cleanup()

    def call(self,args,check=True):
        return subprocess.run(args,cwd=self.root,env=self.env,capture_output=True,text=True,check=check,timeout=30)

    def save_config(self):
        (self.root/'tooling/release/config.json').write_text(json.dumps(self.config))

    def adapter(self,action,check=True):
        result=self.call([sys.executable,'tooling/release/adapter.py',action],check)
        return json.loads(result.stdout) if result.returncode==0 else result

    def prepare(self):
        version=self.adapter('version')['sourceRevision']
        self.env['PROJECT_TARGET_REVISION']=version
        return self.adapter('prepare')

    def test_snapshot_dirty_inputs_reuse_and_integrity(self):
        first=self.prepare();folder=next(self.store.glob('*/'+first['artifactId'][7:]))
        self.assertFalse((folder/'data').exists())
        self.assertEqual(first,self.prepare())
        (folder/'built.txt').write_text('corrupt')
        self.assertIsNone(self.adapter('version')['builtRevision'])
        self.assertEqual(first,self.prepare())
        self.assertEqual((folder/'built.txt').read_text(),'built')
        (self.root/'worker.py').write_text('changed source')
        self.assertNotEqual(self.adapter('version')['sourceRevision'],first['builtRevision'])
        self.assertNotEqual((folder/'worker.py').read_text(),'changed source')

    def test_activate_reads_real_pid_and_preserves_data(self):
        data=self.root/'data';data.mkdir();(data/'original').write_text('keep')
        (self.root/'.env').write_text('PRIVATE=not-for-build')
        prepared=self.prepare();folder=next(self.store.glob('*/'+prepared['artifactId'][7:]))
        self.assertFalse((folder/'.env').exists())
        self.env['PROJECT_ARTIFACT_ID']=prepared['artifactId']
        self.assertEqual(self.adapter('activate')['runningRevision'],prepared['builtRevision'])
        self.assertTrue((data/'activated').exists())
        self.assertEqual((data/'original').read_text(),'keep')
        self.assertEqual(self.adapter('version')['runningRevision'],prepared['builtRevision'])
        self.adapter('stop')
        self.assertIsNone(self.adapter('version')['runningRevision'])
        self.assertEqual((data/'original').read_text(),'keep')

    def test_failed_prepare_never_activates_or_links_live_data(self):
        self.config['prepare']=[[sys.executable,'-c','raise RuntimeError("build failure")']]
        self.save_config();target=self.adapter('version')['sourceRevision'];self.env['PROJECT_TARGET_REVISION']=target
        self.assertNotEqual(self.adapter('prepare',False).returncode,0)
        self.assertFalse((self.root/'data').exists())
        self.assertIsNone(self.adapter('version')['builtRevision'])

    def test_source_change_and_escaped_artifact_are_rejected(self):
        old=self.adapter('version')['sourceRevision'];(self.root/'new.py').write_text('new')
        self.env['PROJECT_TARGET_REVISION']=old
        self.assertNotEqual(self.adapter('prepare',False).returncode,0)
        self.env['PROJECT_ARTIFACT_ID']='../../elsewhere'
        self.assertNotEqual(self.adapter('activate',False).returncode,0)

    def test_pid_reuse_and_process_exit_never_claim_current(self):
        prepared=self.prepare();self.env['PROJECT_ARTIFACT_ID']=prepared['artifactId'];self.adapter('activate')
        active=next(self.store.glob('*/active.json'));record=json.loads(active.read_text())
        for p in record['processes']:p['identity']='stale PID signature'
        active.write_text(json.dumps(record))
        self.assertIsNone(self.adapter('version')['runningRevision'])
        # Restore ownership for cleanup.
        self.adapter('stop')

    def test_scaffold_installs_contract_without_build_or_start(self):
        (self.root/'control-panel.json').write_text(json.dumps({'name':'fixture','workingDirectory':'.'}))
        generator=TEMPLATE.parents[1].parent/'scripts/scaffold-release.py'
        self.call([sys.executable,str(generator),str(self.root),'--config',str(self.root/'tooling/release/config.json')])
        manifest=json.loads((self.root/'control-panel.json').read_text())
        self.assertEqual(manifest['release']['protocol'],1)
        self.assertTrue((self.root/'scripts/release-version.sh').is_file())
        self.assertFalse((self.root/'data').exists())
        self.assertFalse((self.root/'built.txt').exists())
        self.assertFalse(self.store.exists())

    def test_only_declared_public_build_environment_affects_revision(self):
        self.config['buildEnvironment']=['VITE_API_BASE']
        self.config['buildEnvFiles']=['.env']
        self.save_config()
        envfile=self.root/'.env';envfile.write_text('VITE_API_BASE=/api\nPRIVATE_KEY=first-secret\n')
        first=self.adapter('version')['sourceRevision']
        envfile.write_text('VITE_API_BASE=/api\nPRIVATE_KEY=changed-secret\n')
        self.assertEqual(first,self.adapter('version')['sourceRevision'])
        envfile.write_text('VITE_API_BASE=/new-api\nPRIVATE_KEY=changed-secret\n')
        self.assertNotEqual(first,self.adapter('version')['sourceRevision'])

    def test_external_source_symlink_rejected_without_reading_target(self):
        (self.root/'escape.py').symlink_to(Path(self.temporary.name)/'outside')
        (Path(self.temporary.name)/'outside').write_text('private')
        result=self.adapter('version',False)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('private',result.stderr)

import signal
if __name__=='__main__':unittest.main()
