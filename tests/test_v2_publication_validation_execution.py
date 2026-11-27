"""Whole original publication validation, real frozen model/provider fixture and inert replay."""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,shutil,subprocess,sys,unittest
from contextlib import nullcontext
from datetime import datetime as ActualDatetime
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from jsonschema import Draft202012Validator
import test_v2_lifecycle_ledger_validation_execution as reference
from test_v2_personal_channel_programs import snapshot
from lib.lifecycle_ledger_validation_ports import execute
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.pilot_run_intake_io import ReplayRunIO
from lib.pilot_run_intake_ports import ledger,transaction_name
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.retained_argparse import capture_context
WRAPPER=reference.WRAPPER.replace("packet=runpy.run_path(script,run_name='immutable_whole_validator');returned=error=signal=None","from pathlib import Path\nfrom lib.governance_lifecycle.operating_acceptance import validate_publication\nreturned=error=signal=None").replace("try:returned=packet['main']()","try:returned=validate_publication(Path(script).parents[1],sys.argv[1])")
class WholePublicationValidationExecution(unittest.TestCase):
    def setUp(self):
        self.reference=reference.WholeLifecycleValidatorExecution();self.reference.setUp();self.addCleanup(self.reference.doCleanups);self.serial=0
    def compare(self,base,*,mode='private-candidate'):
        case=self.reference
        before=snapshot(case.source);env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','LD_','DYLD_'))};env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(case.source/'scripts'),GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1')
        if case.provider_calls is not None:
            env['PATH']=str(Path(case.provider).parent)+os.pathsep+env.get('PATH','');case.provider_calls.unlink(missing_ok=True)
        old=subprocess.run([sys.executable,'-B','-c',WRAPPER,str(case.source/'scripts/validate_governance_lifecycle_ledger.py'),case.clock or 'none',base],cwd=case.source,env=env,capture_output=True,timeout=300);self.assertEqual(old.returncode,0,old.stderr[-4000:]);parts=old.stdout.rsplit(b'\nAXIOM_ORIGINAL_RESULT=',1);self.assertEqual(len(parts),2,old.stdout[-4000:]);expected=json.loads(parts[1]);self.assertEqual(snapshot(case.source),before)
        old_calls=None if case.provider_calls is None else case.provider_calls.read_bytes() if case.provider_calls.exists() else b''
        if case.provider_calls is not None:case.provider_calls.unlink(missing_ok=True)
        self.serial+=1;record=Record(case.private/('records-'+str(self.serial)),{'prototype':'whole original validator','base_ref':base},{'prototype':True});record.append({'kind':'execution-intent'});owner=NativeRunIO(record,mode=mode,cwd=str(case.source),private_state=case.private,ledger=ledger(str(case.source)),transaction_name=transaction_name)
        parser=capture_context()
        chosen=case.clock
        class Clock:
            @staticmethod
            def now(zone):return ActualDatetime.fromisoformat(chosen.replace('Z','+00:00')).astimezone(zone)
        with patch('lib.providers.personal_channel_transport.datetime',Clock) if chosen else nullcontext():
            actual=execute(str(case.source),str(case.source),[],owner,validator_class=Draft202012Validator,parser_context=parser,provider_executable=case.provider,temporary_parent=str(case.temporary),publication_base_ref=base)
        if case.provider_calls is not None:self.assertEqual(case.provider_calls.read_bytes() if case.provider_calls.exists() else b'',old_calls)
        self.assertEqual({k:actual[k] for k in expected},expected,(base,actual,expected));self.assertEqual(actual['stdout'].encode(),parts[0]);raw=b''.join((record.blobs/part['blob']['sha256']).read_bytes() if 'blob' in part else part['text'].encode() for part in actual['stderr_parts']);self.assertEqual(raw,old.stderr);self.assertEqual(snapshot(case.source),before)
        record.finish('complete',{'exit_code':actual['exit_code'],'kernel_result':actual},owner.touched);_,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
        def inert(ref):
            value=cache[ref['sha256']];self.assertEqual(len(value),ref['bytes']);self.assertEqual(hashlib.sha256(value).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return value
        moved=case.source.with_name(case.source.name+'-temporarily-unavailable');case.source.rename(moved)
        try:
            replay=ReplayRunIO(events,inert,mode,str(case.source),ledger=ledger(str(case.source)),transaction_name=transaction_name)
            with patch('subprocess.Popen',side_effect=AssertionError('No Git/provider')),patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No temporary scope')),patch('os.open',side_effect=AssertionError('No source/private/clock input')):
                pure=execute(str(case.source),str(case.source),[],replay,validator_class=Draft202012Validator,parser_context=parser,provider_executable=case.provider,temporary_parent=str(case.temporary),publication_base_ref=base);replay.finish()
            self.assertEqual(pure,actual);self.assertEqual(seen,set(cache))
            for name,value in cache.items():blob({'sha256':name,'bytes':len(value)})
            self.assertTrue(closed())
        finally:moved.rename(case.source)
        return actual

    def test_active_original_precondition_rechecks_provider_without_new_captures(self):
        case=self.reference;case.tools();base=case.base();value=self.compare(base);self.assertEqual(value['exit_code'],0,value);self.assertTrue(value['return_value']['live_activation_approved']);self.assertIn('/issues/91',case.provider_calls.read_text())
    def test_inactive_role_withdrawal_preserves_permission_reducing_publication(self):
        case=self.reference;base=case.fresh_case('action');value=self.compare(base);self.assertEqual(value['exit_code'],0,value);self.assertFalse(value['return_value']['live_activation_approved']);self.assertIn('/issues/900001',case.provider_calls.read_text())
    def test_original_modified_accepted_transaction_stops_before_provider(self):
        case=self.reference;case.tools();base=case.base();path=next((case.source/'governance/lifecycle/synthetic/transactions').glob('*.json'));path.write_bytes(b'{"explicit_modified_transaction":true}');value=self.compare(base);self.assertEqual(value['kernel_exception'],{'type':'ContractError','message':'Accepted transaction modified'});self.assertFalse(case.provider_calls.exists())
    def test_active_changed_provider_is_not_approved_by_historical_acceptance(self):
        case=self.reference;case.tools();base=case.base();case.change_provider('operating');value=self.compare(base);self.assertEqual(value['exit_code'],1);self.assertIsNotNone(value['kernel_exception']);self.assertIsNone(value['return_value'])
    def test_whole_new_receipt_original_precondition_and_private_temporary_cleanup(self):
        case=self.reference;base=case.fresh_case('receipt');value=self.compare(base);self.assertEqual(value['exit_code'],0,value);self.assertTrue(value['return_value']['live_activation_approved']);self.assertFalse(list(case.temporary.iterdir()))
    def test_whole_new_receipt_original_precondition_with_native_temporary_cleanup(self):
        case=self.reference;base=case.fresh_case('receipt');value=self.compare(base,mode='selected-files');self.assertEqual(value['exit_code'],0,value);self.assertFalse(list(case.temporary.iterdir()))
    def test_new_operating_capture_retains_both_original_fresh_checks(self):
        case=self.reference;base=case.fresh_case('operating');value=self.compare(base);self.assertEqual(value['exit_code'],0,value);self.assertIn('/issues/91',case.provider_calls.read_text())
    def test_inactive_pilot_rejects_new_observation_after_valid_fresh_receipt_and_withdrawal(self):
        from acceptance.lifecycle_validator_fixture import append_role_withdrawal,refresh
        case=self.reference;base=case.fresh_case('receipt');append_role_withdrawal(case.source,case.provider_tools,'2026-09-13T17:00:00Z');refresh(case.source,case.provider_tools)
        for path in (case.source/'governance/lifecycle/pilot-actions/transactions').glob('*.json'):case.git('add','--',str(path))
        value=self.compare(base);self.assertEqual(value['kernel_exception'],{'type':'ContractError','message':'Inactive pilot cannot publish a new observation'})
if __name__=='__main__':unittest.main(verbosity=2)
