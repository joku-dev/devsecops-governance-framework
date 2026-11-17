"""Whole original normal dispatch: minimal non-Git contracts and bounded Git names."""
from copy import deepcopy
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests/acceptance')]
from lib.providers import review_dispatch as source
from lib.provider_ports import review_dispatch_profile, review_plan_profile
from lib import review_git, review_planning
import v1_review_planning_oracle as oracle

FIXTURE = ROOT / 'tests/fixtures/v2-review-planning'
METADATA = ROOT / 'tests/fixtures/v2-review-metadata'
PROFILE = 'legacy-role-dispatch-v1'


class DispatchSources(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve(); self.files = oracle.target_files(FIXTURE)

    def target(self, name, object_format=None):
        root = self.base / name; root.mkdir(mode=0o700)
        for name, row in self.files.items():
            if not name.startswith(('.agents/roles/', '.agents/skills/', '.agents/routing/')): continue
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(row['bytes']); path.chmod(row['mode'])
        if object_format:
            (root / 'docs').mkdir(); (root / 'docs/original.md').write_text('original')
            oracle.git(root, 'init', '-q', '-b', 'main', '--object-format=' + object_format)
            oracle.git(root, 'add', '--all'); oracle.git(root, 'commit', '-qm', 'synthetic fixture')
        return root

    def old(self, root):
        value = oracle.OriginalReview(FIXTURE, METADATA, root); self.addCleanup(value.close); return value

    def compare(self, root, base=None, paths=None):
        facts, raw = source.capture(root, base, paths or [], PROFILE)
        roles, routing = source.validate(facts, raw, PROFILE)
        actual = review_planning.dispatch(facts['changed_paths'], roles, routing, review_dispatch_profile(PROFILE))
        old = self.old(root); selected = paths if paths else old.review.changed_files(root, base)
        expected = old.dispatch.build_dispatch(selected)
        self.assertEqual(actual, expected)
        self.assertEqual(review_planning.render_text(actual), old.dispatch.render_text(expected))
        return facts, raw

    def test_explicit_paths_need_no_git_protocol_or_execution_files(self):
        root = self.target('explicit')
        self.assertFalse((root / '.git').exists()); self.assertFalse((root / '.agents/review-protocol.yaml').exists())
        facts, raw = self.compare(root, base='not-a-real-ref', paths=['docs/example.md', 'model/controls/test.yaml'])
        self.assertIsNone(facts['git']); self.assertEqual(facts['selection_mode'], 'explicit_paths')
        self.assertFalse(any(name.startswith(('scripts/', '.codex/')) for name in raw))
        self.assertNotIn('.agents/review-protocol.yaml', raw)
        with self.assertRaises((ValueError, KeyError)): review_planning.contracts(raw)

    def test_working_git_names_and_branch_ref_match_original_for_both_object_formats(self):
        for object_format in ('sha1', 'sha256'):
            root = self.target(object_format, object_format)
            baseline = oracle.git(root, 'rev-parse', 'HEAD'); oracle.git(root, 'branch', 'original-base', baseline)
            (root / 'docs/committed.md').write_text('committed'); oracle.git(root, 'add', '--all'); oracle.git(root, 'commit', '-qm', 'next')
            (root / 'docs/staged.md').write_text('staged'); oracle.git(root, 'add', 'docs/staged.md'); (root / 'docs/staged.md').unlink()
            (root / 'docs/untracked.md').write_text('untracked')
            oracle.git(root, 'mv', 'docs/original.md', 'docs/renamed.md')
            facts, raw = self.compare(root, base='original-base')
            self.assertEqual(facts['git']['target_commit'], baseline)
            self.assertEqual(len(facts['git']['head_commit']), 40 if object_format == 'sha1' else 64)
            self.assertIn('docs/staged.md', facts['changed_paths'])
            self.assertIn('docs/original.md', facts['changed_paths']); self.assertIn('docs/renamed.md', facts['changed_paths'])

    def test_empty_working_diff_and_explicit_normalized_paths_keep_original_wires(self):
        root = self.target('empty', 'sha1'); facts, raw = self.compare(root)
        self.assertEqual(facts['changed_paths'], [])
        self.compare(root, paths=['./docs/example.md', 'docs/example.md', 'model/controls/test.yaml'])

    def test_changed_program_bodies_and_unrelated_adapters_are_not_read_or_executed(self):
        root = self.target('inert', 'sha1'); marker = self.base / 'executed'
        poison = root / 'scripts/poison.py'; poison.parent.mkdir()
        poison.write_text('from pathlib import Path\nPath(' + repr(str(marker)) + ').touch()\n')
        optional = root / '.codex/agents/repo-steward.toml'; optional.parent.mkdir(parents=True)
        optional.symlink_to(self.base / 'not-present')
        read = source.regular_file; names = []
        def limited(root, name):
            self.assertTrue(name.startswith('.agents/')); names.append(name); return read(root, name)
        with patch.object(source, 'regular_file', side_effect=limited): facts, raw = self.compare(root)
        self.assertIn('scripts/poison.py', facts['changed_paths']); self.assertNotIn('scripts/poison.py', raw)
        self.assertTrue(names); self.assertFalse(marker.exists())

    def test_retained_contracts_remain_valid_after_caller_removal_and_tampering_rejected(self):
        root = self.target('replay'); facts, raw = self.compare(root, paths=['docs/example.md'])
        shutil.rmtree(root); source.validate(facts, raw, PROFILE)
        for key, value in [('schema_version', True), ('git', {'head_commit': 'a' * 40}), ('selection_mode', 'other')]:
            bad = deepcopy(facts); bad[key] = value
            with self.assertRaises(ValueError): source.validate(bad, raw, PROFILE)
        name = next(iter(raw)); changed = dict(raw); changed[name] += b'\n'
        with self.assertRaisesRegex(ValueError, 'dispatch_contract_bytes_changed'): source.validate(facts, changed, PROFILE)
        changed = dict(raw); changed['scripts/poison.py'] = b'inert'
        with self.assertRaises(ValueError): source.validate(facts, changed, PROFILE)

    def test_profile_source_changes_budgets_and_symlinks_fail_closed(self):
        root = self.target('reject')
        with self.assertRaisesRegex(ValueError, 'unsupported_review_dispatch_profile'):
            source.capture(root, None, ['docs/example.md'], 'other')
        observe = source.observe; calls = []
        def changed(*args):
            facts, raw = observe(*args); calls.append(1)
            if len(calls) > 1: facts['changed_paths'] = ['docs/changed.md']
            return facts, raw
        with patch.object(source, 'observe', side_effect=changed), self.assertRaisesRegex(ValueError, 'dispatch_target_changed_during_capture'):
            source.capture(root, None, ['docs/example.md'], PROFILE)
        with patch.object(source, 'MAX_FACTS', 1), self.assertRaisesRegex(ValueError, 'dispatch_facts_budget'):
            source.capture(root, None, ['docs/example.md'], PROFILE)
        role = root / '.agents/roles/repo-steward.yaml'; saved = role.read_bytes(); role.unlink()
        outside = self.base / 'outside.yaml'; outside.write_bytes(saved); role.symlink_to(outside)
        with self.assertRaises(ValueError): source.capture(root, None, ['docs/example.md'], PROFILE)


if __name__ == '__main__': unittest.main()
