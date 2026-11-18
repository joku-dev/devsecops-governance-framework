"""Every source Git request replayed from retained raw observations, offline."""
import base64
import copy
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import test_v2_repository_capture as fixture
from lib import repository_capture as contract
from lib.providers.repository_source import RepositorySource
from lib.providers.release_references import ReleaseReferences
from lib.providers.repository_acquisition_replay import audit_acquisition


@unittest.skipUnless(shutil.which('git'), 'local Git not present')
class RepositoryAcquisitionReplayTests(unittest.TestCase):
    command = fixture.RepositoryCaptureTests.command
    commit = fixture.RepositoryCaptureTests.commit
    journal = fixture.RepositoryCaptureTests.journal
    port = fixture.RepositoryCaptureTests.port

    def setUp(self):fixture.RepositoryCaptureTests.setUp(self)

    def acquired(self, profile=contract.COMMITTED):
        port = self.port()
        manifest, files, commit = RepositorySource(port, self.revision, profile=profile).capture()
        references = ReleaseReferences(self.source, read=port.read).capture()
        phases = [{'phase': row['stage'], 'observation': row['observation']} for row in self.rows]
        return manifest, files, commit, references, phases

    def test_complete_committed_graph_and_every_git_call_replay_after_source_deletion(self):
        self.command('tag', 'test-baseline')
        inputs = self.acquired(); shutil.rmtree(self.source)
        with patch('subprocess.Popen', side_effect=AssertionError('native execution during replay')), \
             patch('pathlib.Path.resolve', side_effect=AssertionError('caller filesystem consulted')):
            result = audit_acquisition(*inputs)
        self.assertEqual(result['native_reads'], len(inputs[-1]) // 3)
        self.assertTrue(result['closed_input_graph_consistent'])
        self.assertFalse(result['independent_execution_attested'])

    def test_working_bytes_remain_explicit_declared_data_and_never_become_committed_blobs(self):
        (self.source / 'model/catalog.json').write_bytes(b'actual working change')
        inputs = self.acquired(contract.WORKING); shutil.rmtree(self.source)
        with patch('subprocess.Popen', side_effect=AssertionError('no native replay')):
            self.assertTrue(audit_acquisition(*inputs)['closed_input_graph_consistent'])

    def test_mutated_phase_fields_order_and_extra_reads_are_rejected(self):
        original = self.acquired()
        variants = []
        phases = copy.deepcopy(original[-1]); phases[0], phases[1] = phases[1], phases[0]; variants.append(phases)
        phases = copy.deepcopy(original[-1]); phases[0]['observation']['argv'] += ['unexpected']; variants.append(phases)
        phases = copy.deepcopy(original[-1]); phases[1]['observation']['process_started'] = False; variants.append(phases)
        phases = copy.deepcopy(original[-1]); phases += phases[:3]; variants.append(phases)
        variants.append(copy.deepcopy(original[-1][:-3]))
        for phases in variants:
            with self.subTest(index=variants.index(phases)), self.assertRaises(ValueError):
                audit_acquisition(*original[:-1], phases)

    def test_changed_successful_raw_binding_is_not_accepted_even_with_matching_phase_metadata(self):
        inputs = list(self.acquired()); phases = inputs[-1]
        # stdout is only present in the final observation. Changing a successful
        # root lookup must still fail the exact source binding.
        phases[5]['observation']['stdout_base64'] = base64.b64encode(b'/different\n').decode()
        with self.assertRaisesRegex(ValueError, 'source_binding_changed'):audit_acquisition(*inputs)

    def test_native_cleanup_failure_and_boolean_returncodes_are_not_success(self):
        original = self.acquired()
        for changed in ({'cleanup_absence_check': 'unknown'}, {'cleanup_signal_permission_denied': True},
                        {'returncode': True}, {'timed_out': True}):
            phases = copy.deepcopy(original[-1]); phases[2]['observation'].update(changed)
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                audit_acquisition(*original[:-1], phases)

    def test_tool_under_source_and_expanded_stream_limits_are_rejected(self):
        original = self.acquired()
        phases = copy.deepcopy(original[-1])
        for row in phases[:3]:row['observation']['stdout_limit'] = 999999999
        with self.assertRaises(ValueError):audit_acquisition(*original[:-1], phases)
        phases = copy.deepcopy(original[-1])
        for row in phases:
            row['observation']['tool_path'] = str(self.source / 'git')
            row['observation']['argv'][0] = str(self.source / 'git')
        with self.assertRaisesRegex(ValueError, 'tool_binding_changed'):audit_acquisition(*original[:-1], phases)

    def test_reference_metadata_cannot_be_replaced_by_same_revision_different_refs(self):
        inputs = list(self.acquired()); inputs[3] = copy.deepcopy(inputs[3])
        inputs[3]['refs']['new-baseline'] = self.revision
        with self.assertRaises(ValueError):audit_acquisition(*inputs)

    def test_source_graph_and_native_observation_contract_are_closed(self):
        original = self.acquired()
        phases = copy.deepcopy(original[-1]); phases[2]['observation']['extra'] = True
        with self.assertRaises(ValueError):audit_acquisition(*original[:-1], phases)
        phases = copy.deepcopy(original[-1]); phases[2]['observation']['stdout_base64'] += '\n'
        with self.assertRaises(ValueError):audit_acquisition(*original[:-1], phases)


if __name__ == '__main__':unittest.main()
