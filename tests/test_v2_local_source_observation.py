"""Original V1 physical inputs, minimal inert-data reads and closed replay observations."""
from copy import deepcopy
import base64
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests/acceptance')]
from lib.providers import local_source_observation as native
from lib import onboarding_readiness
from v1_source_inspection_oracle import load_fixture,make_repository,original_files
FIXTURES=ROOT/'tests/fixtures/axiom-v1-parity/source-inspection';PROFILE='legacy-worktree-signatures-v1'


class NativeSourceObservation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name).resolve();self.contract=load_fixture(FIXTURES)

    def write_case(self,name,case):
        root=self.base/name;root.mkdir()
        for name,entry in case['files'].items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(entry['base64'],validate=True) if isinstance(entry,dict) else entry.encode())
        return root

    def render(self,observation,texts,target):
        facts=native.facts(observation,texts,product_label=self.contract['product_label'],target_label=str(target),at=self.contract['at']);paths=self.contract['logical_outputs']
        result={paths['integration']:(json.dumps(facts['integration'],indent=2)+'\n').encode()}
        if observation['inspection_kind']!='integration':
            report=onboarding_readiness.assess_surface('synthetic/native',surface=facts['surface'],ci_files=facts['onboarding_ci_files'],ci_text=facts['onboarding_ci_text'],integration=facts['integration'],at=self.contract['at'],target_label=str(target))
            result[paths['onboarding_json']]=(json.dumps(report,indent=2)+'\n').encode();result[paths['onboarding_markdown']]=onboarding_readiness.render_markdown(report).encode()
        return result

    def compare_original(self,target,tag):
        expected,exits=original_files(FIXTURES,self.base/('oracle-'+tag),target,'synthetic/native',self.contract['at'])
        observation,texts=native.capture(target,'all',PROFILE);actual=self.render(observation,texts,target);self.assertEqual(actual,expected)
        return observation,texts,actual

    def test_full_original_json_markdown_from_non_git_positive_missing_and_binary_cases(self):
        for case in self.contract['cases']:
            with self.subTest(case=case['id']):
                root=self.write_case(case['id'],case);self.assertFalse((root/'.git').exists());self.compare_original(root,case['id'])

    def test_empty_directory_keeps_original_findings_without_git(self):
        root=self.base/'empty';root.mkdir();self.compare_original(root,'empty')

    def test_native_pattern_union_matches_original_for_nested_hidden_and_newline_paths(self):
        root=self.write_case('native-patterns',self.contract['cases'][0])
        names=['.github/workflows/second.yaml','Jenkinsfile','prefix.gitlab-ci.yml','azure-pipelines.yml',
            'docs/governance/extra.json','.factory/security/.hidden','docs/security/extra.md',
            '.agent-executions/extra.yml','.slice-candidate-creations/extra.json','examples/governance_case/without-extension',
            'tests/root.py','tests/sub/helper.py','src/root.py','src/sub\nfolder/module.py','scripts/flat.py','scripts/deep/not-counted.py','artifacts/vulnerability.json']
        for name in names:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('SeCrEtS\n# devsecops-governance-framework\n')
        self.compare_original(root,'native-patterns')

    def test_dirty_untracked_and_poison_source_observed_without_execution(self):
        root=self.base/'dirty';make_repository(root,self.contract['cases'][0]);ci=root/'.github/workflows/ci.yml';ci.write_text('name: Dirty\r\njobs: {}\r\n')
        (ci.parent/'untracked.yml').write_text('name: Untracked\n# devsecops-governance-framework\n')
        marker=self.base/'executed';poison=root/'scripts/poison.py';poison.parent.mkdir(exist_ok=True);poison.write_text('from pathlib import Path\nPath('+repr(str(marker))+').touch()\n')
        observation,texts,actual=self.compare_original(root,'dirty');self.assertFalse(marker.exists());self.assertNotIn('scripts/poison.py',texts)
        self.assertIn('untracked.yml',actual[self.contract['logical_outputs']['integration']].decode());self.assertIn(b'\r\n',texts['.github/workflows/ci.yml'])

    def test_closed_observation_replays_after_caller_deleted(self):
        root=self.write_case('caller',self.contract['cases'][0]);observation,texts,before=self.compare_original(root,'caller');saved=json.loads(json.dumps(observation));shutil.rmtree(root)
        self.assertEqual(self.render(saved,texts,root),before);self.assertTrue(native.profile(PROFILE)['working_tree_used'])

    def test_integration_only_never_reads_security_or_recurses_unrelated_directories(self):
        root=self.write_case('integration',self.contract['cases'][0]);security=root/'docs/security/private.md';security.parent.mkdir(parents=True,exist_ok=True);security.write_text('SYNTHETIC_PRIVATE_SECURITY')
        original=native.regular_bytes;reads=[]
        def check(root,name):
            reads.append(name);self.assertFalse(name.startswith('docs/'));return original(root,name)
        with patch.object(native,'regular_bytes',side_effect=check):observation,texts=native.capture(root,'integration',PROFILE)
        self.assertTrue(reads);self.assertNotIn(str(security.relative_to(root)),texts);self.assertFalse(any(row['path'].startswith('docs/') for row in observation['nodes']))
        expected,_=original_files(FIXTURES,self.base/'oracle-integration',root,'synthetic/native',self.contract['at'])
        self.assertEqual(self.render(observation,texts,root),{self.contract['logical_outputs']['integration']:expected[self.contract['logical_outputs']['integration']]})

    def test_original_first_eight_security_texts_and_directory_existence_semantics(self):
        root=self.base/'surfaces';root.mkdir();(root/'README.md').mkdir();(root/'pyproject.toml').mkdir();security=root/'docs/security';security.mkdir(parents=True)
        for n in range(9):(security/(str(n)+'.md')).write_text('secrets' if n==8 else 'inert')
        (root/'sbom-directory').mkdir();(root/'sbom-directory/file.txt').write_text('not itself an artifact name')
        observation,texts,actual=self.compare_original(root,'surfaces');self.assertNotIn('docs/security/8.md',texts)
        facts=native.facts(observation,texts,product_label='axiom-v2',target_label=str(root),at=self.contract['at']);self.assertFalse(facts['surface']['secrets_scan_support']);self.assertFalse(facts['surface']['supply_chain_artifact_present'])

    def test_selected_symlinks_are_rejected_without_reading_outside(self):
        root=self.write_case('unsafe',self.contract['cases'][0]);outside=self.base/'outside';outside.write_text('SYNTHETIC_PRIVATE_OUTSIDE');ci=root/'.github/workflows/ci.yml';ci.unlink();ci.symlink_to(outside)
        with patch.object(native,'regular_bytes',side_effect=AssertionError('must not read selected symlink')):
            with self.assertRaisesRegex(ValueError,'selected_local_source_symlink_forbidden'):native.capture(root,'all',PROFILE)
        ci.unlink();shutil.rmtree(root/'.github');(root/'.github').symlink_to(self.base,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'selected_local_source_symlink_forbidden'):native.capture(root,'integration',PROFILE)

    def test_tampered_members_blobs_profiles_and_types_rejected(self):
        root=self.write_case('tamper',self.contract['cases'][0]);observation,texts=native.capture(root,'all',PROFILE)
        mutations=[]
        bad=deepcopy(observation);bad['schema_version']=True;mutations.append(bad)
        bad=deepcopy(observation);bad['nodes'].append(deepcopy(bad['nodes'][0]));mutations.append(bad)
        bad=deepcopy(observation);bad['nodes'][0]['path']='../outside';mutations.append(bad)
        bad=deepcopy(observation);bad['profile']='other';mutations.append(bad)
        bad=deepcopy(observation);bad['extra']='SYNTHETIC_PRIVATE';mutations.append(bad)
        for bad in mutations:
            with self.assertRaises(ValueError):native.validate(bad,texts)
        key=next(iter(texts));changed=dict(texts);changed[key]+=b'x'
        with self.assertRaisesRegex(ValueError,'local_source_text_changed'):native.validate(observation,changed)
        changed=dict(texts);changed['../outside']=b'x'
        with self.assertRaisesRegex(ValueError,'local_source_text_membership_changed'):native.validate(observation,changed)

    def test_budgets_unknown_profile_and_change_during_capture(self):
        root=self.write_case('budget',self.contract['cases'][0])
        for name,limit in [('MAX_NODES',1),('MAX_NAMES',1),('MAX_FILE',1),('MAX_TEXT',1),('MAX_FACTS',1)]:
            with self.subTest(limit=name),patch.object(native,name,limit),self.assertRaises(ValueError):native.capture(root,'all',PROFILE)
        with self.assertRaisesRegex(ValueError,'unknown_local_source_observation_profile'):native.capture(self.base/'absent','all','other')
        original=native.inventory;calls=[]
        def changed(root,kind):
            value=original(root,kind);calls.append(1);return value if len(calls)==1 else value+[{'path':'later','kind':'file'}]
        with patch.object(native,'inventory',side_effect=changed),self.assertRaisesRegex(ValueError,'local_source_changed_during_capture'):native.capture(root,'all',PROFILE)


if __name__=='__main__':unittest.main()
