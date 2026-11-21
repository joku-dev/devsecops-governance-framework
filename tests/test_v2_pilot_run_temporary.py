"""Original temporary cleanup, partial failure and inert source-deleted replay."""
from pathlib import Path
from unittest.mock import patch
import errno,hashlib,json,os,shutil,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.pilot_run_intake_io import ReplayRunIO
from lib.providers.pilot_run_temporary import NativeTemporaryFactory
from lib.pilot_run_temporary import ReplayTemporaryFactory
from lib.pilot_run_private_temporary import PrivateTemporaryFactory
from lib.personal_channel_ports import exclusive_factory
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.requirement_review_output import RetainedOutputError
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError

class PilotRunTemporary(unittest.TestCase):
    def setUp(self):
        previous=os.umask(0o077);self.addCleanup(os.umask,previous)
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.top=Path(temporary.name).resolve();self.source=self.top/'source';self.source.mkdir(mode=0o700)
        self.parent=self.top/'temps';self.parent.mkdir(mode=0o700);self.private=self.top/'state';self.private.mkdir(mode=0o700)
        self.record=Record(self.private/'records',{'test':'temporary-scope'},{'source_only':True});self.record.append({'kind':'execution-intent'})
        self.owner=NativeRunIO(self.record,mode='selected-files',cwd=str(self.source),private_state=self.private,product_root=ROOT,ledger=str(self.source/'ledger'),transaction_name=lambda raw:'unused.json')
    def body(self,owner,path):
        directory=str(Path(path)/'capture');owner.mkdir(directory,0o777,True,True,directory)
        selected=str(Path(directory)/'snapshot.json')
        with exclusive_factory(owner,selected,selected) as stream:stream.write(b'{"captured":true}\n')
    def original(self,path,*,partial=False):
        # Random temp name is explicit captured environment input, injected into
        # the unchanged stdlib constructor for an exact counterfactual name.
        def fail(name,**kwargs):
            (Path(name)/'capture/snapshot.json').unlink();raise OSError(errno.EIO,'cleanup failed after one child')
        with patch('tempfile._get_candidate_names',return_value=iter([Path(path).name[3:]])):
            factory=tempfile.TemporaryDirectory(dir=str(self.parent));self.assertEqual(factory.name,path)
            try:
                if partial:
                    with patch.object(tempfile.TemporaryDirectory,'_rmtree',side_effect=fail):
                        with factory as original:
                            p=Path(original)/'capture/snapshot.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'{"captured":true}\n')
                else:
                    with factory as original:
                        p=Path(original)/'capture/snapshot.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'{"captured":true}\n')
            except OSError as error:return {'type':type(error).__name__,'message':str(error)}
        return None
    def capture_and_replay(self,partial=False):
        factory=NativeTemporaryFactory(self.owner,str(self.parent));session=None;path=None;actual_error=None
        def fail(name,**kwargs):
            (Path(name)/'capture/snapshot.json').unlink();raise OSError(errno.EIO,'cleanup failed after one child')
        try:
            session=factory.TemporaryDirectory();path=session.path
            if partial:
                with patch.object(tempfile.TemporaryDirectory,'_rmtree',side_effect=fail):
                    with session as selected:self.body(self.owner,selected)
            else:
                with session as selected:self.body(self.owner,selected)
        except RetainedOutputError as error:actual_error={'type':error.original_type,'message':error.original_message}
        self.assertTrue(session.done);self.assertEqual(session.release(),{'original_cleanup_attempted':True});self.assertFalse(self.record.capture_incomplete)
        self.assertFalse(self.owner.files)
        after={p.relative_to(self.parent).as_posix():('directory' if p.is_dir() else p.read_bytes()) for p in self.parent.rglob('*')}
        if partial:shutil.rmtree(path)
        self.assertEqual(self.original(path,partial=partial),actual_error)
        expected={p.relative_to(self.parent).as_posix():('directory' if p.is_dir() else p.read_bytes()) for p in self.parent.rglob('*')}
        self.assertEqual(after,expected)
        self.record.finish('complete',{'exit_code':1 if partial else 0},self.owner.touched)
        _,_,_,events,blob,closed=read_record(self.record.root);cache={p.name:p.read_bytes() for p in self.record.blobs.iterdir()};seen=set()
        def inert(ref):
            raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return raw
        shutil.rmtree(self.source);shutil.rmtree(self.parent)
        replay=ReplayRunIO(events,inert,'selected-files',str(self.source),ledger=str(self.source/'ledger'),transaction_name=lambda raw:'unused.json');failure=None
        with patch('os.open',side_effect=AssertionError('No source')),patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No temporary effect')):
            scope=ReplayTemporaryFactory(replay,str(self.parent)).TemporaryDirectory();self.assertEqual(scope.path,path)
            try:
                with scope as selected:self.body(replay,selected)
            except RetainedOutputError as error:failure={'type':error.original_type,'message':error.original_message}
            self.assertEqual(scope.release(),{'original_cleanup_attempted':True});replay.finish()
        self.assertEqual(failure,actual_error);self.assertEqual(replay.files,self.owner.files);self.assertEqual(replay.touched,self.owner.touched);self.assertEqual(replay.writes,self.owner.writes);self.assertEqual(seen,set(cache))
        for name in seen:blob({'sha256':name,'bytes':len(cache[name])})
        self.assertTrue(closed())
    def test_original_temporary_cleanup_removes_only_own_outputs_and_replays_without_source(self):self.capture_and_replay()
    def test_original_cleanup_failure_retains_partial_tree_without_repeating_cleanup(self):self.capture_and_replay(partial=True)
    def test_replaced_root_is_quarantined_and_never_deleted_by_cleanup_or_finalizer(self):
        session=NativeTemporaryFactory(self.owner,str(self.parent)).TemporaryDirectory();path=Path(session.path);moved=self.parent/'moved-original'
        with self.assertRaisesRegex(InputAdmissionError,'root_replaced'):
            with session:
                path.rename(moved);path.mkdir(mode=0o700);(path/'foreign.txt').write_bytes(b'preserve replacement')
        self.assertFalse(session.resource._finalizer.alive)
        self.assertFalse(session.release()['original_cleanup_attempted']);self.assertTrue(self.record.capture_incomplete)
        self.assertEqual((path/'foreign.txt').read_bytes(),b'preserve replacement');self.assertTrue(moved.is_dir())
    def test_unknown_child_is_admission_failure_and_is_not_deleted(self):
        session=NativeTemporaryFactory(self.owner,str(self.parent)).TemporaryDirectory()
        with self.assertRaisesRegex(InputAdmissionError,'unowned_or_changed_child'):
            with session:(Path(session.path)/'unknown.txt').write_bytes(b'unowned child')
        session.release();self.assertFalse(session.resource._finalizer.alive);self.assertTrue(self.record.capture_incomplete)
        self.assertEqual((Path(session.path)/'unknown.txt').read_bytes(),b'unowned child')

    def test_installed_product_parent_is_rejected_before_any_temporary_creation(self):
        with patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No product write')):
            with self.assertRaisesRegex(InputAdmissionError,'product_export_forbidden'):
                NativeTemporaryFactory(self.owner,str(ROOT)).TemporaryDirectory()
        self.assertTrue(self.record.capture_incomplete)
        for session in self.owner.pilot_temporary_sessions:session.release()
    def test_private_collision_uses_next_name_preserves_source_and_replays_without_native_temporary(self):
        first=self.parent/'tmpaxiom-private-00000001';first.mkdir(mode=0o700);(first/'sentinel').write_bytes(b'preserve existing directory')
        before={str(p.relative_to(self.parent)):('directory' if p.is_dir() else p.read_bytes()) for p in self.parent.rglob('*')}
        self.owner=NativeRunIO(self.record,mode='private-candidate',cwd=str(self.source),private_state=self.private,product_root=ROOT,ledger=str(self.source/'ledger'),transaction_name=lambda raw:'unused.json')
        factory=PrivateTemporaryFactory(self.owner,str(self.parent))
        with factory.TemporaryDirectory() as name:self.body(self.owner,name)
        self.assertEqual(name,str(self.parent/'tmpaxiom-private-00000002'))
        self.assertEqual({str(p.relative_to(self.parent)):('directory' if p.is_dir() else p.read_bytes()) for p in self.parent.rglob('*')},before)
        self.assertFalse(self.owner.files);self.assertFalse(self.record.capture_incomplete)
        with patch('tempfile._get_candidate_names',return_value=iter(['axiom-private-00000001','axiom-private-00000002'])):
            with tempfile.TemporaryDirectory(dir=self.parent) as original:
                self.assertEqual(original,name)
                selected=Path(original)/'capture/snapshot.json';selected.parent.mkdir(parents=True,exist_ok=True);selected.write_bytes(b'{"captured":true}\n')
        self.assertEqual({str(p.relative_to(self.parent)):('directory' if p.is_dir() else p.read_bytes()) for p in self.parent.rglob('*')},before)
        self.record.finish('complete',{'exit_code':0},self.owner.touched)
        _,_,_,events,blob,closed=read_record(self.record.root);cache={p.name:p.read_bytes() for p in self.record.blobs.iterdir()};seen=set()
        def inert(ref):seen.add(ref['sha256']);return cache[ref['sha256']]
        shutil.rmtree(self.source);shutil.rmtree(self.parent)
        replay=ReplayRunIO(events,inert,'private-candidate',str(self.source),ledger=str(self.source/'ledger'),transaction_name=lambda raw:'unused.json')
        with patch('os.open',side_effect=AssertionError('No source')),patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No native temporary')):
            with PrivateTemporaryFactory(replay,str(self.parent)).TemporaryDirectory() as selected:self.body(replay,selected)
            self.assertEqual(selected,name);replay.finish()
        self.assertEqual(replay.projected_changes,self.owner.projected_changes);self.assertEqual(replay.files,{});self.assertEqual(seen,set(cache))
        for name in seen:blob({'sha256':name,'bytes':len(cache[name])})
        self.assertTrue(closed())
if __name__=='__main__':unittest.main(verbosity=2)
