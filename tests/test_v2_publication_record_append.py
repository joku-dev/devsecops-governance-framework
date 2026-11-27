"""Actual append prefixes/modes and explicitly injected IO failures; no disk exhaustion."""
from pathlib import Path
from unittest.mock import patch
from copy import deepcopy
from types import SimpleNamespace
import errno,hashlib,json,os,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
from lib.providers.operational_publication_paths import NativePublisherPaths
from lib.operational_publication_paths import ReplayPublisherPaths,ReplayAppend
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.pilot_run_intake_io import ReplayRunIO
from lib.pilot_run_intake_ports import ledger,transaction_name
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.requirement_review_output import RetainedOutputError
from lib.requirement_validation_replay import IntegrityError
class PublisherAppendFaults(unittest.TestCase):
    def setUp(self):
        previous=os.umask(0o077);self.addCleanup(os.umask,previous);tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.base=Path(tmp.name).resolve();self.source=self.base/'source';self.source.mkdir(mode=0o700);self.private=self.base/'state';self.private.mkdir(mode=0o700);self.output=self.base/'pipeline-output';self.output.write_bytes(b'prior\n')
    def capture(self,*,partial=False,close_error=False):
        record=Record(self.private/'records',{'test':'owned append IO observations'},{'prototype':True});record.append({'kind':'execution-intent'});owner=NativeRunIO(record,mode='private-candidate',cwd=str(self.base),private_state=self.private,ledger=ledger(str(self.source)),transaction_name=transaction_name)
        paths=NativePublisherPaths(owner,source=str(self.source),outputs=[str(self.output)]);session=paths.append(str(self.output),str(self.output));text='pull_request_url=https://example.invalid/review/123\n';error=None
        class PartialDisk:
            def __init__(self,stream):self.stream=stream;self.closed=False
            def write(self,value):
                os.write(self.stream.fileno(),value.encode('utf-8')[:7]);raise OSError(errno.ENOSPC,os.strerror(errno.ENOSPC))
            def close(self):
                self.stream.close();self.closed=True
                if close_error:raise OSError(errno.EIO,os.strerror(errno.EIO))
        try:
            with session:
                if partial:session.stream=PartialDisk(session.stream)
                session.write(text)
        except RetainedOutputError as caught:error={'type':caught.original_type,'message':caught.original_message}
        record.finish('complete',{'exit_code':1 if error else 0},owner.touched);_,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};trace=deepcopy(paths.appends);moved=self.base.with_name(self.base.name+'-unavailable');self.base.rename(moved)
        try:
            replay=ReplayRunIO(events,lambda ref:cache[ref['sha256']],'private-candidate',str(self.base),ledger=ledger(str(self.source)),transaction_name=transaction_name);pure=ReplayPublisherPaths(replay,source=str(self.source),outputs=[str(self.output)]);observed=None
            with patch('os.open',side_effect=AssertionError('No output/source open')):
                try:
                    with pure.append(str(self.output),str(self.output)) as stream:stream.write(text)
                except RetainedOutputError as caught:observed={'type':caught.original_type,'message':caught.original_message}
                replay.finish()
            self.assertEqual(observed,error);self.assertEqual(pure.appends,trace)
        finally:moved.rename(self.base)
        for name,raw in cache.items():blob({'sha256':name,'bytes':len(raw)})
        self.assertTrue(closed());return error,trace,cache
    def test_physical_short_write_then_error_keeps_exact_prefix_after_successful_close(self):
        error,trace,_=self.capture(partial=True);self.assertEqual(error,{'type':'OSError','message':str(OSError(errno.ENOSPC,os.strerror(errno.ENOSPC)))});self.assertEqual(self.output.read_bytes(),b'prior\npull_re');self.assertEqual([v['operation'] for v in trace],['open','write','close'])
    def test_original_close_error_overrides_body_error_with_retained_partial_bytes(self):
        error,_,_=self.capture(partial=True,close_error=True);self.assertEqual(error,{'type':'OSError','message':str(OSError(errno.EIO,os.strerror(errno.EIO)))});self.assertEqual(self.output.read_bytes(),b'prior\npull_re')
    def test_resealed_successful_close_cannot_hide_changed_bytes_or_native_mode(self):
        _,trace,cache=self.capture();events=[]
        def raw(ref):
            value=cache[ref['sha256']];self.assertEqual(hashlib.sha256(value).hexdigest(),ref['sha256']);self.assertEqual(len(value),ref['bytes']);return value
        for attack in ('bytes','mode'):
            paths=SimpleNamespace(owner=SimpleNamespace(blob=raw),appends=[]);decoder=ReplayAppend(paths,str(self.output),str(self.output))
            for step in trace:
                wire={k:deepcopy(step[k]) for k in ('before','after','return_value','error')};kind=step['operation'];text='pull_request_url=https://example.invalid/review/123\n' if kind=='write' else None;args={'path':str(self.output),'label':str(self.output),'mode':'a','encoding':'utf-8','text':text};wire['specification']=args
                if kind=='close':
                    if attack=='bytes':wire['after']['content']=trace[0]['before']['content']
                    else:wire['after']['mode']^=0o100
                    with self.assertRaises(IntegrityError):decoder.decode(kind,args,wire,text)
                else:decoder.decode(kind,args,wire,text)
