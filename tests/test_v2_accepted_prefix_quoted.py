"""Git's literal quoted path output through complete unchanged V1 prefix checks."""
from pathlib import Path
import json,os,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_accepted_prefix as fixture
from test_v2_accepted_prefix_recording import ORACLE,CURRENT
from test_v2_pilot_action_verification import git,commit
from test_v2_personal_channel_programs import snapshot

class WholeQuotedPrefixPaths(unittest.TestCase):
    def setUp(self):
        case=fixture.WholeAcceptedPrefix();case.setUp();self.addCleanup(case.doCleanups);self.fixture=case
    def compare(self,filename,*,literal_exists=False,unquoted=False,ledger=False):
        source,_=self.fixture.selected('normal');relative=('governance/lifecycle/synthetic/transactions/' if ledger else 'model/governance/lifecycle/personal-channel/')+filename
        path=source/relative;path.parent.mkdir(parents=True,exist_ok=True);raw=b'{"explicit_quoted_filename_fixture":true}\n';path.write_bytes(raw)
        git(source,'config','core.quotepath','false' if unquoted else 'true');base=commit(source)
        tree=subprocess.check_output(['git','-C',str(source),'ls-tree','-r',base,'--',relative]).decode();self.assertEqual(len(tree.splitlines()),1);name=tree.split('\t',1)[1].rstrip('\n')
        if unquoted:self.assertEqual(name,relative)
        else:self.assertTrue(name.startswith('"') and name.endswith('"'),name);self.assertNotEqual(name,relative)
        if literal_exists:
            # V1 joins the literal C-quoted label. Preserve that actual behavior;
            # neither test nor V2 decodes it into a different selected path.
            selected=source/name;selected.parent.mkdir(parents=True,exist_ok=True);selected.write_bytes(raw)
        before=snapshot(source);env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','LD_','DYLD_'))};env.update(PYTHONDONTWRITEBYTECODE='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1')
        old=subprocess.run([sys.executable,'-B','-c',ORACLE,str(source),base],cwd=source,env={**env,'PYTHONPATH':str(source/'scripts')},capture_output=True,timeout=300);self.assertEqual(old.returncode,0,old.stderr);expected=json.loads(old.stdout)
        if ledger:self.assertEqual(expected['exception'],{'type':'ContractError','message':'Only published transactions may be tracked in the ledger'})
        elif literal_exists or unquoted:self.assertIsNone(expected['exception']);self.assertEqual(expected['return_value'],3)  # two frozen receipts plus one test transaction
        else:self.assertEqual(expected['exception'],{'type':'ContractError','message':'Accepted preparation deleted or replaced'})
        self.assertEqual(snapshot(source),before)
        actual=subprocess.run([sys.executable,'-B','-c',CURRENT,str(source),base,str(source.parent/('quoted-prefix-private-'+source.name))],cwd=source.parent,env={**env,'PYTHONPATH':str(ROOT/'scripts')},capture_output=True,timeout=300)
        self.assertEqual(actual.returncode,0,actual.stderr[-4500:]);self.assertEqual(actual.stdout,old.stdout);self.assertEqual(actual.stderr,old.stderr);self.assertFalse(source.exists())
    def test_whole_original_C_quoted_non_ASCII_preparation_name_preserves_missing_literal_path_diagnostic(self):self.compare('führung.json')
    def test_whole_original_control_quote_and_backslash_preparation_names_keep_literal_checks(self):
        for name in ('tab\tname.json','line\nname.json','quote"name.json','back\\name.json'):
            with self.subTest(name=name):self.compare(name)
    def test_whole_original_coincidentally_existing_literal_quoted_label_is_hashed_without_decoding(self):
        for name in ('tab\tname.json','quote"name.json'):
            with self.subTest(name=name):self.compare(name,literal_exists=True)
    def test_whole_original_unquoted_unicode_preparation_path_with_core_quote_path_disabled(self):self.compare('führung.json',unquoted=True)
    def test_whole_original_C_quoted_nontransaction_ledger_name_still_fails_before_path_access(self):self.compare('extra\tname.json',ledger=True)
