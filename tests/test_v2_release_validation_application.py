"""Durable product release verification over actual ordinary Git/data fixtures."""
from pathlib import Path
import copy
import json
import os
import shutil
import subprocess
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tests'))
from test_v2_release_verification import fixture,ORIGINAL
from lib.release_validation_application import ReleaseValidationContext
from lib.providers.release_verification import ReleaseVerificationEnvironment
from lib.providers.release_references import ReleaseSource
from lib.consumer_intake_store import atomic_json

AT='2026-11-18T14:45:00Z'


class ReleaseApplicationTests(fixture.ReleaseIntegrityTests):
    def context(self):
        instance=Path(self.temp.name)/'instance';instance.mkdir(mode=0o700,exist_ok=True)
        return ReleaseValidationContext(instance,{'node_id':'a'*32},product_root=self.root)

    def verify(self):
        self.application=self.context()
        operation,value=self.application.create(AT,source_worktree=self.root)
        target=self.application.operations/operation
        # The whole unchanged oracle runs over the SAME private retained data
        # view, with its actual original Git operations explicitly aimed at the
        # source fixture's Git metadata. No output normalization is performed.
        with patch.dict(os.environ,{'GIT_DIR':str(self.root/'.git')}):
            expected=ORIGINAL.verify_release_integrity(target/'inputs',target/'inputs/model/governance/release-signing-policy.yaml')
        self.assertEqual(value['report'],expected)
        self.assertEqual(json.dumps(value['report'],indent=2)+'\n',json.dumps(expected,indent=2)+'\n')
        self.assertEqual(value['exit_code'],0);self.assertEqual(value['execution'],'complete')
        self.assertFalse(value['official_acceptance']);self.assertFalse(value['authority_transferred'])
        self.assertEqual(self.application.inspect(operation),value)
        self.last=(operation,value,target)
        return value['report']

    def test_pending_precedes_native_work_and_starts_are_individually_journalled(self):
        context=self.context();events=[]
        def environment(*args,**kwargs):
            targets=list(context.operations.iterdir());self.assertEqual(len(targets),1)
            self.assertTrue((targets[0]/'pending.json').is_file());self.assertTrue((targets[0]/'input-manifest.json').is_file())
            events.append('intent-before-native');return ReleaseVerificationEnvironment(*args,**kwargs)
        with patch('lib.release_validation_application.ReleaseVerificationEnvironment',side_effect=environment):
            operation,value=context.create(AT,source_worktree=self.root)
        self.assertEqual(events,['intent-before-native'])
        starts=list((context.operations/operation/'starts').iterdir());self.assertEqual(len(starts),len(value['native_observations']))
        self.assertTrue(all(p.stat().st_mode&0o077==0 for p in starts));self.assertEqual(context.inspect(operation),value)

    def test_removed_caller_replays_without_source_capture_or_native_verification(self):
        caller=Path(self.temp.name)/'caller'
        subprocess.run(['git','-c','core.hooksPath=/dev/null','clone','--local','--no-hardlinks',str(self.root),str(caller)],check=True,capture_output=True)
        for path in self.root.rglob('*'):
            if '.git' in path.relative_to(self.root).parts or not path.is_file():continue
            target=caller/path.relative_to(self.root);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
        context=self.context();operation,value=context.create(AT,source_worktree=caller);shutil.rmtree(caller)
        with patch('lib.release_validation_application.ReleaseSource',side_effect=AssertionError('caller access forbidden')),patch('lib.release_validation_application.ReleaseVerificationEnvironment',side_effect=AssertionError('native verification forbidden')):
            self.assertEqual(context.inspect(operation),value)
        self.assertEqual(context.status()[0]['state'],'retained_declared_replay_consistent')

    def test_changed_inputs_leave_completed_native_evidence_pending_without_retry(self):
        context=self.context();original=ReleaseSource.capture;calls=[]
        def changed(source):
            calls.append(True)
            if len(calls)==2:(self.root/'releases/test/payload.txt').write_text('Changed after native execution')
            return original(source)
        with patch('lib.release_validation_application.ReleaseSource.capture',changed):
            with self.assertRaisesRegex(ValueError,'changed_before_admission'):context.create(AT,source_worktree=self.root)
        target=next(context.operations.iterdir());self.assertTrue((target/'native-results.json').exists());self.assertFalse((target/'assessment.json').exists())
        with patch('lib.release_validation_application.ReleaseVerificationEnvironment',side_effect=AssertionError('automatic retry forbidden')):
            self.assertEqual(context.status()[0]['state'],'pending_incomplete_or_invalid')

    def test_unsafe_symlink_is_an_explicit_capture_guard_before_signature_work(self):
        target=self.root/'releases/test/payload.txt';target.unlink();target.symlink_to(Path(self.temp.name)/'outside')
        context=self.context()
        with patch('lib.release_validation_application.ReleaseVerificationEnvironment',side_effect=AssertionError('native work forbidden')):
            with self.assertRaises(ValueError):context.create(AT,source_worktree=self.root)
        self.assertEqual(list(context.operations.iterdir()),[])

    def test_closed_record_authority_report_and_start_journal_reject_tampering(self):
        self.verify();operation,value,target=self.last
        files={name:(target/name).read_bytes() for name in ('assessment.json','native-results.json','pending.json')}
        first=next((target/'starts').iterdir());start=first.read_bytes()
        changes=['authority','report','extra','start','references']
        references=(target/'references.json').read_bytes()
        for change in changes:
            with self.subTest(change=change):
                if change=='authority':
                    for name in files:
                        row=json.loads(files[name]);row['authority_transferred']=True;atomic_json(target/name,row)
                elif change in ('report','extra'):
                    row=copy.deepcopy(value)
                    if change=='report':row['report']['release_tags']=[]
                    else:row['undeclared']=False
                    atomic_json(target/'assessment.json',row);atomic_json(target/'native-results.json',row)
                elif change=='start':first.write_text('{}')
                else:(target/'references.json').write_text('{}')
                with self.assertRaises(ValueError):self.application.inspect(operation)
                for name,raw in files.items():(target/name).write_bytes(raw)
                first.write_bytes(start);(target/'references.json').write_bytes(references)
        self.assertEqual(self.application.inspect(operation),value)

    def test_incomplete_original_failure_is_retained_and_never_replayed_as_success(self):
        import yaml
        policy=yaml.safe_load(self.policy_path.read_bytes());policy['direct_signature']['trusted_signers'][0]['fingerprint']='SHA256:incorrect'
        self.policy_path.write_text(yaml.safe_dump(policy));context=self.context()
        operation,value=context.create(AT,source_worktree=self.root)
        self.assertEqual(value['execution'],'incomplete');self.assertEqual(value['exception_type'],'ValueError');self.assertEqual(value['exit_code'],2)
        with self.assertRaisesRegex(ValueError,'incomplete_execution'):context.inspect(operation)
        self.assertEqual(context.status()[0]['state'],'pending_incomplete_or_invalid')

    def test_missing_manifest_remains_a_complete_original_report_only_result(self):
        self.manifest_path.unlink();result=self.verify()
        self.assertIn(self.legacy_tag,result['unverified_release_tags'])
        self.assertTrue(any('missing or is a symlink' in value for value in result['verification_errors']))

    def test_foreign_source_commit_is_rejected_before_any_operation_or_signature(self):
        caller=Path(self.temp.name)/'foreign'
        subprocess.run(['git','-c','core.hooksPath=/dev/null','clone','--local','--no-hardlinks',str(self.root),str(caller)],check=True,capture_output=True)
        (caller/'other').write_text('foreign base')
        for args in [('config','user.name','Other'),('config','user.email','other@example.invalid'),('config','commit.gpgsign','false'),('add','other'),('commit','-qm','Other base')]:
            subprocess.run(['git','-C',str(caller),'-c','core.hooksPath=/dev/null',*args],check=True,capture_output=True)
        context=self.context()
        with patch('lib.release_validation_application.ReleaseVerificationEnvironment',side_effect=AssertionError('native signature work forbidden')):
            with self.assertRaisesRegex(ValueError,'revision_mismatch'):context.create(AT,source_worktree=caller)
        self.assertEqual(list(context.operations.iterdir()),[])

    def test_start_journal_failure_keeps_pending_and_cleans_owned_capsule(self):
        context=self.context();original=atomic_json
        def failed(path,value,*args,**kwargs):
            if Path(path).parent.name=='starts':raise PermissionError('Injected journal failure')
            return original(path,value,*args,**kwargs)
        with patch('lib.release_validation_application.atomic_json',side_effect=failed):
            with self.assertRaises(PermissionError):context.create(AT,source_worktree=self.root)
        target=next(context.operations.iterdir());self.assertTrue((target/'pending.json').exists())
        self.assertFalse((target/'assessment.json').exists());self.assertEqual(list((target/'native-work').iterdir()),[])
        self.assertEqual(context.status()[0]['state'],'pending_incomplete_or_invalid')

    def test_nonfinite_original_report_is_incomplete_not_unreadable_admitted_json(self):
        import math,yaml
        policy=yaml.safe_load(self.policy_path.read_bytes());policy['schema_version']=float('nan')
        self.policy_path.write_text(yaml.safe_dump(policy))
        old=ORIGINAL.verify_release_integrity(self.root,self.policy_path)
        self.assertTrue(math.isnan(old['policy_version']))
        context=self.context();operation,value=context.create(AT,source_worktree=self.root)
        self.assertEqual(value['execution'],'incomplete');self.assertEqual(value['exception_type'],'ValueError')
        self.assertEqual(value['exit_code'],2);self.assertIsNone(value['report'])
        self.assertTrue(value['native_observations'])
        def invalid(number):raise AssertionError('A retained record must contain only valid JSON numbers: '+number)
        target=context.operations/operation
        for name in ('assessment.json','native-results.json'):
            self.assertEqual(json.loads((target/name).read_bytes(),parse_constant=invalid),value)
        with self.assertRaisesRegex(ValueError,'incomplete_execution'):context.inspect(operation)
        self.assertEqual(context.status()[0]['state'],'pending_incomplete_or_invalid')


class Sha256ReleaseApplicationTests(ReleaseApplicationTests):
    def git(self,*args):
        if args and args[0]=='init':args=('init','--object-format=sha256',*args[1:])
        return super().git(*args)
