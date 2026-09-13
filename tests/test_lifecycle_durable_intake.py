"""Durable pilot eligibility preserves evidence and rejects conflicting acceptance."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from jsonschema import ValidationError

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'scripts'))
import test_lifecycle_live_evidence as fixture
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ContractError
from lib.governance_lifecycle.live_admission import (
    append_capture, capture_files, load_operating, origin_key, producer_fingerprint,
    project_receipts, replay_embedded, replay_receipts, verify_new_receipts,
)
from lib.governance_lifecycle.live_evidence import collect_preflight
from lib.governance_lifecycle.store import load_transactions


class DurableIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name); self.ledger=self.root/'ledger'
        self.source=fixture.LiveEvidenceTests(); self.source.setUp()
        self.profile=load_operating()
        self.capture=self.root/'capture'
        self.collect(self.capture)

    def collect(self,path):
        collect_preflight('123',path,fetch=self.source.fake_fetch,captured_at=fixture.AT)

    def append(self,path=None,sequence=0,at=fixture.AT):
        return append_capture(self.ledger,path or self.capture,self.profile,recorded_at=at,expected_sequence=sequence)

    def test_real_operating_values_are_confirmed_but_activation_is_separate(self):
        self.assertEqual(self.profile['operating_policy']['maximum_age_seconds'],86400)
        self.assertFalse(self.profile['live_activation_approved'])
        self.assertFalse(self.profile['operating_policy']['automatic_deletion'])
        self.assertEqual(self.profile['authorization']['statement'],'ja')
        bad=deepcopy(self.profile); bad['operating_policy']['maximum_age_seconds']=999999
        with self.assertRaises(ValidationError):
            append_capture(self.ledger,self.capture,bad,recorded_at=fixture.AT,expected_sequence=0)

    def test_complete_capture_survives_source_removal_and_replays(self):
        self.assertEqual(self.append()['outcome'],'eligible_for_pilot')
        import shutil
        shutil.rmtree(self.capture)
        records=load_transactions(self.ledger)
        self.assertEqual(len(replay_receipts(records,self.profile)),1)
        self.assertIn('artifact.zip',records[0]['capture'])
        self.assertIn('preflight.json',records[0]['capture'])
        index=project_receipts(records,self.profile)
        self.assertFalse(index['official_state'])
        self.assertFalse(index['live_activation_approved'])
        if records[0]['criterion']['status']=='pass':
            self.assertIsNone(index['pilot_finding'])

    def test_exact_replay_is_noop_even_when_original_evidence_is_now_old(self):
        self.append()
        original=list((self.ledger/'transactions').iterdir())[0].read_bytes()
        self.assertEqual(self.append(sequence=999,at='2026-09-15T13:00:00Z')['outcome'],'duplicate')
        self.assertEqual(len(load_transactions(self.ledger)),1)
        self.assertEqual(list((self.ledger/'transactions').iterdir())[0].read_bytes(),original)

    def test_stale_new_evidence_and_future_receipt_are_rejected(self):
        with self.assertRaisesRegex(ContractError,'stale'):
            self.append(at='2026-09-14T13:00:00Z')
        with self.assertRaisesRegex(ContractError,'predates capture'):
            self.append(at='2026-09-13T12:59:59Z')
        self.assertEqual(load_transactions(self.ledger),[])

    def test_same_origin_changed_archive_is_persisted_as_quarantine(self):
        self.append()
        # Change non-authoritative text, preserve the explicit criterion, but bind new raw bytes.
        self.source.report['risk_statement']='Changed producer bytes under the same origin'
        self.source.repack()
        changed=self.root/'changed'; self.collect(changed)
        self.assertEqual(self.append(changed,sequence=1)['outcome'],'quarantined')
        self.assertEqual(self.append(changed,sequence=99)['outcome'],'duplicate')
        records=load_transactions(self.ledger)
        self.assertEqual(len(records),2)
        self.assertEqual(records[1]['conflicts_with']['id'],records[0]['transaction_id'])
        self.assertEqual(project_receipts(records,self.profile)['counts']['quarantined'],1)

    def test_competing_content_with_stale_sequence_cannot_win_concurrent_append(self):
        # The pure append boundary serializes file writers; different content cannot share a head.
        self.source.report['risk_statement']='competing content'; self.source.repack()
        changed=self.root/'competing'; self.collect(changed)
        def attempt(path):
            try:return self.append(path)['outcome']
            except ContractError:return 'rejected'
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(attempt,[self.capture,changed]))
        self.assertEqual(sorted(outcomes),['eligible_for_pilot','rejected'])
        self.assertEqual(len(load_transactions(self.ledger)),1)

    def test_pass_after_failure_does_not_close_and_same_time_conflict_is_visible(self):
        import yaml
        from assess_governance_repository_security import assess
        model=yaml.safe_load(self.source.files['model/controls/governance-repository-security.yaml'])
        observation=deepcopy(self.source.report['observation'])
        observation['repository']['required_approving_reviews']=0
        self.source.report=assess(model,observation); self.source.repack()
        failed=self.root/'failed'; self.collect(failed)
        self.append(failed)
        observation['repository']['required_approving_reviews']=1
        self.source.run['id']=124; self.source.artifact['id']=457
        self.source.artifact['workflow_run']['id']=124
        self.source.report=assess(model,observation); self.source.repack()
        def fetch(endpoint,*,raw=False):
            return self.source.fake_fetch(endpoint.replace('/runs/124','/runs/123').replace('/artifacts/457','/artifacts/456'),raw=raw)
        ambiguous=self.root/'ambiguous'
        collect_preflight('124',ambiguous,fetch=fetch,captured_at=fixture.AT)
        self.assertEqual(self.append(ambiguous,sequence=1)['outcome'],'quarantined')
        observation['observed_at']='2026-09-13T12:59:06Z'
        self.source.run['id']=125; self.source.artifact['id']=458
        self.source.artifact['workflow_run']['id']=125
        self.source.report=assess(model,observation); self.source.repack()
        def later_fetch(endpoint,*,raw=False):
            return self.source.fake_fetch(endpoint.replace('/runs/125','/runs/123').replace('/artifacts/458','/artifacts/456'),raw=raw)
        passed=self.root/'passed'
        collect_preflight('125',passed,fetch=later_fetch,captured_at=fixture.AT)
        self.assertEqual(self.append(passed,sequence=2)['outcome'],'eligible_for_pilot')
        index=project_receipts(load_transactions(self.ledger),self.profile)
        self.assertEqual(index['latest_criterion_result'],'pass')
        self.assertEqual(index['pilot_finding']['state'],'needs_clarification')
        self.assertFalse(index['pilot_finding']['closure_supported'])

    def test_tampered_bytes_sequence_and_disposition_fail_full_replay(self):
        self.append(); original=load_transactions(self.ledger)
        for mutate in (lambda r:r.update(sequence=9),lambda r:r.update(outcome='accepted_live'),
                       lambda r:r['capture'].update(**{'report.json':'dGFtcGVyZWQ='})):
            records=deepcopy(original); mutate(records[0])
            with self.assertRaises((ContractError,ValidationError)):replay_receipts(records,self.profile)
        with self.assertRaises(ContractError):replay_embedded({'../escape':'eA=='})

    def test_merge_provider_check_rejects_offline_forgery_and_expired_new_receipt(self):
        self.append(); record=load_transactions(self.ledger)[0]
        import shutil
        target=self.root/'repo'/'governance/lifecycle/live-validation/transactions'
        shutil.copytree(self.ledger/'transactions',target)
        capture,_=capture_files(self.capture)
        # No network is used here; test explicitly models independent provider disagreement.
        with patch('lib.governance_lifecycle.live_admission.load_operating',return_value=self.profile), \
             patch('lib.governance_lifecycle.live_admission.subprocess.check_output',return_value=''), \
             patch('lib.governance_lifecycle.live_admission.collect_preflight',return_value=deepcopy(capture)) as collect:
            collect.return_value['source']['report_sha256']='0'*64
            with self.assertRaisesRegex(ContractError,'independently retrieved'):
                verify_new_receipts(self.root/'repo','0'*40)
            collect.return_value=deepcopy(capture)
            with patch('lib.governance_lifecycle.live_admission.datetime') as clock:
                from datetime import datetime,timezone
                clock.now.return_value=datetime(2026,9,15,tzinfo=timezone.utc)
                with self.assertRaisesRegex(ContractError,'stale at PR acceptance'):
                    verify_new_receipts(self.root/'repo','0'*40)


if __name__=='__main__':unittest.main()
