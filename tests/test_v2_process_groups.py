"""Never turn a denied signal into success without observed owned-group quiescence."""
import errno
import os
from pathlib import Path
import signal
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

ROOT=Path(os.environ.get('AXIOM_TEST_PRODUCT_ROOT',Path(__file__).resolve().parents[1]));sys.path.insert(0,str(ROOT/'scripts'))
from lib.providers import process_groups as groups


class OwnedProcessGroups(unittest.TestCase):
    def process(self):return SimpleNamespace(pid=123456,wait=Mock(return_value=0))

    def test_actual_lookup_absence_is_cached_and_never_resignals_a_reusable_group_id(self):
        process=self.process()
        with patch.object(groups.os,'killpg',side_effect=ProcessLookupError) as send,patch.object(groups,'group_state',side_effect=AssertionError('Unneeded process enumeration')):
            groups.stop(process,graceful=True);groups.stop(process,graceful=True)
        self.assertEqual(send.call_count,1);self.assertEqual(groups.observations(process),{'cleanup_signal_permission_denied':False,'cleanup_absence_check':'kernel_absent'})

    def test_denied_signal_requires_confirmed_absent_or_only_defunct_members(self):
        for state in ('absent','zombies'):
            with self.subTest(state=state):
                process=self.process()
                with patch.object(groups.os,'killpg',side_effect=PermissionError(errno.EPERM,'synthetic denial')) as send,patch.object(groups,'group_state',return_value=state):
                    groups.stop(process,graceful=True);groups.stop(process,graceful=True)
                self.assertEqual(send.call_count,1)
                observed={**groups.observations(process),'process_started':True};self.assertTrue(groups.consistent(observed))
                self.assertTrue(observed['cleanup_signal_permission_denied']);self.assertEqual(observed['cleanup_absence_check'],'process_table_'+state)

    def test_live_or_unproven_group_remains_error_and_denied_signal_is_not_retried(self):
        process=self.process()
        with patch.object(groups.os,'killpg',side_effect=PermissionError(errno.EPERM,'synthetic denial')) as send,patch.object(groups,'group_state',return_value='unproven'):
            for unused in range(2):
                with self.assertRaises(PermissionError):groups.stop(process,graceful=True)
        self.assertEqual(send.call_count,1);process.wait.assert_not_called()
        self.assertFalse(groups.consistent({**groups.observations(process),'process_started':True}))

    def test_linux_denial_is_never_reinterpreted_through_a_possibly_restricted_process_table(self):
        process=self.process()
        with patch.object(groups.sys,'platform','linux'),patch.object(groups.os,'killpg',side_effect=PermissionError),patch.object(groups.subprocess,'run',side_effect=AssertionError('No process-table exception on Linux')):
            with self.assertRaises(PermissionError):groups.stop(process)

    def test_process_table_must_be_complete_enough_to_include_observer_and_have_no_live_target(self):
        cases=[(b'100 S\n','absent'),(b'100 R\n200 Z\n200 Z+\n','zombies'),(b'100 S\n200 S\n','unproven'),
            (b'100 S\n200 Z\n200 R\n','unproven'),(b'200 Z\n','unproven'),(b'','unproven'),(b'invalid\n','unproven'),(b'100 S\n\xff','unproven')]
        with patch.object(groups.sys,'platform','darwin'),patch.object(groups.os,'getpgrp',return_value=100):
            for raw,expected in cases:
                with self.subTest(raw=raw):
                    response=SimpleNamespace(returncode=0,stdout=raw)
                    with patch.object(groups.subprocess,'run',return_value=response) as run:self.assertEqual(groups.group_state(200),expected)
                    self.assertEqual(run.call_args.args[0],['/bin/ps','-A','-o','pgid=,state='])

    def test_process_observation_failure_timeout_or_budget_never_proves_absence(self):
        responses=[SimpleNamespace(returncode=1,stdout=b'100 S\n'),SimpleNamespace(returncode=0,stdout=b'x'*(groups.MAX_PROCESS_TABLE+1))]
        with patch.object(groups.sys,'platform','darwin'),patch.object(groups.os,'getpgrp',return_value=100):
            for response in responses:
                with patch.object(groups.subprocess,'run',return_value=response):self.assertEqual(groups.group_state(200),'unproven')
            for error in (FileNotFoundError(),PermissionError(),subprocess.TimeoutExpired('ps',2)):
                with patch.object(groups.subprocess,'run',side_effect=error):self.assertEqual(groups.group_state(200),'unproven')

    def test_parent_waits_remain_bounded_even_after_kill(self):
        process=self.process();process.wait.side_effect=subprocess.TimeoutExpired('synthetic',2)
        with patch.object(groups.os,'killpg'):
            with self.assertRaises(subprocess.TimeoutExpired):groups.stop(process,graceful=True)
        self.assertEqual(process.wait.call_count,2)
        self.assertTrue(all(call.kwargs=={'timeout':2} for call in process.wait.call_args_list))

    def test_retained_cleanup_facts_cannot_claim_denial_without_matching_absence_proof(self):
        valid={'process_started':True,'cleanup_signal_permission_denied':True,'cleanup_absence_check':'process_table_absent'}
        self.assertTrue(groups.consistent(valid));self.assertTrue(groups.consistent({}))
        for change in ({'cleanup_absence_check':'unproven'},{'cleanup_absence_check':'not_needed'},{'process_started':False},{'cleanup_signal_permission_denied':False}):
            with self.subTest(change=change):self.assertFalse(groups.consistent({**valid,**change}))
        self.assertFalse(groups.consistent({'cleanup_signal_permission_denied':True}))
