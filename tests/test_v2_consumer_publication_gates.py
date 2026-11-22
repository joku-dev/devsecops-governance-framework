"""Actual complete consumer gate vs original, with closed source-free replay."""
from pathlib import Path
from contextlib import redirect_stdout,redirect_stderr
from datetime import datetime as NativeDatetime
from unittest.mock import patch
import hashlib,io,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.providers.consumer_publication_gates import gates,release
from lib.providers.consumer_lifecycle_io import NativeConsumerIO
from lib.consumer_lifecycle_io import ReplayConsumerIO
from lib.providers.consumer_lifecycle_storage import Record,read_record,encode
from lib.synthetic_lifecycle_application import closed_validator
from lib.personal_channel_context import OrderedStderr
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError
from test_v2_consumer_lifecycle_io import transaction_name
from test_v2_consumer_lifecycle_execution import FixedClock
from test_v2_synthetic_ledger_core import snapshot
from test_portable_runtime import OPA
import test_v2_consumer_lifecycle_program as reference

WRAPPER=reference.WRAPPER[:reference.WRAPPER.index('path=sys.argv[1]')]+r'''
from pathlib import Path
import json
from lib.governance_lifecycle.consumer_acceptance import validate_publication
value=validate_publication(Path(sys.argv[1]),sys.argv[2])
print(json.dumps(value,sort_keys=True))
'''


class WholeConsumerPublicationGates(unittest.TestCase):
    def setUp(self):
        self.fixture=reference.WholeConsumerProgram();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups);self.source=self.fixture.root;self.parent=self.fixture.parent
        self.environment={**os.environ,'PYTHONPATH':str(self.source/'scripts'),'PATH':str(self.fixture.tools)+os.pathsep+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null','GIT_CONFIG_NOSYSTEM':'1'}
        def git(*args):return subprocess.check_output(['git','-c','core.hooksPath=/dev/null',*args],cwd=self.source,env=self.environment,stderr=subprocess.PIPE)
        git('init','--initial-branch=main');git('add','--all');git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-qm','Explicit immutable consumer acceptance fixture');self.base=git('rev-parse','HEAD').decode().strip()
    def compare(self,kind='normal',mode='private-candidate'):
        if kind=='rewritten-prefix':
            name=self.source/'model/governance/lifecycle/consumer-operation/acceptance.json';name.write_bytes(name.read_bytes()+b'\n')
        before=snapshot(self.source);calls=self.fixture.tools/'calls.jsonl';calls.unlink(missing_ok=True)
        old=subprocess.run([sys.executable,'-B','-c',WRAPPER,str(self.source),self.base],cwd=self.source,env=self.environment,capture_output=True,timeout=240);expected_calls=calls.read_bytes() if calls.exists() else b'';calls.unlink(missing_ok=True)
        private=self.parent/'gate-state';private.mkdir(mode=0o700);temporary=self.parent/'gate-temporary';temporary.mkdir(mode=0o700);workarea=private/'opa-workarea';workarea.mkdir(mode=0o700);record=Record(private/'records',{'prototype':'whole consumer publication gate'},{'prototype':True});record.append({'kind':'execution-intent'});owner=NativeConsumerIO(record,mode=mode,cwd=str(self.source),private_state=private,product_root=ROOT,source=str(self.source),transaction_name=transaction_name)
        hashes=frozenset({hashlib.sha256(OPA.read_bytes()).hexdigest()})
        def run(io):
            err=OrderedStderr();value=error=None;gate=gates(str(self.source),str(self.source),io,validator_class=closed_validator(io,{'resources':[]}),provider_executable=str(self.fixture.tools/'gh'),temporary_parent=str(temporary),emit_stderr=err.emit_raw,environment=self.environment,opa_tool=str(OPA),approved_opa_hashes=hashes,opa_workarea=str(workarea))
            try:
                try:value=gate.validate_publication(str(self.source),self.base)
                except (InputAdmissionError,IntegrityError):raise
                except RetainedOutputError as caught:error={'type':caught.original_type,'message':caught.original_message}
                except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
            finally:release(io)
            return {'exit_code':1 if error is not None else 0,'value':value,'error':error,'stderr':err.getvalue(),'stderr_parts':err.parts}
        with patch('lib.providers.personal_channel_transport.datetime',FixedClock):actual=run(owner)
        if actual['error'] is None:self.assertEqual(old.returncode,0,old.stderr[-3000:]);self.assertEqual(json.loads(old.stdout),actual['value']);self.assertEqual(old.stderr,b'')
        else:self.assertEqual(old.returncode,1);self.assertTrue(old.stderr.decode().endswith(actual['error']['type']+': '+actual['error']['message']+'\n'),(old.stderr[-3000:],actual['error']))
        self.assertEqual(calls.read_bytes() if calls.exists() else b'',expected_calls);self.assertEqual(snapshot(self.source),before);self.assertEqual(list(temporary.iterdir()),[]);self.assertEqual(list(workarea.iterdir()),[])
        record.finish('complete',actual,owner.touched);_,_,retained,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()}
        shutil.rmtree(self.source);shutil.rmtree(self.fixture.tools);shutil.rmtree(temporary);shutil.rmtree(workarea)
        pure=ReplayConsumerIO(events,lambda ref:cache[ref['sha256']],mode,str(self.source),source=str(self.source),transaction_name=transaction_name)
        with patch('subprocess.Popen',side_effect=AssertionError('No Git/provider/OPA')),patch('os.open',side_effect=AssertionError('No native source or output')),patch('lib.providers.personal_channel_transport.datetime',side_effect=AssertionError('No current clock')):again=run(pure);pure.finish()
        self.assertEqual(encode(again),encode(retained['result']));self.assertEqual(pure.touched,retained['touched_files'])
        for name,raw in cache.items():self.assertEqual(blob({'sha256':name,'bytes':len(raw)}),raw)
        self.assertTrue(closed());return actual
    def test_complete_original_consumer_acceptance_gate_and_replay_private_mode(self):self.assertIsNone(self.compare()['error'])
    def test_complete_original_consumer_acceptance_gate_and_replay_native_mode(self):self.assertIsNone(self.compare(mode='selected-files')['error'])
    def test_rewritten_accepted_consumer_prefix_keeps_original_failure_before_publication(self):self.assertEqual(self.compare('rewritten-prefix')['error']['type'],'ContractError')
