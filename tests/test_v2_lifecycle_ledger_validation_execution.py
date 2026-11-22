"""Whole original validator subprocess versus composed native and inert replay."""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,shutil,subprocess,sys,unittest
from contextlib import nullcontext
from datetime import datetime as ActualDatetime
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from jsonschema import Draft202012Validator
import test_v2_repository_lifecycle_history as history
from test_v2_personal_channel_programs import snapshot
from lib.lifecycle_ledger_validation_ports import execute
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.pilot_run_intake_io import ReplayRunIO
from lib.pilot_run_intake_ports import ledger,transaction_name
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.retained_argparse import capture_context

WRAPPER='''import json,runpy,sys
script,at=sys.argv[1:3];sys.argv=[script,*sys.argv[3:]]
if at!='none':
 from datetime import datetime as ActualDatetime
 import lib.governance_lifecycle.live_evidence as evidence
 import lib.governance_lifecycle.live_admission as admission
 import lib.governance_lifecycle.personal_probe as personal
 class Clock:
  @staticmethod
  def now(zone):return ActualDatetime.fromisoformat(at.replace('Z','+00:00')).astimezone(zone)
 evidence.datetime=admission.datetime=personal.datetime=Clock
packet=runpy.run_path(script,run_name='immutable_whole_validator');returned=error=signal=None
try:returned=packet['main']()
except SystemExit as e:signal={'type':'SystemExit','value':e.code}
except Exception as e:error={'type':type(e).__name__,'message':str(e)}
print('\\nAXIOM_ORIGINAL_RESULT='+json.dumps({'return_value':returned,'kernel_exception':error,'original_exit_signal':signal}))
'''
class WholeLifecycleValidatorExecution(unittest.TestCase):
    def setUp(self):
        c=history.LifecycleHistoryTests();c.setUp();self.addCleanup(c.doCleanups);self.history=c;self.source=c.root
        # Materialize only whole byte-pinned original modules in the isolated
        # fixture; original validation is not patched or replaced with stubs.
        groups=('lifecycle_helpers','lifecycle_history','lifecycle_capture_adapter','lifecycle_history_support')
        for group in groups:
            for name,row in history.CONTRACT[group].items():
                raw=(history.FIXTURES/row['fixture']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),row['source_sha256']);p=self.source/row['source_path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        self.private=self.source.parent/'whole-validator-state';self.private.mkdir(mode=0o700);self.temporary=self.source.parent/'whole-validator-temporaries';self.temporary.mkdir(mode=0o700)
        self.serial=0;self.provider='never-called-for-accepted-fixture';self.clock=None;self.provider_calls=None
    def git(self,*args):return subprocess.check_output(['git','-C',str(self.source),*args],env={**os.environ,'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null','GIT_CONFIG_NOSYSTEM':'1'},stderr=subprocess.PIPE)
    def base(self):
        self.git('init','--initial-branch=whole-validator-fixture');self.git('config','gc.auto','0');self.git('config','maintenance.auto','false');self.git('add','--all');self.git('-c','user.name=Isolated whole validator fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null','commit','--quiet','-m','Immutable whole validator fixture');return self.git('rev-parse','HEAD').decode().strip()
    def compare(self,argv=(),*,mode='private-candidate'):
        before=snapshot(self.source);env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','LD_','DYLD_'))};env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(self.source/'scripts'),GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1')
        if self.provider_calls is not None:
            env['PATH']=str(Path(self.provider).parent)+os.pathsep+env.get('PATH','');self.provider_calls.unlink(missing_ok=True)
        old=subprocess.run([sys.executable,'-B','-c',WRAPPER,str(self.source/'scripts/validate_governance_lifecycle_ledger.py'),self.clock or 'none',*argv],cwd=self.source,env=env,capture_output=True,timeout=300);self.assertEqual(old.returncode,0,old.stderr[-4000:]);parts=old.stdout.rsplit(b'\nAXIOM_ORIGINAL_RESULT=',1);self.assertEqual(len(parts),2,old.stdout[-4000:]);expected=json.loads(parts[1]);self.assertEqual(snapshot(self.source),before)
        old_calls=None if self.provider_calls is None else self.provider_calls.read_bytes() if self.provider_calls.exists() else b''
        if self.provider_calls is not None:self.provider_calls.unlink(missing_ok=True)
        self.serial+=1;record=Record(self.private/('records-'+str(self.serial)),{'prototype':'whole original validator','argv':list(argv)},{'prototype':True});record.append({'kind':'execution-intent'});owner=NativeRunIO(record,mode=mode,cwd=str(self.source),private_state=self.private,ledger=ledger(str(self.source)),transaction_name=transaction_name)
        parser=capture_context()
        chosen=self.clock
        class Clock:
            @staticmethod
            def now(zone):return ActualDatetime.fromisoformat(chosen.replace('Z','+00:00')).astimezone(zone)
        with patch('lib.providers.personal_channel_transport.datetime',Clock) if chosen else nullcontext():
            actual=execute(str(self.source),str(self.source),argv,owner,validator_class=Draft202012Validator,parser_context=parser,provider_executable=self.provider,temporary_parent=str(self.temporary))
        if self.provider_calls is not None:self.assertEqual(self.provider_calls.read_bytes() if self.provider_calls.exists() else b'',old_calls)
        self.assertEqual({k:actual[k] for k in expected},expected,(argv,actual,expected));self.assertEqual(actual['stdout'].encode(),parts[0]);raw=b''.join((record.blobs/part['blob']['sha256']).read_bytes() if 'blob' in part else part['text'].encode() for part in actual['stderr_parts']);self.assertEqual(raw,old.stderr);self.assertEqual(snapshot(self.source),before)
        record.finish('complete',{'exit_code':actual['exit_code'],'kernel_result':actual},owner.touched);_,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
        def inert(ref):
            value=cache[ref['sha256']];self.assertEqual(len(value),ref['bytes']);self.assertEqual(hashlib.sha256(value).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return value
        moved=self.source.with_name(self.source.name+'-temporarily-unavailable');self.source.rename(moved)
        try:
            replay=ReplayRunIO(events,inert,mode,str(self.source),ledger=ledger(str(self.source)),transaction_name=transaction_name)
            with patch('subprocess.Popen',side_effect=AssertionError('No Git/provider')),patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No temporary scope')),patch('os.open',side_effect=AssertionError('No source/private/clock input')):
                pure=execute(str(self.source),str(self.source),argv,replay,validator_class=Draft202012Validator,parser_context=parser,provider_executable=self.provider,temporary_parent=str(self.temporary));replay.finish()
            self.assertEqual(pure,actual);self.assertEqual(seen,set(cache))
            for name,value in cache.items():blob({'sha256':name,'bytes':len(value)})
            self.assertTrue(closed())
        finally:moved.rename(self.source)
        return actual
    def test_whole_original_zero_argument_validation_native_and_source_free_replay(self):
        value=self.compare();self.assertEqual(value['exit_code'],0,value);self.assertIn('no live activation.',value['stdout'])
    def test_whole_original_accepted_base_and_provider_flag_retains_all_four_zero_counts(self):
        base=self.base();value=self.compare(['--base-ref',base,'--verify-new-provider']);self.assertEqual(value['exit_code'],0,value);self.assertEqual(value['stdout'].count('Independently checked 0'),4);self.assertIn('Preserved ',value['stdout'])
    def test_original_provider_without_base_fails_after_structural_checks(self):
        value=self.compare(['--verify-new-provider']);self.assertEqual(value['kernel_exception'],{'type':'ContractError','message':'Provider verification requires an accepted base'})
    def test_original_help_unknown_missing_argument_and_zero_base_paths(self):
        for argv in (['--help'],['--unknown'],['--base-ref'],['--base-ref','0'*40]):
            with self.subTest(argv=argv):self.compare(argv)
    def test_original_prefix_failure_short_circuits_later_ledger_validation(self):
        base=self.base();row=next((self.source/'governance/lifecycle/synthetic/transactions').glob('*.json'));row.write_bytes(b'{"explicit_modified_transaction":true}\n');value=self.compare(['--base-ref',base]);self.assertEqual(value['kernel_exception'],{'type':'ContractError','message':'Accepted transaction modified'});self.assertNotIn('Lifecycle:',value['stdout'])

    def tools(self):
        from acceptance.lifecycle_validator_fixture import prepare_tools
        self.provider_tools=self.source.parent/'whole-validator-fake-provider';prepare_tools(self.source,self.provider_tools);self.provider=str(self.provider_tools/'gh');self.provider_calls=self.provider_tools/'calls.jsonl';self.clock='2026-09-13T17:00:01Z'
        return self.provider_tools

    def base_without(self,path):
        raw=path.read_bytes();mode=path.stat().st_mode&0o777;path.unlink();base=self.base();path.write_bytes(raw);path.chmod(mode);self.git('add','--',str(path));return base

    def test_whole_original_new_receipt_collects_actual_fake_provider_bytes_and_temporary_data(self):
        base=self.fresh_case('receipt')
        value=self.compare(['--base-ref',base,'--verify-new-provider']);self.assertEqual(value['exit_code'],0,value);self.assertIn('Independently checked 1 new pilot receipts',value['stdout']);self.assertTrue(self.provider_calls.read_bytes());self.assertFalse(list(self.temporary.iterdir()))

    def test_whole_original_new_personal_capture_uses_current_head_and_rechecks_provider(self):
        from acceptance.lifecycle_validator_fixture import refresh,append_personal
        # Build a coherent private historical prefix using the original
        # generators. This is not a change to real history or an approval.
        for path in sorted((self.source/'governance/lifecycle/live-validation/transactions').glob('*.json'))[1:]:path.unlink()
        tools=self.tools();refresh(self.source,tools);base=self.base();append_personal(self.source,tools,'2026-09-13T17:00:00Z');refresh(self.source,tools);self.git('add','--','generated/reports/lifecycle-personal-channel/00000002.json')
        value=self.compare(['--base-ref',base,'--verify-new-provider']);self.assertEqual(value['exit_code'],0,value);self.assertIn('Independently checked 1 new personal-channel captures',value['stdout'])

    def test_whole_original_new_operating_capture_retains_fresh_provider_and_projection_checks(self):
        from acceptance.lifecycle_validator_fixture import refresh,append_operating
        tools=self.tools();base=self.base();append_operating(self.source,tools,'2026-09-13T17:00:00Z');refresh(self.source,tools);self.git('add','--','generated/reports/lifecycle-operating-acceptance/00000002.json')
        value=self.compare(['--base-ref',base,'--verify-new-provider']);self.assertEqual(value['exit_code'],0,value);self.assertIn('Independently checked 1 new operating acceptance captures',value['stdout'])

    def test_whole_original_new_synthetic_role_withdrawal_action_keeps_inactive_operating_guard(self):
        from acceptance.lifecycle_validator_fixture import refresh,append_role_withdrawal
        tools=self.tools();base=self.base();append_role_withdrawal(self.source,tools,'2026-09-13T17:00:00Z');refresh(self.source,tools)
        for path in (self.source/'governance/lifecycle/pilot-actions/transactions').glob('*.json'):self.git('add','--',str(path))
        value=self.compare(['--base-ref',base,'--verify-new-provider']);self.assertEqual(value['exit_code'],0,value);self.assertIn('Independently checked 1 new action proofs',value['stdout']);self.assertNotIn('/issues/91',self.provider_calls.read_text());self.assertIn('checked 0 new operating acceptance captures',value['stdout'])

    def fresh_case(self,kind):
        from acceptance.lifecycle_validator_fixture import refresh,append_personal,append_operating,append_role_withdrawal
        if kind=='personal':
            for path in sorted((self.source/'governance/lifecycle/live-validation/transactions').glob('*.json'))[1:]:path.unlink()
        tools=self.tools()
        if kind=='receipt':
            receipt=sorted((self.source/'governance/lifecycle/live-validation/transactions').glob('*.json'))[-1];raw=receipt.read_bytes();mode=receipt.stat().st_mode&0o777;receipt.unlink();refresh(self.source,tools);base=self.base();receipt.write_bytes(raw);receipt.chmod(mode);refresh(self.source,tools);self.git('add','--',str(receipt));return base
        if kind=='personal':refresh(self.source,tools)
        base=self.base()
        if kind=='personal':append_personal(self.source,tools,'2026-09-13T17:00:00Z');names=['generated/reports/lifecycle-personal-channel/00000002.json']
        elif kind=='operating':append_operating(self.source,tools,'2026-09-13T17:00:00Z');names=['generated/reports/lifecycle-operating-acceptance/00000002.json']
        else:append_role_withdrawal(self.source,tools,'2026-09-13T17:00:00Z');names=[str(p) for p in (self.source/'governance/lifecycle/pilot-actions/transactions').glob('*.json')]
        refresh(self.source,tools)
        for name in names:self.git('add','--',name)
        return base

    def change_provider(self,kind):
        import base64
        config=self.provider_tools/'responses.json';responses=json.loads(config.read_bytes())
        if kind=='receipt':
            key=next(k for k in responses if k.endswith('/zip') and '/10320359471/' in k);responses[key]=base64.b64encode(b'EXPLICIT corrupted fake provider archive').decode()
        else:
            number={'personal':87,'operating':91,'action':900001}[kind];key=next(k for k in responses if f'/issues/{number}/comments?' in k);rows=json.loads(base64.b64decode(responses[key]));self.assertTrue(rows);rows[-1]['body']+='\nEXPLICITLY CHANGED AT THE FAKE PROVIDER';responses[key]=base64.b64encode(json.dumps(rows).encode()).decode()
        config.write_text(json.dumps(responses))

    def test_whole_original_native_temporary_receipt_effects_cleanup_and_pure_reconstruction(self):
        base=self.fresh_case('receipt');value=self.compare(['--base-ref',base,'--verify-new-provider'],mode='selected-files');self.assertEqual(value['exit_code'],0,value);self.assertIn('checked 1 new pilot receipts',value['stdout']);self.assertFalse(list(self.temporary.iterdir()))

    def test_whole_original_changed_archive_stops_before_later_fresh_helpers(self):
        base=self.fresh_case('receipt');self.change_provider('receipt');value=self.compare(['--base-ref',base,'--verify-new-provider']);self.assertEqual(value['exit_code'],1);self.assertIsNotNone(value['kernel_exception']);self.assertNotIn('new personal-channel captures',value['stdout']);self.assertFalse(list(self.temporary.iterdir()))

    def test_whole_original_changed_personal_provider_preserves_prior_receipt_output_and_stops(self):
        base=self.fresh_case('personal');self.change_provider('personal');value=self.compare(['--base-ref',base,'--verify-new-provider']);self.assertEqual(value['exit_code'],1);self.assertEqual(value['kernel_exception']['message'],'Personal channel provider state differs');self.assertIn('new pilot receipts',value['stdout']);self.assertNotIn('new action proofs',value['stdout'])

    def test_whole_original_changed_action_statement_prevents_final_operating_and_projection_output(self):
        base=self.fresh_case('action');self.change_provider('action');value=self.compare(['--base-ref',base,'--verify-new-provider']);self.assertEqual(value['exit_code'],1);self.assertEqual(value['kernel_exception']['message'],'New action differs from independently retrieved personal statement');self.assertIn('new personal-channel captures',value['stdout']);self.assertNotIn('new operating acceptance captures',value['stdout'])

    def test_whole_original_changed_operating_statement_fails_after_prior_three_outputs(self):
        base=self.fresh_case('operating');self.change_provider('operating');value=self.compare(['--base-ref',base,'--verify-new-provider']);self.assertEqual(value['exit_code'],1);self.assertIsNotNone(value['kernel_exception']);self.assertIn('new action proofs',value['stdout']);self.assertNotIn('Lifecycle:',value['stdout'])

    def test_whole_original_active_changed_index_rechecks_existing_operating_acceptance_without_new_capture(self):
        base=self.fresh_case('receipt');value=self.compare(['--base-ref',base,'--verify-new-provider']);self.assertEqual(value['exit_code'],0,value);self.assertIn('checked 1 new pilot receipts',value['stdout']);self.assertIn('checked 0 new operating acceptance captures',value['stdout']);self.assertIn('/issues/91',self.provider_calls.read_text())

    def test_whole_original_base_only_checks_prefix_and_structure_without_provider_GETs(self):
        base=self.base();value=self.compare(['--base-ref',base]);self.assertEqual(value['exit_code'],0,value);self.assertIn('Preserved ',value['stdout']);self.assertNotIn('Independently checked',value['stdout'])