class QuotedPrefixApplication(unittest.TestCase):
    def test_public_capture_retains_original_complete_error_or_success_for_literal_quoted_paths(self):
        from lib.accepted_prefix_application import generate,inspect
        from lib.portable.runtime import source_digest
        from lib.functional_parity import git_read
        for literal_exists in (False,True):
            with self.subTest(literal_exists=literal_exists):
                case=fixture.WholeAcceptedPrefix();case.setUp()
                try:
                    source,_=case.selected('normal');relative='model/governance/lifecycle/personal-channel/tab\tname.json';path=source/relative;path.parent.mkdir(parents=True,exist_ok=True);raw=b'{"explicit_quoted_API_fixture":true}\n';path.write_bytes(raw);base=commit(source)
                    label=subprocess.check_output(['git','-C',str(source),'ls-tree','-r',base,'--',relative]).decode().split('\t',1)[1].rstrip('\n');self.assertTrue(label.startswith('"'))
                    if literal_exists:
                        selected=source/label;selected.parent.mkdir(parents=True,exist_ok=True);selected.write_bytes(raw)
                    before=snapshot(source);old=subprocess.run([sys.executable,'-B','-c',ORACLE,str(source),base],cwd=source,env={**os.environ,'PYTHONPATH':str(source/'scripts'),'PYTHONDONTWRITEBYTECODE':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null'},capture_output=True,timeout=300);self.assertEqual(old.returncode,0,old.stderr);expected=json.loads(old.stdout)
                    instance=source.parent/'quoted-prefix-api-node';instance.mkdir(mode=0o700);settings={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
                    receipt,result=generate({'source_worktree':str(source),'base_ref':base,'transport_profile':'legacy-accepted-prefix-git-v1'},instance,settings);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_return_value'],expected['return_value']);self.assertEqual(result['kernel_result']['kernel_exception'],expected['exception']);self.assertEqual(receipt['original_exit_code'],0 if literal_exists else 1);self.assertEqual(snapshot(source),before);self.assertFalse(receipt['source_export_requested']);self.assertFalse(receipt['official_acceptance'])
                    import shutil
                    from unittest.mock import patch
                    shutil.rmtree(source)
                    with patch('subprocess.Popen',side_effect=AssertionError('No source Git')):
                        self.assertTrue(inspect(receipt['record_root'],node=settings)['retained_declared_replay_consistent'])
                finally:case.doCleanups()

class QuotedPrefixAdmission(unittest.TestCase):
    def test_malformed_foreign_and_traversal_labels_cannot_expand_the_source_selection(self):
        from jsonschema import Draft202012Validator
        from lib.repository_lifecycle.context import RepositoryLifecycle
        from lib.accepted_prefix_protocol import LegacyAcceptedPrefixProtocol
        from lib.requirement_validation_budget import InputAdmissionError
        profile=LegacyAcceptedPrefixProtocol(RepositoryLifecycle(Path('/chosen-source'),validator_class=Draft202012Validator,path_factory=Path))
        malformed=['"outside/secret.json"','"model/governance/lifecycle/personal-channel/../outside"','"model/governance/lifecycle/personal-channel/unclosed','"model/governance/lifecycle/personal-channel/bad\\q"','"model/governance/lifecycle/personal-channel/bad\\777"','"model/governance/lifecycle/personal-channel/raw\ncontrol"','"model/governance/lifecycle/personal-channel/extra"quote"','/other-source/"model/governance/lifecycle/personal-channel/file"','"/model/governance/lifecycle/personal-channel/file"']
        for label in malformed:
            with self.subTest(label=label),self.assertRaises(InputAdmissionError):profile.hashed_path(label,'/chosen-source')

if __name__=='__main__':unittest.main(verbosity=2)
