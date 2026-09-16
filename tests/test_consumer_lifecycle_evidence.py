"""Real retained producer bytes; adversarial copies are local injected fixtures only."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import base64
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.governance_lifecycle.adapter import strict_json,json_bytes
from lib.governance_lifecycle.contracts import ContractError,timestamp
from lib.governance_lifecycle.consumer_contracts import load_operating,load_model
from lib.governance_lifecycle.consumer_evidence import verify_capture,replay_capture,collect_preflight
from lib.governance_lifecycle.consumer_admission import prepare_receipt,replay_receipts,capture_files,append_capture
from lib.governance_lifecycle.consumer_acceptance import check_prefix
from lib.governance_lifecycle.store import load_transactions

CAPTURE=ROOT/'generated/reports/consumer-lifecycle-preflight/main-run-34778861076'


class ConsumerEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile=load_operating()
        cls.preflight=strict_json((CAPTURE/'preflight.json').read_bytes())
        cls.snapshots={p:(CAPTURE/p).read_bytes() for p in cls.preflight['capture']['snapshot_sha256']}
        cls.at=cls.preflight['captured_at']

    def verify(self,files=None):
        return verify_capture(self.profile,files or self.snapshots,captured_at=self.at)

    def mutate_metadata(self,name,mutator):
        files=dict(self.snapshots);data=strict_json(files[name]);mutator(data);files[name]=json_bytes(data)
        if name.endswith('-before.json'):files[name.replace('-before','-after')]=files[name]
        return files

    def rewrite_archive(self,mutator):
        files=dict(self.snapshots)
        with zipfile.ZipFile(io.BytesIO(files['artifact.zip'])) as z:members={n:z.read(n) for n in z.namelist()}
        mutator(members)
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in members.items():z.writestr(name,data)
        files['artifact.zip']=stream.getvalue()
        artifact=strict_json(files['artifact-before.json']);artifact['digest']='sha256:'+hashlib.sha256(files['artifact.zip']).hexdigest()
        artifact['size_in_bytes']=len(files['artifact.zip'])
        files['artifact-before.json']=files['artifact-after.json']=json_bytes(artifact)
        return files

    def test_real_capture_matches_independent_opa_gate(self):
        result=self.verify()
        self.assertEqual(result['criterion']['status'],'fail')
        self.assertEqual(result['criterion']['granularity'],'gate')
        self.assertEqual(len(result['criterion']['source_messages']),2)
        self.assertEqual(replay_capture(CAPTURE),result)

    def test_manual_fork_rerun_and_incomplete_runs_are_rejected(self):
        for mutate in (lambda x:x.update(event='workflow_dispatch'),lambda x:x.update(head_branch='other'),
                       lambda x:x.update(run_attempt=2),lambda x:x['head_repository'].update(id=9),
                       lambda x:x.update(conclusion='failure'),lambda x:x.update(head_sha='abc')):
            with self.subTest(mutate=mutate),self.assertRaises(ContractError):self.verify(self.mutate_metadata('run-before.json',mutate))

    def test_wrong_archive_digest_association_and_expiry_are_rejected(self):
        for mutate in (lambda x:x.update(digest='sha256:'+'0'*64),lambda x:x['workflow_run'].update(id=1),
                       lambda x:x.update(expired=True),lambda x:x.update(expires_at='2026-01-01T00:00:00Z')):
            with self.subTest(mutate=mutate),self.assertRaises(ContractError):self.verify(self.mutate_metadata('artifact-before.json',mutate))

    def test_workflow_baseline_and_policy_drift_are_rejected(self):
        for name in ['consumer-workflow.yml','producer/policies/opa/architecture_operation_readiness.rego']:
            files=dict(self.snapshots);files[name]+=b'\n'
            with self.assertRaises(ContractError):self.verify(files)
        with self.assertRaises(ContractError):self.verify(self.mutate_metadata('baseline-tag.json',lambda x:x['object'].update(sha='a'*40)))
        with self.assertRaises(ContractError):self.verify(self.mutate_metadata('run-before.json',lambda x:x.update(referenced_workflows=[])))

    def test_duplicate_gate_and_fabricated_pass_are_rejected(self):
        def fabricate(members):
            report=strict_json(members['architecture-governance-report.json'])
            gate=report['gates'][2];gate['status']='pass';gate['findings']=[]
            report['summary'].update(passed=1,with_findings=3,finding_count=23)
            members['architecture-governance-report.json']=json_bytes(report)
        with self.assertRaisesRegex(ContractError,'independent pinned OPA'):self.verify(self.rewrite_archive(fabricate))
        def duplicate(members):
            report=strict_json(members['architecture-governance-report.json']);report['gates'][2]['id']=report['gates'][1]['id']
            members['architecture-governance-report.json']=json_bytes(report)
        with self.assertRaises(ContractError):self.verify(self.rewrite_archive(duplicate))

    def test_archive_traversal_and_disabled_gate_are_rejected(self):
        with self.assertRaisesRegex(ContractError,'archive members'):
            self.verify(self.rewrite_archive(lambda m:m.update({'../outside':b'bad'})))
        def disable(members):
            data=strict_json(members['architecture-release-input.json']);data['release_candidate']=False
            members['architecture-release-input.json']=json_bytes(data)
        with self.assertRaisesRegex(ContractError,'Release gate required'):self.verify(self.rewrite_archive(disable))

    def test_metadata_race_and_wrong_target_are_rejected(self):
        files=dict(self.snapshots);data=strict_json(files['run-after.json']);data['updated_at']=self.at;files['run-after.json']=json_bytes(data)
        with self.assertRaisesRegex(ContractError,'metadata changed'):self.verify(files)
        def change(members):
            report=strict_json(members['architecture-governance-report.json']);report['target']['commit']='badcommit'
            members['architecture-governance-report.json']=json_bytes(report)
        with self.assertRaises(ContractError):self.verify(self.rewrite_archive(change))

    def test_receipt_replay_idempotency_conflict_and_freshness(self):
        capture,files=capture_files(CAPTURE);encoded={p:base64.b64encode(b).decode() for p,b in files.items()}
        first=prepare_receipt(capture,encoded,self.profile,[],recorded_at=self.at,expected_sequence=0)
        self.assertEqual(replay_receipts([first],self.profile),[first])
        late=(timestamp(capture['source']['observed_at'])+timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.assertIsNone(prepare_receipt(capture,encoded,self.profile,[first],recorded_at=late,expected_sequence=999))
        with self.assertRaisesRegex(ContractError,'stale'):
            prepare_receipt(capture,encoded,self.profile,[],recorded_at=late,expected_sequence=0)
        with self.assertRaisesRegex(ContractError,'Stale receipt sequence'):
            prepare_receipt(capture,encoded,self.profile,[],recorded_at=self.at,expected_sequence=1)
        # Isolate identity/conflict policy; mutated capture is not valid provider evidence.
        changed=deepcopy(capture);changed['source']['artifact_sha256']='0'*64
        conflict=prepare_receipt(changed,encoded,self.profile,[first],recorded_at=self.at,expected_sequence=1)
        self.assertEqual(conflict['outcome'],'quarantined')
        with self.assertRaises(ContractError):replay_receipts([first,conflict],self.profile)

    def test_exclusive_store_and_capture_mutation_detection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'ledger'
            first=append_capture(root,CAPTURE,self.profile,recorded_at=self.at,expected_sequence=0)
            second=append_capture(root,CAPTURE,self.profile,recorded_at=self.at,expected_sequence=1)
            self.assertEqual(first['outcome'],'eligible_for_pilot');self.assertEqual(second['outcome'],'duplicate')
            self.assertEqual(len(load_transactions(root)),1)

    def test_publisher_cannot_modify_other_consumer_or_existing_history(self):
        import publish_consumer_lifecycle as publisher
        self.assertTrue(publisher.allowed('status/governance-consumer-lifecycle.json','consumer-lifecycle'))
        for path in ['status/governance-lifecycle-live.json','status/results/example.json','model/governance/lifecycle/consumer-operation/roles.json']:
            self.assertFalse(publisher.allowed(path,'consumer-lifecycle'))
        self.assertIn('consumer-lifecycle-guard.yml',publisher.CHECK_WORKFLOWS)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);subprocess.run(['git','init','-q',str(root)],check=True)
            path=root/'governance/consumer-lifecycle/acceptance/00000001.json';path.parent.mkdir(parents=True);path.write_text('{}\n')
            subprocess.run(['git','add','.'],cwd=root,check=True)
            subprocess.run(['git','-c','user.name=fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-qm','fixture'],cwd=root,check=True)
            path.write_text('{"changed":true}\n')
            with self.assertRaisesRegex(ValueError,'append-only'):publisher.selected_paths(root,'consumer-lifecycle')
            with self.assertRaisesRegex(ContractError,'rewritten'):check_prefix(root,'HEAD')


if __name__=='__main__':unittest.main()
