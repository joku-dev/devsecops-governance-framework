"""Whole original exclusive effects projected privately and replayed without source access."""
from pathlib import Path
from unittest.mock import patch
import hashlib,os,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.synthetic_lifecycle_io import ReplayIO
from lib.personal_channel_private import PrivateExclusive

class PrivateCapture(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old)
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.root=Path(temp.name).resolve();self.serial=0
    def compare(self,kind):
        self.serial+=1;data=self.root/('data-'+str(self.serial));data.mkdir(mode=0o700);path=data/'capture.json'
        if kind=='file':path.write_bytes(b'original opaque\x00\xff')
        if kind=='directory':path.mkdir(mode=0o700)
        if kind=='missing-parent':path=data/'missing/capture.json'
        payload=b'' if kind=='empty' else b'capture\x00\xffbytes'
        def state():
            return {p.relative_to(data).as_posix():('directory',p.stat().st_mode&511) if p.is_dir() else ('file',p.read_bytes(),p.stat().st_mode&511) for p in data.rglob('*')}
        before=state();error=None
        try:
            with path.open('xb') as stream:count=stream.write(payload)
        except OSError as caught:error={'type':type(caught).__name__,'message':str(caught)}
        expected=state()
        if kind in ('normal','empty'):path.unlink()
        self.assertEqual(state(),before)
        private=self.root/('private-'+str(self.serial));private.mkdir(mode=0o700);record=Record(private/'records',{'prototype':'private exclusive'},{'prototype':True});record.append({'kind':'execution-intent'})
        owner=NativeIO(record,mode='private-candidate',cwd=str(data),private_state=private,product_root=ROOT);actual=None
        try:
            with PrivateExclusive(owner,str(path),str(path)) as stream:self.assertEqual(stream.write(payload),len(payload))
        except OSError as caught:actual={'type':type(caught).__name__,'message':str(caught)}
        self.assertEqual(actual,error);self.assertEqual(state(),before)
        candidate=dict(before)
        for name,value in owner.projected_changes.items():
            relative=Path(name).relative_to(data).as_posix()
            if value['kind']=='file':candidate[relative]=('file',(record.blobs/value['content']['sha256']).read_bytes(),value['mode'])
            elif value['kind']=='directory':candidate[relative]=('directory',value['mode'])
            else:self.fail(value)
        self.assertEqual(candidate,expected)
        record.finish('complete',{'exit_code':1 if error else 0,'error':error},owner.touched)
        _,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
        def inert(ref):
            raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return raw
        import shutil
        shutil.rmtree(data)
        replay=ReplayIO(events,inert,'private-candidate',str(data));replayed=None
        with patch('os.open',side_effect=AssertionError('No native open')),patch('os.write',side_effect=AssertionError('No native write')),patch('subprocess.Popen',side_effect=AssertionError('No native program')):
            try:
                with PrivateExclusive(replay,str(path),str(path)) as stream:self.assertEqual(stream.write(payload),len(payload))
            except OSError as caught:replayed={'type':type(caught).__name__,'message':str(caught)}
            replay.finish()
        self.assertEqual(replayed,error);self.assertEqual(replay.projected_changes,owner.projected_changes);self.assertEqual(replay.files,owner.files);self.assertEqual(replay.writes,owner.writes);self.assertEqual(seen,set(cache))
        for sha in seen:blob({'sha256':sha,'bytes':len(cache[sha])})
        self.assertTrue(closed())
    def test_all_original_private_exclusive_cases_preserve_source_and_full_candidate(self):
        for kind in ('normal','empty','file','directory','missing-parent'):
            with self.subTest(kind=kind):self.compare(kind)

if __name__=='__main__':unittest.main(verbosity=2)
