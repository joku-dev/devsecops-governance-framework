"""Whole original request preparation, closed node bindings and actual V2 CLI."""
from pathlib import Path
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from datetime import datetime as NativeDatetime
import copy,errno,hashlib,io,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_personal_channel_programs as fixture
import test_v2_pilot_action_preparation as reference
from test_v2_personal_channel_exclusive import FaultStream
from lib.pilot_action_preparation_application import generate,inspect,request_valid,run,PROFILE
from lib.pilot_action_preparation_ports import read_record,encode,AUTHORITY
from lib.providers.personal_channel_exclusive import NativeExclusive
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read
from lib.requirement_validation_budget import InputAdmissionError

class PilotActionPreparationApplication(unittest.TestCase):
    def setUp(self):
        temp=fixture.WholePersonalChannelPrograms();temp.setUp();self.addCleanup(temp.doCleanups);self.fixture=temp
        self.source,_,self.tools=temp.fixture(prefix=False)
        (self.source/'scripts/prepare_lifecycle_pilot_action.py').write_bytes((reference.FIXTURE/'prepare_lifecycle_pilot_action.py.txt').read_bytes())
        self.body=self.source/'body.json';self.body.write_text(json.dumps({'kind':'role_withdrawal','reason':'Synthetic preview; never current consent or authority.'}))
        self.output=self.source/'request.json';self.instance=self.source.parent/'instance';self.instance.mkdir(mode=0o700)
        self.settings={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
    def args(self):return ['--body',str(self.body),'--discussion-number','900001','--output',str(self.output)]
    def generate(self,native=False,args=None,**options):
        with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}),patch('lib.providers.pilot_action_preparation_clock.datetime',reference.FrozenDatetime):
            return generate({'source_worktree':str(self.source),'legacy_arguments':self.args() if args is None else args,'capture_profile':'legacy-lifecycle-capture-v1','write_selected_files':native,**options},self.instance,self.settings)
    def original(self,args=None,*,at=reference.AT,fault=None):
        wrapper='''import builtins,os,runpy,sys,types
from pathlib import Path
from datetime import datetime as NativeDatetime,timezone
path=sys.argv[1];at=sys.argv[2];fault=sys.argv[3];selected=sys.argv[4];native_import=builtins.__import__;native_open=Path.open
class FrozenDatetime:
 @staticmethod
 def now(zone):return NativeDatetime.fromisoformat(at.replace('Z','+00:00')).astimezone(zone)
def selected_import(name,globals=None,locals=None,fromlist=(),level=0):
 if name=='datetime' and globals and globals.get('__file__')==path:return types.SimpleNamespace(datetime=FrozenDatetime,timezone=timezone)
 return native_import(name,globals,locals,fromlist,level)
class Fault:
 def __init__(self,stream):self.stream=stream
 def __enter__(self):self.stream.__enter__();return self
 def write(self,raw):
  self.stream.write(raw[:7]);self.stream.flush();raise OSError(28,os.strerror(28),selected)
 def __exit__(self,*error):self.stream.close()
def opened(path,*args,**kw):
 stream=native_open(path,*args,**kw)
 return Fault(stream) if fault=='write7' and str(path)==selected and args==('xb',) else stream
Path.open=opened;builtins.__import__=selected_import
sys.argv=[path,*sys.argv[5:]];runpy.run_path(path,run_name='__main__')
'''
        return subprocess.run([sys.executable,'-B','-c',wrapper,str(self.source/'scripts/prepare_lifecycle_pilot_action.py'),at,fault or '',str(self.output),*(self.args() if args is None else args)],cwd=self.source,capture_output=True,timeout=180,
            env={**os.environ,'PYTHONPATH':str(self.source/'scripts'),'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':'60','LINES':'24'})
    def reseal(self,root,events,value):
        previous='0'*64
        for i,event in enumerate(events):
            raw=encode({'sequence':i,'previous':previous,'value':event});(root/'events'/f'{i:08}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
        value['event_count'],value['event_tip']=len(events),previous;(root/'result.json').write_bytes(encode(value))

    def test_whole_original_native_private_file_bytes_modes_and_statement_match(self):
        before=fixture.snapshot(self.source);old=self.original();self.assertEqual(old.returncode,0,old.stderr)
        expected=fixture.snapshot(self.source);payload=self.output.read_bytes();fixture.restore(self.source,before)
        for native in (False,True):
            with self.subTest(native=native):
                receipt,result=self.generate(native);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0)
                self.assertEqual(result['kernel_result']['stdout'].encode(),old.stdout);self.assertEqual(result['kernel_result']['stderr'].encode(),old.stderr)
                self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred'])
                _,_,_,_,blob,_=read_record(receipt['record_root']);self.assertEqual(blob(result['successful_outputs'][str(self.output)]),payload)
                self.assertEqual(fixture.snapshot(self.source),expected if native else before)
                checked=inspect(receipt['record_root'],node=self.settings);self.assertTrue(checked['retained_declared_replay_consistent']);fixture.restore(self.source,before)
        stdout,stderr=io.StringIO(),io.StringIO()
        with patch('lib.providers.pilot_action_preparation_clock.datetime',reference.FrozenDatetime),patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}),redirect_stdout(stdout),redirect_stderr(stderr):
            code=run(['generate','--profile',PROFILE,'--capture-profile','legacy-lifecycle-capture-v1','--source-worktree',str(self.source),'--format','legacy','--',*self.args()],self.instance,self.settings)
        self.assertEqual(code,0);self.assertEqual(stdout.getvalue().encode(),old.stdout);self.assertEqual(stderr.getvalue().encode(),old.stderr)

    def test_source_deleted_pure_replay_and_foreign_node_rejection_both_modes(self):
        before=fixture.snapshot(self.source)
        receipts=[]
        for native in (False,True):
            receipt,_=self.generate(native);self.assertEqual(receipt['state'],'complete',receipt);receipts.append(receipt);fixture.restore(self.source,before)
        shutil.rmtree(self.source)
        with patch('subprocess.Popen',side_effect=AssertionError('No program')),patch('lib.pilot_action_preparation_application.NativeIO',side_effect=AssertionError('No selected source')),patch('lib.pilot_action_preparation_ports.NativePreparationClock',side_effect=AssertionError('No native clock')):
            for receipt in receipts:
                self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
                with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'b'*32})

    def test_original_existing_file_error_is_complete_but_clock_input_and_terminal_failures_are_incomplete(self):
        self.output.write_bytes(b'opaque existing bytes\x00\xff');old=self.original();self.assertEqual(old.returncode,1)
        receipt,result=self.generate(native=True);self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],1);self.assertTrue(receipt['source_effects_may_be_partial'])
        error=result['kernel_result']['kernel_exception'];self.assertTrue(old.stderr.endswith((error['type']+': '+error['message']+'\n').encode()));self.assertEqual(self.output.read_bytes(),b'opaque existing bytes\x00\xff');self.output.unlink()
        with patch('lib.providers.synthetic_lifecycle_io.NativeIO.read',side_effect=InputAdmissionError('unavailable captured input')):receipt,_=self.generate()
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
        with patch('lib.providers.pilot_action_preparation_clock.NativePreparationClock.__call__',side_effect=InputAdmissionError('unobserved native clock')):receipt,_=self.generate()
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code'])
        with patch('lib.pilot_action_preparation_application.Record.finish',side_effect=OSError('terminal unavailable')):receipt,result=self.generate()
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(receipt['journal_terminal_written']);self.assertEqual(result['exit_code'],0)

    def test_native_seven_byte_original_failure_preserves_partial_bytes_no_statement_and_partial_hint(self):
        before=fixture.snapshot(self.source);old=self.original(fault='write7');self.assertEqual(old.returncode,1);expected=self.output.read_bytes();self.assertEqual(len(expected),7);fixture.restore(self.source,before)
        opening=NativeExclusive.open_stream
        def selected(handle):return FaultStream(opening(handle),'write7',handle.label)
        with patch.object(NativeExclusive,'open_stream',selected):receipt,result=self.generate(native=True)
        self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],1);self.assertTrue(receipt['source_effects_may_be_partial'])
        self.assertEqual(self.output.read_bytes(),expected);self.assertEqual(result['kernel_result']['stdout'].encode(),old.stdout);self.assertEqual(old.stdout,b'')
        error=result['kernel_result']['kernel_exception'];self.assertTrue(old.stderr.endswith((error['type']+': '+error['message']+'\n').encode()));self.assertEqual(result['successful_outputs'],{})
        shutil.rmtree(self.source);self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_strict_profiles_parser_and_metadata_fail_before_record(self):
        receipt,_=self.generate(args=['--help']);request,*_=read_record(receipt['record_root'])
        for bad in ({**request,'schema_version':True},{**request,'capture_profile':'unknown'},{**request,'argv':[True]},{**request,'parser_context':{}},{**request,'resources':[{'uri':'https://invalid','label':'relative'}]}):
            with self.assertRaises(ValueError):request_valid(bad)
        with patch('lib.pilot_action_preparation_application.Record',side_effect=AssertionError('No record')):
            with self.assertRaisesRegex(ValueError,'capture_profile'):self.generate(capture_profile='unknown')

    def test_resealed_result_authority_source_clock_parser_and_orphan_blob_attacks_reject(self):
        for attack in ('stdout','authority','source','clock','parser','orphan'):
            with self.subTest(attack=attack):
                receipt,_=self.generate(args=['--help'] if attack=='parser' else None);root=Path(receipt['record_root']);request,source,value,events,blob,_=read_record(root)
                if attack=='stdout':value['result']['kernel_result']['stdout']='forged statement';self.reseal(root,events,value)
                elif attack=='authority':value['official_acceptance']=0;self.reseal(root,events,value)
                elif attack=='source':source['source_digest']='0'*64;(root/'source.json').write_bytes(encode(source))
                elif attack=='clock':
                    index=next(i for i,row in enumerate(events) if row.get('kind')=='intent' and row.get('action')=='pilot-action-preparation-clock');row=events[index+1];wire=json.loads(blob(row['value']));wire['value']='2026-11-15T12:00:01Z';raw=encode(wire);sha=hashlib.sha256(raw).hexdigest();(root/'blobs'/sha).write_bytes(raw);row['value']={'sha256':sha,'bytes':len(raw)};self.reseal(root,events,value)
                elif attack=='parser':request['parser_context']['width']=24;events[1]['request']=request;(root/'request.json').write_bytes(encode(request));self.reseal(root,events,value)
                else:raw=b'orphan';(root/'blobs'/hashlib.sha256(raw).hexdigest()).write_bytes(raw)
                with self.assertRaises(ValueError,msg=attack):inspect(root)

    def test_actual_cli_private_generate_help_inspect_and_instance_free_replay(self):
        from test_portable_runtime import OPA
        node=self.source.parent/'cli-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')];environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':'60','LINES':'24'}
        def call(args,expected=0):
            result=subprocess.run([*cli,*args],capture_output=True,env=environment,timeout=180);self.assertEqual(result.returncode,expected,result.stderr[-3000:]);return result
        call(['--instance',str(node),'init','--development','--opa',str(OPA)])
        base=['--instance',str(node),'pilot-action-requests','generate','--profile',PROFILE,'--capture-profile','legacy-lifecycle-capture-v1','--source-worktree',str(self.source)]
        old=self.original(['--help']);legacy=call([*base,'--format','legacy','--','--help']);self.assertEqual(legacy.stdout,old.stdout);self.assertEqual(legacy.stderr,old.stderr)
        before=fixture.snapshot(self.source);receipt=json.loads(call([*base,'--',*self.args()]).stdout);self.assertEqual(receipt['state'],'complete')
        request,_,retained,events,blob,_=read_record(receipt['record_root']);i=next(i for i,row in enumerate(events) if row.get('kind')=='intent' and row.get('action')=='pilot-action-preparation-clock');at=json.loads(blob(events[i+1]['value']))['value']
        # Bind the independent unchanged original to the actual captured clock
        # input; never normalize generated request/statement bytes afterwards.
        old=self.original(at=at);self.assertEqual(old.returncode,0,old.stderr);payload=self.output.read_bytes();fixture.restore(self.source,before)
        result=retained['result'];self.assertEqual(result['kernel_result']['stdout'].encode(),old.stdout);self.assertEqual(result['kernel_result']['stderr'].encode(),old.stderr);self.assertEqual(blob(result['successful_outputs'][str(self.output)]),payload)
        self.assertEqual(fixture.snapshot(self.source),before)
        checked=json.loads(call(['--instance',str(node),'pilot-action-requests','inspect','--record',receipt['record_root']]).stdout);shutil.rmtree(self.source)
        replayed=json.loads(call(['pilot-action-requests','replay','--record',receipt['record_root']]).stdout);self.assertEqual(checked,replayed)
        self.assertTrue(json.loads((node/'instance.json').read_bytes())['development']);self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')

if __name__=='__main__':unittest.main(verbosity=2)
