"""A passing own suite must not hide changes to governance meaning."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from acceptance.product_generated_effects import checked_change, retain_effects, retain_additions


class GeneratedProductEffects(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.source = Path(temporary.name).resolve()
        self.example = self.source / 'docs/examples/evidence-attestation.example.json'
        self.example.parent.mkdir(parents=True)
        self.example.write_bytes(b'{"fixture":true}\n')
        self.pin = hashlib.sha256(self.example.read_bytes()).hexdigest()

    def check(self, name, before, after):
        return checked_change(name, before, after, self.source, self.pin)

    def test_raw_metadata_effects_are_retained_with_independent_byte_pins(self):
        name = 'generated/reports/source-lineage-report.json'
        before = b'{"generated_at":"2026-11-18T10:00:00Z","missing":0}\n'
        after = before.replace(b'18T10', b'19T11')
        path = self.source / name
        path.parent.mkdir(parents=True)
        path.write_bytes(after)
        destination = self.source / 'audit'
        rows = retain_effects(self.source, {name: before}, destination, self.pin)
        self.assertEqual(len(rows), 1)
        for label, raw in (('before', before), ('after', after)):
            self.assertEqual((destination / label / name).read_bytes(), raw)
            self.assertEqual(rows[0][label + '_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(rows[0][label + '_bytes'], len(raw))

    def test_json_governance_changes_and_naive_times_cannot_be_masked(self):
        name = 'generated/reports/source-lineage-report.json'
        before = b'{"generated_at":"2026-11-18T10:00:00Z","missing":0}'
        for after in (before.replace(b'"missing":0', b'"missing":1'),
                      before.replace(b'18T10:00:00Z', b'19T10:00:00')):
            with self.subTest(after=after), self.assertRaises(ValueError):
                self.check(name, before, after)
        with self.assertRaises(ValueError):
            self.check('generated/reports/unknown.json', before, before.replace(b'18T', b'19T'))

    def test_attestation_display_path_requires_exact_unchanged_local_example(self):
        name = 'generated/reports/evidence-attestation-pilot.json'
        relative = 'docs/examples/evidence-attestation.example.json'
        before = json.dumps({'attestation_ref': '/old/operator/' + relative, 'verified': True}).encode()
        after = json.dumps({'attestation_ref': str(self.example), 'verified': True}).encode()
        self.assertEqual(self.check(name, before, after), 'owned_example_display_path_only')
        with self.assertRaises(ValueError):
            self.check(name, before, after.replace(b'"verified": true', b'"verified": false'))
        self.example.write_bytes(b'{"changed":true}\n')
        with self.assertRaises(ValueError):
            self.check(name, before, after)

    def test_markdown_and_viewer_reject_semantic_changes_beside_timestamps(self):
        name = 'generated/reports/source-lineage-report.md'
        before = b'# Source lineage\nGenerated: `2026-11-18T10:00:00Z`\nMissing: 0\n'
        after = before.replace(b'18T10', b'19T11')
        self.assertEqual(self.check(name, before, after), 'generation_timestamp_only')
        with self.assertRaises(ValueError):
            self.check(name, before, after.replace(b'Missing: 0', b'Missing: 1'))
        name = 'generated/viewer/status-viewer.html'
        before = b'<script>{"kind":"governance-intelligence-graph","generated_at":"2026-11-18T10:00:00Z","findings":0}</script>'
        after = before.replace(b'18T10', b'19T11')
        self.assertEqual(self.check(name, before, after), 'embedded_graph_generation_timestamp_only')
        with self.assertRaises(ValueError):
            self.check(name, before, after.replace(b'"findings":0', b'"findings":1'))
        with self.assertRaises(ValueError):
            self.check(name, before.replace(b'governance-intelligence-graph', b'other-graph'),
                       after.replace(b'governance-intelligence-graph', b'other-graph'))

    def viewer_output(self, raw):
        path = self.source / 'generated/viewer/app/data.json'
        path.parent.mkdir(parents=True)
        path.write_bytes(raw)
        return path

    def test_the_one_known_generated_payload_requires_exact_whole_projection_and_retains_bytes(self):
        raw = b'{"version":1,"repositories":[],"scope":"synthetic boundary fixture"}\n'
        path = self.viewer_output(raw)
        destination = self.source / 'artifacts'
        rows = retain_additions(self.source, {'generated/viewer/app/data.json'}, raw, destination)
        self.assertEqual((destination / 'generated/viewer/app/data.json').read_bytes(), raw)
        self.assertEqual(rows[0]['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertFalse(rows[0]['authority_transferred'])
        self.assertFalse(rows[0]['official_acceptance'])
        self.assertEqual(path.read_bytes(), raw)

    def test_generated_payload_semantics_and_unknown_paths_are_never_ignored(self):
        raw = b'{"version":1,"official_acceptance":false}\n'
        self.viewer_output(raw.replace(b'false', b'true'))
        with self.assertRaisesRegex(ValueError, 'projection_mismatch'):
            retain_additions(self.source, {'generated/viewer/app/data.json'}, raw, self.source / 'audit')
        with self.assertRaisesRegex(ValueError, 'unknown_product_test_generated_output'):
            retain_additions(self.source, {'generated/viewer/app/unlisted.json'}, raw, self.source / 'audit')
        self.assertFalse((self.source / 'audit').exists())

    def test_generated_payload_symlinks_are_rejected_without_reading_external_content(self):
        raw = b'{"version":1}\n'
        path = self.viewer_output(raw)
        external = self.source / 'other-context.json'
        external.write_bytes(raw)
        path.unlink(); path.symlink_to(external)
        with self.assertRaises(ValueError):
            retain_additions(self.source, {'generated/viewer/app/data.json'}, raw, self.source / 'audit')
        self.assertFalse((self.source / 'audit').exists())
