"""Recorded owned metadata creation/cleanup, quarantine and process-free replay."""
from pathlib import Path
from unittest.mock import patch
import copy,hashlib,shutil,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.providers.accepted_prefix_hash_scope import NativeHashAuxiliary
from lib.accepted_prefix_hash_scope import ReplayHashAuxiliary,creation_value,removal_value
from lib.accepted_prefix_git_context import attribute_values,ATTRIBUTES
from lib.providers.synthetic_lifecycle_storage import read_record
from lib.synthetic_lifecycle_io import ReplayIO
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
import test_v2_personal_channel_transport as fixture
from test_v2_accepted_prefix_transport import git

class OwnedPrefixHashScope(unittest.TestCase):
    def setUp(self):
        case=fixture.WholeReadTransport();case.setUp();self.addCleanup(case.doCleanups);self.fixture=case;self.root=case.data
        self.assertEqual(git(self.root,'init','--initial-branch=fixture').returncode,0)
        self.path='explicit-prefix-data.json';(self.root/self.path).write_bytes(b'initial\n');self.assertEqual(git(self.root,'add','--',self.path).returncode,0)
        (self.root/'.gitattributes').write_text(self.path+' text eol=lf\n');(self.root/self.path).write_bytes(b'a\r\nb\r\n')
        raw=git(self.root,'check-attr','-z',*ATTRIBUTES,'--',self.path);self.assertEqual(raw.returncode,0);self.attrs=attribute_values(raw.stdout,self.path)
        self.record,self.owner=case.owner();self.index=(self.root/'.git/index').read_bytes();self.objects=self.root/'.git/objects'
    def make(self,**options):return NativeHashAuxiliary(self.owner,self.root,self.path,self.attrs,{},index=self.index,shared={},objects=str(self.objects),**options)
    def test_recorded_scope_preserves_actual_hash_then_pure_creation_and_cleanup_without_inputs(self):
        original=git(self.root,'hash-object','--',str(self.root/self.path));scope=self.make();actual=git(self.root,'hash-object','--',str(self.root/self.path),aux=Path(scope.label))
        self.assertEqual((actual.returncode,actual.stdout,actual.stderr),(original.returncode,original.stdout,original.stderr))
        removed=scope.finish();self.assertFalse(Path(scope.label).exists());self.assertFalse(self.record.capture_incomplete)
        self.record.finish('complete',{'exit_code':0},self.owner.touched);_,_,_,events,blob,closed=read_record(self.record.root);cache={p.name:p.read_bytes() for p in self.record.blobs.iterdir()}
        shutil.rmtree(self.root);scope.parent.rmdir();replay=ReplayIO(events,lambda ref:cache[ref['sha256']],'private-candidate',str(self.root))
        with patch('os.open',side_effect=AssertionError('No private or source read')),patch('subprocess.Popen',side_effect=AssertionError('No Git')),patch('os.mkdir',side_effect=AssertionError('No auxiliary creation')):
            pure=ReplayHashAuxiliary(replay,self.root,self.path,self.attrs,{},index=self.index,shared={},objects=str(self.objects),private_parent=str(scope.parent));self.assertEqual(pure.arguments.private_gitdir,scope.label);self.assertEqual(pure.finish(),removed);replay.finish()
        for name,raw in cache.items():blob({'sha256':name,'bytes':len(raw)})
        self.assertTrue(closed())
    def test_unknown_top_child_is_quarantined_without_deleting_any_known_or_unknown_data(self):
        scope=self.make();foreign=Path(scope.label)/'unexpected';foreign.write_bytes(b'preserve unknown data');before={str(p.relative_to(scope.label)):p.read_bytes() for p in Path(scope.label).rglob('*') if p.is_file() and not p.is_symlink()}
        with self.assertRaisesRegex(InputAdmissionError,'unknown_scope_entry_quarantined'):scope.finish()
        self.assertTrue(self.record.capture_incomplete);self.assertEqual({str(p.relative_to(scope.label)):p.read_bytes() for p in Path(scope.label).rglob('*') if p.is_file() and not p.is_symlink()},before)
    def test_unknown_nested_child_or_changed_known_bytes_are_quarantined(self):
        for kind in ('nested','bytes','alias','mode'):
            with self.subTest(kind=kind):
                if kind!='nested':self.setUp()
                scope=self.make();target=Path(scope.label)/'info/attributes';before=target.read_bytes()
                if kind=='nested':(Path(scope.label)/'refs/heads/unexpected').write_bytes(b'preserve')
                elif kind=='bytes':target.write_bytes(b'changed')
                elif kind=='alias':target.unlink();target.symlink_to(self.root/self.path)
                else:target.chmod(0o644)
                with self.assertRaises(InputAdmissionError):scope.finish()
                self.assertTrue(Path(scope.label).exists());self.assertTrue(self.record.capture_incomplete);self.assertTrue((Path(scope.label)/'HEAD').exists())
                if kind=='alias':self.assertEqual((self.root/self.path).read_bytes(),b'a\r\nb\r\n')
    def test_journal_loss_after_creation_preserves_directory_and_never_retries_or_auto_cleans(self):
        original=self.owner.perform;effects=[]
        def lost(action,arguments,effect,**options):
            def observed():
                value=effect();effects.append(value);return value
            result=original(action,arguments,observed,**options)
            if action.endswith('-create'):raise OSError('explicit injected lost completion')
            return result
        with patch.object(self.owner,'perform',side_effect=lost):
            with self.assertRaisesRegex(OSError,'lost completion'):self.make()
        self.assertEqual(len(effects),1);scope=Path(effects[0]['scope_label']);self.assertTrue(scope.is_dir());self.assertTrue((scope/'HEAD').is_file());self.assertTrue(self.record.capture_incomplete)
    def test_existing_capture_incomplete_prevents_cleanup_side_effects(self):
        scope=self.make();self.record.capture_incomplete=True
        with patch('os.unlink',side_effect=AssertionError('No cleanup after journal loss')):
            with self.assertRaisesRegex(InputAdmissionError,'journal_loss_quarantined'):scope.finish()
        self.assertTrue(Path(scope.label).exists())
    def test_unknown_child_appearing_before_removal_intent_executes_is_retained(self):
        scope=self.make();original=self.owner.perform
        def race(action,arguments,effect,**options):
            if action.endswith('-remove'):(Path(scope.label)/'raced-child').write_bytes(b'preserve')
            return original(action,arguments,effect,**options)
        with patch.object(self.owner,'perform',side_effect=race):
            with self.assertRaises(InputAdmissionError):scope.finish()
        self.assertTrue((Path(scope.label)/'raced-child').exists());self.assertTrue((Path(scope.label)/'HEAD').exists())
    def test_resealed_identity_manifest_flags_and_cleanup_claims_cannot_expand_scope(self):
        scope=self.make();cache={hashlib.sha256(raw).hexdigest():raw for raw in scope.files.values()}
        for change in (lambda w:w.update(scope_label=str(scope.parent/'outside')),lambda w:w.update(scope_identity=[True,1]),lambda w:w.update(OS_isolation_attested=True),lambda w:w['file_identities'].pop('HEAD'),lambda w:w['files']['HEAD'].update(bytes=True),lambda w:w['directories'].update(unknown=[1,2])):
            bad=copy.deepcopy(scope.wire);change(bad)
            with self.assertRaises(IntegrityError):creation_value(bad,scope.spec,scope.files,lambda ref:cache[ref['sha256']])
        removed=scope.finish()
        for change in (lambda w:w.update(native_auxiliary_removed=False),lambda w:w.update(OS_isolation_attested=True),lambda w:w.update(schema_version=True),lambda w:w.update(scope_identity=[False,1])):
            bad=copy.deepcopy(removed);change(bad)
            with self.assertRaises(IntegrityError):removal_value(bad,scope.wire)
