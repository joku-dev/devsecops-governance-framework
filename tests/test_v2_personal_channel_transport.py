"""Actual fixed GET/Git subprocess bytes, original diagnostics and no-process replay."""
from pathlib import Path
from unittest.mock import patch
import base64,copy,hashlib,json,os,signal,subprocess,sys,tempfile,time,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.providers.personal_channel_protocol import LegacyPersonalProtocol,CAPTURES
from lib.providers.personal_channel_transport import NativePersonalTransport
from lib.providers.personal_channel_process import NativeReadProcess
from lib.personal_channel_process import ReplayPersonalTransport,clock_value,MAX_STDOUT
from lib.synthetic_lifecycle_io import ReplayIO
from lib.requirement_review_output import RetainedOutputError
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
import test_v2_personal_channel_programs as original

ENDPOINT='repos/owner/repo/issues/87'

class WholeReadTransport(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old)
        fixture=original.WholePersonalChannelPrograms();fixture.setUp();self.addCleanup(fixture.doCleanups);self.data,_,_=fixture.fixture();self.parent=self.data.parent;self.serial=0
    def owner(self):
        self.serial+=1;private=self.parent/('transport-state-'+str(self.serial));private.mkdir(mode=0o700)
        record=Record(private/'records',{'prototype':'whole read transport'},{'prototype':True});record.append({'kind':'execution-intent'})
        owner=NativeIO(record,mode='private-candidate',cwd=str(self.data),private_state=private,product_root=ROOT)
        return record,owner
    def tool(self,kind,stdout=b'opaque\x00\xffstdout',stderr=b'raw\xff\x00stderr\r\n',exit=0):
        self.serial+=1;tools=self.parent/('read-tools-'+str(self.serial));tools.mkdir(mode=0o700)
        code='''import base64,json,os,signal,sys
from pathlib import Path
c=json.loads((Path(__file__).parent/'config.json').read_bytes())
assert sys.argv[1:6]==['api','--hostname','github.com','--method','GET'] if c['kind']=='get' else sys.argv[1:][-7:][:4]==['ls-tree','-r','--name-only','HEAD'] or sys.argv[1:][-6:][:3]==['ls-tree','-r','--name-only']
sys.stdout.buffer.write(base64.b64decode(c['stdout']));sys.stdout.buffer.flush()
sys.stderr.buffer.write(base64.b64decode(c['stderr']));sys.stderr.buffer.flush()
if c['exit']<0:os.kill(os.getpid(),-c['exit'])
raise SystemExit(c['exit'])
'''
        name='gh' if kind=='get' else 'git';path=tools/name;path.write_text('#!'+sys.executable+'\n'+code);path.chmod(0o700)
        (tools/'config.json').write_text(json.dumps({'kind':kind,'stdout':base64.b64encode(stdout).decode(),'stderr':base64.b64encode(stderr).decode(),'exit':exit}))
        return tools
    def compare(self,kind,*,out=b'opaque\x00\xffstdout',err=b'raw\xff\x00stderr\r\n',exit=0):
        tools=self.tool(kind,out,err,exit);environment={**os.environ,'PATH':str(tools)+os.pathsep+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1'}
        code="from lib.governance_lifecycle.live_evidence import github_get;import sys;sys.stdout.buffer.write(github_get("+repr(ENDPOINT)+"))" if kind=='get' else "import subprocess,sys;sys.stdout.write(subprocess.check_output(['git','ls-tree','-r','--name-only','HEAD','--',"+repr(CAPTURES)+"],text=True))"
        old=subprocess.run([sys.executable,'-B','-c',code],cwd=self.data,env={**environment,'PYTHONPATH':str(self.data/'scripts')},capture_output=True,timeout=120)
        record,owner=self.owner();parts=[];profile=LegacyPersonalProtocol();transport=NativePersonalTransport(owner,self.data,profile,emit_stderr=parts.append,environment=environment)
        actual=None;error=None
        try:actual=transport.fetch(ENDPOINT) if kind=='get' else transport.check_output(['git','ls-tree','-r','--name-only','HEAD','--',CAPTURES],cwd=self.data,text=True)
        except RetainedOutputError as caught:error={'type':caught.original_type,'message':caught.original_message}
        except UnicodeError as caught:error={'type':type(caught).__name__,'message':str(caught)}
        if old.returncode==0:self.assertIsNone(error);self.assertEqual(actual if type(actual) is bytes else actual.encode(),old.stdout);self.assertEqual(err,old.stderr)
        else:
            self.assertIsNotNone(error);self.assertTrue(old.stderr.endswith((error['type']+': '+error['message']+'\n').encode()),(error,old.stderr[-2000:]));self.assertTrue(old.stderr.startswith(err))
        native_err=b''.join((record.blobs/ref['sha256']).read_bytes() for ref in parts);self.assertEqual(native_err,err);self.assertFalse(record.capture_incomplete)
        at=transport.clock();self.assertEqual(clock_value({'schema_version':1,'clock':'UTC-seconds','value':at}),at)
        record.finish('complete',{'exit_code':1 if error else 0,'error':error,'value_base64':None if actual is None else base64.b64encode(actual if type(actual) is bytes else actual.encode()).decode()},owner.touched)
        _,_,value,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
        def inert(ref):
            raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return raw
        import shutil
        shutil.rmtree(self.data)
        replay=ReplayIO(events,inert,'private-candidate',str(self.data));emitted=[];port=ReplayPersonalTransport(replay,self.data,profile,emit_stderr=emitted.append);replayed=None;replay_error=None
        with patch('subprocess.Popen',side_effect=AssertionError('No native program')),patch('os.open',side_effect=AssertionError('No native open')),patch('lib.providers.personal_channel_transport.datetime',side_effect=AssertionError('No native clock')):
            try:replayed=port.fetch(ENDPOINT) if kind=='get' else port.check_output(['git','ls-tree','-r','--name-only','HEAD','--',CAPTURES],cwd=self.data,text=True)
            except RetainedOutputError as caught:replay_error={'type':caught.original_type,'message':caught.original_message}
            except UnicodeError as caught:replay_error={'type':type(caught).__name__,'message':str(caught)}
            self.assertEqual(port.clock(),at);replay.finish()
        self.assertEqual(replay_error,error);self.assertEqual(replayed,actual);self.assertEqual(emitted,parts);self.assertEqual(seen,set(cache))
        for sha in seen:blob({'sha256':sha,'bytes':len(cache[sha])})
        self.assertTrue(closed());return events,cache

    def test_original_fixed_get_binary_bytes_and_raw_stderr_are_retained_and_replayed(self):self.compare('get')
    def test_original_nonzero_get_exception_preserves_preceding_raw_stderr(self):self.compare('get',exit=7)
    def test_original_signal_get_diagnostic_is_bound_to_producer_runtime(self):self.compare('get',exit=-signal.SIGTERM)
    def test_original_git_text_universal_newlines_and_raw_stderr_remain_distinct(self):
        from lib.personal_channel_process import process_value
        events,cache=self.compare('git-tree',out=b'first\r\nsecond\rthird\n',err=b'git\xffstderr\r\n')
        returned=next(row for row in events if row.get('kind')=='returned');wire=json.loads(cache[returned['value']['sha256']]);spec=wire['specification']
        wire['observation']['timed_out']=True
        wire['original_error']={'type':'TimeoutExpired','message':f"Command '{spec['original_arguments']}' timed out after {spec['timeout']} seconds"}
        with self.assertRaises(IntegrityError):process_value(wire,spec,LegacyPersonalProtocol(),lambda ref:cache[ref['sha256']],emit_stderr=lambda ref:self.fail('No raw output from an inadmissible Git timeout verdict'))
    def test_original_git_stdout_decode_error_precedes_nonzero_exit_error(self):self.compare('git-tree',out=b'\xffnot-UTF8',exit=7)

    def test_invalid_or_nonread_requests_fail_before_any_process(self):
        record,owner=self.owner();port=NativePersonalTransport(owner,self.data,LegacyPersonalProtocol(),emit_stderr=lambda ref:None)
        with patch('subprocess.Popen',side_effect=AssertionError('No program')):
            for endpoint in ['https://example.invalid/data','repos/owner/repo/issues/87/comments?per_page=100&page=11','repos/owner/repo/issues/87 --method POST']:
                with self.assertRaises(InputAdmissionError):port.fetch(endpoint)
        self.assertTrue(record.capture_incomplete)

    def test_stdout_budget_exhaustion_is_incomplete_without_original_verdict(self):
        tools=self.tool('get',stdout=b'x'*(MAX_STDOUT+1),stderr=b'');record,owner=self.owner();port=NativePersonalTransport(owner,self.data,LegacyPersonalProtocol(),emit_stderr=lambda ref:None,environment={**os.environ,'PATH':str(tools)})
        with self.assertRaises(InputAdmissionError):port.fetch(ENDPOINT)
        self.assertTrue(record.capture_incomplete)

    def test_real_low_level_timeout_observes_termination_and_retains_partial_pipes(self):
        process=NativeReadProcess();code,out,err=process.run([sys.executable,'-B','-c',"import sys,time;sys.stdout.buffer.write(b'prefix');sys.stdout.flush();sys.stderr.buffer.write(b'error');sys.stderr.flush();time.sleep(5)"],str(self.data),dict(os.environ),.15)
        self.assertTrue(process.observation['timed_out']);self.assertTrue(process.observation['terminal_observed']);self.assertLess(code,0);self.assertEqual(out,b'prefix');self.assertEqual(err,b'error')

    def test_original_timeout_starts_after_process_creation_even_when_constructor_is_slow(self):
        popen=subprocess.Popen
        def delayed(*args,**kwargs):time.sleep(.25);return popen(*args,**kwargs)
        command=[sys.executable,'-B','-c',"import time;print('whole original output',flush=True);time.sleep(.03)"]
        with patch('subprocess.Popen',delayed):
            expected=subprocess.check_output(command,timeout=.15)
            process=NativeReadProcess();code,out,err=process.run(command,str(self.data),dict(os.environ),.15)
        self.assertEqual(code,0);self.assertFalse(process.observation['timed_out']);self.assertEqual(out,expected);self.assertEqual(err,b'')

    def test_finite_git_observation_deadline_is_incomplete_without_an_original_timeout_verdict(self):
        tools=self.tool('git-tree',stdout=b'',stderr=b'');program=tools/'git'
        program.write_text('#!'+sys.executable+'\nimport time\ntime.sleep(5)\n');program.chmod(0o700)
        record,owner=self.owner();port=NativePersonalTransport(owner,self.data,LegacyPersonalProtocol(),emit_stderr=lambda ref:None,environment={**os.environ,'PATH':str(tools)+os.pathsep+os.environ['PATH']})
        case=self
        class ControlledCaptureDeadline(NativeReadProcess):
            def run(self,arguments,cwd,environment,timeout):
                case.assertEqual(timeout,90)
                # A deliberately shorter native capture budget makes the
                # production deadline classification observable in this test.
                return super().run(arguments,cwd,environment,.15)
        port.process_factory=ControlledCaptureDeadline
        with self.assertRaises(InputAdmissionError):port.check_output(['git','ls-tree','-r','--name-only','HEAD','--',CAPTURES],cwd=self.data,text=True)
        self.assertTrue(record.capture_incomplete)

    def test_missing_default_provider_keeps_original_file_not_found_and_replays_without_program_lookup(self):
        environment={**os.environ,'PATH':str(self.parent/'no-programs')}
        old=subprocess.run([sys.executable,'-B','-c',"from lib.governance_lifecycle.live_evidence import github_get;github_get("+repr(ENDPOINT)+")"],cwd=self.data,env={**environment,'PYTHONPATH':str(self.data/'scripts')},capture_output=True)
        record,owner=self.owner();port=NativePersonalTransport(owner,self.data,LegacyPersonalProtocol(),emit_stderr=lambda ref:self.fail('No stderr before program starts'),environment=environment)
        with self.assertRaises(RetainedOutputError) as caught:port.fetch(ENDPOINT)
        self.assertEqual(caught.exception.original_type,'FileNotFoundError');self.assertTrue(old.stderr.endswith(('FileNotFoundError: '+caught.exception.original_message+'\n').encode()))
        self.assertFalse(record.capture_incomplete);record.finish('complete',{'exit_code':1},owner.touched)
        _,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
        def inert(ref):
            raw=cache[ref['sha256']];self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);self.assertEqual(len(raw),ref['bytes']);seen.add(ref['sha256']);return raw
        import shutil
        shutil.rmtree(self.data)
        replay=ReplayIO(events,inert,'private-candidate',str(self.data));port=ReplayPersonalTransport(replay,self.data,LegacyPersonalProtocol(),emit_stderr=lambda ref:self.fail('No stderr'))
        with patch('subprocess.Popen',side_effect=AssertionError('No program lookup or execution')),patch('os.open',side_effect=AssertionError('No native input')):
            with self.assertRaises(RetainedOutputError) as replayed:port.fetch(ENDPOINT)
            replay.finish()
        self.assertEqual(replayed.exception.original_message,caught.exception.original_message);self.assertEqual(seen,set(cache))
        for sha in seen:blob({'sha256':sha,'bytes':len(cache[sha])})
        self.assertTrue(closed())

    def test_real_local_git_tree_output_matches_original_and_creates_no_new_repository_files(self):
        import shutil
        git=shutil.which('git');self.assertIsNotNone(git)
        def run(*args):return subprocess.run([git,'-C',str(self.data),*args],check=True,capture_output=True)
        run('init','--initial-branch=fixture');run('add','--all')
        run('-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null','-c','user.name=AXIOM isolated original test','-c','user.email=fixture@invalid.example','commit','--quiet','-m','Private read-only transport fixture')
        before=original.snapshot(self.data);command=['git','ls-tree','-r','--name-only','HEAD','--',CAPTURES]
        expected=subprocess.check_output(command,cwd=self.data,text=True)
        record,owner=self.owner();stderr=[];port=NativePersonalTransport(owner,self.data,LegacyPersonalProtocol(),emit_stderr=stderr.append)
        self.assertEqual(port.check_output(command,cwd=self.data,text=True),expected)
        self.assertEqual(stderr,[]);self.assertFalse(record.capture_incomplete);self.assertEqual(original.snapshot(self.data),before)

    def test_resealed_process_semantic_mutations_and_noncanonical_clock_are_rejected(self):
        from lib.personal_channel_process import process_value
        events,cache=self.compare('get',out=b'whole response',err=b'')
        returned=next(row for row in events if row.get('kind')=='returned')
        wire=json.loads(cache[returned['value']['sha256']]);spec=wire['specification'];profile=LegacyPersonalProtocol()
        def blob(ref):
            raw=cache[ref['sha256']];self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);self.assertEqual(len(raw),ref['bytes']);return raw
        changes=[lambda w:w['source_after']['identity'].__setitem__(1,w['source_after']['identity'][1]+1),
                 lambda w:w['actual_arguments'].append('--method=POST'),
                 lambda w:w['observation'].__setitem__('OS_network_or_process_tree_isolation_attested',True),
                 lambda w:w['observation'].__setitem__('terminal_observed',False),
                 lambda w:w.__setitem__('returncode',7),
                 lambda w:w.__setitem__('original_error',{'type':'CalledProcessError','message':'invented'}),
                 lambda w:w['program'].__setitem__('resolved',spec['source_root']+'/tool'),
                 lambda w:w.__setitem__('effective_encoding','utf-8'),
                 lambda w:w['stdout'].__setitem__('bytes',True)]
        with patch('subprocess.Popen',side_effect=AssertionError('No native process')),patch('os.open',side_effect=AssertionError('No native source')):
            for index,change in enumerate(changes):
                with self.subTest(index=index):
                    bad=copy.deepcopy(wire);change(bad)
                    with self.assertRaises(IntegrityError):process_value(bad,spec,profile,blob,emit_stderr=lambda ref:None)
            for value in ('2026-02-30T12:00:00Z','2026-11-15T12:00:00+00:00','2026-11-15T12:00:00.000Z'):
                with self.subTest(clock=value):
                    with self.assertRaises(IntegrityError):clock_value({'schema_version':1,'clock':'UTC-seconds','value':value})

if __name__=='__main__':unittest.main(verbosity=2)
