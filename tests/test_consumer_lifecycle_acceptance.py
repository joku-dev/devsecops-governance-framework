"""Consumer tests inject comments; no operating consent is issued by tests."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.governance_lifecycle.adapter import json_bytes
from lib.governance_lifecycle.contracts import ContractError,timestamp
from lib.governance_lifecycle.personal_probe import statement_body,collect_bound
from lib.governance_lifecycle import consumer_acceptance as op


class ConsumerAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.request=op.request();self.comments=[]
        self.original_projection=op.project_actions
        candidate=op.project_actions();candidate['roles_active']=True
        projection=patch.object(op,'project_actions',return_value=candidate)
        projection.start();self.addCleanup(projection.stop)
        self.at=(timestamp(self.request['created_at'])+timedelta(seconds=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        original_collect=op.collect
        clock=patch.object(op,'collect',side_effect=lambda repo=ROOT,fetch=None,captured_at=None:
            original_collect(repo,fetch=fetch,captured_at=captured_at or self.at))
        clock.start();self.addCleanup(clock.stop)

    def fetch(self,endpoint,*,raw=False):
        if '/comments?' in endpoint:return json_bytes(self.comments)
        if endpoint.endswith('/rules/branches/main'):
            return json_bytes([{'type':'required_status_checks','parameters':{
                'strict_required_status_checks_policy':True,
                'required_status_checks':[{'context':'Consumer Lifecycle Guard','integration_id':15368}]}}])
        return json_bytes({'number':self.request['discussion_number'],'html_url':f"https://github.com/joku-dev/devsecops-governance-framework/pull/{self.request['discussion_number']}",'pull_request':{'url':'injected test fixture'}})

    def add(self,disposition='approve',previous=None):
        number=600000+len(self.comments)
        self.comments.append({'id':number,'body':statement_body(self.request,disposition=disposition,supersedes_comment_id=previous),
            'user':{'id':81616324,'type':'User'},'performed_via_github_app':None,
            'issue_url':f"https://api.github.com/repos/joku-dev/devsecops-governance-framework/issues/{self.request['discussion_number']}",
            'html_url':f"https://github.com/joku-dev/devsecops-governance-framework/pull/{self.request['discussion_number']}#issuecomment-{number}",
            'created_at':self.at,'updated_at':self.at})
        return number

    def snapshot(self,previous=()):
        return collect_bound(self.request,assessor=op.assess,previous_comments=previous,fetch=self.fetch,captured_at=self.at)

    def test_current_repository_remains_inactive_and_template_is_bound(self):
        with patch.object(op,'project_actions',self.original_projection):op.validate()
        with patch.object(op,'captures',return_value=[]):
            index=op.projection()
            self.assertFalse(index['live_activation_approved'])
            self.assertEqual(index['operating_acceptance']['status'],'waiting_for_personal_acceptance')

    def test_personal_acceptance_enables_only_exact_implementation(self):
        self.add();snapshot=self.snapshot()
        with patch.object(op,'captures',return_value=[snapshot]):
            index=op.projection();self.assertTrue(index['live_activation_approved'])
            self.assertEqual(index['enforcement'],'report_only')
            self.assertEqual(index['scope']['repository_id'],'joku-dev/governance-framework-demo-consumer')
            changed=deepcopy(self.request['implementation_manifest']);changed[next(iter(changed))]='0'*64
            with patch.object(op,'manifest',return_value=changed):
                self.assertFalse(op.projection()['live_activation_approved'])
        self.assertFalse(snapshot['result']['remediation_or_closure_authorized'])

    def test_rejection_revocation_or_deleted_comment_disable_operation(self):
        number=self.add();approved=self.snapshot()
        self.add('revoke',number);revoked=self.snapshot(previous=approved['result']['relevant_comments'])
        with patch.object(op,'captures',return_value=[approved,revoked]):self.assertFalse(op.effective()['effective'])
        self.comments=[];deleted=self.snapshot(previous=approved['result']['relevant_comments'])
        self.assertEqual(deleted['result']['status'],'needs_clarification')
        with patch.object(op,'captures',return_value=[approved,deleted]):self.assertFalse(op.effective()['effective'])

    def test_role_withdrawal_disables_effective_operation(self):
        self.add();snapshot=self.snapshot()
        with patch.object(op,'captures',return_value=[snapshot]),patch.object(op,'project_actions',return_value={'roles_active':False}):
            self.assertFalse(op.effective()['effective'])

    def test_provider_recheck_detects_withdrawal_before_new_operation(self):
        self.add();snapshot=self.snapshot()
        with patch.object(op,'captures',return_value=[snapshot]):
            self.assertEqual(op.verify_provider(fetch=self.fetch)['result']['status'],'confirmed')
            self.comments[0]['body']='Removed approval'
            with self.assertRaisesRegex(ContractError,'changed or was withdrawn'):op.verify_provider(fetch=self.fetch)

    def test_active_operation_requires_strict_guard_from_github_actions(self):
        self.add();snapshot=self.snapshot()
        valid=[{'type':'required_status_checks','parameters':{
            'strict_required_status_checks_policy':True,
            'required_status_checks':[{'context':'Consumer Lifecycle Guard','integration_id':15368}]}}]
        wrong_app=deepcopy(valid);wrong_app[0]['parameters']['required_status_checks'][0]['integration_id']=1
        nonstrict=deepcopy(valid);nonstrict[0]['parameters']['strict_required_status_checks_policy']=False
        for rules in ([],wrong_app,nonstrict):
            def fetch(endpoint,*,raw=False):
                return json_bytes(rules) if endpoint.endswith('/rules/branches/main') else self.fetch(endpoint,raw=raw)
            with self.subTest(rules=rules),patch.object(op,'captures',return_value=[snapshot]):
                with self.assertRaisesRegex(ContractError,'strict required'):op.verify_provider(fetch=fetch)

    def test_activation_without_evidence_does_not_claim_observed_health(self):
        self.assertEqual(self.original_projection()['finding_state'],'not_observed')

    def test_channel_probe_or_changed_operating_scope_cannot_authorize_activation(self):
        from lib.governance_lifecycle.adapter import strict_json
        probe=strict_json((ROOT/'generated/reports/lifecycle-personal-channel/00000001.json').read_bytes())
        result=op.assess(self.request,probe['result']['relevant_comments'],captured_at=self.at)
        self.assertEqual(result['status'],'waiting_for_personal_statement')
        self.add();changed=deepcopy(self.request);changed['implementation_manifest'][next(iter(changed['implementation_manifest']))]='0'*64
        self.assertEqual(op.assess(changed,self.comments,captured_at=self.at)['status'],'waiting_for_personal_statement')

    def test_new_capture_is_independently_checked_and_history_is_preserved(self):
        self.add();snapshot=self.snapshot()
        with patch.object(op,'captures',return_value=[snapshot]),patch.object(op.subprocess,'check_output',return_value=''):
            self.assertEqual(op.verify_new_captures(ROOT,'fixture-base',fetch=self.fetch,checked_at=self.at),1)
            self.comments[0]['body']='Altered approval'
            with self.assertRaisesRegex(ContractError,'differs from GitHub'):
                op.verify_new_captures(ROOT,'fixture-base',fetch=self.fetch,checked_at=self.at)
        with patch.object(op,'captures',return_value=[snapshot]),patch.object(op.subprocess,'check_output',return_value=op.CAPTURES+'/00000001.json\n'),patch.object(op,'projection',return_value={'live_activation_approved':False}):
            with patch.object(op,'collect') as forbidden:
                self.assertEqual(op.verify_new_captures(ROOT,'fixture-base'),0);forbidden.assert_not_called()

    def test_runner_stops_before_collecting_evidence_without_acceptance(self):
        import run_consumer_lifecycle as runner
        with patch.object(runner,'verify_provider',side_effect=ContractError('No operating acceptance')),patch.object(runner,'collect_preflight') as forbidden:
            with self.assertRaises(ContractError):runner.run('observe',run_id='123')
            forbidden.assert_not_called()

    def test_inactive_publication_rejects_grants_but_preserves_withdrawal(self):
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory() as temporary,ExitStack() as stack:
            for target in ('lib.governance_lifecycle.consumer_acceptance.check_prefix',
                           'lib.governance_lifecycle.consumer_admission.verify_new_receipts',
                           'lib.governance_lifecycle.consumer_actions.verify_new_actions'):
                stack.enter_context(patch(target))
            stack.enter_context(patch.object(op,'verify_new_captures'))
            stack.enter_context(patch.object(op,'validate',return_value={'live_activation_approved':False}))
            stack.enter_context(patch.object(op.subprocess,'check_output',return_value=''))
            record={'sequence':1,'transaction_id':'transaction:'+'0'*64,'outcome':'eligible_for_pilot','request':{'body':{'kind':'decision'}}}
            stack.enter_context(patch('lib.governance_lifecycle.store.load_transactions',return_value=[record]))
            with self.assertRaisesRegex(ContractError,'Inactive consumer cannot publish an action grant'):
                op.validate_publication(Path(temporary),'fixture-base')
            record['request']['body']['kind']='role_withdrawal'
            self.assertFalse(op.validate_publication(Path(temporary),'fixture-base')['live_activation_approved'])

    def test_capture_loader_rejects_forged_transport_or_missing_history(self):
        self.add();snapshot=self.snapshot()
        with tempfile.TemporaryDirectory() as temporary,patch.object(op,'request',return_value=self.request):
            root=Path(temporary);directory=root/op.CAPTURES;directory.mkdir(parents=True)
            file=directory/'00000001.json';file.write_bytes(json_bytes(snapshot))
            with self.assertRaisesRegex(ContractError,'source or request differs'):op.captures(root)
            snapshot['capture_method']='github_api_get_via_gh';file.write_bytes(json_bytes(snapshot))
            self.assertEqual(len(op.captures(root)),1)
            (directory/'00000002.json').write_bytes(json_bytes(snapshot))
            with self.assertRaisesRegex(ContractError,'loses prior statement history'):op.captures(root)

    def test_manual_workflow_and_dispatched_checks_preserve_publication_gate(self):
        text=(ROOT/'.github/workflows/consumer-lifecycle-update.yml').read_text()
        workflow=yaml.load(text,Loader=yaml.BaseLoader)
        self.assertEqual(set(workflow['on']),{'workflow_dispatch'})
        self.assertEqual(workflow['jobs']['propose']['if'],"github.ref == 'refs/heads/main'")
        self.assertIn('scripts/publish_consumer_lifecycle.py',text)
        self.assertIn('echo "$PWD/.venv-validation/bin" >> "$GITHUB_PATH"',text)
        self.assertNotIn('gh pr merge',text);self.assertNotIn('git push',text)
        checks=(ROOT/'.github/workflows/consumer-lifecycle-guard.yml').read_text()
        self.assertIn('CONSUMER_EVENT" = workflow_dispatch',checks)
        self.assertIn('refs/remotes/origin/main',checks)
        self.assertIn('--verify-provider',checks)
        guard=yaml.load(checks,Loader=yaml.BaseLoader)
        self.assertEqual(guard['on']['workflow_run']['workflows'],['Governance CI'])
        dispatcher=guard['jobs']['dispatch-operational-guard']
        self.assertIn('head_repository.id == github.event.repository.id',dispatcher['if'])
        self.assertIn('[ "$current_sha" = "$GUARD_HEAD_SHA" ]',checks)
        self.assertFalse(any('uses' in step for step in dispatcher['steps']))


if __name__=='__main__':unittest.main()
