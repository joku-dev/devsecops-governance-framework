"""Actual valid V1 YAML beyond an added budget is technical incomplete, never a verdict."""
from contextlib import redirect_stdout,redirect_stderr
import hashlib,io,json
from pathlib import Path
import sys,unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_requirement_validation as reference
from lib.requirement_validation_application import check,inspect
from lib.providers.sbom_export_storage import read_record
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read


class RequirementSourceAdmissionClassification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reference.WholeRequirementValidation.setUpClass()

    def setUp(self):
        self.case=reference.WholeRequirementValidation('test_whole_real_default_data_and_no_history_call')
        self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.data=self.case.root
        self.instance=self.data.parent/'instance';self.instance.mkdir(mode=0o700)
        self.settings={'node_id':'c'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),
                       'runtime_source_digest':source_digest()}

    def original(self):
        original=reference.ORIGINAL;stdout,stderr=io.StringIO(),io.StringIO()
        with patch.object(original,'ROOT',self.data),patch.multiple(original,**{k:self.data/n for k,n in reference.PATHS.items()}),patch.object(sys,'argv',['original']),redirect_stdout(stdout),redirect_stderr(stderr):
            try:code,error=original.main(),None
            except Exception as exc:code,error=1,{'type':type(exc).__name__,'message':str(exc)}
        return {'exit_code':code,'stdout':stdout.getvalue(),'stderr':stderr.getvalue(),'kernel_exception':error}

    def current(self):
        return check({'source_worktree':str(self.data),'base_ref':None},self.instance,self.settings)

    def assert_technical_limit(self):
        self.assertEqual(self.original()['exit_code'],0)
        receipt,result=self.current()
        self.assertEqual(receipt['state'],'incomplete');self.assertEqual(receipt['exit_code'],2)
        self.assertIsNone(receipt['original_exit_code']);self.assertIsNone(result)
        retained=read_record(receipt['record_root'])[2]
        self.assertEqual(retained['exception_type'],'InputAdmissionError')
        self.assertFalse(retained['official_acceptance']);self.assertFalse(retained['authority_transferred'])
        reconstructed=inspect(receipt['record_root'])
        self.assertEqual(reconstructed['state'],'incomplete')
        self.assertFalse(reconstructed['retained_declared_replay_consistent'])

    def test_valid_original_catalog_duplicate_scalar_aliases_hit_added_budget_as_incomplete2(self):
        path=self.data/reference.PATHS['CATALOG'];raw=path.read_bytes()
        import yaml
        value=yaml.safe_load(raw)['catalog_id']
        header=('catalog_id: &admission_id '+json.dumps(value)+'\n'+'catalog_id: *admission_id\n'*5000).encode()
        path.write_bytes(header+raw)
        self.assert_technical_limit()

    def test_native_frontmatter_admission_is_not_swallowed_by_original_valueerror_handling(self):
        name=self.case.native_case;case=self.case.read(name)
        case['intake_type']='native_git'
        case['source']['source_path']='docs/governance/requirements/native-sources/ADMISSION-TEST.md'
        raw=('---\nid: &admission_id NATIVE-REQ-2026-TEST\n'+'id: *admission_id\n'*5000+
             'title: Explicit fixture\nnormative_strength: MUST\ndomain: devsecops\nowner: Fixture owner\ndecision_ref: '+case['source']['decision_ref']+'\n---\nThe explicit test statement.\n').encode()
        target=self.data/case['source']['source_path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        case['source']['source_sha256']=hashlib.sha256(raw).hexdigest();self.case.put(name,case)
        self.assert_technical_limit()

    def test_genuine_original_null_catalog_exception_remains_complete_original_exit1(self):
        (self.data/reference.PATHS['CATALOG']).write_bytes(b'null')
        expected=self.original();self.assertEqual(expected['exit_code'],1)
        receipt,result=self.current()
        self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['exit_code'],1)
        self.assertEqual(result,expected)
        self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_native_file_alias_admission_does_not_label_a_projected_error_as_original_exit(self):
        path=self.data/reference.PATHS['CATALOG'];raw=path.read_bytes();path.unlink()
        outside=self.data.parent/'catalog-target.yaml';outside.write_bytes(raw);path.symlink_to(outside)
        self.assertEqual(self.original()['exit_code'],0)
        receipt,result=self.current()
        self.assertEqual(receipt['state'],'incomplete');self.assertEqual(receipt['exit_code'],2)
        self.assertIsNone(receipt['original_exit_code'])
        self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])


if __name__=='__main__':unittest.main()
