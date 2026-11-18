"""Every release-native invocation has separate intent, start and completion."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import MethodType
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.providers.repository_git import RepositoryGit
from lib.providers.release_references import ReleaseReferences
from lib.providers.release_verification import ReleaseVerificationEnvironment
from lib.release_verification import ReleaseVerification
from lib.release_replay import ReplayReleaseEnvironment
from lib.providers import process_groups


@unittest.skipUnless(shutil.which('git') and shutil.which('ssh-keygen'),'local Git/SSH tools absent')
class RepositoryReleasePortTests(unittest.TestCase):
    def setUp(self):
        import test_release_integrity as fixture
        self.git=MethodType(fixture.ReleaseIntegrityTests.git,self)
        fixture.ReleaseIntegrityTests.setUp(self)
        self.files={p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*')
            if p.is_file() and '.git' not in p.relative_to(self.root).parts}
        self.area=Path(self.temp.name)/'native';self.area.mkdir(mode=0o700)
        self.rows=[]
        self.references=ReleaseReferences(self.root).capture()

    def native(self,**overrides):
        def record(stage):return lambda row:self.rows.append({'stage':stage,'observation':copy.deepcopy(row)})
        options={'on_intent':record('intent'),'on_start':record('started'),'on_finish':record('finished')}
        options.update(overrides)
        return ReleaseVerificationEnvironment(self.root,self.files,self.references,self.area,**options)

    def test_journaled_source_git_reader_retains_the_complete_original_reference_capsule(self):
        rows=[]
        port=RepositoryGit(self.root,shutil.which('git'),on_intent=lambda row:None,
            on_start=lambda row:None,on_finish=lambda row:rows.append(copy.deepcopy(row)))
        actual=ReleaseReferences(self.root,read=port.read).capture()
        self.assertEqual(actual,self.references)
        self.assertTrue(any(row['arguments'][:2]==['cat-file','-t'] for row in rows))
        self.assertTrue(any(row['arguments'][:2]==['cat-file','tag'] for row in rows))
        self.assertTrue(all(row['returncode']==0 and row['error_type'] is None for row in rows))

    def test_all_capsule_preparation_and_verification_native_calls_have_three_journal_phases(self):
        with self.native() as native:
            report=ReleaseVerification(native).verify_release_integrity()
            self.assertEqual(report['unverified_release_tags'],[])
            self.assertEqual([row['stage'] for row in self.rows],['intent','started','finished']*len(native.observations))
            self.assertEqual([row['observation'] for row in self.rows if row['stage']=='finished'],native.observations)
            for index in range(0,len(self.rows),3):
                intent,start,finish=[row['observation'] for row in self.rows[index:index+3]]
                self.assertFalse(intent['process_started']);self.assertTrue(start['process_started'])
                self.assertIsNone(start['returncode']);self.assertEqual(finish['returncode'],native.observations[index//3]['returncode'])
            metadata=copy.deepcopy(native.metadata);observations=copy.deepcopy(native.observations)
        replay=ReplayReleaseEnvironment(self.root,self.files,self.references,metadata,observations)
        with patch('subprocess.Popen',side_effect=AssertionError('no process during replay')):
            self.assertEqual(ReleaseVerification(replay).verify_release_integrity(),report);replay.finish()
        self.assertEqual(list(self.area.iterdir()),[])

    def test_failed_durable_intent_prevents_capsule_process_creation(self):
        def fail(_):raise OSError('controlled native intent failure')
        with patch('subprocess.Popen',side_effect=AssertionError('must not start')):
            with self.assertRaisesRegex(OSError,'controlled native intent'):self.native(on_intent=fail)
        self.assertEqual(self.rows,[])
        self.assertEqual(list(self.area.iterdir()),[])

    def test_failed_completion_journal_cannot_admit_a_successful_capsule(self):
        original=subprocess.Popen;processes=[]
        def started(*args,**kwargs):
            process=original(*args,**kwargs);processes.append(process);return process
        def fail(_):raise OSError('controlled native completion failure')
        with patch('subprocess.Popen',side_effect=started):
            with self.assertRaisesRegex(OSError,'controlled native completion'):self.native(on_finish=fail)
        self.assertTrue(processes)
        for process in processes:
            self.assertIsNotNone(process.poll());self.assertTrue(process.stdout.closed and process.stderr.closed)
        self.assertEqual(list(self.area.iterdir()),[])

    def test_cleanup_error_still_closes_every_stream_and_preserves_the_failure(self):
        original=subprocess.Popen;processes=[];real_stop=process_groups.stop
        def started(*args,**kwargs):
            process=original(*args,**kwargs);processes.append(process);return process
        def cleanup(process):
            real_stop(process);raise PermissionError('controlled post-cleanup failure')
        with patch('subprocess.Popen',side_effect=started),patch.object(process_groups,'stop',side_effect=cleanup):
            with self.assertRaisesRegex(PermissionError,'controlled post-cleanup'):self.native()
        self.assertTrue(processes)
        for process in processes:
            self.assertIsNotNone(process.poll());self.assertTrue(process.stdout.closed and process.stderr.closed)
        self.assertEqual(self.rows[-1]['stage'],'finished')
        self.assertEqual(self.rows[-1]['observation']['error_type'],'PermissionError')

    def test_a_release_tool_inside_the_inspected_repository_is_never_executed(self):
        fake=self.root/'git';fake.write_text('#!/bin/sh\nexit 0\n');fake.chmod(0o700)
        with patch('subprocess.Popen',side_effect=AssertionError('inspected program must not execute')):
            with self.assertRaisesRegex(ValueError,'inside_inspected_source'):self.native(git_tool=fake)
        self.assertEqual(list(self.area.iterdir()),[])

    def test_a_crypto_tool_inside_the_inspected_repository_is_an_incomplete_observation(self):
        from lib.providers.attestation_verification import verify,outcome
        fake=self.root/'openssl';fake.write_text('#!/bin/sh\nexit 0\n');fake.chmod(0o700)
        with patch('shutil.which',return_value=str(fake)),patch('subprocess.Popen',side_effect=AssertionError('inspected program must not execute')):
            row,stdout,stderr=verify('key',b'statement',b'signature',self.area,'legacy-attestation-pilot-v1',lambda row:None,forbidden_root=self.root)
        self.assertFalse(row['process_started'])
        self.assertEqual(row['error_type'],'ValueError')
        with self.assertRaises(ValueError):outcome(row)
        self.assertEqual((stdout,stderr),(b'',b''))

    def test_git_reader_cannot_expand_its_finite_stdout_budget(self):
        port=RepositoryGit(self.root,shutil.which('git'),on_intent=lambda row:None,on_start=lambda row:None,on_finish=lambda row:None)
        with self.assertRaises(ValueError):port.read('cat-file','-t',self.references['source_head'],limit=33)
        with self.assertRaises(ValueError):port.read('rev-parse','--verify','--end-of-options','refs/heads/main')
        with self.assertRaises(ValueError):port.read('-c','color.ui=false','-c','column.ui=never','tag','--list','*')


if __name__=='__main__':unittest.main()
