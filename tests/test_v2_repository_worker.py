"""Actual worker replay and resource/pipe failures without invoking producer code."""
import copy
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib import repository_worker_protocol as protocol
from lib.providers import repository_worker as worker
from lib.portable.runtime import source_digest
from lib.v2_boundary import violations


class WorkerSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name).resolve()
        self.ps=worker.executable('/bin/ps')[0]

    def run_child(self,program,*,raw=b'{}',timeout=5,memory=protocol.MEMORY_BYTES):
        return worker.supervise([sys.executable,'-I','-B','-c',program],raw,
            timeout=timeout,memory_limit=memory,ps_tool=self.ps)

    def stopped(self,pid):
        deadline=time.monotonic()+2
        while True:
            result=subprocess.run([self.ps,'-o','stat=','-p',str(pid)],capture_output=True,text=True,timeout=1)
            if result.returncode==1 or result.stdout.strip().startswith('Z') or time.monotonic()>=deadline:break
            time.sleep(.02)
        self.assertTrue(result.returncode==1 or result.stdout.strip().startswith('Z'),result.stdout)

    def test_large_simultaneous_input_output_and_stderr_do_not_deadlock(self):
        raw=b'x'*protocol.MAX_REQUEST
        stdout,observed=self.run_child("import sys;sys.stderr.buffer.write(b'e'*60000);sys.stderr.flush();"
            "data=sys.stdin.buffer.read();sys.stdout.buffer.write(data*8)",raw=raw)
        self.assertEqual(stdout,raw*8)
        self.assertEqual(observed['stderr_bytes'],60000)
        self.assertEqual(observed['stderr_sha256'],hashlib.sha256(b'e'*60000).hexdigest())
        self.assertFalse(observed['kernel_peak_rss_ceiling_claimed'])
        self.assertFalse(observed['independent_execution_attested'])

    def test_timeout_kills_and_reaps_the_owned_worker(self):
        path=self.base/'pid'
        code=f"import os,time;open({str(path)!r},'w').write(str(os.getpid()));time.sleep(20)"
        with self.assertRaisesRegex(TimeoutError,'wall_budget'):self.run_child(code,timeout=.5)
        self.stopped(int(path.read_text()))

    def test_inherited_pipe_holder_is_terminated_after_parent_exit(self):
        path=self.base/'child'
        code=f"import os,time;pid=os.fork();open({str(path)!r},'w').write(str(os.getpid())) if pid==0 else None;time.sleep(20) if pid==0 else None"
        with self.assertRaisesRegex(TimeoutError,'wall_budget'):self.run_child(code,timeout=.7)
        self.stopped(int(path.read_text()))

    def test_resident_growth_is_observed_and_stopped(self):
        path=self.base/'pid'
        code=f"import os,time;open({str(path)!r},'w').write(str(os.getpid()));data=bytearray(64*1024**2);time.sleep(20)"
        with self.assertRaisesRegex(ValueError,'resident_budget'):
            self.run_child(code,memory=32*1024**2)
        self.stopped(int(path.read_text()))

    def test_stdout_and_stderr_floods_are_bounded(self):
        for stream,count in [('stdout',protocol.MAX_RESPONSE+1),('stderr',65537)]:
            with self.subTest(stream=stream),self.assertRaisesRegex(ValueError,'stream_budget'):
                self.run_child(f"import sys;sys.stdin.buffer.read();sys.{stream}.buffer.write(b'x'*{count})")

    def test_stalled_memory_observer_rejects_result_and_stops_owned_worker(self):
        observer=self.base/'slow-observer';observer.write_text('#!/bin/sh\nexec /bin/sleep 3\n');observer.chmod(0o700)
        path=self.base/'pid'
        code=f"import os,time;open({str(path)!r},'w').write(str(os.getpid()));time.sleep(20)"
        with self.assertRaisesRegex(ValueError,'memory_observation_failed'):
            worker.supervise([sys.executable,'-I','-B','-c',code],b'{}',timeout=5,
                memory_limit=protocol.MEMORY_BYTES,ps_tool=str(observer))
        self.stopped(int(path.read_text()))

    def test_nonzero_worker_does_not_return_partial_or_private_output(self):
        with self.assertRaisesRegex(ValueError,'^repository_replay_worker_process_failed$'):
            self.run_child("import sys;sys.stdin.buffer.read();print('private partial result');sys.stderr.write('private detail');sys.exit(2)")

    def test_supervisor_rejects_unbounded_requests_before_start(self):
        for changes in ({'raw':b''},{'raw':b'x'*(protocol.MAX_REQUEST+1)},
                        {'timeout':121},{'timeout':True},{'memory':protocol.MEMORY_BYTES+1}):
            with self.subTest(changes=list(changes)),patch.object(worker.subprocess,'Popen',side_effect=AssertionError('must not start')):
                with self.assertRaises(ValueError):self.run_child('raise AssertionError()',**changes)

    def test_protocol_is_neutral_and_limits_are_not_an_authority_claim(self):
        self.assertEqual(violations('protocol.py',(ROOT/'scripts/lib/repository_worker_protocol.py').read_text()),[])


