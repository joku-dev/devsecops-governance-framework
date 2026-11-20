"""Whole nested security/release capture and no-native retained reconstruction."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from lib.operations_replay import ReplayCalls
from lib.operations_collection import collect
from lib.operations_reporting import build_report, render_markdown
from lib.operations_security import reconstruct
from lib.providers import operations_files, operations_report_profile as profile
from lib.providers.operations_security import NativeSecurity, RetainedSecurity
from lib.providers.sbom_export_storage import Record, read_record, AUTHORITY
from lib.retained_security_tree import RetainedTree
from lib.v2_boundary import violations
import test_v2_self_security_application as native_tests
from test_v2_operations_reporting import OLD


class NestedOperationsSecurityTests(unittest.TestCase):
    def setUp(self):
        native_tests.NativeSecurityReports.setUp(self)
        model = self.source / operations_files.SECURITY_MODEL
        model.parent.mkdir(parents=True, exist_ok=True)
        model.write_bytes(self.model)
        self.record = Record(self.base / 'parent-records', {'kind': 'controlled-security-composition-test'}, {})
        self.sources = operations_files.NativeSources(self.source, self.record, profile.INDEXES)
        self.native = NativeSecurity(self.record, self.sources, self.context, source_worktree=self.source)
        self.at = '2026-11-15T12:00:00+00:00'

    def transport(self, path):
        return native_tests.NativeSecurityReports.transport(self, path)

    def acquire(self):
        with patch('lib.providers.self_security_native.Reader.get', side_effect=self.transport):
            result = self.native.security('owner/repo', self.at)
        self.record.finish('complete', {'exit_code': 0}, {})
        return result

    def retained(self):
        _, _, result, events, blob, closed = read_record(self.record.root)
        calls = ReplayCalls(events, blob, expected_opened={'kind': 'opened', **AUTHORITY})
        sources = operations_files.RetainedSources(calls, profile.INDEXES)
        reader = RetainedSecurity(calls, sources, binding=self.context.binding, source_root=str(self.source))
        return reader, calls, result, closed

    def nested(self):
        _, _, _, events, blob, _ = read_record(self.record.root)
        outcome = next(row for row in events if row.get('kind') == 'returned' and row.get('operation') == 3)
        return json.loads(blob(outcome['value'])), blob

    def test_actual_signature_capture_whole_original_report_and_replay_without_native_or_current_source(self):
        expected = self.acquire()
        self.assertEqual(len(expected['criteria']), 16)
        value, _ = self.nested()
        child = self.context.operations / value['operation']
        raw = json.loads((child / 'outputs/report.json').read_bytes())
        self.assertEqual(json.dumps(expected, indent=2), json.dumps(profile.native_security_error_projection(raw), indent=2))
        self.assertEqual(self.context.inspect(value['operation'])['release_assessment'], value['release_operation'])
        self.assertTrue(raw['observation']['release_integrity']['release_tags'])
        self.assertFalse(raw['observation']['release_integrity']['unverified_release_tags'])
        self.assertTrue(any('HTTP 403' in s for s in expected['observation']['api_errors']))
        self.assertTrue(any('http_403' in s for s in raw['observation']['api_errors']))
        (self.source / '.github/CODEOWNERS').write_text('changed after capture')
        (self.source / 'releases/test/payload.txt').write_text('changed after capture')
        reader, calls, terminal, closed = self.retained()
        with patch('subprocess.Popen', side_effect=AssertionError('No program in retained reconstruction')), \
             patch('lib.providers.self_security_native.Reader.get', side_effect=AssertionError('No fresh HTTP')), \
             patch('lib.providers.retained_security_files.capture', side_effect=AssertionError('No current child-tree read')), \
             patch.object(operations_files, 'held_root', side_effect=AssertionError('No current source read')), \
             patch('lib.self_security_application.security_clock', side_effect=AssertionError('No fresh clock')):
            actual = reader.security('owner/repo', self.at)
        calls.finish(terminal['result'])
        self.assertTrue(closed())
        self.assertEqual(json.dumps(actual, indent=2), json.dumps(expected, indent=2))

    def test_whole_collector_with_actual_local_sources_nested_crypto_and_original_complete_report(self):
        config = json.loads((ROOT / '.github/operations-report.json').read_bytes())
        config['repository'] = 'owner/repo'
        status = self.source / 'status'
        status.mkdir()
        (status / 'application-repository-integrations.yaml').write_text('integrations: []\n')
        for name in profile.INDEXES.values():
            (status / name).write_text('{"repositories":[]}\n')
        (status / 'intake-events').mkdir()
        (status / 'intake-events/one.json').write_text(json.dumps({'status': 'success',
            'completed_at': '2026-11-15T11:00:00Z', 'duration_ms': 321, 'repository_id': 'owner/consumer',
            'intake_type': 'devsecops_governance', 'evidence_type': 'governance_result',
            'collector': {'id': 'controlled-fixture', 'version': '1'}}))
        sha = self.context.binding['source_revision']
        run = {'head_sha': sha, 'created_at': '2026-11-15T11:00:00Z', 'status': 'completed', 'conclusion': 'success', 'id': 42}
        def environment(sources, security):
            return SimpleNamespace(main_reference=lambda _: {'object': {'sha': sha}},
                workflow_queries=profile.workflow_queries, workflow_runs=lambda *args: {'workflow_runs': [deepcopy(run)]},
                pull_requests=lambda _: [], registry=sources.registry, index_domains=sources.index_domains,
                index=sources.index, records=sources.records, security=security.security)
        now = datetime(2026, 11, 15, 12, tzinfo=timezone.utc)
        with patch('lib.providers.self_security_native.Reader.get', side_effect=self.transport):
            actual = collect(config, now, environment(self.sources, self.native))
        self.assertEqual(actual['errors'], [])
        self.assertEqual(actual['intake_health']['summary']['events']['total'], 1)
        self.assertEqual(actual['intake_health']['summary']['events']['duration_ms']['p95'], 321)
        def original_api(arguments):
            if arguments[:3] == ['gh', 'pr', 'list']:
                return []
            return {'object': {'sha': sha}} if arguments[-1].endswith('/git/ref/heads/main') else {'workflow_runs': [deepcopy(run)]}
        with patch.object(OLD, 'command_json', side_effect=original_api), \
             patch.object(OLD, 'collect_live', return_value=deepcopy(actual['security']['observation'])):
            expected = OLD.collect(config, self.source, now)
        self.assertEqual(json.dumps(actual, indent=2), json.dumps(expected, indent=2))
        actual_report = build_report(actual, config, now, sha, profile=profile)
        expected_report = OLD.build_report(expected, config, now, sha)
        self.assertEqual(json.dumps(actual_report, indent=2), json.dumps(expected_report, indent=2))
        self.assertEqual(render_markdown(actual_report), OLD.render_markdown(expected_report))
        self.record.finish('complete', {'exit_code': 0}, {})
        _, _, terminal, events, blob, closed = read_record(self.record.root)
        calls = ReplayCalls(events, blob, expected_opened={'kind': 'opened', **AUTHORITY})
        sources = operations_files.RetainedSources(calls, profile.INDEXES)
        retained = RetainedSecurity(calls, sources, binding=self.context.binding, source_root=str(self.source))
        with patch('subprocess.Popen', side_effect=AssertionError('No fresh program in complete retained collection')), \
             patch.object(operations_files, 'held_root', side_effect=AssertionError('No current source read')):
            replayed = collect(config, now, environment(sources, retained))
        calls.finish(terminal['result'])
        self.assertTrue(closed())
        self.assertEqual(json.dumps(replayed, indent=2), json.dumps(expected, indent=2))

    def test_full_nested_binding_and_metadata_source_response_output_signature_tampering_are_rejected(self):
        self.acquire()
        value, blob = self.nested()
        expected = dict(binding=self.context.binding, repository='owner/repo', observed_at=self.at,
                        model_raw=self.model, source_root=str(self.source))
        reconstruct(value, blob, **expected)
        for section, name in (('security', 'pending.json'), ('security', 'responses/01.json'),
                              ('security', 'inputs/source/.github/CODEOWNERS'), ('security', 'outputs/report.json'),
                              ('release', 'references.json'), ('release', 'assessment.json'),
                              ('release', 'inputs/releases/test/payload.txt'), ('release', 'starts/00001.json')):
            with self.subTest(section=section, name=name):
                changed = deepcopy(value)
                raw = b'{}\n'
                reference = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
                changed[section]['files'][name] = reference
                with self.assertRaises((ValueError, KeyError)):
                    reconstruct(changed, lambda ref: raw if ref == reference else blob(ref), **expected)
        for key, other in (('repository', 'other/repo'), ('observed_at', '2026-11-16T00:00:00Z'),
                           ('source_root', '/different-source'), ('model_raw', self.model + b'\n')):
            with self.subTest(request=key), self.assertRaises(ValueError):
                reconstruct(value, blob, **{**expected, key: other})
        with self.assertRaises(ValueError):
            reconstruct(value, blob, **{**expected, 'binding': {**self.context.binding, 'node_id': 'c' * 32}})

    def test_missing_or_invalid_model_never_starts_child_acquisition(self):
        path = self.source / operations_files.SECURITY_MODEL
        path.unlink()
        with patch.object(self.context, 'create', side_effect=AssertionError('No child for unreadable model')):
            with self.assertRaises(FileNotFoundError):
                self.native.security('owner/repo', self.at)
            path.write_bytes(b'value: &a [*a]\n')
            with self.assertRaisesRegex(ValueError, 'recursive_alias'):
                self.native.security('owner/repo', self.at)
        self.assertFalse(self.record.capture_incomplete)

    def test_incomplete_child_cannot_be_recorded_as_complete_parent(self):
        with patch.object(self.context, 'create', return_value=('a' * 64, {'execution': 'incomplete'})):
            with self.assertRaisesRegex(ValueError, 'nested_security_incomplete'):
                self.native.security('owner/repo', self.at)
        self.assertTrue(self.record.capture_incomplete)
        self.assertFalse(any(p.name == 'result.json' for p in self.record.root.iterdir()))

    def test_retained_tree_rejects_noncanonical_labels_unbounded_or_conflicting_members(self):
        for label, data, dirs in (('/safe/../foreign', {}, ['']), ('/safe', {'same': b'a'}, ['', 'same']),
                                  ('/safe', {'missing/file': b'a'}, ['']), ('relative', {}, [''])):
            with self.subTest(label=label), self.assertRaises(ValueError):
                RetainedTree(label, data, dirs)
        for name in ('scripts/lib/operations_security.py', 'scripts/lib/retained_security.py', 'scripts/lib/retained_security_tree.py'):
            self.assertEqual(violations(name, (ROOT / name).read_text()), [])


if __name__ == '__main__':
    unittest.main()
