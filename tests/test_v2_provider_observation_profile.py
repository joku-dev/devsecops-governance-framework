"""Checked profile bytes retain UTF8 and service-ACL admission without credential reads."""
from pathlib import Path
from unittest.mock import patch
import copy,errno,json,os,stat,struct,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.providers.consumer_lifecycle_storage import Record,read_record
from lib.providers.provider_observation_private_ports import NativePrivateMetadata
from lib.provider_observation_private_ports import ReplayPrivateMetadata,STAT_FIELDS
from lib.providers.provider_observation_profile import NativeCheckedProfile
from lib.provider_observation_profile import ReplayCheckedProfile
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from test_v2_provider_observation_reads import Cursor


class CheckedProfileData(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old);temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name).resolve();self.file=self.base/'profile.json';self.file.write_bytes(b'{"line":"one"}\r\n');self.state=self.base/'records';self.state.mkdir(mode=0o700)
    def create(self):
        record=Record(self.state,{'profile_bytes_only':True},{'no_authority':True});meta=NativePrivateMetadata(record,cwd=str(self.base),files=[str(self.file)]);meta.check_private_file(meta.path(str(self.file)));return record,meta,NativeCheckedProfile(record,meta,profile=str(self.file))
    def test_actual_profile_bytes_and_universal_newlines_replay_without_source(self):
        record,meta,profile=self.create();expected=self.file.read_text(encoding='utf-8');self.assertEqual(profile.read(meta.path(str(self.file)),'utf-8',None),expected);profile.release_resources();meta.release_resources();record.finish('complete',{'exit_code':0},{})
        _,_,_,events,blob,closed=read_record(record.root);cursor=Cursor(events);cursor.position=1;consumed=set();cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};moved=self.base.with_name(self.base.name+'-absent');self.base.rename(moved)
        def retained(ref):consumed.add(ref['sha256']);return cache[ref['sha256']]
        try:
            with patch('os.open',side_effect=AssertionError('No profile source read')),patch('os.stat',side_effect=AssertionError('No profile source stat')):
                puremeta=ReplayPrivateMetadata(cursor,retained,cwd=str(self.base),files=[str(self.file)]);puremeta.check_private_file(puremeta.path(str(self.file)));pure=ReplayCheckedProfile(cursor,puremeta,retained,profile=str(self.file));self.assertEqual(pure.read(puremeta.path(str(self.file)),'utf-8',None),expected)
        finally:moved.rename(self.base)
        self.assertEqual(consumed,set(cache))
        for key in consumed:blob({'sha256':key,'bytes':len(cache[key])})
        self.assertTrue(closed())
    def test_original_UTF8_decode_failure_is_recomputed_from_profile_data(self):
        self.file.write_bytes(b'{"broken":"\xff"}');record,meta,profile=self.create()
        with self.assertRaises(UnicodeDecodeError) as old:self.file.read_text(encoding='utf-8')
        with self.assertRaises(UnicodeDecodeError) as actual:profile.read(meta.path(str(self.file)),'utf-8',None)
        self.assertEqual(str(actual.exception),str(old.exception));self.assertFalse(record.capture_incomplete);profile.release_resources();meta.release_resources();record.finish('complete',{'exit_code':1},{})
        _,_,_,events,blob,_=read_record(record.root);cursor=Cursor(events);cursor.position=1;puremeta=ReplayPrivateMetadata(cursor,blob,cwd=str(self.base),files=[str(self.file)]);puremeta.check_private_file(puremeta.path(str(self.file)));pure=ReplayCheckedProfile(cursor,puremeta,blob,profile=str(self.file))
        with self.assertRaises(UnicodeDecodeError) as replay:pure.read(puremeta.path(str(self.file)),'utf-8',None)
        self.assertEqual(str(replay.exception),str(old.exception))
    def test_other_role_changed_source_and_missing_private_admission_never_read_payload(self):
        record,meta,profile=self.create();other=self.base/'credential';other.write_bytes(b'Never record this credential');meta.targets=(*meta.targets,str(other));meta.check_private_file(meta.path(str(other)))
        with patch('lib.providers.provider_observation_profile.held_root',side_effect=AssertionError('No other-role payload')),self.assertRaises(InputAdmissionError):profile.read(meta.path(str(other)),'utf-8',None)
        self.assertTrue(record.capture_incomplete);self.assertEqual(list(record.blobs.iterdir()),[])
        record,meta,profile=self.create();self.file.write_bytes(b'Changed profile')
        with self.assertRaises(InputAdmissionError):profile.read(meta.path(str(self.file)),'utf-8',None)
        self.assertTrue(record.capture_incomplete);self.assertEqual(list(record.blobs.iterdir()),[])
    def test_record_completion_loss_after_profile_read_stops_without_retry(self):
        record,meta,profile=self.create();append=record.append
        def lose(row):
            if row.get('kind')=='provider-profile-read-outcome':raise OSError('Controlled profile completion loss')
            append(row)
        record.append=lose
        with self.assertRaises(InputAdmissionError):profile.read(meta.path(str(self.file)),'utf-8',None)
        with patch('lib.providers.provider_observation_profile.held_root',side_effect=AssertionError('No retry')),self.assertRaises(InputAdmissionError):profile.read(meta.path(str(self.file)),'utf-8',None)
        self.assertTrue(record.capture_incomplete);self.assertFalse(profile.release_resources()['required']);meta.release_resources()
    def test_root_service_ACL_facets_feed_actual_checked_data_read_without_a_current_UID_gate(self):
        logical='/run/credentials/fixture.service/profile.json';directory=str(Path(logical).parent);actual_path=self.file;expected={k:getattr(actual_path.stat(),k) for k in STAT_FIELDS};expected.update(st_uid=0,st_mode=stat.S_IFREG|0o440);uid=os.geteuid()
        record=Record(self.state,{'root_service_ACL_facets_simulated':True},{'live_privileged_service_acceptance':False})
        class ServiceMetadata(NativePrivateMetadata):
            def __init__(this):
                this.record=record;this.raw_descriptors={};this.failed=False;this.closed=False;this.initialize({'platform':'linux','O_RDONLY':0,'O_NOFOLLOW':131072},str(self.base),[logical]);this.append({'kind':'provider-private-context','context':this.context})
            def native(this,operation,args):
                if operation=='is_symlink':return False
                if operation=='open':token=this.last_descriptor+1;this.raw_descriptors[token]={'fd':None};return token
                if operation=='fstat':return expected
                if operation=='close':this.raw_descriptors.pop(args['descriptor']);return None
                if operation=='geteuid':return uid
                if operation=='environment':return directory
                if operation=='stat':return {**expected,'st_mode':stat.S_IFDIR|0o550}
                if operation=='resolve':return directory
                if operation=='mountinfo':return '35 29 0:32 / '+directory+' ro - tmpfs tmpfs ro\n'
                if operation=='getxattr':
                    permission=4 if 'descriptor' in args else 5;rows=[(1,permission,0xffffffff),(2,permission,uid),(4,0,0xffffffff),(16,permission,0xffffffff),(32,0,0xffffffff)];return record.blob(struct.pack('<I',2)+b''.join(struct.pack('<HHI',*row) for row in rows))
                raise AssertionError(operation)
        meta=ServiceMetadata();meta.check_private_file(meta.path(logical));self.assertEqual(meta.successful_private_checks[logical],expected)
        profile=NativeCheckedProfile(record,meta,profile=logical);snapshot=profile.snapshot
        def declared_root(info):return {**snapshot(info),'st_uid':0,'st_mode':stat.S_IFREG|0o440}
        profile.snapshot=declared_root
        def selected_path(value):self.assertEqual(value,logical);return actual_path
        with patch('lib.providers.provider_observation_profile.Path',side_effect=selected_path):self.assertEqual(profile.read(meta.path(logical),'utf-8',None),actual_path.read_text(encoding='utf-8'))
        self.assertFalse(record.capture_incomplete);profile.release_resources();meta.release_resources();record.finish('complete',{'exit_code':0},{})
        _,_,_,events,blob,closed=read_record(record.root);cursor=Cursor(events);cursor.position=1;cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};consumed=set();text=actual_path.read_text(encoding='utf-8');actual_path.unlink()
        def retained(ref):consumed.add(ref['sha256']);return cache[ref['sha256']]
        with patch('os.open',side_effect=AssertionError('No service replay IO')):
            puremeta=ReplayPrivateMetadata(cursor,retained,cwd=str(self.base),files=[logical]);puremeta.check_private_file(puremeta.path(logical));pure=ReplayCheckedProfile(cursor,puremeta,retained,profile=logical);self.assertEqual(pure.read(puremeta.path(logical),'utf-8',None),text)
        self.assertEqual(consumed,set(cache))
        for name in consumed:blob({'sha256':name,'bytes':len(cache[name])})
        self.assertTrue(closed())
    def test_resealed_profile_stat_encoding_and_blob_are_rejected(self):
        record,meta,profile=self.create();profile.read(meta.path(str(self.file)),'utf-8',None);profile.release_resources();meta.release_resources();record.finish('complete',{'exit_code':0},{})
        _,_,_,events,blob,_=read_record(record.root)
        for kind in ('stat','encoding','blob'):
            changed=copy.deepcopy(events);row=next(x for x in changed if x.get('kind')=='provider-profile-read-intent')
            if kind=='stat':row['private_stat']['st_uid']=False
            elif kind=='encoding':row['encoding']='latin-1'
            else:next(x for x in changed if x.get('kind')=='provider-profile-read-outcome')['content']={'sha256':'0'*64,'bytes':1}
            cursor=Cursor(changed);cursor.position=1;puremeta=ReplayPrivateMetadata(cursor,blob,cwd=str(self.base),files=[str(self.file)]);puremeta.check_private_file(puremeta.path(str(self.file)));pure=ReplayCheckedProfile(cursor,puremeta,blob,profile=str(self.file))
            with self.subTest(kind=kind),self.assertRaises((IntegrityError,InputAdmissionError)):pure.read(puremeta.path(str(self.file)),'utf-8',None)
