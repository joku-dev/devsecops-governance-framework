"""Actual original xb byte effects, close errors, pure replay and release boundaries."""
from pathlib import Path
from unittest.mock import patch
import copy,errno,gc,hashlib,json,os,sys,tempfile,unittest,weakref
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.personal_channel_exclusive import NativeExclusive
from lib.personal_channel_exclusive import ReplayExclusive
from lib.synthetic_lifecycle_io import ReplayIO
from lib.requirement_review_output import RetainedOutputError
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError

class FaultStream:
    def __init__(self,stream,kind,label):self.stream,self.kind,self.label=stream,kind,label
    @property
    def closed(self):return self.stream.closed
    def fileno(self):return self.stream.fileno()
    def __enter__(self):self.stream.__enter__();return self
    def __exit__(self,*error):self.close()
    def write(self,raw):
        if self.kind=='write7':
            self.stream.write(raw[:7]);self.stream.flush();raise OSError(errno.ENOSPC,os.strerror(errno.ENOSPC),self.label)
        if self.kind=='short':self.stream.write(raw[:7]);return min(7,len(raw))
        return self.stream.write(raw)
    def close(self):
        if self.kind=='unclosed':raise OSError(errno.ENOSPC,os.strerror(errno.ENOSPC),self.label)
        self.stream.close()
        if self.kind=='close':raise OSError(errno.ENOSPC,os.strerror(errno.ENOSPC),self.label)

