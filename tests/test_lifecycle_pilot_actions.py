"""Explicitly injected transport/state fixtures; no fixture is published as personal consent."""
from copy import deepcopy
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import sys
import tempfile
import unittest
from unittest.mock import patch
from jsonschema import ValidationError

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.governance_lifecycle.adapter import json_bytes,strict_json
from lib.governance_lifecycle.contracts import ContractError,canonical_digest
from lib.governance_lifecycle.kernel import transaction_ref
from lib.governance_lifecycle.live_admission import load_operating
from lib.governance_lifecycle.live_preparation import validate_preparation,revision_ref
from lib.governance_lifecycle.personal_probe import statement_body,collect_bound
from lib.governance_lifecycle.pilot_actions import (
    ACTION_LEDGER,assess_action_comments,prepare_action,prior_statements,replay_actions,state_at,
    validate_context,verify_new_actions,append_action_snapshot,project_actions,
)
from lib.governance_lifecycle.store import load_transactions


def at(n):return f'2026-09-13T15:{n//60:02d}:{n%60:02d}Z'


class PilotActionTests(unittest.TestCase):
    def setUp(self):
        self.profile=load_operating();self.binding=validate_preparation()['binding']
        self.receipts=[];self.actions=[];self.comments={};self.clock=1
        self.receipt('fail',0)

    def receipt(self,result,second):
        record={'sequence':len(self.receipts)+1,'recorded_at':at(second),'outcome':'eligible_for_pilot',
            'criterion':{'status':result},'source':{'observed_at':at(second)}}
        record['transaction_id']='transaction:'+canonical_digest(record)
        self.receipts.append(record);return record

    def request(self,body):
        n=self.clock;self.clock+=3
        kind=body['kind'];role='closure_approver' if kind=='closure' else 'role_registry_owner' if kind=='role_withdrawal' else 'remediation_decider'
        if kind=='withdrawal':
            target=next(a for a in self.actions if transaction_ref(a)==body['target_ref']);role=target['request']['required_role']
        return {'schema_version':'0.1.0','request_type':'lifecycle-pilot-action','environment':'live_pilot_validation',
            'repository_id':self.profile['scope']['repository_id'],'scope':self.profile['scope'],
            'operating_profile_ref':revision_ref(self.profile),'role_binding_ref':revision_ref(self.binding),
            'created_at':at(n),'discussion_number':900000+n,'required_role':role,'required_subject_id':'github-user:81616324',
            'expected_receipt_head':transaction_ref(self.receipts[-1]),'expected_action_head':transaction_ref(self.actions[-1]) if self.actions else None,
            'expected_revision':len(self.receipts)+len(self.actions),'body':body}

    def decision(self):
        state=state_at(self.receipts,self.actions)
        return self.request({'kind':'decision','failure_ref':transaction_ref([r for r in self.receipts if r['criterion']['status']=='fail'][-1]),
            'supersedes_ref':transaction_ref(state['decision']) if state['decision'] else None,
            'plan':{'action':'Restore required review through the governed settings process','owner_id':'github-user:81616324',
                'target_at':'2026-09-14T15:00:00Z','work_url':'https://github.com/joku-dev/devsecops-governance-framework/issues/900000'}})

    def fetch(self,endpoint,*,raw=False):
        number=int(endpoint.split('/issues/')[1].split('/')[0]);request,comments=self.comments[number]
        if '/comments?' in endpoint:return json_bytes(comments)
        return json_bytes({'number':number,'html_url':f"https://github.com/{request['repository_id']}/pull/{number}",'pull_request':{'url':'synthetic transport fixture'}})

    def snapshot(self,request,disposition='approve',previous=None,issued=None):
        number=request['discussion_number'];comments=self.comments.setdefault(number,(request,[]))[1]
        when=issued or at(int(request['created_at'][14:16])*60+int(request['created_at'][17:19])+1)
        comment_id=100000+sum(len(v[1]) for v in self.comments.values())
        comments.append({'id':comment_id,'body':statement_body(request,disposition=disposition,supersedes_comment_id=previous),
            'user':{'id':81616324,'type':'User'},'performed_via_github_app':None,
            'issue_url':f"https://api.github.com/repos/{request['repository_id']}/issues/{number}",
            'html_url':f"https://github.com/{request['repository_id']}/pull/{number}#issuecomment-{comment_id}",
            'created_at':when,'updated_at':when})
        snapshot=collect_bound(request,assessor=assess_action_comments,previous_comments=prior_statements(self.actions,request),fetch=self.fetch,captured_at=when)
        if getattr(self,'claim_provider',False):snapshot['capture_method']='github_api_get_via_gh'
        return snapshot

    def append(self,request,**kwargs):
        snapshot=self.snapshot(request,**kwargs)
        action=prepare_action(snapshot,self.profile,self.binding,self.receipts,self.actions,
            recorded_at=snapshot['result']['captured_at'],expected_sequence=len(self.actions))
        if action:self.actions.append(action)
        return action

    def completed(self):
        decision=self.append(self.decision())
        for progress in ('in_progress','completed'):
            self.append(self.request({'kind':'progress','decision_ref':transaction_ref(decision),'progress':progress,'evidence_note':'Explicitly synthetic work progress attestation'}))
        return decision,self.actions[-1]

    def closed(self):
        decision,progress=self.completed();self.receipt('pass',self.clock);self.clock+=1
        closure=self.append(self.request({'kind':'closure','decision_ref':transaction_ref(decision),
            'progress_ref':transaction_ref(progress),'passing_ref':transaction_ref(self.receipts[-1])}))
        return decision,closure

    def test_decision_progress_pass_and_closure_require_exact_bound_chain(self):
        decision,closure=self.closed();state=state_at(self.receipts,self.actions)
        self.assertEqual(state['closure'],closure)
        self.assertFalse(closure['official_state']);self.assertFalse(closure['live_activation_approved'])
        # Receipt provenance is tested by the real receipt suite. Here the injected
        # state fixtures isolate action replay and never claim provider authenticity.
        with patch('lib.governance_lifecycle.pilot_actions.replay_receipts',side_effect=lambda r,p:r):
            self.assertEqual(replay_actions(self.receipts,self.actions,self.profile,self.binding),self.actions)
            altered=deepcopy(self.actions);altered[-1]['request']['body']['decision_ref']['digest']='0'*64
            with self.assertRaises(ContractError):replay_actions(self.receipts,altered,self.profile,self.binding)

    def test_actual_retained_pass_has_no_finding_or_actions(self):
        from generate_lifecycle_pilot_actions import validate
        index=validate()
        self.assertEqual(index,project_actions())
        self.assertFalse(index['official_state'])

    def test_pass_alone_cannot_create_a_decision(self):
        self.receipts[0]['criterion']['status']='pass'
        request=self.request({'kind':'decision','failure_ref':transaction_ref(self.receipts[0]),'supersedes_ref':None,
            'plan':{'action':'No failure exists','owner_id':'github-user:81616324','target_at':at(100),'work_url':'https://github.com/joku-dev/devsecops-governance-framework/issues/900000'}})
        with self.assertRaisesRegex(ContractError,'real eligible failure'):self.append(request)

    def test_role_scope_digest_and_stale_revision_are_enforced(self):
        original=self.decision()
        for mutate in (lambda r:r.update(required_role='closure_approver'),lambda r:r.update(required_subject_id='github-user:42'),
                       lambda r:r.update(expected_revision=999),lambda r:r['role_binding_ref'].update(digest='0'*64),
                       lambda r:r['expected_receipt_head'].update(digest='0'*64)):
            request=deepcopy(original);mutate(request)
            with self.assertRaises(ContractError):validate_context(request,self.profile,self.binding,self.receipts,[],at=at(5))
        changed=deepcopy(original);changed['scope']['repository_id']='other/repo'
        with self.assertRaises(ValidationError):validate_context(changed,self.profile,self.binding,self.receipts,[],at=at(5))

    def test_probe_consent_cannot_be_reused_for_action(self):
        probe=strict_json((ROOT/'generated/reports/lifecycle-personal-channel/00000001.json').read_bytes())
        with self.assertRaises(ValidationError):
            prepare_action(probe,self.profile,self.binding,self.receipts,[],recorded_at=at(5),expected_sequence=0)
        request=self.decision();result=assess_action_comments(request,probe['result']['relevant_comments'],captured_at=at(5))
        self.assertEqual(result['status'],'waiting_for_personal_statement')

    def test_changed_plan_after_statement_cannot_inherit_consent(self):
        request=self.decision();snapshot=self.snapshot(request)
        changed=deepcopy(snapshot);changed['request']['body']['plan']['action']='A different action'
        with self.assertRaisesRegex(ContractError,'projection differs'):
            prepare_action(changed,self.profile,self.binding,self.receipts,[],recorded_at=at(5),expected_sequence=0)

    def test_revocation_after_closure_reopens_without_erasing_history(self):
        decision,closure=self.closed();last=decision['snapshot']['result']['last_statement_id']
        revoked=self.append(decision['request'],disposition='revoke',previous=last,issued=at(self.clock+1))
        self.assertEqual(revoked['outcome'],'withdrawn');self.assertIsNone(state_at(self.receipts,self.actions)['closure'])
        self.assertIn(closure,self.actions)
        self.assertIsNone(prepare_action(revoked['snapshot'],self.profile,self.binding,self.receipts,self.actions,
            recorded_at=at(200),expected_sequence=999))

    def test_progress_withdrawal_after_closure_invalidates_closure(self):
        self.closed();progress=self.actions[2]
        self.append(progress['request'],disposition='revoke',previous=progress['snapshot']['result']['last_statement_id'],issued=at(self.clock+1))
        self.assertIsNone(state_at(self.receipts,self.actions)['closure'])

    def test_explicit_closure_withdrawal_and_role_withdrawal(self):
        decision,closure=self.closed()
        self.append(self.request({'kind':'withdrawal','target_ref':transaction_ref(closure),'reason':'Correction required'}))
        self.assertIsNone(state_at(self.receipts,self.actions)['closure'])
        self.append(self.request({'kind':'role_withdrawal','reason':'Pilot appointments withdrawn'}))
        self.assertFalse(state_at(self.receipts,self.actions)['roles_active'])
        with self.assertRaisesRegex(ContractError,'roles have been withdrawn'):self.append(self.decision())

    def test_new_failure_reopens_but_old_failure_does_not(self):
        self.closed();closed_state=state_at(self.receipts,self.actions)
        late=self.receipt('fail',self.clock+1);late['source']['observed_at']=at(0)
        self.assertEqual(state_at(self.receipts,self.actions)['closure'],closed_state['closure'])
        late['source']['observed_at']=at(self.clock+1)
        self.assertTrue(state_at(self.receipts,self.actions)['reopened'])
        self.assertIsNone(state_at(self.receipts,self.actions)['decision'])

    def test_stale_evidence_and_quarantine_prevent_grants(self):
        request=self.decision()
        with self.assertRaisesRegex(ContractError,'stale or future'):
            validate_context(request,self.profile,self.binding,self.receipts,[],at='2026-09-15T15:00:00Z')
        self.receipts[0]['outcome']='quarantined';request['expected_receipt_head']=transaction_ref(self.receipts[0])
        with self.assertRaisesRegex(ContractError,'Unresolved evidence conflict'):self.append(request)

    def test_completed_work_without_new_pass_cannot_close(self):
        decision,progress=self.completed()
        request=self.request({'kind':'closure','decision_ref':transaction_ref(decision),'progress_ref':transaction_ref(progress),'passing_ref':transaction_ref(self.receipts[-1])})
        with self.assertRaisesRegex(ContractError,'latest eligible PASS'):self.append(request)

    def test_deleted_original_comment_is_retained_as_clarification_and_withdraws_authority(self):
        decision=self.append(self.decision());request=decision['request']
        self.comments[request['discussion_number']][1].clear()
        snapshot=collect_bound(request,assessor=assess_action_comments,previous_comments=prior_statements(self.actions,request),fetch=self.fetch,captured_at=at(10))
        action=prepare_action(snapshot,self.profile,self.binding,self.receipts,self.actions,recorded_at=at(10),expected_sequence=1)
        self.actions.append(action)
        self.assertEqual(action['outcome'],'needs_clarification')
        self.assertIsNone(state_at(self.receipts,self.actions)['decision'])

    def test_concurrent_appends_cannot_share_a_sequence(self):
        request=self.decision();one=self.snapshot(request)
        other=deepcopy(request);other['discussion_number']+=1;other['body']['plan']['action']='Competing plan';two=self.snapshot(other)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            def context(repo):return self.profile,self.binding,self.receipts,load_transactions(root/ACTION_LEDGER)
            def append(snapshot):
                try:return append_action_snapshot(root,snapshot,recorded_at=at(5),expected_sequence=0)['outcome']
                except ContractError:return 'rejected'
            with patch('lib.governance_lifecycle.pilot_actions.load_context',side_effect=context):
                with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(append,[one,two]))
            self.assertEqual(sorted(outcomes),['eligible_for_pilot','rejected'])
            self.assertEqual(len(load_transactions(root/ACTION_LEDGER)),1)

    def test_provider_recheck_rejects_modified_consent_and_withdrawn_dependency(self):
        self.claim_provider=True  # An asserted transport label is independently checked against the injected API.
        decision=self.append(self.decision())
        self.append(self.request({'kind':'progress','decision_ref':transaction_ref(decision),'progress':'in_progress','evidence_note':'Synthetic fixture'}))
        old_name=f"{ACTION_LEDGER}/transactions/00000001-{decision['transaction_id'].split(':')[1]}.json\n"
        with patch('lib.governance_lifecycle.pilot_actions.load_context',return_value=(self.profile,self.binding,self.receipts,self.actions)), \
             patch('lib.governance_lifecycle.pilot_actions.subprocess.check_output',return_value=old_name):
            self.assertEqual(verify_new_actions(ROOT,'fixture-base',fetch=self.fetch,checked_at=at(50)),1)
            self.comments[decision['request']['discussion_number']][1][0]['body']='Deleted personal approval'
            with self.assertRaisesRegex(ContractError,'prerequisite was changed or withdrawn'):
                verify_new_actions(ROOT,'fixture-base',fetch=self.fetch,checked_at=at(50))


if __name__=='__main__':unittest.main()
