"""Public application, original wire, immutable replay and explicit output effects."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from lib.candidate_index_application import CandidateIndexContext, run, project, wire
from lib.portable.contracts import canonical_digest
from lib.portable_intake.publisher import path_for
from lib.providers.candidate_index_source import PROFILE
from test_v2_candidate_index_sources import record


class CandidateApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.instance = self.base/'instance'; self.instance.mkdir(mode=0o700)
        self.producer = self.base/'producer'; self.producer.mkdir(mode=0o700)
        self.settings = {'node_id': 'a'*32}
        self.context = CandidateIndexContext(self.instance, self.settings)

    def write(self, document=None):
        document = record() if document is None else document
        path = self.producer/path_for(document)
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(wire(document))
        return path

    def call(self, *arguments):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            status = run(list(arguments), self.instance, self.settings)
        self.assertEqual(status, 0)
        return stdout.getvalue()

    def test_retained_whole_projection_replays_after_original_source_removed(self):
        path = self.write()
        before = {p.relative_to(self.producer).as_posix(): p.read_bytes() for p in self.producer.rglob('*.json')}
        assessment_id, value = self.context.create(self.producer)
        self.assertEqual({p.relative_to(self.producer).as_posix(): p.read_bytes() for p in self.producer.rglob('*.json')}, before)
        expected = project(before)
        shutil.rmtree(self.producer)
        self.assertEqual(self.context.inspect(assessment_id), value)
        self.assertEqual((self.context.artifacts/assessment_id/'index.json').read_bytes(), expected)
        self.assertFalse(value['official_acceptance']); self.assertFalse(value['native_verification_performed'])

    def test_public_generate_legacy_output_and_overwrite_keep_before_bytes(self):
        self.write()
        destination = self.producer/'generated/portable-intake/index.json'
        destination.parent.mkdir(parents=True); destination.write_bytes(b'old artifact\n')
        stdout = self.call('generate', '--profile', PROFILE, '--root', str(self.producer),
                           '--output', str(destination), '--format', 'legacy')
        self.assertEqual(stdout, '')
        self.assertEqual(destination.read_bytes(), project({path_for(record()): wire(record())}))
        transactions = list(self.context.exports.iterdir()); self.assertEqual(len(transactions), 1)
        self.assertEqual((transactions[0]/'before.bin').read_bytes(), b'old artifact\n')
        intent = json.loads((transactions[0]/'intent.json').read_text())
        receipt = json.loads((transactions[0]/'receipt.json').read_text())
        self.assertEqual(intent['phase'], 'prepared'); self.assertEqual(receipt['phase'], 'completed')
        self.assertEqual(destination.stat().st_mode & 0o777, 0o600)

    def test_public_inspect_export_and_default_committed_product_data(self):
        self.write()
        result = json.loads(self.call('generate', '--profile', PROFILE))
        identifier = result['assessment_id']
        value = json.loads(self.call('inspect', '--id', identifier))
        self.assertTrue(value['retained_sources_and_complete_original_output_reverified'])
        manifest = self.context.input_data(value['assessment']['input_id'])[1]
        self.assertEqual(manifest['origin']['mode'], 'committed')
        self.assertEqual(manifest['origin']['root'], str(ROOT))
        output = self.base/'export.json'
        self.call('export', '--id', identifier, '--output', str(output))
        self.assertEqual(output.read_bytes(), (self.context.artifacts/identifier/'index.json').read_bytes())

    def test_changed_raw_input_and_output_and_unexpected_member_are_rejected(self):
        self.write(); identifier, value = self.context.create(self.producer)
        source = self.context.inputs/value['input_id']/'data'/path_for(record())
        before = source.read_bytes(); source.write_bytes(before+b' ')
        with self.assertRaisesRegex(ValueError, 'retained_input_changed'): self.context.inspect(identifier)
        source.write_bytes(before)
        artifact = self.context.artifacts/identifier/'index.json'
        original = artifact.read_bytes(); artifact.write_bytes(original+b' ')
        with self.assertRaisesRegex(ValueError, 'output_changed'): self.context.inspect(identifier)
        artifact.write_bytes(original)
        extra = self.context.inputs/value['input_id']/'extra.json'; extra.write_text('{}'); extra.chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'members_changed'): self.context.inspect(identifier)

    def test_assessment_binding_rejects_other_node_runtime_and_unknown_contract_field(self):
        self.write(); identifier, value = self.context.create(self.producer)
        other_instance = self.base/'other'; other_instance.mkdir(mode=0o700)
        other = CandidateIndexContext(other_instance, {'node_id': 'b'*32})
        with self.assertRaisesRegex(ValueError, 'node_runtime_or_product_changed'): other.validate(value)
        for key, replacement in [('runtime_source_digest', 'f'*64), ('extra', False)]:
            changed = {**value, key: replacement}
            with self.assertRaises(ValueError): self.context.validate(changed)

    def test_inside_source_accepted_status_product_instance_and_symlink_outputs_rejected(self):
        self.write(); identifier, value = self.context.create(self.producer)
        for output in (self.producer/'status/results/official.json', ROOT/'generated/portable-intake/index.json',
                       self.instance/'anything.json'):
            previous = output.read_bytes() if output.exists() else None
            with self.assertRaises(ValueError): self.context.export(identifier, output)
            self.assertEqual(output.read_bytes() if output.exists() else None, previous)
        target = self.base/'target'; target.write_text('keep')
        link = self.base/'output.json'; link.symlink_to(target)
        with self.assertRaises(ValueError): self.context.export(identifier, link)
        self.assertEqual(target.read_text(), 'keep')

    def test_invalid_candidate_fails_before_retention_or_external_effect(self):
        document = record(); document['run_url'] = 'https://invalid.example/forged'
        self.write(document); output = self.base/'output.json'
        with self.assertRaisesRegex(ValueError, 'candidate_run_link_mismatch'):
            self.call('generate', '--profile', PROFILE, '--root', str(self.producer), '--output', str(output))
        self.assertFalse(output.exists())
        self.assertEqual(list(self.context.inputs.iterdir()), [])

    def test_interrupted_export_preserves_prepared_intent_without_automatic_retry(self):
        self.write(); identifier, value = self.context.create(self.producer)
        output = self.base/'external.json'; output.write_bytes(b'previous bytes')
        with patch('lib.candidate_index_application.replace_candidate_index_output',
                   side_effect=OSError('injected exporter failure')):
            with self.assertRaises(OSError): self.context.export(identifier, output)
        self.assertEqual(output.read_bytes(), b'previous bytes')
        transactions = list(self.context.exports.iterdir()); self.assertEqual(len(transactions), 1)
        self.assertEqual((transactions[0]/'before.bin').read_bytes(), b'previous bytes')
        self.assertEqual(json.loads((transactions[0]/'intent.json').read_text())['phase'], 'prepared')
        self.assertFalse((transactions[0]/'receipt.json').exists())
        self.context.inspect(identifier)
        self.assertEqual(len(list(self.context.exports.iterdir())), 1)

    def test_external_output_change_and_unsafe_hardlink_cannot_be_replaced(self):
        from lib.providers.candidate_index_source import observe_output, replace_output
        output = self.base/'external.json'; output.write_bytes(b'previous')
        before, metadata = observe_output(output)
        output.write_bytes(b'concurrent actor')
        with self.assertRaisesRegex(ValueError, 'external_output_changed'):
            replace_output(output, b'replacement', before, metadata)
        self.assertEqual(output.read_bytes(), b'concurrent actor')
        alias = self.base/'alias.json'; os.link(output, alias)
        with self.assertRaisesRegex(ValueError, 'owned_regular_output_required'): observe_output(alias)

    def test_duplicate_key_and_invalid_schema_are_product_errors_without_retained_artifacts(self):
        path = self.write(); path.write_bytes(b'{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(ValueError, 'duplicate'): self.context.create(self.producer)
        path.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'invalid_candidate_index_payload'):
            self.context.create(self.producer)
        self.assertEqual(list(self.context.inputs.iterdir()), [])
        self.assertEqual(list(self.context.artifacts.iterdir()), [])

    def test_public_v2_router_uses_real_development_instance_without_admission_mock(self):
        from lib.v2_application import initialize
        from lib.portable.runtime import approved_opa_hashes, file_digest
        opa = shutil.which('opa')
        if not opa or file_digest(opa) not in approved_opa_hashes('1.18.2'):
            self.skipTest('Pinned OPA required for actual development instance admission')
        self.write(); instance = self.base/'admitted'
        initialize(instance, opa=opa, port=19011, development=True)
        output = self.base/'actual-router.json'
        completed = subprocess.run([sys.executable, str(ROOT/'scripts/axiom_v2.py'),
            '--instance', str(instance), 'candidate-index', 'generate', '--profile', PROFILE,
            '--root', str(self.producer), '--output', str(output), '--format', 'legacy'],
            capture_output=True, timeout=120)
        self.assertEqual((completed.returncode, completed.stdout, completed.stderr), (0, b'', b''))
        self.assertEqual(output.read_bytes(), project({path_for(record()): wire(record())}))
        self.assertEqual(json.loads((instance/'consumer.json').read_text())['mode'], 'paused')


if __name__ == '__main__': unittest.main()
