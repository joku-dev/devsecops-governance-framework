"""Real secret text reads, opaque HTTPS use, inert replay and no retained payload."""
from pathlib import Path
from unittest.mock import patch
import copy,errno,json,os,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.providers.consumer_lifecycle_storage import Record,read_record
from lib.providers.provider_observation_private_ports import NativePrivateMetadata
from lib.provider_observation_private_ports import ReplayPrivateMetadata
from lib.providers.provider_observation_credentials import NativeCredentialCapability
from lib.provider_observation_credentials import ReplayCredentialCapability
from lib.provider_observation_context import SecretText
from lib.provider_observation_reads import reader_type,ReplayObservationReads
from lib.providers.provider_observation_reads import NativeObservationReads
from lib.providers.transports import Reader
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from test_v2_provider_observation_reads import Cursor,Response

TOKEN='synthetic-private-read-capability-no-live-provider-c47018'


class CheckedCredentialReads(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old);tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.base=Path(tmp.name).resolve();self.file=self.base/'credential';self.file.write_text('  '+TOKEN+'\n');self.state=self.base/'records';self.state.mkdir(mode=0o700)
    def create(self):
        record=Record(self.state,{'profile':'checked-credential-port-only'},{'no_whole_operator_acceptance':True});meta=NativePrivateMetadata(record,cwd=str(self.base),files=[str(self.file)]);meta.check_private_file(meta.path(str(self.file)));credentials=NativeCredentialCapability(record,meta,credential=str(self.file));return record,meta,credentials
    def private(self,record):
        for path in record.root.rglob('*'):
            if path.is_file():self.assertNotIn(TOKEN.encode(),path.read_bytes())
    def test_whole_private_check_text_newlines_and_native_HTTPS_use_then_source_free_replay(self):
        raw=('  '+TOKEN+'\r\nsecond-line\rlast\n').encode();self.file.write_bytes(raw);record,meta,credentials=self.create();reference=credentials.read(meta.path(str(self.file)));self.assertIsInstance(reference,SecretText);self.assertEqual(credentials.resolve(reference),self.file.read_text());calls=[]
        class Opener:
            def open(this,request,*,timeout):calls.append(request.get_header('Authorization'));return Response(b'{"observed":true}')
        reads=NativeObservationReads(record,credentials.resolve);cls=reader_type(reads,Reader)
        with patch('lib.providers.transports.build_opener',return_value=Opener()):reader=cls('https://api.example.test',reference.strip(),budget=150);self.assertEqual(reader.get('/one'),{'observed':True})
        self.assertEqual(calls,['Bearer '+self.file.read_text().strip()]);reads.release_credentials();self.assertFalse(credentials.release_resources()['required']);self.assertFalse(meta.release_resources()['required']);record.finish('complete',{'exit_code':0},{})
        self.private(record);_,_,_,events,blob,closed=read_record(record.root);cursor=Cursor(events);cursor.position=1;cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};moved=self.base.with_name(self.base.name+'-absent');self.base.rename(moved)
        try:
            with patch('os.open',side_effect=AssertionError('No credential replay read')),patch('os.stat',side_effect=AssertionError('No source metadata')),patch('lib.providers.transports.build_opener',side_effect=AssertionError('No network replay')):
                puremeta=ReplayPrivateMetadata(cursor,lambda ref:cache[ref['sha256']],cwd=str(self.base),files=[str(self.file)]);puremeta.check_private_file(puremeta.path(str(self.file)));pure=ReplayCredentialCapability(cursor,puremeta,credential=str(self.file));cap=pure.read(puremeta.path(str(self.file)));read=ReplayObservationReads(cursor,lambda ref:cache[ref['sha256']],reader_url=Reader.url);reader=reader_type(read,Reader)('https://api.example.test',cap.strip(),budget=150);self.assertEqual(reader.get('/one'),{'observed':True});self.assertEqual(cursor.position,len(events)-1)
        finally:moved.rename(self.base)
        for name,raw in cache.items():blob({'sha256':name,'bytes':len(raw)})
        self.assertTrue(closed());self.assertIsNone(credentials.value)
    def test_read_without_successful_private_check_cannot_open_payload(self):
        record=Record(self.state,{'profile':'unchecked'},{'no_authority':True});meta=NativePrivateMetadata(record,cwd=str(self.base),files=[str(self.file)]);credentials=NativeCredentialCapability(record,meta,credential=str(self.file))
        with patch('lib.providers.provider_observation_credentials.held_root',side_effect=AssertionError('No unchecked credential open')),self.assertRaises((IntegrityError,InputAdmissionError)):credentials.read(meta.path(str(self.file)))
    def test_changed_or_oversized_secret_is_technical_incomplete_with_no_payload_or_digest(self):
        for change in ('changed','oversized'):
            with self.subTest(change=change):
                self.file.write_text(TOKEN);record,meta,credentials=self.create()
                if change=='changed':self.file.write_text('Changed '+TOKEN)
                else:
                    self.file.write_text(TOKEN*2000);meta.successful_private_checks.clear();meta.check_private_file(meta.path(str(self.file)))
                with self.assertRaises(InputAdmissionError):credentials.read(meta.path(str(self.file)))
                self.assertTrue(record.capture_incomplete);self.assertIsNone(credentials.value);self.private(record);credentials.release_resources();meta.release_resources()
    def test_invalid_default_text_decoding_is_redacted_without_a_false_original_verdict(self):
        self.file.write_bytes(TOKEN.encode()+b'\xff');record,meta,credentials=self.create()
        with self.assertRaises(InputAdmissionError):credentials.read(meta.path(str(self.file)))
        self.assertTrue(record.capture_incomplete);self.private(record);self.assertFalse(credentials.release_resources()['required']);meta.release_resources()
    def test_lost_completion_after_secret_read_never_enables_a_provider_request(self):
        record,meta,credentials=self.create();append=record.append
        def lose(row):
            if row.get('kind')=='provider-credential-read-outcome':raise OSError('Controlled completion loss')
            return append(row)
        record.append=lose
        with self.assertRaises(InputAdmissionError):credentials.read(meta.path(str(self.file)))
        self.assertIsNone(credentials.value);self.assertTrue(record.capture_incomplete);self.private(record)
        with self.assertRaises(InputAdmissionError):credentials.resolve(SecretText('credential-1'))
        credentials.release_resources();meta.release_resources()
    def test_disappeared_secret_has_original_file_error_and_its_metadata_only_replay(self):
        record,meta,credentials=self.create();self.file.unlink()
        with self.assertRaises(FileNotFoundError):credentials.read(meta.path(str(self.file)))
        self.assertFalse(record.capture_incomplete);credentials.release_resources();meta.release_resources();record.finish('complete',{'exit_code':1},{})
        _,_,_,events,blob,_=read_record(record.root);cursor=Cursor(events);cursor.position=1;puremeta=ReplayPrivateMetadata(cursor,blob,cwd=str(self.base),files=[str(self.file)]);puremeta.check_private_file(puremeta.path(str(self.file)));pure=ReplayCredentialCapability(cursor,puremeta,credential=str(self.file))
        with patch('os.open',side_effect=AssertionError('No replay secret open')),self.assertRaises(FileNotFoundError):pure.read(puremeta.path(str(self.file)))
    def test_resealed_private_stat_capability_and_codec_changes_are_rejected(self):
        record,meta,credentials=self.create();credentials.read(meta.path(str(self.file)));credentials.release_resources();meta.release_resources();record.finish('complete',{'exit_code':0},{})
        _,_,_,events,blob,_=read_record(record.root)
        for change in ('stat','identifier','encoding'):
            with self.subTest(change=change):
                changed=copy.deepcopy(events);read=next(x for x in changed if x.get('kind')=='provider-credential-read-intent')
                if change=='stat':read['private_stat']['st_size']+=1
                elif change=='identifier':read['identifier']='credential-2'
                else:next(x for x in changed if x.get('kind')=='provider-credential-read-outcome')['encoding']='unknown-codec-for-fixture'
                cursor=Cursor(changed);cursor.position=1;puremeta=ReplayPrivateMetadata(cursor,blob,cwd=str(self.base),files=[str(self.file)]);puremeta.check_private_file(puremeta.path(str(self.file)));pure=ReplayCredentialCapability(cursor,puremeta,credential=str(self.file))
                with self.assertRaises((IntegrityError,InputAdmissionError)):pure.read(puremeta.path(str(self.file)))
