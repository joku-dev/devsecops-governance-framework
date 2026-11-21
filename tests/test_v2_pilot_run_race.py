"""Two real initialized-ledger writers recheck complete captures under original lock."""
from pathlib import Path
from unittest.mock import patch
import base64,hashlib,json,os,shutil,subprocess,sys,time,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_personal_channel_programs as reference
from test_v2_pilot_run_intake import CONTRACT,FIXTURE,transaction_name

CHILD=r'''from pathlib import Path
import json,os,sys,time
kind,root,control,which,product=sys.argv[1:];root=Path(root);control=Path(control)
arguments=json.loads((control/(which+'-arguments.json')).read_bytes())
def announce(stage):
 (control/(which+'-'+stage)).write_text('actual original lock boundary')
 if which=='first' and stage=='held':
  start=time.monotonic()
  while not (control/'release-first').exists():
   assert time.monotonic()-start<60,'Test barrier timeout, never a business verdict'
   time.sleep(.01)
if kind=='original':
 sys.path.insert(0,str(root/'scripts'))
 import fcntl
 from lib.governance_lifecycle.live_admission import append_capture
 actual=fcntl.flock
 def observed(fd,operation):
  if operation==fcntl.LOCK_EX:announce('attempt')
  value=actual(fd,operation)
  if operation==fcntl.LOCK_EX:announce('held')
  return value
 fcntl.flock=observed
 try:result=append_capture(**arguments);value={'exit_code':0,'return_value':result,'kernel_exception':None}
 except Exception as error:value={'exit_code':1,'return_value':None,'kernel_exception':{'type':type(error).__name__,'message':str(error)}}
else:
 sys.path.insert(0,str(Path(product)/'scripts'))
 from jsonschema import Draft202012Validator
 from lib.pilot_run_intake_context import execute
 from lib.providers.pilot_run_intake_io import NativeRunIO
 from lib.providers.synthetic_ledger_effects import NativeLedgerEffects
 from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
 from lib.providers.synthetic_lifecycle_storage import Record
 from lib.providers.retained_argparse import capture_context
 from lib.personal_channel_ports import exclusive_factory
 actual=NativeLedgerEffects.flock
 def observed(effect,descriptor,operation):
  if operation==effect.LOCK_EX:announce('attempt')
  value=actual(effect,descriptor,operation)
  if operation==effect.LOCK_EX:announce('held')
  return value
 NativeLedgerEffects.flock=observed
 state=control/('state-'+which);state.mkdir(mode=0o700)
 record=Record(state/'records',{'test':'real competing run capture'},{'source_only':True});record.append({'kind':'execution-intent'})
 def name_of(raw):
  row=json.loads(raw);return f"{row['sequence']:08d}-{row['transaction_id'].split(':')[1]}.json"
 owner=NativeRunIO(record,mode='selected-files',cwd=str(root),private_state=state,product_root=Path(product),ledger=arguments['root'],transaction_name=name_of)
 result=execute(str(root),str(root),[],owner,validator_class=Draft202012Validator,historical_provider_factory=lambda context:LegacyRepositoryLifecycleCapture(context),fresh_provider_factory=lambda context,emit:None,effects_factory=lambda io:NativeLedgerEffects(io,arguments['root'],transaction_name=name_of),exclusive_factory=exclusive_factory,temporary_factory=lambda io:None,parser_context=capture_context(),clock_factory=lambda io:None,invocation={'method':'append_capture','arguments':arguments})
 assert not record.capture_incomplete
 record.finish('complete',{'exit_code':result['exit_code'],'kernel_result':result},owner.touched)
 value={key:result[key] for key in ('exit_code','return_value','kernel_exception')};value['record_root']=str(record.root)
print(json.dumps(value))
'''

