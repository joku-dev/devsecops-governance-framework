"""Complete original fresh main: GETs, two clocks, receipts and owned cleanup."""
from pathlib import Path
from datetime import datetime as ActualDatetime,timedelta
from contextlib import ExitStack
from unittest.mock import patch
import base64,hashlib,json,os,shutil,stat,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from jsonschema import Draft202012Validator
import test_v2_personal_channel_programs as reference
import test_v2_live_preflight as preflight_reference
from lib.pilot_run_intake_context import execute
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.pilot_run_intake_io import ReplayRunIO
from lib.providers.pilot_run_temporary import NativeTemporaryFactory,NativeTemporary
from lib.pilot_run_temporary import ReplayTemporaryFactory
from lib.pilot_run_private_temporary import PrivateTemporaryFactory
from lib.synthetic_ledger_private import PrivateLedgerPort
from lib.providers.lifecycle_preflight import LegacyLifecyclePreflight
from lib.providers.lifecycle_preflight_protocol import NativePreflightTransport,ReplayPreflightTransport
from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
from lib.providers.synthetic_ledger_effects import NativeLedgerEffects
from lib.synthetic_ledger_replay_effects import ReplayLedgerEffects
from lib.personal_channel_ports import exclusive_factory
from lib.providers.retained_argparse import capture_context
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from test_v2_pilot_run_intake import CONTRACT,FIXTURE,transaction_name

