"""Personal probe tests separate account identity, explicit attestation and runtime authority."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.governance_lifecycle.adapter import json_bytes, strict_json
from lib.governance_lifecycle.contracts import ContractError
from lib.governance_lifecycle.personal_probe import (
    MARKER, STATEMENT, assess_comments, collect_probe, replay_probe_snapshot, statement_body, validate_request,
)
from generate_personal_channel_probe import REQUEST, validate
from lib.governance_lifecycle.live_admission import VALIDATION_LEDGER
from lib.governance_lifecycle.store import load_transactions
from lib.governance_lifecycle.kernel import transaction_ref

AT='2026-09-13T14:00:00Z'


class PersonalChannelTests(unittest.TestCase):
    def setUp(self):
        self.request=strict_json((ROOT/REQUEST).read_bytes())
        # Keep the probe's original valid ledger prefix as the fixture, even after
        # later real receipts advance the repository's current head.
        history=load_transactions(ROOT/VALIDATION_LEDGER)
        end=next(i for i,t in enumerate(history) if transaction_ref(t)==self.request['receipt_head_ref'])
        self.history=history[:end+1]
        ledger=patch('lib.governance_lifecycle.personal_probe.load_transactions',return_value=self.history)
        ledger.start(); self.addCleanup(ledger.stop)

    def comment(self,id=100,disposition='approve',previous=None):
        return {'id':id,'body':statement_body(self.request,disposition=disposition,supersedes_comment_id=previous),
            'user':{'id':81616324,'type':'User','login':'joku-dev'},'performed_via_github_app':None,
            'issue_url':'https://api.github.com/repos/joku-dev/devsecops-governance-framework/issues/87',
            'html_url':f'https://github.com/joku-dev/devsecops-governance-framework/pull/87#issuecomment-{id}',
            'created_at':f'2026-09-13T13:40:{id-100:02d}Z','updated_at':f'2026-09-13T13:40:{id-100:02d}Z'}

    def assess(self,comments,previous=()):
        return assess_comments(self.request,comments,captured_at=AT,previous_comments=previous)

    def test_checked_request_and_template_are_bound_to_confirmed_state(self):
        self.assertEqual(validate(),self.request)
        validate_request(self.request,ROOT)
        self.assertIn(STATEMENT,statement_body(self.request))
        with patch('lib.governance_lifecycle.personal_probe.load_transactions',return_value=[]):
            with self.assertRaisesRegex(ContractError,'receipt reference'):
                validate_request(self.request,ROOT)

    def test_explicit_personal_statement_confirms_probe_only(self):
        result=self.assess([self.comment()])
        self.assertEqual(result['status'],'confirmed')
        self.assertFalse(result['live_activation_approved'])
        self.assertFalse(result['remediation_or_closure_authorized'])
        self.assertFalse(result['official_state'])
        self.assertEqual(result['human_presence'],'explicitly_self_attested_not_provider_attested')

    def test_github_crlf_is_equivalent_but_raw_comment_edits_remain_visible(self):
        comment=self.comment(); comment['body']=comment['body'].replace('\n','\r\n')
        result=self.assess([comment])
        self.assertEqual(result['status'],'confirmed')
        self.assertEqual(result['relevant_comments'][0]['body'],comment['body'])
        edited=deepcopy(comment); edited['body']=edited['body'].replace('\r\n','\n')
        self.assertEqual(self.assess([edited],previous=[comment])['status'],'needs_clarification')
        wrong=deepcopy(comment); wrong['body']=wrong['body'].replace(STATEMENT,'approved')
        self.assertEqual(self.assess([wrong])['status'],'needs_clarification')

    def test_identity_alone_or_unrelated_approval_is_insufficient(self):
        c=self.comment();c['body']='Approved, please merge'
        self.assertEqual(self.assess([c])['status'],'waiting_for_personal_statement')
        c=self.comment();payload=strict_json(c['body'][len(MARKER):]);payload['statement']='approved'
        c['body']=MARKER+json_bytes(payload).decode()
        self.assertEqual(self.assess([c])['status'],'needs_clarification')
        payload['request_digest']='0'*64;c['body']=MARKER+json_bytes(payload).decode()
        self.assertEqual(self.assess([c])['status'],'waiting_for_personal_statement')

    def test_wrong_account_bot_and_app_cannot_confirm(self):
        for mutate in (lambda c:c['user'].update(id=42),lambda c:c['user'].update(type='Bot'),
                       lambda c:c.update(performed_via_github_app={'id':42}),lambda c:c.pop('performed_via_github_app')):
            c=self.comment();mutate(c);result=self.assess([c])
            self.assertEqual(result['status'],'waiting_for_personal_statement')
            self.assertEqual(result['unauthorized_comment_ids'],[100])

    def test_edited_wrong_discussion_and_future_comments_do_not_confirm(self):
        for mutate in (lambda c:c.update(updated_at='2026-09-13T13:45:00Z'),
                       lambda c:c.update(issue_url='https://api.github.com/repos/other/repo/issues/87'),
                       lambda c:c.update(created_at='2026-09-14T13:40:00Z',updated_at='2026-09-14T13:40:00Z')):
            c=self.comment();mutate(c)
            self.assertEqual(self.assess([c])['status'],'needs_clarification')

    def test_rejection_revocation_and_explicit_reconfirmation_preserve_history(self):
        rejected=self.comment(disposition='reject')
        self.assertEqual(self.assess([rejected])['status'],'rejected')
        approved=self.comment();revoked=self.comment(101,'revoke',100)
        result=self.assess([approved,revoked]);self.assertEqual(result['status'],'revoked')
        renewed=self.comment(102,'approve',101)
        result=self.assess([approved,revoked,renewed])
        self.assertEqual(result['status'],'confirmed');self.assertEqual(len(result['relevant_comments']),3)
        bad=self.comment(101,'revoke',999)
        self.assertEqual(self.assess([approved,bad])['status'],'needs_clarification')

    def test_later_deletion_or_edit_is_detected_from_prior_capture(self):
        approved=self.comment()
        self.assertEqual(self.assess([],previous=[approved])['status'],'needs_clarification')
        changed=deepcopy(approved);changed['body']='removed statement'
        self.assertEqual(self.assess([changed],previous=[approved])['status'],'needs_clarification')

    def test_duplicate_ids_malformed_json_and_unreferenced_reapproval(self):
        approved=self.comment()
        with self.assertRaisesRegex(ContractError,'Duplicate'):
            self.assess([approved,approved])
        malformed=self.comment();malformed['body']=MARKER+'{"request_digest":'
        self.assertEqual(self.assess([malformed])['status'],'needs_clarification')
        self.assertEqual(self.assess([approved,self.comment(101)])['status'],'needs_clarification')

    def fake_fetch(self,comments):
        def fetch(endpoint,*,raw=False):
            root='repos/joku-dev/devsecops-governance-framework/issues/87'
            if endpoint==root:
                return json_bytes({'number':87,'html_url':'https://github.com/joku-dev/devsecops-governance-framework/pull/87','pull_request':{'url':'provider-reference'}})
            self.assertEqual(endpoint,root+'/comments?per_page=100&page=1')
            return json_bytes(comments)
        return fetch

    def test_capture_and_offline_replay_never_authenticate_offline_data_as_live_consent(self):
        snapshot=collect_probe(self.request,repo=ROOT,fetch=self.fake_fetch([self.comment()]),captured_at=AT)
        self.assertEqual(snapshot['capture_method'],'injected_test_transport')
        self.assertEqual(replay_probe_snapshot(snapshot),snapshot['result'])
        changed=deepcopy(snapshot);changed['result']['live_activation_approved']=True
        with self.assertRaisesRegex(ContractError,'projection'):
            replay_probe_snapshot(changed)

    def test_retained_channel_capture_replays_and_provider_disagreement_fails(self):
        from generate_personal_channel_evidence import validate as validate_evidence, verify_new_captures
        captures=validate_evidence(); snapshot=captures[-1]
        with patch('generate_personal_channel_evidence.subprocess.check_output',return_value=''):
            self.assertEqual(verify_new_captures(ROOT,'fixture-base',collector=lambda *a,**k:snapshot),len(captures))
            changed=deepcopy(snapshot);changed['result']['status']='revoked'
            with self.assertRaisesRegex(ContractError,'provider state differs'):
                verify_new_captures(ROOT,'fixture-base',collector=lambda *a,**k:changed)
        with patch('generate_personal_channel_evidence.subprocess.check_output',return_value='generated/reports/lifecycle-personal-channel/00000001.json\n'):
            with patch('generate_personal_channel_evidence.collect_probe') as forbidden:
                self.assertEqual(verify_new_captures(ROOT,'fixture-base',collector=forbidden),0)
                forbidden.assert_not_called()

    def test_provider_race_is_rejected(self):
        calls=0;initial=self.fake_fetch([self.comment()])
        def race(endpoint,*,raw=False):
            nonlocal calls
            if '/comments?' in endpoint:
                calls+=1
                if calls==2:return json_bytes([])
            return initial(endpoint,raw=raw)
        with self.assertRaisesRegex(ContractError,'changed during capture'):
            collect_probe(self.request,repo=ROOT,fetch=race,captured_at=AT)


if __name__=='__main__':unittest.main()
