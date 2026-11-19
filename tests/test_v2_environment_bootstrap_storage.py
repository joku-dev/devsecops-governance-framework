"""Actual storage failures must prevent native execution and false completion."""
from pathlib import Path
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.environment_bootstrap import run
from lib.providers import environment_bootstrap_storage as storage


class EnvironmentBootstrapStorage(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name).resolve();self.root.chmod(0o700)

    def journal(self):
        return storage.BootstrapJournal(self.root,{'profile':'source-intake-environment-v1'},
            {'kind':'explicit_test_source','authority_transferred':False})

    def test_repeated_operation_never_reuses_or_overwrites_previous_record(self):
        with self.journal() as first:
            original=(first.root/'request.json').read_bytes()
            first.before('preflight')
            old=first.root
        with self.journal() as second:
            self.assertNotEqual(old,second.root)
            self.assertEqual((old/'request.json').read_bytes(),original)
            self.assertFalse((old/'result.json').exists())

    def test_real_fsynced_intent_is_present_before_native_port_runs(self):
        journal=self.journal();self.addCleanup(journal.close)
        class Ports:
            def perform(inner,action):
                raw=storage.read_private(journal.root/'events.jsonl',storage.MAX_JOURNAL)
                rows=[json.loads(line) for line in raw.splitlines()]
                self.assertEqual(rows[-1]['payload']['kind'],'phase-intent')
                self.assertEqual(rows[-1]['payload']['action'],action)
                return True if action=='environment_python_executable' else None
        result=run('source-intake-environment-v1',Ports(),journal)
        summary=journal.finish({'state':result.state,'operations':result.operations})
        self.assertEqual(summary['state'],'complete')
        self.assertFalse(summary['official_acceptance'])
        self.assertFalse(summary['independent_execution_authenticated'])
        self.assertEqual((journal.root/'events.jsonl').stat().st_mode&0o777,0o600)

    def test_fsync_failure_prevents_native_port_execution(self):
        with self.journal() as journal:
            class Ports:
                calls=0
                def perform(inner,action):inner.calls+=1
            ports=Ports()
            with patch.object(storage.os,'fsync',side_effect=OSError('declared full disk')):
                with self.assertRaisesRegex(OSError,'declared full disk'):
                    run('source-intake-environment-v1',ports,journal)
            self.assertEqual(ports.calls,0)
            self.assertFalse((journal.root/'result.json').exists())

    def test_external_append_is_rejected_before_next_effect(self):
        with self.journal() as journal:
            with (journal.root/'events.jsonl').open('ab') as stream:stream.write(b'foreign\n')
            with self.assertRaisesRegex(ValueError,'changed_before_append'):journal.before('preflight')

    def test_replaced_or_linked_log_is_rejected_before_next_effect(self):
        for kind in ('replace','hardlink'):
            with self.subTest(kind=kind),self.journal() as journal:
                path=journal.root/'events.jsonl'
                if kind=='replace':
                    path.rename(journal.root/'old-log');path.write_bytes(b'foreign')
                else:os.link(path,journal.root/'second-link')
                with self.assertRaisesRegex(ValueError,'path_replaced|changed_before_append'):
                    journal.before('preflight')

    def test_pending_or_failed_phase_cannot_be_labelled_complete(self):
        with self.journal() as journal:
            token=journal.before('preflight')
            with self.assertRaisesRegex(ValueError,'terminal_result_mismatch'):journal.finish({'state':'complete'})
            journal.failed(token,'declared_native_failure')
            with self.assertRaisesRegex(ValueError,'terminal_result_mismatch'):journal.finish({'state':'complete'})
            self.assertEqual(journal.finish({'state':'failed'})['state'],'failed')

    def test_unknown_interruption_retains_pending_intent_without_fabricated_failure(self):
        with self.journal() as journal:
            journal.before('preflight')
            info=journal.finish({'state':'incomplete','process_current_liveness_claimed':False})
            self.assertEqual(info['state'],'incomplete')
            events=[json.loads(line)['payload'] for line in (journal.root/'events.jsonl').read_bytes().splitlines()]
            self.assertFalse(any(e.get('state')=='failed' for e in events))
            self.assertEqual(events[-1]['state'],'incomplete')

    def test_nan_and_duplicate_keys_are_never_accepted_as_metadata(self):
        with self.assertRaises(ValueError):storage.encoded({'number':float('nan')})
        with self.assertRaisesRegex(ValueError,'duplicate_metadata_key'):storage.document(b'{"a":1,"a":2}')
        with self.assertRaisesRegex(ValueError,'nonfinite_metadata'):storage.document(b'{"a":NaN}')

    def test_world_readable_or_symlink_storage_is_rejected(self):
        bad=self.root/'bad';bad.mkdir(mode=0o755);bad.chmod(0o755)
        self.assertTrue(bad.stat().st_mode&0o077,'Unsafe permission fixture must survive a restrictive inherited umask')
        with self.assertRaisesRegex(ValueError,'private_owned_storage'):storage.BootstrapJournal(bad,{}, {})
        alias=self.root/'alias';alias.symlink_to(self.root,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink_forbidden'):storage.BootstrapJournal(alias,{}, {})

    def test_outcome_without_intent_or_bool_phase_token_is_rejected(self):
        with self.journal() as journal:
            for token in (None, True, 0):
                with self.subTest(token=token),self.assertRaisesRegex(ValueError,'phase_result_mismatch'):
                    journal.after(token,None)
                with self.subTest(token=token),self.assertRaisesRegex(ValueError,'phase_failure_mismatch'):
                    journal.failed(token,'declared_failure')
            phase=journal.before('preflight')
            with self.assertRaisesRegex(ValueError,'phase_result_mismatch'):journal.after(False,None)
            journal.after(phase,None)

    def test_missing_required_operations_never_become_complete(self):
        with self.journal() as journal:
            with self.assertRaisesRegex(ValueError,'observation_incomplete'):
                journal.finish({'state':'complete','operations':0})
            self.assertFalse((journal.root/'result.json').exists())

    def test_existing_stream_mode_change_is_detected_before_append(self):
        with self.journal() as journal:
            (journal.root/'events.jsonl').chmod(0o644)
            with self.assertRaisesRegex(ValueError,'private_journal_required'):journal.before('preflight')

    def test_private_read_rejects_symlink_ancestor_not_only_leaf(self):
        with self.journal() as journal:
            link=self.root/'alias';link.symlink_to(journal.root,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'storage_symlink_forbidden'):
                storage.read_private(link/'request.json')

    def test_retained_complete_rederives_whole_core_and_does_not_claim_current_environment(self):
        with self.journal() as journal:
            class Ports:
                def perform(self,action):return True if action=='environment_python_executable' else None
            value=run('source-intake-environment-v1',Ports(),journal)
            journal.finish({'state':'complete','operations':value.operations})
            record=storage.inspect(journal.root)
            self.assertEqual(record['declared_result'],'complete')
            self.assertFalse(record['current_environment_rechecked'])
            self.assertFalse(record['current_process_liveness_checked'])
            self.assertFalse(record['independent_execution_authenticated'])

    def test_open_phase_stays_pending_without_liveness_inference_or_retry(self):
        with self.journal() as journal:
            journal.before('preflight')
            report=storage.inspect(journal.root)
            self.assertEqual(report['state'],'pending_incomplete')
            self.assertIsNone(report['declared_result'])
            self.assertFalse(report['current_process_liveness_checked'])

    def test_unknown_file_or_changed_source_is_not_tolerated_as_retained_evidence(self):
        for kind in ('unknown','source'):
            with self.subTest(kind=kind),self.journal() as journal:
                if kind=='unknown':(journal.root/'unexpected').write_bytes(b'not allowed')
                else:(journal.root/'source.json').write_text('{}\n')
                with self.assertRaisesRegex(ValueError,'file_membership_changed|input_binding_changed'):
                    storage.inspect(journal.root)

    def test_truncated_or_modified_hashed_event_cannot_be_replayed(self):
        for kind in ('truncated','modified'):
            with self.subTest(kind=kind),self.journal() as journal:
                path=journal.root/'events.jsonl';raw=path.read_bytes()
                path.write_bytes(raw[:-1] if kind=='truncated' else raw.replace(b'opened',b'forged'))
                with self.assertRaisesRegex(ValueError,'truncated_or_empty|digest_changed'):
                    storage.inspect(journal.root)