class WholeFreshPilotRun(unittest.TestCase):
    def setUp(self):
        f=preflight_reference.WholeLivePreflight();f.setUp();self.addCleanup(f.doCleanups);self.fixture=f
    def compare(self,kind,native=True):
        root,tools,_,at,_=self.fixture.selected(kind if kind in ('metadata-race','invalid-json') else 'normal')
        for name,row in CONTRACT['files'].items():
            raw=(FIXTURE/row['fixture']).read_bytes();p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        ledger=root/'governance/lifecycle/live-validation'
        if kind!='duplicate':shutil.rmtree(ledger)
        seq=99 if kind in ('duplicate','stale') else 0
        receipt_at=(ActualDatetime.fromisoformat(at.replace('Z','+00:00'))+timedelta(seconds=1)).isoformat().replace('+00:00','Z')
        parent=root.parent/('temporary-'+str(self.fixture.fixture.serial));parent.mkdir(mode=0o700)
        temporary=parent/'tmpboundcase';partial=str(temporary/'capture/repository.json')
        if kind=='large-valid':
            config=json.loads((tools/'responses.json').read_bytes());endpoint=next(name for name in config if '/actions/' not in name and '/contents/' not in name)
            raw=base64.b64decode(config[endpoint][0]);config[endpoint]=[base64.b64encode(b' '*(13*1024**2)+raw).decode('ascii')];(tools/'responses.json').write_text(json.dumps(config))
        # The selected fake replies contain the same explicit original run ID.
        replies=json.loads((tools/'responses.json').read_bytes());endpoint=next(name for name in replies if '/actions/runs/' in name and '?' not in name)
        run_id=endpoint.rsplit('/',1)[1];argv=['--run-id',run_id,'--expected-sequence',str(seq)]
        original=r'''import errno,io,json,os,runpy,stat,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime as ActualDatetime
import lib.governance_lifecycle.live_evidence as evidence
at,receipt_at,parent,kind,partial=sys.argv[1:6];script=sys.argv[6];sys.argv=sys.argv[6:]
class CaptureClock:
 @staticmethod
 def now(zone):return ActualDatetime.fromisoformat(at.replace('Z','+00:00')).astimezone(zone)
class ReceiptClock:
 @staticmethod
 def now(zone):return ActualDatetime.fromisoformat(receipt_at.replace('Z','+00:00')).astimezone(zone)
evidence.datetime=CaptureClock
original_temp=tempfile.TemporaryDirectory
create_names=tempfile._get_candidate_names
def create():
 with patch('tempfile._get_candidate_names',return_value=iter(['boundcase'])):return original_temp(dir=parent)
class Partial:
 def __init__(self,stream):self.stream=stream
 def __getattr__(self,name):return getattr(self.stream,name)
 def __enter__(self):return self
 def __exit__(self,*args):return self.stream.__exit__(*args)
 def write(self,raw):self.stream.write(raw[:7]);self.stream.flush();raise OSError(28,'No space left on device')
original_open=io.open
def opened(file,mode='r',*args,**kwargs):
 stream=original_open(file,mode,*args,**kwargs)
 return Partial(stream) if kind=='partial-seven' and mode=='xb' and str(file)==partial else stream
original_sync=os.fsync
def sync(fd):
 if kind=='directory-fsync' and stat.S_ISDIR(os.fstat(fd).st_mode):raise OSError(errno.EIO,'receipt directory sync failed')
 return original_sync(fd)
def cleanup(name,**kwargs):
 (Path(name)/'capture/repository.json').unlink();raise OSError(errno.EIO,'cleanup failed after receipt publication')
packet=runpy.run_path(script,run_name='whole_original_fixture');main=packet['main'];main.__globals__['datetime']=ReceiptClock;main.__globals__['tempfile']=SimpleNamespace(TemporaryDirectory=create)
with patch('io.open',side_effect=opened),patch('os.fsync',side_effect=sync):
 if kind=='cleanup-failure':
  with patch.object(original_temp,'_rmtree',side_effect=cleanup):main()
 else:main()
'''
        env={**os.environ,'PYTHONPATH':str(root/'scripts'),'PYTHONDONTWRITEBYTECODE':'1','PATH':str(tools)+os.pathsep+os.environ['PATH'],'COLUMNS':'60','LINES':'24'}
        before=reference.snapshot(root);old=subprocess.run([sys.executable,'-B','-c',original,at,receipt_at,str(parent),kind,partial,str(root/'scripts/intake_lifecycle_pilot_run.py'),*argv],cwd=root,env=env,capture_output=True,timeout=180)
        code=0 if kind in ('normal','duplicate','large-valid') else 1;self.assertEqual(old.returncode,code,(kind,old.stderr[-4000:]))
        expected=reference.snapshot(root);temp_expected=reference.snapshot(parent);reference.restore(root,before)
        if temporary.exists():shutil.rmtree(temporary)
        calls=tools/'calls.jsonl';old_calls=calls.read_bytes();calls.unlink()
        state=root.parent/('state-fresh-'+str(self.fixture.fixture.serial));state.mkdir(mode=0o700)
        record=Record(state/'records',{'test':'whole original fresh pilot-run '+kind},{'source_only':True});record.append({'kind':'execution-intent'})
        mode='selected-files' if native else 'private-candidate'
        owner=NativeRunIO(record,mode=mode,cwd=str(root),private_state=state,product_root=ROOT,ledger=str(ledger),transaction_name=transaction_name)
        with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}):parser=capture_context()
        class FixedTemporary(NativeTemporary):
            def create_resource(self,parent):
                with patch('tempfile._get_candidate_names',return_value=iter(['boundcase'])):return super().create_resource(parent)
        class FixedFactory(NativeTemporaryFactory):
            def TemporaryDirectory(self):return FixedTemporary(self.owner,self.parent)
        class FixedPrivateFactory(PrivateTemporaryFactory):
            def candidate(self):return str(temporary)
        ports={}
        def fresh(context,emit,replay=False):
            transport=ReplayPreflightTransport(owner=ports['owner'],root=context.root,emit_stderr=emit) if replay else NativePreflightTransport(owner=ports['owner'],root=context.root,emit_stderr=emit,provider_executable=str(tools/'gh'))
            ports['transport']=transport
            return LegacyLifecyclePreflight(context,transport=transport,clock=transport.clock)
        def selected_exclusive(io,path,label):
            value=exclusive_factory(io,path,label)
            if kind=='partial-seven' and path==partial and hasattr(io,'record'):
                class Partial:
                    def __init__(self,stream):self.stream=stream
                    def __getattr__(self,name):return getattr(self.stream,name)
                    def write(self,raw):self.stream.write(raw[:7]);self.stream.flush();raise OSError(28,'No space left on device')
                value.stream=Partial(value.stream)
            return value
        common={'validator_class':Draft202012Validator,'historical_provider_factory':lambda context:LegacyRepositoryLifecycleCapture(context),'exclusive_factory':selected_exclusive,'parser_context':parser,'clock_factory':lambda io:ports['transport'].clock}
        samples=iter([at,receipt_at]);clock_calls=[]
        class Clock:
            @staticmethod
            def now(zone):
                value=next(samples);clock_calls.append(value);return ActualDatetime.fromisoformat(value.replace('Z','+00:00')).astimezone(zone)
        original_sync=NativeLedgerEffects.sync_descriptor
        def sync(self,fd):
            if kind=='directory-fsync' and stat.S_ISDIR(os.fstat(fd).st_mode):raise OSError(5,'receipt directory sync failed')
            return original_sync(self,fd)
        def fail_cleanup(name,**kwargs):
            (Path(name)/'capture/repository.json').unlink();raise OSError(5,'cleanup failed after receipt publication')
        ports['owner']=owner
        with ExitStack() as stack:
            stack.enter_context(patch('lib.providers.personal_channel_transport.datetime',Clock))
            stack.enter_context(patch.object(NativeLedgerEffects,'sync_descriptor',sync))
            if kind=='cleanup-failure':stack.enter_context(patch.object(tempfile.TemporaryDirectory,'_rmtree',side_effect=fail_cleanup))
            result=execute(str(root),str(root),argv,owner,effects_factory=lambda io:NativeLedgerEffects(io,str(ledger),transaction_name=transaction_name) if native else PrivateLedgerPort(io,str(ledger)),fresh_provider_factory=fresh,temporary_factory=lambda io:FixedFactory(io,str(parent)) if native else FixedPrivateFactory(io,str(parent)),**common)
        self.assertFalse(record.capture_incomplete,(kind,result));self.assertEqual(result['exit_code'],old.returncode,result);self.assertEqual(result['stdout'].encode(),old.stdout)
        if result['kernel_exception'] is None:self.assertEqual(result['stderr'].encode(),old.stderr)
        else:
            error=result['kernel_exception'];self.assertTrue(old.stderr.endswith((error['type']+': '+error['message']+'\n').encode()),(result,old.stderr[-2500:]))
        if native:self.assertEqual(reference.snapshot(root),expected);self.assertEqual(reference.snapshot(parent),temp_expected)
        else:
            self.assertEqual(reference.snapshot(root),before);self.assertEqual(reference.snapshot(parent),({},{}))
            for base,initial,wanted in ((root,before,expected),(parent,({},{}),temp_expected)):
                files,dirs=map(dict,initial)
                for label,value in owner.projected_changes.items():
                    if not Path(label).is_relative_to(base):continue
                    name=Path(label).relative_to(base).as_posix()
                    if value['kind']=='file':files[name]=((record.blobs/value['content']['sha256']).read_bytes(),value['mode'])
                    elif value['kind']=='directory':dirs[name]=value['mode']
                    elif value['kind']=='missing':files.pop(name,None);dirs.pop(name,None)
                    else:self.fail(value)
                self.assertEqual((files,dirs),wanted)
        self.assertEqual(calls.read_bytes(),old_calls)
        self.assertFalse(result['kernel_end_ledger_descriptors']);self.assertEqual(clock_calls,[] if kind in ('metadata-race','invalid-json') else [at] if kind=='partial-seven' else [at,receipt_at])
        if kind=='large-valid':
            if native:self.assertGreater(next((ledger/'transactions').glob('*.json')).stat().st_size,16*1024**2)
            else:self.assertTrue(any(value.get('kind')=='file' and value['content']['bytes']>16*1024**2 for name,value in owner.projected_changes.items() if Path(name).parent==ledger/'transactions'))
        if kind in ('directory-fsync','cleanup-failure'):self.assertEqual(len(list((ledger/'transactions').glob('*.json'))),1);self.assertEqual(result['stdout'],'')
        if kind=='cleanup-failure':self.assertFalse((temporary/'capture/repository.json').exists());self.assertTrue(temporary.is_dir())
        self.assertFalse(any(str(p).startswith(str(temporary)) for p in owner.files) if kind!='cleanup-failure' else False)
        record.finish('complete',{'exit_code':result['exit_code'],'kernel_result':result},owner.touched)
        _,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
        def inert(ref):
            raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return raw
        shutil.rmtree(root);shutil.rmtree(parent);shutil.rmtree(tools)
        replay=ReplayRunIO(events,inert,mode,str(root),ledger=str(ledger),transaction_name=transaction_name);ports['owner']=replay
        with patch('os.open',side_effect=AssertionError('No selected source')),patch('subprocess.Popen',side_effect=AssertionError('No provider')),patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No temporary creation')):
            actual=execute(str(root),str(root),argv,replay,effects_factory=lambda io:ReplayLedgerEffects(io,str(ledger),transaction_name=transaction_name) if native else PrivateLedgerPort(io,str(ledger)),fresh_provider_factory=lambda context,emit:fresh(context,emit,True),temporary_factory=lambda io:ReplayTemporaryFactory(io,str(parent)) if native else FixedPrivateFactory(io,str(parent)),**common);replay.finish()
        self.assertEqual(actual,result);self.assertEqual(replay.files,owner.files);self.assertEqual(replay.writes,owner.writes);self.assertEqual(replay.touched,owner.touched);self.assertEqual(replay.projected_changes,owner.projected_changes);self.assertEqual(seen,set(cache))
        for name in seen:blob({'sha256':name,'bytes':len(cache[name])})
        self.assertTrue(closed())
    def both(self,kind):
        for native in (True,False):
            with self.subTest(kind=kind,native=native):self.compare(kind,native)
    def test_complete_original_fresh_main_two_clocks_atomic_receipt_and_cleanup(self):self.both('normal')
    def test_complete_original_fresh_duplicate_precedes_stale_sequence(self):self.both('duplicate')
    def test_complete_original_stale_sequence_cleans_capture_and_releases_lock(self):self.both('stale')
    def test_complete_original_metadata_race_and_invalid_JSON_clean_temporary_before_clock(self):
        for kind in ('metadata-race','invalid-json'):
            with self.subTest(kind=kind):self.both(kind)
    def test_original_partial_seven_byte_capture_error_is_cleaned_without_a_receipt(self):self.compare('partial-seven')
    def test_original_receipt_directory_fsync_error_keeps_receipt_then_cleans_capture(self):self.compare('directory-fsync')
    def test_original_cleanup_error_keeps_published_receipt_and_partial_capture_without_print(self):self.compare('cleanup-failure')
    def test_complete_original_large_valid_fresh_capture_publishes_receipt_above_16MiB(self):self.both('large-valid')

if __name__=='__main__':unittest.main(verbosity=2)