class WholeExclusiveCapture(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old)
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.parent=Path(temp.name).resolve();self.serial=0

    def owner(self,case):
        self.serial+=1;private=self.parent/('private-'+str(self.serial));private.mkdir(mode=0o700)
        record=Record(private/'records',{'prototype':'exclusive original binary observation'},{'prototype':True});record.append({'kind':'execution-intent','test_case':case})
        owner=NativeIO(record,mode='selected-files',cwd=str(self.parent),private_state=private,product_root=ROOT)
        return record,owner

    def compare(self,*,kind='normal',before=None,payload=b'complete\x00capture\xffbytes',mask=0o077):
        self.serial+=1;data=self.parent/('data-'+str(self.serial));data.mkdir(mode=0o700);path=data/'capture.json'
        if before=='file':path.write_bytes(b'existing opaque\x00\xff');path.chmod(0o640)
        if before=='directory':path.mkdir(mode=0o700)
        pre=None if before is None else (path.read_bytes(),path.stat().st_mode&511) if before=='file' else 'directory'
        def state():return ('file',path.read_bytes(),path.stat().st_mode&511) if path.is_file() else ('directory',path.stat().st_mode&511) if path.is_dir() else ('missing',)
        oldmask=os.umask(mask)
        try:
            error=None;count=None
            try:
                stream=path.open('xb')
                if kind!='normal':stream=FaultStream(stream,kind,str(path))
                with stream:count=stream.write(payload)
            except OSError as caught:error={'type':type(caught).__name__,'message':str(caught)}
            expected=state()
            if kind=='unclosed':
                # The unobserved original stream is cleaned separately; this
                # case has no complete accepted original verdict below.
                stream.stream.close()
            if pre is None and path.is_file():path.unlink()
            elif before=='file':self.assertEqual((path.read_bytes(),path.stat().st_mode&511),pre)
            record,owner=self.owner(kind)
            native=NativeExclusive.open_stream
            def selected(handle):
                value=native(handle)
                return value if kind=='normal' else FaultStream(value,kind,str(path))
            captured=None;actual_count=None
            try:
                with patch.object(NativeExclusive,'open_stream',selected):
                    with NativeExclusive(owner,str(path),str(path)) as stream:actual_count=stream.write(payload)
            except RetainedOutputError as caught:captured={'type':caught.original_type,'message':caught.original_message}
            except InputAdmissionError as caught:
                if kind!='unclosed':raise
                captured={'capture_incomplete':str(caught)}
            self.assertEqual(state(),expected)
            if kind=='unclosed':
                self.assertTrue(record.capture_incomplete);session=owner.personal_exclusive_sessions[0]
                released=session.release();self.assertTrue(released['released']);self.assertFalse(released['original_verdict']);return
            self.assertEqual(captured,error);self.assertEqual(actual_count,count);self.assertFalse(record.capture_incomplete)
            for session in getattr(owner,'personal_exclusive_sessions',[]):self.assertTrue(session.release()['already_closed'])
            result={'exit_code':1 if error else 0,'error':error,'count':count,'files':owner.files,'writes':owner.writes}
            record.finish('complete',result,owner.touched)
            _,_,value,events,blob,closed=read_record(record.root)
            cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
            def inert(ref):
                raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return raw
            if path.is_file():path.unlink()
            elif path.is_dir():path.rmdir()
            replay=ReplayIO(events,inert,'selected-files',str(self.parent));replayed=None;replayed_count=None
            with patch('os.open',side_effect=AssertionError('Replay cannot open native files')),patch('os.write',side_effect=AssertionError('Replay cannot write')),patch('subprocess.Popen',side_effect=AssertionError('Replay cannot run programs')):
                try:
                    with ReplayExclusive(replay,str(path),str(path)) as stream:replayed_count=stream.write(payload)
                except RetainedOutputError as caught:replayed={'type':caught.original_type,'message':caught.original_message}
                replay.finish()
            self.assertEqual(replayed,error);self.assertEqual(replayed_count,count);self.assertEqual(replay.files,owner.files);self.assertEqual(replay.writes,owner.writes);self.assertEqual(replay.touched,owner.touched);self.assertEqual(seen,set(cache))
            for sha in seen:self.assertEqual(blob({'sha256':sha,'bytes':len(cache[sha])}),cache[sha])
            self.assertTrue(closed())
            return record,owner,events,blob,value
        finally:os.umask(oldmask)

    def test_whole_native_binary_and_empty_file_modes_match_original_and_replay(self):
        for raw in (b'',b'opaque\x00\xff\r\nUTF8-'+ 'ä'.encode()):
            for mask in (0o077,0o027):
                with self.subTest(raw=raw,mask=mask):self.compare(payload=raw,mask=mask)

    def test_existing_file_and_directory_are_not_replaced_or_truncated(self):
        for before in ('file','directory'):
            with self.subTest(before=before):self.compare(before=before)

    def test_original_seven_byte_failure_and_late_close_failure_replay_exact_bytes(self):
        for kind in ('write7','close','short'):
            with self.subTest(kind=kind):self.compare(kind=kind)

    def test_unclosed_close_error_is_incomplete_and_cleanup_is_not_original_verdict(self):
        self.compare(kind='unclosed')

    def test_journal_return_failure_does_not_turn_unobserved_cleanup_flush_into_original_verdict(self):
        data=self.parent/'journal-data';data.mkdir(mode=0o700);path=data/'capture.json';record,owner=self.owner('journal-abort')
        stream=NativeExclusive(owner,str(path),str(path));original=record.append
        def append(row):
            if row.get('kind')=='returned':raise OSError(errno.ENOSPC,os.strerror(errno.ENOSPC))
            return original(row)
        with patch.object(record,'append',append):
            with self.assertRaises(InputAdmissionError):
                with stream:stream.write(b'buffered original payload')
        self.assertTrue(record.capture_incomplete);self.assertFalse(stream.resource.closed);self.assertEqual(path.read_bytes(),b'')
        released=stream.release();self.assertTrue(released['released']);self.assertFalse(released['original_verdict']);self.assertTrue(released['unobserved_close_may_flush']);self.assertEqual(path.read_bytes(),b'buffered original payload');self.assertFalse(owner.files)

    def test_replaced_descriptor_is_not_closed_by_release_or_later_object_collection(self):
        from lib.providers.personal_channel_exclusive import _QUARANTINED_STREAMS
        data=self.parent/'descriptor-data';data.mkdir(mode=0o700);path=data/'capture.json';other=data/'unowned.json';record,owner=self.owner('descriptor-replaced')
        stream=NativeExclusive(owner,str(path),str(path));token=stream.fd;os.close(token)
        replacement=os.open(other,os.O_RDWR|os.O_CREAT|os.O_EXCL,0o600)
        if replacement!=token:os.dup2(replacement,token);os.close(replacement)
        expected=os.fstat(token);saved=None;own=None
        resource=weakref.ref(stream.resource)
        try:
            with self.assertRaisesRegex(InputAdmissionError,'descriptor_replaced'):stream.release()
            actual=os.fstat(token);self.assertEqual((actual.st_dev,actual.st_ino),(expected.st_dev,expected.st_ino));self.assertTrue(record.capture_incomplete);self.assertTrue(any(item is stream.resource for item in _QUARANTINED_STREAMS));self.assertFalse(stream.resource.closed)
            del stream,owner;gc.collect();self.assertIsNotNone(resource());actual=os.fstat(token);self.assertEqual((actual.st_dev,actual.st_ino),(expected.st_dev,expected.st_ino));self.assertFalse(resource().closed)
        finally:
            # The test owns both descriptors and explicitly restores the
            # selected inode before disposing of the quarantined object.
            saved=os.dup(token);own=os.open(path,os.O_WRONLY);os.dup2(own,token);os.close(own);resource().close();os.close(saved)
            _QUARANTINED_STREAMS[:]=[item for item in _QUARANTINED_STREAMS if item is not resource()]

    def test_resealed_wrong_content_and_descriptor_and_closed_state_are_rejected(self):
        for attack in ('bytes','identity','closed'):
            with self.subTest(attack=attack):
                _,_,events,blob,_=self.compare();changed=copy.deepcopy(events)
                returned=[row for row in changed if row.get('kind')=='returned'][-1];wire=json.loads(blob(returned['value']))
                extra={}
                if attack=='bytes':
                    raw=b'forged';ref={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};extra[ref['sha256']]=raw;wire['snapshot']['content']=ref
                elif attack=='identity':wire['opened_file']['identity'][1]+=1
                else:wire['closed']=False
                raw=(json.dumps(wire,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':'))+'\n').encode();ref={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};extra[ref['sha256']]=raw;returned['value']=ref
                def retained(ref):return extra[ref['sha256']] if ref['sha256'] in extra else blob(ref)
                replay=ReplayIO(changed,retained,'selected-files',str(self.parent));selection=changed[2]['selection']['path']
                with self.assertRaises((IntegrityError,ValueError)):
                    with ReplayExclusive(replay,selection,selection) as stream:stream.write(b'complete\x00capture\xffbytes')

if __name__=='__main__':unittest.main(verbosity=2)
