"""Actual private-file metadata and complete original check through inert replay."""
from pathlib import Path
from unittest.mock import patch
import copy,errno,json,os,shutil,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.providers.consumer_lifecycle_storage import Record,read_record
from lib.providers.provider_observation_private_ports import NativePrivateMetadata
from lib.provider_observation_private_ports import ReplayPrivateMetadata,MetadataProtocol
from lib.private_credentials import check_private_file
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from test_v2_provider_observation_reads import Cursor


class PrivateMetadataPorts(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old);temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.base=Path(temporary.name).resolve();self.file=self.base/'credential';self.file.write_bytes(b'Synthetic payload that no metadata operation may retain\n');self.state=self.base/'records';self.state.mkdir(mode=0o700)
    def run_check(self,*,path=None,mode=0o600):
        self.file.chmod(mode);path=path or self.file;record=Record(self.state,{'private_metadata_only':True},{'no_authority':True});port=NativePrivateMetadata(record,cwd=str(self.base),files=[str(path)]);before=self.file.read_bytes();original=actual=None
        try:check_private_file(path)
        except Exception as caught:original={'type':type(caught).__name__,'message':str(caught)}
        try:port.check_private_file(port.path(str(path)))
        except Exception as caught:actual={'type':type(caught).__name__,'message':str(caught)}
        resources=port.release_resources();self.assertEqual(actual,original);self.assertEqual(self.file.read_bytes(),before);record.finish('incomplete' if record.capture_incomplete else 'complete',{'exit_code':0 if actual is None else 1},{});_,_,_,events,blob,closed=read_record(record.root)
        for member in record.root.rglob('*'):
            if member.is_file():self.assertNotIn(before.strip(),member.read_bytes())
        return record,port,actual,events,blob,closed,resources,path
    def replay(self,captured):
        record,port,error,events,blob,closed,resources,path=captured;cursor=Cursor(events);cursor.position=1;cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};moved=self.base.with_name(self.base.name+'-source-absent');self.base.rename(moved)
        try:
            with patch('os.open',side_effect=AssertionError('No metadata source open')),patch('os.stat',side_effect=AssertionError('No metadata source stat')),patch('subprocess.Popen',side_effect=AssertionError('No programs')):
                pure=ReplayPrivateMetadata(cursor,lambda ref:cache[ref['sha256']],cwd=str(self.base),files=[str(path)]);actual=None
                try:pure.check_private_file(pure.path(str(path)))
                except (IntegrityError,InputAdmissionError):raise
                except Exception as caught:actual={'type':type(caught).__name__,'message':str(caught)}
                self.assertEqual(actual,error);self.assertEqual(cursor.position,len(events)-1);self.assertEqual(pure.descriptors,{})
                self.assertEqual(pure.successful_private_checks,port.successful_private_checks)
        finally:moved.rename(self.base)
        for name,raw in cache.items():blob({'sha256':name,'bytes':len(raw)})
        self.assertTrue(closed())
    def test_full_original_check_of_real_private_file_and_replay_without_any_filesystem(self):
        c=self.run_check();self.assertFalse(c[6]['required']);self.assertIsNone(c[2]);self.assertIn(str(self.file),c[1].successful_private_checks);self.replay(c)
    def test_original_missing_symlink_public_file_and_directory_failures_replay(self):
        for kind in ('missing','symlink','public','directory'):
            with self.subTest(kind=kind):
                path=self.base/'missing' if kind=='missing' else self.file
                if kind=='symlink':path=self.base/'link';path.symlink_to(self.file)
                if kind=='directory':path=self.base
                c=self.run_check(path=path,mode=0o644 if kind=='public' else 0o600);self.assertIsNotNone(c[2]);self.assertEqual(c[1].successful_private_checks,{});self.replay(c)
    def test_payload_read_is_not_a_metadata_capability(self):
        record=Record(self.state,{'private_metadata_only':True},{'no_authority':True});port=NativePrivateMetadata(record,cwd=str(self.base),files=[str(self.file)])
        with self.assertRaisesRegex(InputAdmissionError,'payload_read_forbidden'):port.path(str(self.file)).read_text()
        self.assertEqual(port.raw_descriptors,{})
    def test_native_fstat_failure_preserves_original_finally_close(self):
        record=Record(self.state,{'private_metadata_only':True},{'no_authority':True});port=NativePrivateMetadata(record,cwd=str(self.base),files=[str(self.file)]);native=port.native
        def fail(operation,args):
            if operation=='fstat':raise OSError(errno.EIO,'Controlled fstat failure')
            return native(operation,args)
        port.native=fail
        with self.assertRaises(OSError) as caught:port.check_private_file(port.path(str(self.file)))
        self.assertEqual(caught.exception.errno,errno.EIO);self.assertEqual(port.raw_descriptors,{});self.assertFalse(port.release_resources()['required']);self.assertFalse(record.capture_incomplete)
    def test_lost_fstat_completion_stops_original_native_IO_and_closes_only_owned_fd_as_extra_cleanup(self):
        record=Record(self.state,{'private_metadata_only':True},{'no_authority':True});port=NativePrivateMetadata(record,cwd=str(self.base),files=[str(self.file)]);append=record.append;pending=None;native=port.native;native_calls=[]
        def observe(operation,args):native_calls.append(operation);return native(operation,args)
        port.native=observe
        def lose(row):
            nonlocal pending
            if row.get('kind')=='provider-private-intent':pending=row['action']
            if row.get('kind')=='provider-private-outcome' and pending=='fstat':raise OSError('Controlled metadata completion loss')
            return append(row)
        record.append=lose
        with self.assertRaises(InputAdmissionError):port.check_private_file(port.path(str(self.file)))
        self.assertNotIn('close',native_calls);self.assertTrue(record.capture_incomplete);resources=port.release_resources();self.assertTrue(resources['required']);self.assertEqual(resources['outside_original_cleanup'][0]['state'],'closed');self.assertEqual(port.raw_descriptors,{})
    def test_resealed_stat_boolean_flags_and_descriptor_counters_are_rejected(self):
        c=self.run_check();events=c[3]
        for kind in ('stat-type','flags','fd'):
            with self.subTest(kind=kind):
                changed=copy.deepcopy(events)
                if kind=='stat-type':next(x for x in changed if x.get('kind')=='provider-private-outcome' and isinstance(x['packet']['value'],dict) and 'st_mode' in x['packet']['value'])['packet']['value']['st_uid']=False
                elif kind=='flags':next(x for x in changed if x.get('action')=='open')['arguments']['flags']=True
                else:next(x for x in changed if x.get('action')=='close')['arguments']['descriptor']=True
                cursor=Cursor(changed);cursor.position=1;pure=ReplayPrivateMetadata(cursor,lambda ref:b'',cwd=str(self.base),files=[str(self.file)])
                with self.assertRaises((IntegrityError,InputAdmissionError)):pure.check_private_file(pure.path(str(self.file)))
                position=cursor.position
                with self.assertRaises((IntegrityError,InputAdmissionError)):pure.geteuid()
                self.assertEqual(position,cursor.position)
