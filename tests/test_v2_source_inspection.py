"""Original consumer-source wires, retained Git proof and private replay boundaries."""
from contextlib import redirect_stdout
from copy import deepcopy
import base64
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts')); sys.path.insert(0, str(ROOT / 'tests/acceptance'))
from lib import source_snapshot_proof as proof, source_inspection_application as app
from lib.provider_ports import source_inspection_profile
from lib.portable.contracts import canonical_digest
from lib.consumer_intake_store import atomic_json
from v1_source_inspection_oracle import load_fixture, make_repository, original_files, git

FIXTURES = ROOT / 'tests/fixtures/axiom-v1-parity/source-inspection'
AT = '2026-11-15T12:00:00Z'; PROFILE = source_inspection_profile('legacy-ci-signatures-v1')


class SourceInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve(); self.fixture = load_fixture(FIXTURES)
        self.repository = self.root / 'consumer'; self.revision = make_repository(self.repository, self.fixture['cases'][0])
        self.node = self.root / 'node'; self.node.mkdir(mode=0o700); (self.node / 'state').mkdir(mode=0o700)
        self.context = app.SourceInspectionContext(self.node, {'node_id': 'synthetic-source-node', 'product': 'axiom-v2'})

    def create(self, kind='all', **changes):
        args = dict(kind=kind, repository=self.repository, revision=self.revision, repository_id='synthetic/consumer',
                    profile=deepcopy(PROFILE), at=AT); args.update(changes)
        return self.context.create(**args)

    def test_complete_original_json_markdown_match_positive_missing_ci_and_binary_cases(self):
        for case in self.fixture['cases']:
            with self.subTest(case=case['id']):
                repository = self.root / case['id']; revision = make_repository(repository, case)
                expected, exits = original_files(FIXTURES, self.root / ('oracle-' + case['id']), repository, 'synthetic/consumer', AT)
                self.assertEqual(list(exits), case['expected_exits'])
                identifier, value = self.create(repository=repository, revision=revision)
                self.assertEqual(self.context.inspect(identifier), value)
                self.assertEqual(set(value['files']), set(expected))
                for name, raw in expected.items(): self.assertEqual((self.context.artifacts / identifier / name).read_bytes(), raw)
                self.assertEqual(self.context.legacy_exit(identifier), max(exits))
                self.assertEqual(self.create(repository=repository, revision=revision)[0], identifier)

    def test_actual_persisted_manifest_budget_is_rejected_before_cache_admission(self):
        probe = self.root / 'probe'; probe.mkdir(mode=0o700)
        manifest = proof.capture(self.repository, self.revision, probe)
        compact = len(json.dumps(manifest, sort_keys=True).encode())
        persisted = len((json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode())
        self.assertLess(compact, persisted)
        with patch.object(proof, 'MAX_MANIFEST', (compact + persisted) // 2), \
             self.assertRaisesRegex(ValueError, 'source_manifest_budget'):
            self.create()
        self.assertEqual(list(self.context.inputs.iterdir()), [])
        identifier, value = self.create(); self.assertEqual(self.context.inspect(identifier), value)

    def test_each_finite_kind_has_only_its_original_outputs_and_explicit_legacy_exit(self):
        for kind, names in [('integration', {app.INTEGRATION}), ('onboarding', {app.ONBOARDING + '.json', app.ONBOARDING + '.md'})]:
            identifier, value = self.create(kind)
            self.assertEqual(set(value['files']), names); self.assertEqual(self.context.legacy_exit(identifier), 0)
        with self.assertRaisesRegex(ValueError, 'unsupported_source_inspection_kind'): self.create(kind='arbitrary-script')

    def test_dirty_worktree_and_poison_source_are_ignored_and_original_repository_is_not_needed_for_replay(self):
        expected, _ = original_files(FIXTURES, self.root / 'oracle', self.repository, 'synthetic/consumer', AT)
        (self.repository / '.github/workflows/ci.yml').write_text('dirty false findings')
        (self.repository / 'README.md').unlink()
        marker = self.root / 'executed'; poison = self.repository / 'scripts/check_repo_governance_integration.py'
        poison.write_text(f'from pathlib import Path\nPath({str(marker)!r}).touch()\n')
        identifier, value = self.create(); self.assertFalse(value['working_tree_used']); self.assertFalse(marker.exists())
        for name, raw in expected.items(): self.assertEqual((self.context.artifacts / identifier / name).read_bytes(), raw)
        shutil.rmtree(self.repository); self.assertEqual(self.context.inspect(identifier), value)

    def test_explicit_clock_uses_original_utc_second_display_while_binding_full_input(self):
        at = '2026-11-15T14:00:00.123456+02:00'
        expected, _ = original_files(FIXTURES, self.root / 'oracle', self.repository, 'synthetic/consumer', at)
        identifier, value = self.create(at=at); self.assertEqual(value['assessed_at'], at)
        for name, raw in expected.items(): self.assertEqual((self.context.artifacts / identifier / name).read_bytes(), raw)
        with self.assertRaises(ValueError): self.create(at='2026-11-15T12:00:00')

    def test_source_labels_are_declared_unverified_and_all_authority_stays_false(self):
        _, value = self.create()
        self.assertEqual(value['evidence_trust'], 'unverified'); self.assertEqual(value['product_label'], 'axiom-v2')
        self.assertFalse(value['repository_identity_verified']); self.assertEqual(value['declared_repository_id'], 'synthetic/consumer')
        for flag in ('official_acceptance','production_approval','risk_acceptance','authority_transferred',
                     'operating_acceptance_inherited','provider_invoked','published'): self.assertIs(value[flag], False)
        self.assertEqual(value['mode'], 'report-only')

    def test_unknown_or_forged_profiles_fail_before_any_git_read(self):
        with patch.object(proof, 'git_read', side_effect=AssertionError('must not read source')):
            with self.assertRaises(ValueError): self.create(profile={'profile': 'unknown', 'source_signature_only': True})
            for change in ({'source_signature_only': False}, {'source_signature_only': 1}, {'extra': True}):
                with self.assertRaises(ValueError): self.create(profile={**PROFILE, **change})

    def test_output_mutation_extra_member_and_symlink_are_rejected(self):
        identifier, value = self.create(); root = self.context.artifacts / identifier; path = root / app.INTEGRATION; old = path.read_bytes()
        path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'source_inspection_output_changed'): self.context.inspect(identifier)
        path.write_bytes(old); extra = root / 'extra.txt'; extra.write_text('extra')
        with self.assertRaisesRegex(ValueError, 'source_inspection_output_members_changed'): self.context.inspect(identifier)
        extra.unlink(); extra.symlink_to(path)
        with self.assertRaisesRegex(ValueError, 'unsafe_source_inspection_artifact'): self.context.inspect(identifier)

    def test_record_change_and_foreign_node_are_rejected(self):
        identifier, value = self.create(); record = self.context.assessments / (identifier + '.json')
        changed = deepcopy(value); changed['declared_repository_id'] = 'synthetic/forged'; atomic_json(record, changed)
        with self.assertRaisesRegex(ValueError, 'source_inspection_record_changed'): self.context.inspect(identifier)
        atomic_json(record, value)
        other = app.SourceInspectionContext(self.node, {'node_id': 'other-source-node', 'product': 'axiom-v2'})
        with self.assertRaisesRegex(ValueError, 'source_inspection_node_runtime_or_product_changed'): other.inspect(identifier)

    def test_resealed_authority_or_kind_conversion_cannot_reinterpret_old_outputs(self):
        identifier, value = self.create(kind='integration')
        for key, changed_value in [('official_acceptance', True), ('repository_identity_verified', True), ('inspection_kind', 'onboarding')]:
            changed = deepcopy(value); changed[key] = changed_value; forged = canonical_digest(changed)
            atomic_json(self.context.assessments / (forged + '.json'), changed)
            shutil.copytree(self.context.artifacts / identifier, self.context.artifacts / forged)
            with self.assertRaises(ValueError): self.context.inspect(forged)

    def test_retained_manifest_and_data_cannot_be_resealed_away_from_original_git_commit(self):
        identifier, value = self.create(); data, manifest = self.context.input_data(value['input_id'])
        path = data / 'README.md'; path.write_text('forged source')
        with self.assertRaisesRegex(ValueError, 'source_blob_changed'): self.context.inspect(identifier)
        manifest['files']['README.md'].update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                            git_blob=proof.object_sha('blob', path.read_bytes()))
        with self.assertRaisesRegex(ValueError, 'source_tree_changed'): proof.verify(data, manifest)
        atomic_json(data.parent / 'manifest.json', manifest)
        with self.assertRaisesRegex(ValueError, 'source_inspection_input_changed'): self.context.inspect(identifier)

    def test_cli_default_findings_zero_and_explicit_legacy_exit_one_without_mode_change(self):
        repository = self.root / 'missing'; revision = make_repository(repository, self.fixture['cases'][1])
        args = ['create','--kind','all','--repo',str(repository),'--revision',revision,'--repository-id','synthetic/missing',
                '--profile','legacy-ci-signatures-v1','--at',AT]
        settings = {'node_id': 'synthetic-source-node', 'product': 'axiom-v2'}
        with redirect_stdout(io.StringIO()) as output: self.assertEqual(app.run(args,self.node,settings),0)
        receipt = json.loads(output.getvalue()); self.assertEqual(receipt['original_finding_exit'],1)
        with redirect_stdout(io.StringIO()) as output: self.assertEqual(app.run([*args,'--fail-on-findings'],self.node,settings),1)
        self.assertEqual(json.loads(output.getvalue())['assessment_id'],receipt['assessment_id'])
        self.assertFalse(json.loads(output.getvalue())['official_acceptance'])


class SourceProofTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve(); self.repository = self.root / 'repo'
        self.revision = make_repository(self.repository, load_fixture(FIXTURES)['cases'][0])
        self.data = self.root / 'data'; self.data.mkdir(mode=0o700)
        self.manifest = proof.capture(self.repository,self.revision,self.data)

    def test_original_git_tree_and_commit_match_and_mode_tree_commit_reseals_fail(self):
        self.assertEqual(self.manifest['tree'],git(self.repository,'rev-parse','HEAD^{tree}'))
        self.assertEqual(proof.verify(self.data,self.manifest),self.manifest)
        for kind in ('mode','tree','commit','version','bytes'):
            forged=deepcopy(self.manifest);name=next(iter(forged['files']))
            if kind=='mode':forged['files'][name]['mode']='100755'
            elif kind=='tree':forged['tree']='0'*40
            elif kind=='commit':forged['commit_object_base64']=base64.b64encode(b'forged commit').decode()
            elif kind=='version':forged['schema_version']=True
            else:forged['files'][name]['bytes']=True
            with self.subTest(kind=kind), self.assertRaises(ValueError):proof.verify(self.data,forged)

    def test_extra_empty_directories_and_files_and_symlink_members_are_not_committed_input(self):
        directory=self.data/'ambient';directory.mkdir()
        with self.assertRaisesRegex(ValueError,'source_members_changed'):proof.verify(self.data,self.manifest)
        directory.rmdir();extra=self.data/'extra.txt';extra.write_text('extra')
        with self.assertRaisesRegex(ValueError,'source_members_changed'):proof.verify(self.data,self.manifest)
        extra.unlink();extra.symlink_to(self.data/'README.md')
        with self.assertRaisesRegex(ValueError,'unsafe_source_data'):proof.verify(self.data,self.manifest)

    def test_all_source_budgets_and_free_space_reserve_are_enforced_before_copy(self):
        for name,limit in [('MAX_FILES',1),('MAX_FILE',1),('MAX_TOTAL',1),('MAX_MANIFEST',1),('MAX_COMMIT',1),('MAX_PATH',1)]:
            with self.subTest(budget=name), tempfile.TemporaryDirectory() as temporary:
                target=Path(temporary).resolve();
                with patch.object(proof,name,limit),self.assertRaises(ValueError):proof.capture(self.repository,self.revision,target)
                self.assertEqual(list(target.iterdir()),[])
        with tempfile.TemporaryDirectory() as temporary:
            target=Path(temporary).resolve()
            with patch.object(proof,'reserve',side_effect=ValueError('disk_reserve')),self.assertRaisesRegex(ValueError,'disk_reserve'):
                proof.capture(self.repository,self.revision,target)
            self.assertEqual(list(target.iterdir()),[])

    def test_exact_commit_root_and_portable_case_collisions_are_checked(self):
        target=self.root/'fresh';target.mkdir()
        for repository, revision in [(self.repository,'HEAD'),(self.repository/'src',self.revision)]:
            with self.assertRaises(ValueError):proof.capture(repository,revision,target)
        blob=git(self.repository,'rev-parse','HEAD:README.md')
        for name in ('Case.txt','case.txt'):git(self.repository,'update-index','--add','--cacheinfo','100644,'+blob+','+name)
        tree=git(self.repository,'write-tree');commit=git(self.repository,'commit-tree',tree,'-p',self.revision,'-m','Case collision fixture')
        with self.assertRaises(ValueError):proof.capture(self.repository,commit,target)
        self.assertEqual(list(target.iterdir()),[])

    def test_deep_bounded_git_tree_hashing_does_not_recurse(self):
        blob = hashlib.sha1(b'blob 0\0', usedforsecurity=False).hexdigest()
        expected = hashlib.sha1(b'tree 29\0' + b'100644 f\0' + bytes.fromhex(blob), usedforsecurity=False).hexdigest()
        for _ in range(1500):
            body = b'40000 d\0' + bytes.fromhex(expected)
            expected = hashlib.sha1(b'tree ' + str(len(body)).encode() + b'\0' + body, usedforsecurity=False).hexdigest()
        self.assertEqual(proof.tree_sha({'d/' * 1500 + 'f': {'mode': '100644', 'git_blob': blob}}), expected)

    def test_unicode_aliases_and_case_variants_of_git_metadata_are_not_portable_source(self):
        for names in [('é.txt', 'e\u0301.txt'), ('é/a.txt', 'e\u0301/b.txt'), ('nested/.GiT/config',)]:
            with self.subTest(names=names), self.assertRaises(ValueError): proof.portable_source_names(names)
        proof.portable_source_names(['é/a.txt', 'ordinary/.gitignore'])

    def test_source_input_root_and_tracked_symlinks_are_rejected(self):
        link=self.root/'linked-data';link.symlink_to(self.data,target_is_directory=True)
        with self.assertRaises(ValueError):proof.verify(link,self.manifest)
        (self.repository/'link').symlink_to('README.md');git(self.repository,'add','link');git(self.repository,'commit','-m','Tracked symlink fixture')
        target=self.root/'fresh';target.mkdir()
        with self.assertRaises(ValueError):proof.capture(self.repository,git(self.repository,'rev-parse','HEAD'),target)
        self.assertEqual(list(target.iterdir()),[])


if __name__=='__main__':unittest.main()
