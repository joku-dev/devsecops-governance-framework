"""Native review participation cannot silently become governance authority."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from jsonschema import Draft202012Validator,ValidationError

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.portable_intake.assurance import subject,role_candidate,capture_reviews,capture_security,legacy_module
from test_portable_operations import FakeAPI,SHA
from test_portable_runtime import context


class NativeReviewAPI(FakeAPI):
    base='https://scm.example/api'
    def __init__(self,provider):super().__init__(provider);self.reviews=[];self.changed=False
    def get(self,path):
        if path.endswith('/approvals'):return {'approved_by':self.reviews}
        if path.endswith(('/pulls/7','/merge_requests/opaque-mr-key','/pull-requests/opaque-pr-key')):
            value=self.native(sha='d'*40 if self.changed else SHA);value['reviewers']=deepcopy(self.reviews);return value
        return super().get(path)
    def pages(self,path,**kwargs):return deepcopy(self.reviews)


class AssuranceTests(unittest.TestCase):
    def scm(self,provider):return context({'github':'github-actions','gitlab':'gitlab-ci','bitbucket-dc':'bamboo'}[provider])['scm']

    def test_subject_namespace_distinguishes_provider_issuer_and_kind(self):
        values=[subject(p,i,'42',k)['subject_key'] for p in ('github','gitlab','bitbucket-dc')
                for i in ('https://one.example','https://two.example') for k in ('user','bot','group','application')]
        self.assertEqual(len(set(values)),24)
        self.assertEqual(subject('github','https://ONE.example:443/','42','user'),subject('github','https://one.example','42','user'))

    def test_role_binding_remains_candidate_and_rejects_name_alias_or_issuer_change(self):
        scm=self.scm('gitlab');actor=subject('gitlab',scm['instance'],'42','user')
        candidate=role_candidate(actor,'governance-owner',scm,SHA)
        schema=json.loads((ROOT/'schemas/provider-role-candidate-v1.schema.json').read_text())
        Draft202012Validator(schema).validate(candidate)
        self.assertFalse(candidate['live_authority']);self.assertFalse(candidate['personal_consent'])
        for flag in ('live_authority','personal_consent','operating_acceptance'):
            with self.assertRaises(ValidationError):Draft202012Validator(schema).validate({**candidate,flag:True})
        with self.assertRaises(ValueError):role_candidate({**actor,'display_name':'owner'},'governance-owner',scm,SHA)
        with self.assertRaises(ValueError):role_candidate(subject('gitlab','https://another.example','42','user'),'governance-owner',scm,SHA)

    def test_github_dismissed_or_other_revision_reviews_do_not_count(self):
        api=NativeReviewAPI('github');scm=self.scm('github')
        api.reviews=[{'user':{'id':42,'type':'User'},'id':1,'state':'APPROVED','commit_id':SHA},
                     {'user':{'id':42,'type':'User'},'id':2,'state':'DISMISSED','commit_id':SHA},
                     {'user':{'id':43,'type':'Bot'},'id':3,'state':'APPROVED','commit_id':'c'*40}]
        value=capture_reviews(scm,api,'7',SHA)
        self.assertEqual(value['latest_bound_approval_participants'],0)
        api.reviews.append({'user':{'id':44,'type':'User'},'id':4,'state':'APPROVED','commit_id':SHA})
        value=capture_reviews(scm,api,'7',SHA)
        self.assertEqual(value['latest_bound_approval_participants'],1)
        self.assertFalse(value['role_approval']);self.assertFalse(value['live_authority']);self.assertEqual(api.writes,[])

    def test_gitlab_approval_without_native_review_sha_is_unknown(self):
        api=NativeReviewAPI('gitlab');api.reviews=[{'user':{'id':42,'username':'owner'}}]
        value=capture_reviews(self.scm('gitlab'),api,'opaque-mr-key',SHA)
        self.assertEqual(value['latest_bound_approval_participants'],0)
        self.assertFalse(value['observations'][0]['revision_bound'])

    def test_bitbucket_last_reviewed_commit_is_bound_without_role_claim(self):
        api=NativeReviewAPI('bitbucket-dc');api.reviews=[{'user':{'id':42,'type':'NORMAL'},'status':'APPROVED','lastReviewedCommit':SHA},
            {'user':{'id':43,'type':'NORMAL'},'status':'APPROVED','lastReviewedCommit':'c'*40}]
        value=capture_reviews(self.scm('bitbucket-dc'),api,'opaque-pr-key',SHA)
        self.assertEqual(value['latest_bound_approval_participants'],1);self.assertFalse(value['operating_acceptance'])

    def test_changed_native_head_and_wrong_api_issuer_are_rejected(self):
        api=NativeReviewAPI('github');api.changed=True
        with self.assertRaisesRegex(ValueError,'revision_changed'):capture_reviews(self.scm('github'),api,'7',SHA)
        api.base='https://attacker.example'
        with self.assertRaisesRegex(ValueError,'issuer_mismatch'):capture_reviews(self.scm('github'),api,'7',SHA)

    def test_head_change_between_two_native_reads_is_rejected(self):
        api=NativeReviewAPI('github');original=api.get;reads=[]
        def get(path):
            if path.endswith('/pulls/7'):
                reads.append(path)
                if len(reads)==2:api.changed=True
            return original(path)
        api.get=get
        with self.assertRaisesRegex(ValueError,'changed_during_capture'):capture_reviews(self.scm('github'),api,'7',SHA)

    def test_gitlab_security_captures_native_primitive_without_claiming_grs_equivalence(self):
        api=NativeReviewAPI('gitlab');original=api.get
        def get(path):
            if '/repository/branches/' in path:return {'name':'trunk','commit':{'id':SHA},'protected':True}
            return {**original(path),'default_branch':'trunk','only_allow_merge_if_pipeline_succeeds':True}
        api.get=get
        value=capture_security(self.scm('gitlab'),api,SHA,'2026-11-15T12:00:00Z')
        self.assertEqual([row['id'] for row in value['criteria'] if row['status']=='pass'],['GRS-001'])
        self.assertEqual(len([row for row in value['criteria'] if row['status']=='not_proven']),15)
        self.assertTrue(value['related_native_capabilities']['pipeline_success_merge_setting'])
        self.assertFalse(value['official_acceptance'])

    def test_github_candidate_observation_reuses_legacy_meanings_without_mutating_module(self):
        import assess_governance_repository_security as accepted
        original=accepted.gh_api;module=legacy_module();self.assertIsNot(module.gh_api,original)
        # The private instance can replace only its transport; the accepted module remains intact.
        module.gh_api=lambda path:({},None)
        self.assertIs(accepted.gh_api,original)
        self.assertEqual(module.observed_values({}),accepted.observed_values({}))
        api=NativeReviewAPI('github');original_get=api.get
        api.get=lambda path:{**original_get(path),'default_branch':'main'}
        fixture=legacy_module()
        fixture.collect_live=lambda repository,at:{'api_errors':[]}
        fixture.observed_values=lambda observation:{'default_branch_protected':True}
        with patch('lib.portable_intake.assurance.subprocess.check_output',side_effect=[SHA,'']),patch('lib.portable_intake.assurance.legacy_module',return_value=fixture):
            value=capture_security(self.scm('github'),api,SHA,'2026-11-15T12:00:00Z')
        self.assertEqual(value['criteria'][0]['status'],'pass')
        self.assertTrue(all(row['status']=='not_proven' for row in value['criteria'][1:]))
        self.assertIs(accepted.gh_api,original)

    def test_github_acquisition_error_never_falls_back_to_a_partial_pass(self):
        api=NativeReviewAPI('github');original_get=api.get
        api.get=lambda path:{**original_get(path),'default_branch':'main'}
        fixture=legacy_module();fixture.collect_live=lambda repo,at:{'api_errors':['http_403']}
        fixture.observed_values=lambda observation:{'default_branch_protected':True}
        with patch('lib.portable_intake.assurance.subprocess.check_output',side_effect=[SHA,'']),patch('lib.portable_intake.assurance.legacy_module',return_value=fixture):
            value=capture_security(self.scm('github'),api,SHA,'2026-11-15T12:00:00Z')
        self.assertTrue(all(row['status']=='not_proven' and row['observed'] is None for row in value['criteria']))

    def test_bitbucket_security_unknown_plugins_cannot_claim_grs_pass(self):
        api=NativeReviewAPI('bitbucket-dc');original=api.get
        api.get=lambda path:{'latestCommit':SHA} if path.endswith('/default-branch') else original(path)
        value=capture_security(self.scm('bitbucket-dc'),api,SHA,'2026-11-15T12:00:00Z')
        self.assertEqual(len(value['criteria']),16)
        self.assertTrue(all(row['status']=='not_proven' for row in value['criteria']))