@unittest.skipUnless(all(shutil.which(name) for name in ('git','ssh-keygen','opa','openssl')),'native validation tools absent')
class WorkerReplayTests(unittest.TestCase):
    def setUp(self):
        from types import MethodType
        import test_v2_repository_inspection as fixture
        self.fixture=fixture.RepositoryInspectionTests
        for name in ('command','commit','execute','inspect'):
            setattr(self,name,MethodType(getattr(self.fixture,name),self))
        self.fixture.setUp(self)
        target=self.base/('a'*64);self.operation.rename(target);self.operation=target

    def header(self):
        return {**self.fixture.header(self),'runtime_source_digest':source_digest()}

    def test_actual_positive_worker_matches_whole_replay_after_source_deletion(self):
        value=self.fixture.real(self,False)
        expected=self.inspect(value)
        original={p.relative_to(self.operation).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.operation.rglob('*') if p.is_file()}
        actual=worker.inspect_operation(self.operation,value['binding'])
        observed=actual.pop('worker_observation')
        self.assertEqual(actual,expected)
        self.assertGreater(observed['resident_bytes_observed_peak'],0)
        self.assertEqual(observed['cpu_seconds_limit'],60)
        self.assertEqual(observed['address_space_bytes_limit'],2*protocol.MEMORY_BYTES if sys.platform.startswith('linux') else None)
        self.assertEqual(original,{p.relative_to(self.operation).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.operation.rglob('*') if p.is_file()})

    def test_actual_negative_worker_preserves_exit_and_rejects_changed_journal(self):
        value=self.fixture.real(self,True)
        expected=self.inspect(value)
        actual=worker.inspect_operation(self.operation,value['binding']);actual.pop('worker_observation')
        self.assertEqual(actual,expected);self.assertEqual(actual['exit_code'],1)
        journal=self.operation/'events.jsonl';original=journal.read_bytes()
        try:
            journal.write_bytes(original.replace(b'operation-start',b'operation-starp',1))
            with self.assertRaisesRegex(ValueError,'process_failed'):worker.inspect_operation(self.operation,value['binding'])
        finally:journal.write_bytes(original)
        changed=copy.deepcopy(value['binding']);changed['runtime_source_digest']='f'*64
        with self.assertRaisesRegex(ValueError,'process_failed'):worker.inspect_operation(self.operation,changed)

    def test_public_cli_uses_admitted_context_and_leaves_whole_inspection_unchanged(self):
        from lib import repository_application as app
        shutil.copytree(ROOT,self.source,dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('.git','__pycache__','.venv*','.DS_Store','*.pyc'))
        self.commit()
        product=self.source
        caller=self.base/'working-source'
        # Use Git's object transfer while background maintenance may repack the
        # fixture; recursively copying a live .git directory races that work.
        self.command('-c','protocol.file.allow=always','clone','--no-local',str(product),str(caller))
        instance=self.base/'instance';instance.mkdir(mode=0o700)
        settings={'node_id':'b'*32,'runtime_source_digest':source_digest(),
                  'source_revision':self.revision,'source_root':str(product),'opa':shutil.which('opa')}
        context=app.RepositoryContext(instance,settings,product_root=product)
        operation,value=context.create('2026-11-15T12:00:00Z',engine_profile='legacy-repository-validator-v1',source_worktree=caller)
        self.assertEqual(value['outcome']['exit_code'],0)
        shutil.rmtree(caller)
        expected=context.inspect(operation)
        stdout=io.StringIO()
        with patch.object(app,'RepositoryContext',return_value=context),contextlib.redirect_stdout(stdout):
            self.assertEqual(app.run(['repository-inspect','--assessment',operation,'--bounded-worker'],instance,settings),0)
        actual=json.loads(stdout.getvalue());observed=actual.pop('worker_observation')
        self.assertEqual(actual,expected);self.assertEqual(observed['returncode'],0)
        self.assertFalse(actual['independent_execution_attested'])
        import axiom_v2 as cli
        stdout,stderr=io.StringIO(),io.StringIO()
        with patch.object(app,'RepositoryContext',return_value=context), \
             patch.object(cli,'run',side_effect=lambda command,arguments,instance_path:app.run(arguments,instance,settings)), \
             patch.object(protocol,'MEMORY_BYTES',32*1024**2), \
             contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
            code=cli.main(['--instance',str(instance),'validation','repository-inspect','--assessment',operation,'--bounded-worker'])
        self.assertEqual(code,2);self.assertEqual(stdout.getvalue(),'')
        self.assertEqual(json.loads(stderr.getvalue()),{'execution':'error','diagnostics':['repository_replay_worker_resident_budget']})
        self.assertEqual(context.inspect(operation),expected)

    def test_worker_messages_cannot_select_another_root_or_promote_authority(self):
        header=self.header()
        packet={'schema_version':1,'profile':protocol.PROFILE,'record_root':str(self.operation),'binding':header}
        self.assertEqual(protocol.request(packet),packet)
        for changed in ({**packet,'record_root':str(self.operation/'..')},
                        {**packet,'program':'/caller/code.py'},
                        {**packet,'binding':{**header,'official_acceptance':True}},
                        {**packet,'profile':'unregistered'}):
            with self.subTest(keys=list(changed)),self.assertRaises(ValueError):protocol.request(changed)


if __name__=='__main__':unittest.main()
