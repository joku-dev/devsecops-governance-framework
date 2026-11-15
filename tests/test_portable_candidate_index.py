"""Separate candidate history cannot update official mainline or trust."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from jsonschema import ValidationError
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.portable.contracts import repository_key
from lib.portable_intake.candidate_index import build_index,validate_candidate
from lib.portable_intake.publisher import candidate,path_for
from test_portable_runtime import context


def document(provider='github-actions',event='push'):
    ctx=context(provider);ctx['ci']['event']=event;ctx['synthetic']=False
    receipt={'producer':ctx,'execution_key':'a'*64,'repository_key':repository_key(ctx['scm']),
        'verifier':{'source_digest':'b'*64},'bundle_digest':'c'*64,'decision':'pass','execution':'complete','trust':'provenance_verified'}
    return candidate(receipt,{k:ctx['ci'][k] for k in ('run_id','job_id','attempt')},'2026-11-15T12:00:00Z')


class CandidateIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def write(self,doc):
        path=self.root/path_for(doc);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(doc));return path
    def test_three_provider_candidates_retain_original_trust_in_separate_history(self):
        for provider in ('github-actions','gitlab-ci','bamboo'):self.write(document(provider))
        value=build_index(self.root)
        self.assertEqual(value['candidate_count'],3);self.assertFalse(value['official_acceptance'])
        self.assertEqual(len(value['repositories']),3)
        for row in value['latest_candidate_by_context'].values():
            self.assertEqual(row['context'],'branch');self.assertFalse(row['mainline_proven'])
            self.assertFalse(row['native_verification_performed']);self.assertEqual(row['candidate']['trust'],'provenance_verified')
    def test_main_named_branch_is_not_official_mainline(self):
        doc=document();doc['revision']['branch']='main';self.write(doc)
        row=next(iter(build_index(self.root)['latest_candidate_by_context'].values()))
        self.assertEqual(row['context'],'branch');self.assertFalse(row['mainline_proven'])
    def test_pr_and_manual_stay_separate_and_history_is_preserved(self):
        first=document(event='pull_request');first['revision']['mode']='source-head';self.write(first)
        second=document(event='manual');second['ci']['run_id']='another';
        # Regenerate all identity/link fields for a second execution.
        from lib.portable_intake.controller import task_key
        from lib.portable_intake.operations import run_link
        second['native_execution_key']=task_key({'scm':second['scm'],'ci':second['ci']},{k:second['ci'][k] for k in ('run_id','job_id','attempt')})
        second['run_url']=run_link(second);self.write(second)
        value=build_index(self.root)
        self.assertEqual(value['candidate_count'],2)
        self.assertEqual({row['context'] for row in value['latest_candidate_by_context'].values()},{'pull_request','manual'})
    def test_identity_or_link_tampering_cannot_move_a_candidate(self):
        for name,value in [('repository_key','e'*64),('native_execution_key','f'*64),('run_url','https://attacker.example/run')]:
            with self.subTest(name=name),self.assertRaises(ValueError):validate_candidate({**document(),name:value})
    def test_added_approval_flags_or_full_baseline_claims_are_rejected(self):
        for name in ('approved','official_acceptance','full_baseline_assessment'):
            with self.subTest(name=name),self.assertRaises(ValidationError):validate_candidate({**document(),name:True})
    def test_missing_merge_parent_is_not_a_complete_merge_context(self):
        doc=document(event='pull_request');doc['revision']['mode']='merge-result'
        with self.assertRaisesRegex(ValueError,'merge_revision_incomplete'):validate_candidate(doc)
    def test_path_and_budget_and_symlink_fail_closed(self):
        doc=document();path=self.write(doc)
        with self.assertRaisesRegex(ValueError,'budget'):build_index(self.root,limit=0)
        bad=path.with_name('e'*64+'.json');path.rename(bad)
        with self.assertRaisesRegex(ValueError,'path_identity'):build_index(self.root)
        bad.unlink();bad.symlink_to('/etc/passwd')
        with self.assertRaisesRegex(ValueError,'symlink'):build_index(self.root)
