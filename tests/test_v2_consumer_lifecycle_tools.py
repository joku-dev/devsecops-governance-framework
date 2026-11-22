"""Approved external tool aliases; no relaxation for actual private/source tools."""
from pathlib import Path
from types import SimpleNamespace
import hashlib,os,shutil,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.providers.consumer_lifecycle_opa import NativeConsumerOPA
from lib.providers.consumer_lifecycle_tools import approved_external_program
from lib.requirement_validation_budget import InputAdmissionError
from test_portable_runtime import OPA


class ConsumerToolSelection(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old);t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.parent=Path(t.name).resolve();self.source=self.parent/'source';self.source.mkdir(mode=0o700);self.private=self.parent/'node';self.private.mkdir(mode=0o700);self.tool=OPA.resolve();self.hashes=frozenset({hashlib.sha256(self.tool.read_bytes()).hexdigest()});self.owner=SimpleNamespace(cwd=str(self.source),private_state=self.private)
    def test_environment_alias_preserves_label_and_binds_same_approved_external_binary(self):
        directory=self.source/'.venv-validation/bin';directory.mkdir(mode=0o700,parents=True);alias=directory/'opa';alias.symlink_to(self.tool)
        with patch('subprocess.Popen',side_effect=AssertionError('Selection alone cannot execute')):
            port=NativeConsumerOPA(self.owner,self.source,tool=str(alias),approved_hashes=self.hashes,workarea=self.private)
            identity=port.admit_tool()
        self.assertEqual(identity['label'],str(alias));self.assertEqual(identity['resolved'],str(self.tool));self.assertIn(identity['sha256'],self.hashes)
    def test_real_private_binary_is_still_rejected_even_with_the_exact_approved_hash(self):
        directory=self.parent/'venv/bin';directory.mkdir(mode=0o700,parents=True);tool=directory/'opa';shutil.copyfile(self.tool,tool);tool.chmod(0o700)
        with patch('subprocess.Popen',side_effect=AssertionError('No private program')):
            with self.assertRaises(InputAdmissionError):approved_external_program(str(tool),str(self.source),str(self.source),self.private,self.hashes)
    def test_source_or_node_binary_and_unapproved_target_remain_forbidden(self):
        with patch('subprocess.Popen',side_effect=AssertionError('No source/node program')):
            for directory in (self.source,self.private):
                tool=directory/'opa';shutil.copyfile(self.tool,tool);tool.chmod(0o700)
                with self.subTest(directory=directory),self.assertRaises(InputAdmissionError):approved_external_program(str(tool),str(self.source),str(self.source),self.private,self.hashes)
            with self.assertRaises(InputAdmissionError):approved_external_program(str(self.tool),str(self.source),str(self.source),self.private,frozenset({'0'*64}))
    def test_credential_label_is_not_accepted_as_an_environment_alias(self):
        directory=self.parent/'.ssh';directory.mkdir(mode=0o700);alias=directory/'opa';alias.symlink_to(self.tool)
        with patch('subprocess.Popen',side_effect=AssertionError('No credential path access')):
            with self.assertRaisesRegex(InputAdmissionError,'private_selection_forbidden'):approved_external_program(str(alias),str(self.source),str(self.source),self.private,self.hashes)
    def test_real_policy_execution_and_inert_replay_keep_the_selected_alias_binding(self):
        import test_v2_consumer_lifecycle_opa as reference
        case=reference.ConsumerOPA();case.setUp();self.addCleanup(case.doCleanups)
        directory=case.parent/'.venv-validation/bin';directory.mkdir(mode=0o700,parents=True);alias=directory/'opa';alias.symlink_to(self.tool)
        actual,wire,_=case.execute('private-candidate',tool=alias)
        self.assertIsNone(actual['error']);self.assertEqual(wire['program']['label'],str(alias));self.assertEqual(wire['program']['resolved'],str(self.tool));self.assertIn(wire['program']['sha256'],self.hashes)
