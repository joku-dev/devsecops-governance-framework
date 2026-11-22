"""Whole original consumer runner, shared effects and source-free reconstruction."""
from pathlib import Path
from datetime import datetime as NativeDatetime
import copy,hashlib,json,os,shutil,subprocess,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.providers.consumer_lifecycle_execution import execute
from lib.providers.consumer_lifecycle_io import NativeConsumerIO
from lib.consumer_lifecycle_io import ReplayConsumerIO
from lib.providers.consumer_lifecycle_storage import Record,read_record,encode
from lib.synthetic_lifecycle_application import closed_validator
from lib.providers.retained_argparse import capture_context
from lib.synthetic_lifecycle_application import result_value
from lib.requirement_validation_budget import InputAdmissionError
import test_v2_consumer_lifecycle_program as reference
from test_v2_synthetic_ledger_core import snapshot,restore
from test_portable_runtime import OPA
from test_v2_consumer_lifecycle_io import transaction_name

class FixedClock:
    @staticmethod
    def now(zone):return NativeDatetime.fromisoformat('2026-11-15T12:00:00+00:00').astimezone(zone)


class WholeConsumerExecution(unittest.TestCase):
    def setUp(self):
        self.fixture=reference.WholeConsumerProgram();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups);self.source=self.fixture.root;self.parent=self.fixture.parent;self.serial=0
    def compare(self,args,mode='private-candidate',expected=0):
        self.serial+=1;before=snapshot(self.source);calls=self.fixture.tools/'calls.jsonl';calls.unlink(missing_ok=True)
        environment={**os.environ,'PYTHONPATH':str(self.source/'scripts'),'PATH':str(self.fixture.tools)+os.pathsep+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':'60','LINES':'24'}
        environment.update(getattr(self,'environment_extra',{}));at=getattr(self,'at',reference.AT)
        wrapper=reference.WRAPPER.replace('2026-11-15T12:00:00+00:00',at.replace('Z','+00:00'))
        old=subprocess.run([sys.executable,'-B','-c',wrapper,str(self.source/'scripts/run_consumer_lifecycle.py'),*args],cwd=self.source,capture_output=True,timeout=240,env=environment);self.assertEqual(old.returncode,expected,old.stderr[-4000:]);after=snapshot(self.source);queries=calls.read_bytes() if calls.exists() else b'';restore(self.source,before);calls.unlink(missing_ok=True)
        private=self.parent/f'execution-state-{self.serial}';private.mkdir(mode=0o700);workarea=private/'opa-workarea';workarea.mkdir(mode=0o700);temporary=self.parent/f'execution-temporary-{self.serial}';temporary.mkdir(mode=0o700);record=Record(private/'records',{'prototype':'complete consumer runner','mode':mode},{'prototype':True});record.append({'kind':'execution-intent'});owner=NativeConsumerIO(record,mode=mode,cwd=str(self.source),private_state=private,product_root=ROOT,source=str(self.source),transaction_name=transaction_name)
        with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}):parser=capture_context()
        hashes=frozenset({hashlib.sha256(OPA.read_bytes()).hexdigest()})
        def run(io):return execute(str(self.source),str(self.source),args,io,validator_class=closed_validator(io,{'resources':[]}),parser_context=parser,provider_executable=str(self.fixture.tools/'gh'),temporary_parent=str(temporary),opa_tool=str(OPA),approved_opa_hashes=hashes,opa_workarea=str(workarea),environment=environment)
        class Clock:
            @staticmethod
            def now(zone):return NativeDatetime.fromisoformat(at.replace('Z','+00:00')).astimezone(zone)
        with patch('lib.providers.personal_channel_transport.datetime',Clock):kernel=run(owner)
        self.assertEqual(kernel['exit_code'],expected,kernel);self.assertEqual(kernel['stdout'].encode(),old.stdout)
        if kernel['kernel_exception'] is None:
            raw=b''.join((record.blobs/part['blob']['sha256']).read_bytes() if 'blob' in part else part['text'].encode() for part in kernel['stderr_parts'])
            self.assertEqual(raw,old.stderr)
        else:
            error=kernel['kernel_exception'];self.assertTrue(old.stderr.decode().endswith(error['type']+': '+error['message']+'\n'),(kernel,old.stderr[-4000:]))
        self.assertEqual(calls.read_bytes() if calls.exists() else b'',queries)
        if mode=='selected-files':actual=snapshot(self.source)
        else:
            self.assertEqual(snapshot(self.source),before);files,dirs=copy.deepcopy(before)
            for name,node in owner.projected_changes.items():
                path=Path(name)
                if not path.is_relative_to(self.source):continue
                relative=path.relative_to(self.source).as_posix()
                if node['kind']=='file':files[relative]=((record.blobs/node['content']['sha256']).read_bytes(),node['mode'])
                elif node['kind']=='directory':dirs[relative]=node['mode']
                elif node['kind']=='missing':files.pop(relative,None);dirs.pop(relative,None)
                else:self.fail('Unknown original projected node')
            actual=files,dirs
        changed=[name for name in set(actual[0])|set(after[0]) if actual[0].get(name)!=after[0].get(name)];self.assertEqual(changed,[]);self.assertEqual(actual[1],after[1]);self.assertEqual(list(temporary.iterdir()),[]);self.assertEqual(list(workarea.iterdir()),[])
        result=result_value(kernel,owner);record.finish('complete',result,owner.touched);_,_,retained,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()}
        shutil.rmtree(self.source);shutil.rmtree(self.fixture.tools);shutil.rmtree(temporary);shutil.rmtree(workarea)
        replay=ReplayConsumerIO(events,lambda ref:cache[ref['sha256']],mode,str(self.source),source=str(self.source),transaction_name=transaction_name)
        with patch('subprocess.Popen',side_effect=AssertionError('No process')),patch('os.open',side_effect=AssertionError('No selected/native inputs or writes')),patch('lib.providers.personal_channel_transport.datetime',side_effect=AssertionError('No current clock')):
            again=run(replay);replay.finish()
        self.assertEqual(encode(result_value(again,replay)),encode(retained['result']));self.assertEqual(replay.touched,retained['touched_files'])
        for name,raw in cache.items():self.assertEqual(blob({'sha256':name,'bytes':len(raw)}),raw)
        self.assertTrue(closed());return kernel
    def test_full_validate_history_policy_and_model_replay_in_both_modes(self):
        for mode in ('private-candidate','selected-files'):
            with self.subTest(mode=mode):
                if self.serial or not self.source.exists():self.fixture.doCleanups();self.setUp()
                self.compare(['--operation','validate'],mode)
    def test_help_and_parser_errors_require_no_consumer_model_policy_or_provider(self):
        shutil.rmtree(self.source/'model')
        self.compare(['--help'])
    def test_acceptance_capture_and_refresh_preserve_whole_outputs_in_both_modes(self):
        for operation in ('acceptance','refresh'):
            for mode in ('private-candidate','selected-files'):
                with self.subTest(operation=operation,mode=mode):
                    if self.serial or not self.source.exists():self.fixture.doCleanups();self.setUp()
                    self.compare(['--operation',operation],mode)
    def test_preflight_captures_all_provider_bytes_and_replays_without_gets_or_opa(self):
        self.fixture.responses=reference.provider_responses(self.source,'34778861076');(self.fixture.tools/'responses.json').write_text(json.dumps(self.fixture.responses))
        self.compare(['--operation','preflight','--source-run-id','34778861076','--output',str(self.source/'generated/reports/consumer-lifecycle-preflight/controlled-new')])
    def test_prepare_acceptance_preserves_request_manifest_and_inactive_output(self):
        (self.source/'model/governance/lifecycle/consumer-operation/acceptance.json').unlink();shutil.rmtree(self.source/'governance/consumer-lifecycle/acceptance')
        result=self.compare(['--operation','prepare-acceptance','--discussion-number','900001']);self.assertEqual(result['exit_code'],0)
    def test_observe_new_eligible_receipt_from_an_explicit_historical_prefix_both_modes(self):
        for mode in ('private-candidate','selected-files'):
            with self.subTest(mode=mode):
                if self.serial or not self.source.exists():self.fixture.doCleanups();self.setUp()
                self.at='2026-10-03T10:58:04Z'
                for ledger,n in [('observations',3),('actions',4)]:
                    paths=list((self.source/'governance/consumer-lifecycle'/ledger/'transactions').glob(f'{n:08d}-*.json'));self.assertEqual(len(paths),1);paths[0].unlink()
                self.compare(['--operation','observe','--source-run-id','37113784702'],mode)
    def test_action_new_personally_bound_closure_from_historical_prefix_both_modes(self):
        for mode in ('private-candidate','selected-files'):
            with self.subTest(mode=mode):
                if self.serial or not self.source.exists():self.fixture.doCleanups();self.setUp()
                self.at='2026-10-03T10:58:04Z'
                path=next((self.source/'governance/consumer-lifecycle/actions/transactions').glob('00000004-*.json'));path.unlink()
                for args in (['init','-q'],['add','--','model/governance/lifecycle/consumer-operation/action-requests/00000004.json']):subprocess.run(['git',*args],cwd=self.source,check=True,capture_output=True)
                self.compare(['--operation','action','--request-path','model/governance/lifecycle/consumer-operation/action-requests/00000004.json'],mode)
    def test_personal_and_guard_reads_keep_original_token_while_evidence_uses_separate_read_token(self):
        self.environment_extra={'GH_TOKEN':'publisher-fixture','CONSUMER_EVIDENCE_TOKEN':'reader-fixture'}
        tool=self.fixture.tools/'gh';code=tool.read_text();anchor="sys.stdout.buffer.write("
        assert anchor in code
        assertion="import os\npersonal=('/issues/' in args[5] or args[5].endswith('/rules/branches/main'))\nassert os.environ['GH_TOKEN']==('publisher-fixture' if personal else 'reader-fixture')\n"
        tool.write_text(code.replace(anchor,assertion+anchor));tool.chmod(0o700)
        self.compare(['--operation','observe','--source-run-id','37113784702'])
    def test_changed_personal_comment_retains_original_error_and_never_grants_new_state(self):
        key=next(k for k in self.fixture.responses if '/issues/101/comments?' in k)
        import base64
        values=json.loads(base64.b64decode(self.fixture.responses[key]));values[-1]['updated_at']='2026-10-03T11:00:00Z';self.fixture.responses[key]=base64.b64encode(json.dumps(values).encode()).decode();(self.fixture.tools/'responses.json').write_text(json.dumps(self.fixture.responses))
        result=self.compare(['--operation','refresh'],expected=1);self.assertEqual(result['kernel_exception']['type'],'ContractError')
