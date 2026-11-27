"""Actual signed release child, whole immutable oracle and source-free recomputation."""
from pathlib import Path
from unittest.mock import patch
import copy,hashlib,json,os,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_release_verification as reference
from lib.providers.consumer_lifecycle_storage import Record,read_record
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.synthetic_lifecycle_io import ReplayIO
from lib.providers.provider_observation_release import NativeObservationRelease
from lib.provider_observation_release import ReplayObservationRelease
from lib.portable.runtime import source_digest
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
AT='2026-11-18T14:45:00Z'


class ObservationRelease(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old);self.fixture=reference.fixture.ReleaseIntegrityTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups);self.base=Path(self.fixture.temp.name).resolve();self.source=self.fixture.root.resolve();self.fixture.root=self.source;self.fixture.policy_path=self.source/'model/governance/release-signing-policy.yaml';self.state=self.base/'records';self.state.mkdir(mode=0o700);self.node={'node_id':'b'*32,'runtime_source_digest':source_digest()};self.revision=self.fixture.git('rev-parse','HEAD').strip()
    def native(self):
        record=Record(self.state,{'release_child_development_only':True},{'installed_acceptance':False});record.append({'kind':'execution-intent'});owner=NativeIO(record,mode='selected-files',cwd=str(self.base),private_state=self.state,product_root=ROOT);return record,NativeObservationRelease(owner,self.source,instance_root=self.state/'children'/record.root.name,node_context=self.node)
    def test_actual_signed_child_matches_whole_original_and_replays_every_file_after_source_is_removed(self):
        record,port=self.native();actual=port.report(self.revision,AT);expected=reference.ORIGINAL.verify_release_integrity(self.source,self.fixture.policy_path);self.assertEqual(actual,expected);record.finish('complete',{'exit_code':0},{})
        _,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};used=set();self.source.rename(self.base/'source-removed');port.instance_root.rename(port.instance_root.with_name(port.instance_root.name+'-removed'))
        def retained(ref):
            raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);used.add(ref['sha256']);return raw
        owner=ReplayIO(events,retained,'selected-files',str(self.base));pure=ReplayObservationRelease(owner,self.source,node_context=self.node)
        with patch('os.open',side_effect=AssertionError('No source/child filesystem replay')),patch('subprocess.Popen',side_effect=AssertionError('No signature/program replay')):
            self.assertEqual(pure.report(self.revision,AT),expected);owner.finish()
        self.assertEqual(used,set(cache))
        for name in used:blob({'sha256':name,'bytes':len(cache[name])})
        self.assertTrue(closed())
    def test_wrong_revision_stops_before_release_operation_and_never_retries(self):
        record,port=self.native()
        with self.assertRaises(InputAdmissionError):port.report('f'*40,AT)
        self.assertTrue(record.capture_incomplete);before=record.sequence
        with self.assertRaises(InputAdmissionError):port.report(self.revision,AT)
        self.assertEqual(before,record.sequence);self.assertEqual(list((port.instance_root/'state/release-validation/operations').iterdir()),[])
    def test_child_alias_and_intent_or_completion_loss_never_allow_a_retry_or_false_original_report(self):
        for kind in ('alias','intent','completion'):
            with self.subTest(kind=kind):
                record,port=self.native();append=record.append
                if kind=='alias':
                    outside=self.base/'outside';outside.mkdir(mode=0o700);(self.state/'children').mkdir(mode=0o700);port.instance_root.symlink_to(outside)
                else:
                    def lose(row):
                        if row.get('kind')==('intent' if kind=='intent' else 'returned'):raise OSError('Controlled private journal loss')
                        append(row)
                    record.append=lose
                with self.assertRaises(InputAdmissionError):port.report(self.revision,AT)
                self.assertTrue(record.capture_incomplete);before=record.sequence
                with self.assertRaises(InputAdmissionError):port.report(self.revision,AT)
                self.assertEqual(record.sequence,before)
                if kind=='alias':self.assertEqual(list(outside.iterdir()),[])
                elif kind=='intent':self.assertFalse(port.instance_root.exists())
                else:self.assertTrue(list((port.instance_root/'state/release-validation/operations').iterdir()))
    def test_resealed_child_authority_and_missing_start_or_empty_directory_are_rejected(self):
        record,port=self.native();port.report(self.revision,AT);record.finish('complete',{'exit_code':0},{})
        _,_,_,events,blob,_=read_record(record.root);position=next(i for i,row in enumerate(events) if row.get('action')=='provider-observation-release-child');wire=json.loads(blob(events[position+1]['value']))
        for kind in ('node','revision','empty-directory','start','authority'):
            changed=copy.deepcopy(wire);extra={}
            if kind=='node':changed['binding']['node_id']='c'*32
            elif kind=='revision':changed['binding']['source_revision']='f'*40
            elif kind=='empty-directory':changed['directories'].remove('native-work')
            elif kind=='start':del changed['files'][next(name for name in changed['files'] if name.startswith('starts/'))]
            else:
                for name in ('pending.json','assessment.json','native-results.json'):
                    value=json.loads(blob(changed['files'][name]));value['official_acceptance']=True;raw=(json.dumps(value)+'\n').encode();ref={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};extra[ref['sha256']]=raw;changed['files'][name]=ref
            raw=json.dumps(changed).encode();ref={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};extra[ref['sha256']]=raw;altered=copy.deepcopy(events);altered[position+1]['value']=ref
            def retained(ref):return extra[ref['sha256']] if ref['sha256'] in extra else blob(ref)
            owner=ReplayIO(altered,retained,'selected-files',str(self.base));pure=ReplayObservationRelease(owner,self.source,node_context=self.node)
            with self.assertRaises(IntegrityError):pure.report(self.revision,AT)
            before=owner.position
            with self.assertRaises(IntegrityError):pure.report(self.revision,AT)
            self.assertEqual(before,owner.position)
