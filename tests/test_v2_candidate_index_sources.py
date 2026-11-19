"""Frozen original real CLI/wires and exact local candidate source capture."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from lib.functional_parity import git_read, V1_REFERENCE
from lib.portable.contracts import repository_key
from lib.portable_intake.candidate_index import build_from_documents, build_index
from lib.portable_intake.publisher import candidate, path_for
from lib.providers import candidate_index_source as capture
from test_portable_runtime import context


def record(provider='github-actions', number=1, event='push', repository=None, branch=None):
    ctx = context(provider)
    selected = number if repository is None else repository
    ctx['scm']['native_id'] = str(100000+selected)
    ctx['scm']['path'] = 'fixture-owner/repository-'+str(selected)
    ctx['ci']['event'] = event
    ctx['ci']['run_id'] = str(200000+number)
    ctx['synthetic'] = True
    if branch is not None:
        ctx['revision']['branch'] = branch
    if event == 'pull_request':
        ctx['revision']['mode'] = 'source-head'
    receipt = {'producer': ctx, 'execution_key': 'a'*64,
               'repository_key': repository_key(ctx['scm']),
               'verifier': {'source_digest': 'b'*64}, 'bundle_digest': 'c'*64,
               'decision': 'pass', 'execution': 'complete', 'trust': 'provenance_verified'}
    return candidate(receipt, {k: ctx['ci'][k] for k in ('run_id', 'job_id', 'attempt')},
                     '2026-11-15T12:00:00Z')


def wire(value):
    return (json.dumps(value, indent=2, sort_keys=True)+'\n').encode()


class CandidateSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = tempfile.TemporaryDirectory()
        cls.original_root = Path(cls.reference.name).resolve()
        archive = git_read(ROOT, 'archive', V1_REFERENCE, 'scripts', 'schemas', 'model',
                           'config', 'releases', 'pipeline-baseline', 'status')
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            for member in source.getmembers():
                assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
                assert member.isdir() or member.isfile()
            source.extractall(cls.original_root, filter='data')
        original = git_read(ROOT, 'show', V1_REFERENCE+':scripts/generate_portable_candidate_index.py')
        assert (cls.original_root/'scripts/generate_portable_candidate_index.py').read_bytes() == original

    @classmethod
    def tearDownClass(cls):
        cls.reference.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.producer = self.root/'producer'
        self.producer.mkdir(mode=0o700)

    def write(self, value, raw=None):
        path = self.producer/path_for(value)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw if raw is not None else wire(value))
        return path

    def original(self):
        destination = self.root/'original-index.json'
        result = subprocess.run([sys.executable,
            str(self.original_root/'scripts/generate_portable_candidate_index.py'),
            '--root', str(self.producer), '--output', str(destination)],
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
            capture_output=True, timeout=120)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b'', b''))
        return destination.read_bytes()

    def decoded(self, files):
        # Same unique-key JSON contract as the original read_json; file acquisition stays separate.
        def unique(pairs):
            value = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError('duplicate_json_key')
                value[key] = item
            return value
        return [(name, json.loads(raw, object_pairs_hook=unique)) for name, raw in files.items()]

    def test_entire_original_cli_file_and_projection_match_all_three_native_profiles(self):
        for provider in ('github-actions', 'gitlab-ci', 'bamboo'):
            self.write(record(provider))
        before = {str(p.relative_to(self.producer)): p.read_bytes()
                  for p in self.producer.rglob('*.json')}
        origin, files = capture.working(self.producer)
        value = build_from_documents(self.decoded(files))
        self.assertEqual(wire(value), self.original())
        self.assertEqual(value, build_index(self.producer))
        self.assertEqual(files, before)
        self.assertEqual(origin['mode'], 'working')
        self.assertFalse(value['official_acceptance'])
        self.assertFalse(value['native_verification_performed'])

    def test_empty_original_tree_is_an_empty_index_without_synthetic_latest(self):
        origin, files = capture.working(self.producer)
        self.assertEqual(files, {})
        self.assertEqual(wire(build_from_documents([])), self.original())

    def test_original_utf8_text_contract_rejects_bom_utf16_and_utf32_before_retention(self):
        from lib.candidate_index_application import CandidateIndexContext
        value = record(branch='feature/Größe')
        text = json.dumps(value, ensure_ascii=False, indent=2)+'\n'
        path = self.write(value, text.encode('utf-8'))
        instance = self.root/'instance'; instance.mkdir(mode=0o700)
        context = CandidateIndexContext(instance, {'node_id': 'a'*32})
        identifier, assessment = context.create(self.producer)
        self.assertEqual((context.artifacts/identifier/'index.json').read_bytes(), self.original())
        before_inputs = set(context.inputs.iterdir()); before_artifacts = set(context.artifacts.iterdir())
        for encoding in ('utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'utf-32', 'utf-32-le', 'utf-32-be'):
            with self.subTest(encoding=encoding):
                path.write_bytes(text.encode(encoding))
                destination = self.root/(encoding+'-original.json')
                result = subprocess.run([sys.executable,
                    str(self.original_root/'scripts/generate_portable_candidate_index.py'),
                    '--root', str(self.producer), '--output', str(destination)],
                    env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}, capture_output=True, timeout=120)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(destination.exists())
                with self.assertRaisesRegex(ValueError, 'invalid_candidate_index_payload'):
                    context.create(self.producer)
                self.assertEqual(set(context.inputs.iterdir()), before_inputs)
                self.assertEqual(set(context.artifacts.iterdir()), before_artifacts)

    def test_complete_public_application_export_is_byte_identical_to_original_cli(self):
        from contextlib import redirect_stdout, redirect_stderr
        from lib.candidate_index_application import run
        for number, provider in enumerate(('github-actions', 'gitlab-ci', 'bamboo'), 1):
            self.write(record(provider, number=number))
        expected = self.original()
        instance = self.root/'instance'; instance.mkdir(mode=0o700)
        output = self.root/'application-index.json'
        stdout = io.StringIO(); stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = run(['generate', '--profile', capture.PROFILE, '--root', str(self.producer),
                          '--output', str(output), '--format', 'legacy'], instance, {'node_id': 'a'*32})
        self.assertEqual((status, stdout.getvalue(), stderr.getvalue()), (0, '', ''))
        self.assertEqual(output.read_bytes(), expected)

    def test_per_context_history_and_equal_timestamp_tiebreaker_match_original(self):
        for n, event in enumerate(('push', 'pull_request', 'manual', 'schedule', 'unknown'), 1):
            self.write(record(number=n, event=event, repository=1))
        _, files = capture.working(self.producer)
        documents = self.decoded(files)
        self.assertEqual(wire(build_from_documents(documents)), self.original())
        self.assertEqual(build_from_documents(documents), build_from_documents(reversed(documents)))
        self.assertTrue(all(not row['mainline_proven']
                            for row in build_from_documents(documents)['latest_candidate_by_context'].values()))
        self.assertEqual(len(build_from_documents(documents)['latest_candidate_by_context']), 3)
        manual = [row for row in build_from_documents(documents)['latest_candidate_by_context'].values()
                  if row['context'] == 'manual']
        self.assertEqual(manual[0]['path'], max(name for name, row in documents
                         if row['event'] in ('manual', 'schedule', 'unknown')))

    def test_source_limits_unexpected_files_and_links_fail_closed(self):
        source = self.write(record())
        with self.assertRaisesRegex(ValueError, 'budget'):
            capture.working(self.producer, limit=0)
        with self.assertRaisesRegex(ValueError, 'budget'):
            capture.working(self.producer, byte_limit=1)
        source.rename(source.with_suffix('.txt'))
        with self.assertRaisesRegex(ValueError, 'unexpected_candidate_member'):
            capture.working(self.producer)
        source.with_suffix('.txt').unlink()
        source.symlink_to('/etc/passwd')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            capture.working(self.producer)

    def test_unicode_branch_and_equivalent_timezone_timestamps_keep_original_wire(self):
        first = record(number=1, repository=1, branch='feature/Größe')
        second = record(number=2, repository=1, branch='feature/Größe')
        second['generated_at'] = '2026-11-15T13:00:00+01:00'
        self.write(first); self.write(second)
        _, files = capture.working(self.producer)
        self.assertEqual(wire(build_from_documents(self.decoded(files))), self.original())

    def test_committed_git_bytes_ignore_dirty_worktree_and_untracked_candidate(self):
        first = self.write(record())
        env = {**os.environ, 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1',
               'GIT_CONFIG_COUNT': '0'}
        def git(*arguments):
            return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null',
                '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture',
                '-c', 'user.email=fixture@example.invalid', *arguments], cwd=self.producer, env=env)
        git('init', '--quiet'); git('add', '--', '.'); git('commit', '--quiet', '-m', 'Synthetic candidate source')
        revision = git('rev-parse', 'HEAD').decode().strip()
        old = first.read_bytes(); first.write_bytes(b'poison')
        self.write(record(number=2))
        origin, files = capture.committed(self.producer, revision)
        self.assertEqual(origin['revision'], revision)
        self.assertEqual(files, {str(first.relative_to(self.producer)): old})
        self.assertEqual(build_from_documents(self.decoded(files))['candidate_count'], 1)

    def test_committed_blob_size_or_identity_cannot_be_forged(self):
        name = path_for(record())
        tree = ('100644 blob '+'a'*40+' 3\t'+name+'\0').encode()
        def forged(root, *arguments):
            if arguments[0] == 'rev-parse':
                return ('b'*40+'\n').encode()
            if arguments[0] == 'ls-tree':
                return tree
            return b'bad'
        with patch.object(capture, 'git_read', side_effect=forged):
            with self.assertRaisesRegex(ValueError, 'blob_changed'):
                capture.committed(self.producer, 'b'*40)

    def test_committed_sha256_git_format_preserves_exact_candidate_blobs(self):
        first = self.write(record())
        env = {**os.environ, 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1',
               'GIT_CONFIG_COUNT': '0'}
        def git(*arguments):
            return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null',
                '-c', 'commit.gpgsign=false', '-c', 'user.name=Fixture',
                '-c', 'user.email=fixture@example.invalid', *arguments], cwd=self.producer, env=env)
        git('init', '--quiet', '--object-format=sha256')
        git('add', '--', '.'); git('commit', '--quiet', '-m', 'Synthetic SHA256 source')
        revision = git('rev-parse', 'HEAD').decode().strip()
        self.assertEqual(len(revision), 64)
        origin, files = capture.committed(self.producer, revision)
        self.assertEqual(files, {str(first.relative_to(self.producer)): first.read_bytes()})
        self.assertEqual(wire(build_from_documents(self.decoded(files))), self.original())

    def test_synthetic_two_thousand_repository_projection_preserves_entire_original_file(self):
        for number in range(2000):
            self.write(record(number=number))
        _, files = capture.working(self.producer)
        value = build_from_documents(self.decoded(files))
        self.assertEqual(wire(value), self.original())
        self.assertEqual(value['candidate_count'], 2000)
        self.assertEqual(len(value['repositories']), 2000)
        self.assertEqual(len(value['latest_candidate_by_context']), 2000)
        self.assertFalse(value['official_acceptance'])


if __name__ == '__main__':
    unittest.main()