class WholeRunWriterRace(unittest.TestCase):
    def compare(self,duplicate):
        fixture=reference.WholePersonalChannelPrograms();fixture.setUp();self.addCleanup(fixture.doCleanups);root,_,tools=fixture.fixture(prefix=False)
        for name,row in CONTRACT['files'].items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((FIXTURE/row['fixture']).read_bytes())
        receipts=[json.loads(p.read_bytes()) for p in sorted((root/'governance/lifecycle/live-validation/transactions').glob('*.json'))]
        selected=[receipts[0],receipts[0] if duplicate else receipts[1]];directories=[];ats=[]
        for index,receipt in enumerate(selected):
            directory=root/('prepared-capture-'+str(index));directory.mkdir(mode=0o700);directories.append(directory)
            for name,encoded in receipt['capture'].items():
                p=directory/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(encoded,validate=True))
            ats.append(json.loads((directory/'preflight.json').read_bytes())['captured_at'])
        ledger=root/'governance/lifecycle/live-validation';shutil.rmtree(ledger);(ledger/'transactions').mkdir(parents=True,mode=0o700);(ledger/'.append.lock').write_bytes(b'');(ledger/'.append.lock').chmod(0o600)
        profile=json.loads((root/'model/governance/lifecycle/live-operating/00000001.json').read_bytes())
        arguments=[{'root':str(ledger),'directory':str(directory),'profile':profile,'recorded_at':max(ats),'expected_sequence':0} for directory in directories]
        before=reference.snapshot(root);results={}
        for kind in ('original','v2'):
            control=root.parent/('run-race-'+kind);control.mkdir(mode=0o700);script=control/'child.py';script.write_text(CHILD)
            for which,args in zip(('first','second'),arguments):(control/(which+'-arguments.json')).write_text(json.dumps(args))
            processes={};logs={}
            try:
                for which in ('first','second'):
                    log=(control/(which+'.stderr')).open('xb');logs[which]=log
                    process=subprocess.Popen([sys.executable,'-B',str(script),kind,str(root),str(control),which,str(ROOT)],stdout=subprocess.PIPE,stderr=log,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':'60','LINES':'24'});processes[which]=process
                    marker=control/('first-held' if which=='first' else 'second-attempt');start=time.monotonic()
                    while not marker.exists():
                        self.assertIsNone(process.poll(),(kind,which,(control/(which+'.stderr')).read_bytes()[-3500:]));self.assertLess(time.monotonic()-start,60);time.sleep(.01)
                self.assertIsNone(processes['first'].poll());self.assertIsNone(processes['second'].poll());self.assertFalse((control/'second-held').exists())
                (control/'release-first').write_text('Observed actual first lock and actual second attempt')
                values={}
                for which,process in processes.items():
                    stdout,_=process.communicate(timeout=60);self.assertEqual(process.returncode,0,(kind,which,(control/(which+'.stderr')).read_bytes()[-3500:]));values[which]=json.loads(stdout)
                self.assertEqual(values['first']['return_value']['outcome'],'eligible_for_pilot')
                if duplicate:self.assertEqual(values['second']['exit_code'],0);self.assertEqual(values['second']['return_value'],{'outcome':'duplicate','transaction_ref':None})
                else:self.assertEqual(values['second']['exit_code'],1);self.assertEqual(values['second']['kernel_exception'],{'type':'ContractError','message':'Stale receipt sequence'})
                self.assertEqual(len(list((ledger/'transactions').glob('*.json'))),1);results[kind]=values
                if kind=='original':expected=reference.snapshot(root);reference.restore(root,before)
                else:
                    self.assertEqual(reference.snapshot(root),expected)
                    for which in ('first','second'):self.assertEqual({k:v for k,v in values[which].items() if k!='record_root'},results['original'][which])
            finally:
                for process in processes.values():
                    if process.poll() is None:process.terminate();process.wait(timeout=10)
                for log in logs.values():log.close()
        shutil.rmtree(root);shutil.rmtree(tools)
        from jsonschema import Draft202012Validator
        from lib.pilot_run_intake_context import execute
        from lib.pilot_run_intake_io import ReplayRunIO
        from lib.synthetic_ledger_replay_effects import ReplayLedgerEffects
        from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
        from lib.providers.retained_argparse import capture_context
        from lib.providers.synthetic_lifecycle_storage import read_record
        from lib.personal_channel_ports import exclusive_factory
        for which,args in zip(('first','second'),arguments):
            saved=Path(results['v2'][which]['record_root']);_,_,terminal,events,blob,closed=read_record(saved);cache={p.name:p.read_bytes() for p in (saved/'blobs').iterdir()};seen=set()
            def inert(ref):
                raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return raw
            io=ReplayRunIO(events,inert,'selected-files',str(root),ledger=str(ledger),transaction_name=transaction_name)
            with patch('os.open',side_effect=AssertionError('No selected source')),patch('subprocess.Popen',side_effect=AssertionError('No process')):
                actual=execute(str(root),str(root),[],io,validator_class=Draft202012Validator,historical_provider_factory=lambda context:LegacyRepositoryLifecycleCapture(context),fresh_provider_factory=lambda context,emit:None,effects_factory=lambda io:ReplayLedgerEffects(io,str(ledger),transaction_name=transaction_name),exclusive_factory=exclusive_factory,temporary_factory=lambda io:None,parser_context=capture_context(),clock_factory=lambda io:None,invocation={'method':'append_capture','arguments':args});io.finish()
            self.assertEqual(actual,terminal['result']['kernel_result']);self.assertEqual(seen,set(cache))
            for sha in seen:blob({'sha256':sha,'bytes':len(cache[sha])})
            self.assertTrue(closed())
    def test_two_real_writers_recheck_new_history_then_duplicate_precedes_stale_sequence(self):self.compare(True)
    def test_two_real_competing_origins_cannot_both_claim_the_same_sequence(self):self.compare(False)

if __name__=='__main__':unittest.main(verbosity=2)
