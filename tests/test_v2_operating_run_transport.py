"""Original binary run result semantics, including nonzero/signal and closed replay."""
from pathlib import Path
from unittest.mock import patch
import base64,copy,hashlib,json,os,shutil,signal,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_personal_channel_transport as fixture
from lib.providers.operating_verification_protocol import NativeOperatingVerificationTransport,ReplayOperatingVerificationTransport,LegacyOperatingVerificationProtocol,INDEX
from lib.providers.personal_channel_process import NativeReadProcess
from lib.personal_channel_process import process_value
from lib.synthetic_lifecycle_io import ReplayIO
from lib.providers.synthetic_lifecycle_storage import read_record
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError

class OperatingRunTransport(unittest.TestCase):
    def setUp(self):
        c=fixture.WholeReadTransport();c.setUp();self.addCleanup(c.doCleanups);self.fixture=c

    def tool(self,code=0,*,sleep=False):
        tools=self.fixture.tool('git-tree',b'opaque\xff\x00stdout\r\n',b'captured\xff\x00stderr\r\n',code)
        p=tools/'git';raw=p.read_text();a=raw.index('assert sys.argv');z=raw.index('\nsys.stdout',a);raw=raw[:a]+"assert sys.argv[1:][-2:]==['show','HEAD:status/governance-lifecycle-live.json']"+raw[z:]
        if sleep:raw=raw.replace('sys.stdout.buffer.write','import time;time.sleep(10)\nsys.stdout.buffer.write',1)
        p.write_text(raw);return tools

    def compare(self,code=0):
        tools=self.tool(code);root=self.fixture.data;env={**os.environ,'PATH':str(tools)+os.pathsep+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1'};command=['git','show','HEAD:'+INDEX]
        expected=subprocess.run(command,cwd=root,env=env,capture_output=True)
        self.assertEqual(expected.returncode,code)
        record,owner=self.fixture.owner();emitted=[];port=NativeOperatingVerificationTransport(owner,root,emit_stderr=emitted.append,environment=env)
        actual=port.run(command,cwd=root,capture_output=True)
        self.assertEqual((actual.args,actual.returncode,actual.stdout,actual.stderr),(expected.args,expected.returncode,expected.stdout,expected.stderr));self.assertEqual(emitted,[]);self.assertFalse(record.capture_incomplete)
        record.finish('complete',{'exit_code':0,'original_returncode':actual.returncode},owner.touched)
        _,_,_,events,blob,closed=read_record(record.root);wire=json.loads(blob(events[3]['value']))
        self.assertIsNone(wire['original_error']);self.assertIsNone(wire['signal_context']);self.assertIsNone(wire['effective_encoding'])
        cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
        def inert(ref):raw=cache[ref['sha256']];self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);self.assertEqual(len(raw),ref['bytes']);seen.add(ref['sha256']);return raw
        shutil.rmtree(root);shutil.rmtree(tools);replay=ReplayIO(events,inert,'private-candidate',str(root));parts=[];pure=ReplayOperatingVerificationTransport(replay,root,emit_stderr=parts.append)
        with patch('os.open',side_effect=AssertionError('No selected input')),patch('subprocess.Popen',side_effect=AssertionError('No program')):
            result=pure.run(command,cwd=root,capture_output=True);replay.finish()
        self.assertEqual(vars(result),vars(actual));self.assertEqual(parts,[]);self.assertEqual(seen,set(cache))
        for name,raw in cache.items():blob({'sha256':name,'bytes':len(raw)})
        self.assertTrue(closed());return wire,cache

    def test_binary_run_preserves_zero_nonzero_and_negative_status_without_raising_or_emitting_stderr(self):
        for code in (0,7,-signal.SIGTERM):
            with self.subTest(code=code):self.setUp();self.compare(code)

    def test_resealed_run_error_status_text_and_authority_attacks_fail_closed(self):
        wire,cache=self.compare(7);profile=LegacyOperatingVerificationProtocol();spec=wire['specification']
        for mutate in (lambda w:w.update(original_error={'type':'CalledProcessError','message':'fabricated'}),lambda w:w.update(returncode=True),lambda w:w.update(effective_encoding='utf-8'),lambda w:w.update(signal_context={'system':'Linux'}),lambda w:w['observation'].update(timed_out=True),lambda w:w['observation'].update(OS_network_or_process_tree_isolation_attested=True),lambda w:w['observation'].update(returncode=0)):
            bad=copy.deepcopy(wire);mutate(bad)
            with self.assertRaises(IntegrityError):process_value(bad,spec,profile,lambda ref:cache[ref['sha256']],emit_stderr=lambda ref:self.fail('Captured run stderr is not inherited'))

    def test_finite_run_capture_deadline_is_incomplete_without_original_timeout_verdict(self):
        tools=self.tool(sleep=True);record,owner=self.fixture.owner();env={**os.environ,'PATH':str(tools)+os.pathsep+os.environ['PATH']};port=NativeOperatingVerificationTransport(owner,self.fixture.data,emit_stderr=lambda ref:self.fail('No inherited stderr'),environment=env)
        class ShortRead(NativeReadProcess):
            def run(self,args,cwd,environment,timeout):return super().run(args,cwd,environment,.03)
        port.process_factory=ShortRead
        with self.assertRaisesRegex(InputAdmissionError,'deadline'):port.run(['git','show','HEAD:'+INDEX],cwd=self.fixture.data,capture_output=True)
        self.assertTrue(record.capture_incomplete)

    def test_missing_Git_run_program_preserves_original_start_error_and_pure_replay(self):
        tools=self.tool();(tools/'git').unlink();record,owner=self.fixture.owner();root=self.fixture.data;env={**os.environ,'PATH':str(tools)};command=['git','show','HEAD:'+INDEX]
        with self.assertRaises(FileNotFoundError) as original:subprocess.run(command,cwd=root,env=env,capture_output=True)
        port=NativeOperatingVerificationTransport(owner,root,emit_stderr=lambda ref:self.fail('No inherited stderr'),environment=env)
        with self.assertRaises(RetainedOutputError) as observed:port.run(command,cwd=root,capture_output=True)
        self.assertEqual(observed.exception.original_type,type(original.exception).__name__);self.assertEqual(observed.exception.original_message,str(original.exception));self.assertFalse(record.capture_incomplete)
        record.finish('complete',{'exit_code':1,'prototype':'original start diagnostic'},owner.touched);_,_,_,events,blob,_=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()}
        shutil.rmtree(root);replay=ReplayIO(events,lambda ref:cache[ref['sha256']],'private-candidate',str(root));pure=ReplayOperatingVerificationTransport(replay,root,emit_stderr=lambda ref:self.fail('No inherited stderr'))
        with patch('os.open',side_effect=AssertionError('No input')),patch('subprocess.Popen',side_effect=AssertionError('No lookup')):
            with self.assertRaises(RetainedOutputError) as saved:pure.run(command,cwd=root,capture_output=True)
            replay.finish()
        self.assertEqual(saved.exception.original_type,observed.exception.original_type);self.assertEqual(saved.exception.original_message,observed.exception.original_message)
