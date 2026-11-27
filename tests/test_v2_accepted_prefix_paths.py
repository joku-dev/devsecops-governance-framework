"""Original filesystem probe semantics, exact errors and closed pure observations."""
from pathlib import Path
from unittest.mock import patch
import copy,os,shutil,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from jsonschema import Draft202012Validator
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.providers.accepted_prefix_paths import NativePrefixPaths
from lib.accepted_prefix_paths import ReplayPrefixPaths,probe_value
from lib.providers.synthetic_lifecycle_storage import read_record
from lib.synthetic_lifecycle_io import ReplayIO
from lib.requirement_validation_replay import IntegrityError
import test_v2_personal_channel_transport as fixture

PREFIX='model/governance/lifecycle/live-pilot/'
class OriginalPrefixPathProbes(unittest.TestCase):
    def setUp(self):
        case=fixture.WholeReadTransport();case.setUp();self.addCleanup(case.doCleanups);self.fixture=case;self.root=case.data;self.context=RepositoryLifecycle(self.root,validator_class=Draft202012Validator)
        self.record,self.owner=case.owner()
    def test_original_regular_directory_symlink_broken_loop_FIFO_and_missing_parent_without_content_reads(self):
        parent=self.root/PREFIX;parent.mkdir(parents=True,exist_ok=True);file=parent/'explicit-file';file.write_bytes(b'explicit data');(parent/'explicit-directory').mkdir();(parent/'explicit-link').symlink_to(file);(parent/'explicit-broken').symlink_to(parent/'absent');(parent/'explicit-loop').symlink_to('explicit-loop');os.mkfifo(parent/'explicit-fifo',0o600)
        paths=[parent/name for name in ('explicit-file','explicit-directory','explicit-link','explicit-broken','explicit-loop','explicit-fifo','absent','missing-parent/file')];expected=[];port=NativePrefixPaths(self.owner,self.root,self.context)
        for p in paths:
            for kind in ('is_file','is_symlink'):
                value=getattr(p,kind)();expected.append((str(p),kind,value))
                with patch('os.open',wraps=os.open):self.assertEqual(port.probe(str(p),kind,str(p)),value)
        self.record.finish('complete',{'exit_code':0},self.owner.touched);_,_,_,events,blob,closed=read_record(self.record.root);cache={p.name:p.read_bytes() for p in self.record.blobs.iterdir()};shutil.rmtree(self.root);replay=ReplayIO(events,lambda ref:cache[ref['sha256']],'private-candidate',str(self.root));pure=ReplayPrefixPaths(replay,self.root,self.context)
        with patch('os.open',side_effect=AssertionError('No input')),patch('os.stat',side_effect=AssertionError('No symlink target stat')),patch('os.lstat',side_effect=AssertionError('No original path')):
            for path,kind,value in expected:self.assertEqual(pure.probe(path,kind,path),value)
            replay.finish()
        for name,raw in cache.items():blob({'sha256':name,'bytes':len(raw)})
        self.assertTrue(closed())
    def test_resealed_nonfile_symlink_result_and_unclosed_path_metadata_fail_closed(self):
        selected=self.root/PREFIX/'explicit-absent';port=NativePrefixPaths(self.owner,self.root,self.context);self.assertFalse(port.probe(str(selected),'is_file',str(selected)));self.record.finish('complete',{'exit_code':0},self.owner.touched);_,_,_,events,blob,_=read_record(self.record.root)
        import json
        wire=json.loads(blob(events[3]['value']));spec=wire['specification']
        for change in (lambda w:w.update(result=True),lambda w:w.update(schema_version=True),lambda w:w.update(official_acceptance=True),lambda w:w['after'].update(kind='file')):
            bad=copy.deepcopy(wire);change(bad)
            with self.assertRaises(IntegrityError):probe_value(bad,spec)

    @unittest.skipIf(os.geteuid()==0,'Root bypasses the original permission boundary')
    def test_original_permission_error_remains_original_error_and_pure_replay(self):
        from lib.requirement_review_output import RetainedOutputError
        parent=self.root/PREFIX/'explicit-denied';parent.mkdir(parents=True);selected=parent/'file';selected.write_bytes(b'private test data');parent.chmod(0)
        self.addCleanup(parent.chmod,0o700)
        with self.assertRaises(PermissionError) as original:selected.is_file()
        port=NativePrefixPaths(self.owner,self.root,self.context)
        with self.assertRaises(RetainedOutputError) as native:port.probe(str(selected),'is_file',str(selected))
        self.assertEqual(native.exception.original_type,'PermissionError');self.assertEqual(native.exception.original_message,str(original.exception));self.assertFalse(self.record.capture_incomplete)
        parent.chmod(0o700);self.record.finish('complete',{'exit_code':1},self.owner.touched);_,_,_,events,blob,_=read_record(self.record.root);cache={p.name:p.read_bytes() for p in self.record.blobs.iterdir()};replay=ReplayIO(events,lambda ref:cache[ref['sha256']],'private-candidate',str(self.root));pure=ReplayPrefixPaths(replay,self.root,self.context)
        with patch('os.open',side_effect=AssertionError('No source')),patch('os.stat',side_effect=AssertionError('No native probe')):
            with self.assertRaises(RetainedOutputError) as retained:pure.probe(str(selected),'is_file',str(selected))
            replay.finish()
        self.assertEqual(retained.exception.original_message,native.exception.original_message)
