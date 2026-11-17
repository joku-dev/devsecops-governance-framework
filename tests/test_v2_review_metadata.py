"""Whole original V1 metadata wires and immutable private replay; no real agent run."""
from copy import deepcopy
from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib import review_metadata as logic
from lib.review_metadata_application import ReviewMetadataContext,render,run,FLAGS
from lib.portable.contracts import canonical_digest
from lib.provider_ports import review_event

spec=importlib.util.spec_from_file_location('original_review_metadata',ROOT/'tests/acceptance/v1_review_metadata_oracle.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
FIXTURES=ROOT/'tests/fixtures/v2-review-metadata';AT='2026-11-17T12:30:00Z'


def raw(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()


class ReviewMetadata(unittest.TestCase):
    def setUp(self):
        self.contract,self.old=oracle.load(FIXTURES);self.schema=json.loads((FIXTURES/'receipt-schema.json').read_text())
        self.receipt=oracle.receipt(self.old);self.subject=oracle.subject()
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name).resolve()
        (self.base/'instance').mkdir(mode=0o700)
        self.app=ReviewMetadataContext(self.base/'instance',{'node_id':'synthetic-review-node'})

    def test_receipt_block_matches_complete_original_ascii_json_wire(self):
        for eligible,kind in [(True,'role_lens'),(True,'human'),(False,'subagent')]:
            with self.subTest(eligible=eligible,kind=kind):
                value=oracle.receipt(self.old,eligible=eligible,kind=kind)
                value['changed_paths']=['docs/Prüfung.md'];oracle.seal(value,self.old)
                expected=(self.old['receipt_block'](value)+'\n').encode()
                self.assertEqual(render('receipt',{'receipt.json':raw(value)},None),{'review-receipt.md':expected})

    def test_original_new_format_summary_counts_declarations_only(self):
        for rows in [[],[self.receipt],[self.receipt,oracle.receipt(self.old,identity='second',eligible=False,kind='human')]]:
            with self.subTest(rows=len(rows)):
                data=b'\n'+b'\n'.join(json.dumps(v,ensure_ascii=False).encode() for v in rows)+b'\n'
                expected=(json.dumps(self.old['summarize_review_usage'](rows),indent=2)+'\n').encode()
                self.assertEqual(render('usage-summary',{'usage.jsonl':data},None),{'review-usage-summary.json':expected})

    def test_declared_scope_status_matches_all_complete_original_json_and_markdown(self):
        changes=[('missing',''),('valid',self.old['receipt_block'](self.receipt)),
                 ('incomplete',self.old['receipt_block'](oracle.receipt(self.old,eligible=False))),
                 ('invalid','<!-- agent-review-receipt:start -->\n```json\n{bad}\n```\n<!-- agent-review-receipt:end -->'),
                 ('duplicate-block',self.old['receipt_block'](self.receipt)*2)]
        stale=deepcopy(self.receipt);stale['head_commit']='d'*40;oracle.seal(stale,self.old)
        changes.append(('stale-head',self.old['receipt_block'](stale)))
        for name,body in changes:
            with self.subTest(case=name):
                event=oracle.event(body,self.subject);expected=self.old['status_with_declared_inputs'](event,self.subject)
                actual=render('status',{'event.json':raw(event),'subject.json':raw(self.subject)},'legacy-pr-review-event-v1')
                self.assertEqual(actual['review-status.json'],(json.dumps(expected,indent=2)+'\n').encode())
                self.assertEqual(actual['review-status.md'],self.old['render_status'](expected).encode())

    def test_target_and_proposed_role_union_still_marks_old_receipt_stale(self):
        scope=deepcopy(self.subject);scope['target']['roles'].insert(0,'governance-analyst');scope['target']['validations'].append('explicit declaration')
        event=oracle.event(self.old['receipt_block'](self.receipt),scope)
        expected=self.old['status_with_declared_inputs'](event,scope)
        result=render('status',{'event.json':raw(event),'subject.json':raw(scope)},'legacy-pr-review-event-v1')
        self.assertEqual(result['review-status.json'],(json.dumps(expected,indent=2)+'\n').encode())
        self.assertEqual(expected['status'],'stale');self.assertIn('governance-analyst',expected['required_roles'])

    def test_source_time_and_private_input_survive_original_caller_deletion(self):
        source=self.base/'receipt.json';source.write_bytes(raw(self.receipt))
        receipt_id,value=self.app.create('receipt',{'receipt.json':source.read_bytes()},AT);source.unlink()
        inspected=self.app.inspect(receipt_id)
        self.assertTrue(inspected['retained_complete_outputs_reverified'])
        self.assertEqual(inspected['assessed_at'],AT)
        self.assertEqual((Path(value['data_directory'])/'review-receipt.md').read_bytes(),(self.old['receipt_block'](self.receipt)+'\n').encode())
        for key in FLAGS:self.assertIs(inspected[key],False,key)

    def test_modified_and_resealed_output_rejected_by_full_rederivation(self):
        identity,value=self.app.create('receipt',{'receipt.json':raw(self.receipt)},AT)
        artifact=Path(value['data_directory'])/'review-receipt.md';original=artifact.read_bytes();artifact.write_bytes(b'forged')
        with self.assertRaisesRegex(ValueError,'output_changed'):self.app.inspect(identity)
        artifact.write_bytes(original)
        record=self.app.assessments/(identity+'.json');stored=json.loads(record.read_text());stored['files']['review-receipt.md']['sha256']='0'*64
        other=canonical_digest(stored);(self.app.assessments/(other+'.json')).write_text(json.dumps(stored))
        with self.assertRaisesRegex(ValueError,'output_manifest_changed'):self.app.inspect(other)

    def test_input_length_members_and_bytes_are_bound(self):
        identity,value=self.app.create('receipt',{'receipt.json':raw(self.receipt)},AT);root=self.app.inputs/value['input_id'];source=root/'receipt.json';saved=source.read_bytes()
        source.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'input_changed'):self.app.inspect(identity)
        source.write_bytes(saved);extra=root/'extra';extra.write_text('unrelated')
        with self.assertRaisesRegex(ValueError,'input_members'):self.app.inspect(identity)
        extra.unlink();self.assertTrue(self.app.inspect(identity)['retained_complete_outputs_reverified'])

    def test_symlink_input_and_extra_output_member_rejected(self):
        identity,value=self.app.create('receipt',{'receipt.json':raw(self.receipt)},AT);root=self.app.inputs/value['input_id'];p=root/'receipt.json';outside=self.base/'original';p.rename(outside);p.symlink_to(outside)
        with self.assertRaises(ValueError):self.app.inspect(identity)
        p.unlink();outside.rename(p)
        (Path(value['data_directory'])/'extra').write_text('unexpected')
        with self.assertRaisesRegex(ValueError,'output_members'):self.app.inspect(identity)

    def test_other_node_and_authority_flags_rejected_even_if_resealed(self):
        identity,value=self.app.create('receipt',{'receipt.json':raw(self.receipt)},AT)
        stored=json.loads((self.app.assessments/(identity+'.json')).read_text())
        for key in ['node_id',*FLAGS]:
            with self.subTest(key=key):
                changed=deepcopy(stored);changed[key]='other-node' if key=='node_id' else True;other=canonical_digest(changed)
                (self.app.assessments/(other+'.json')).write_text(json.dumps(changed))
                with self.assertRaises(ValueError):self.app.inspect(other)

    def test_original_receipt_integrity_and_schema_guards_remain(self):
        bad=[]
        value=deepcopy(self.receipt);value['receipt_digest']='0'*64;bad.append(value)
        value=deepcopy(self.receipt);value['receipt_id']='0'*64;value['receipt_digest']=self.old['digest']({k:v for k,v in value.items() if k!='receipt_digest'});bad.append(value)
        for key in ['independent_human_approval','unexpected_private_text']:
            value=deepcopy(self.receipt);value[key]=True;value.pop('receipt_digest');value['receipt_digest']=self.old['digest'](value);bad.append(value)
        for value in bad:
            with self.subTest(value=value['receipt_id']):
                with self.assertRaises(Exception):self.old['validate_receipt'](value)
                with self.assertRaises(Exception):render('receipt',{'receipt.json':raw(value)},None)

    def test_duplicate_usage_receipts_and_strict_duplicate_json_keys_reject(self):
        with self.assertRaisesRegex(ValueError,'Duplicate receipt'):render('usage-summary',{'usage.jsonl':(json.dumps(self.receipt)+'\n'+json.dumps(self.receipt)+'\n').encode()},None)
        duplicate=raw(self.receipt).decode().replace('"schema_version": "1.0.0"','"schema_version": "1.0.0", "schema_version": "1.0.0"')
        with self.assertRaisesRegex(ValueError,'duplicate_result_input_key'):render('receipt',{'receipt.json':duplicate.encode()},None)
        with self.assertRaisesRegex(ValueError,'nonfinite'):render('receipt',{'receipt.json':b'{"value":NaN}'},None)

    def test_subject_revision_profile_and_declared_scope_guards(self):
        event=oracle.event('',self.subject)
        for profile in [None,'invented']:
            with self.assertRaises(ValueError):render('status',{'event.json':raw(event),'subject.json':raw(self.subject)},profile)
        changed=deepcopy(self.subject);changed['target_commit']='f'*40
        with self.assertRaisesRegex(ValueError,'revision_mismatch'):render('status',{'event.json':raw(event),'subject.json':raw(changed)},'legacy-pr-review-event-v1')
        changed=deepcopy(self.subject);changed['changed_paths']=['../escape']
        with self.assertRaises(ValueError):render('status',{'event.json':raw(event),'subject.json':raw(changed)},'legacy-pr-review-event-v1')
        changed=deepcopy(self.subject);changed['target']['roles']=[]
        with self.assertRaisesRegex(ValueError,'scope_incomplete'):render('status',{'event.json':raw(event),'subject.json':raw(changed)},'legacy-pr-review-event-v1')

    def test_empty_pr_scope_and_absent_receipt_are_report_only(self):
        scope=deepcopy(self.subject);scope['changed_paths']=[]
        for side in ['target','proposed']:scope[side]={'roles':[],'validations':[]}
        event=oracle.event('',scope);expected=self.old['status_with_declared_inputs'](event,scope)
        actual=render('status',{'event.json':raw(event),'subject.json':raw(scope)},'legacy-pr-review-event-v1')
        self.assertEqual(json.loads(actual['review-status.json']),expected)
        self.assertEqual(render('parse-body',{'description.txt':b'no receipt'},None),{'parsed-review-receipt.json':b'null\n'})

    def test_cli_completed_findings_never_create_an_execution_or_approval_claim(self):
        event=self.base/'event.json';subject=self.base/'subject.json';event.write_bytes(raw(oracle.event('',self.subject)));subject.write_bytes(raw(self.subject));out=io.StringIO()
        (self.base/'cli').mkdir(mode=0o700)
        with redirect_stdout(out):self.assertEqual(run(['status','--event',str(event),'--subject',str(subject),'--event-profile','legacy-pr-review-event-v1','--at',AT],self.base/'cli',{'node_id':'cli-node'}),0)
        value=json.loads(out.getvalue());report=json.loads((Path(value['data_directory'])/'review-status.json').read_text());self.assertEqual(report['status'],'missing')
        self.assertFalse(value['current_revision_checked']);self.assertFalse(value['agent_execution_verified'])

    def test_budget_and_invalid_inputs_create_no_accepted_assessment(self):
        before=set(self.app.assessments.iterdir())
        for kind,files in [('receipt',{'receipt.json':b'{}'}),('parse-body',{'description.txt':b'x'*(1048576+1)}),('usage-summary',{'usage.jsonl':b'not json'})]:
            with self.subTest(kind=kind):
                with self.assertRaises(Exception):self.app.create(kind,files,AT)
        self.assertEqual(set(self.app.assessments.iterdir()),before)

    def test_cli_missing_usage_log_matches_original_empty_summary_without_inventing_file_presence(self):
        root=self.base/'missing-cli';root.mkdir(mode=0o700);out=io.StringIO()
        with redirect_stdout(out):self.assertEqual(run(['usage-summary','--usage-log',str(self.base/'absent.jsonl'),'--at',AT],root,{'node_id':'missing-cli'}),0)
        value=json.loads(out.getvalue());self.assertEqual(value['source_origin'],{'kind':'operator','present':False})
        self.assertEqual((Path(value['data_directory'])/'review-usage-summary.json').read_bytes(),(json.dumps(self.old['summarize_review_usage']([]),indent=2)+'\n').encode())

    def test_capacity_guards_reject_before_persisting_inputs(self):
        from unittest.mock import patch
        before=set(self.app.inputs.iterdir())
        with patch('lib.review_metadata_application.MAX_JSON',8):
            with self.assertRaisesRegex(ValueError,'input_budget'):self.app.create('receipt',{'receipt.json':raw(self.receipt)},AT)
        self.assertEqual(before,set(self.app.inputs.iterdir()))
        with self.assertRaisesRegex(ValueError,'event_budget'):logic.parse_usage((json.dumps(self.receipt)+'\n').encode(),self.schema,max_events=0)

    def test_tampered_profile_operation_and_event_source_do_not_relabel_results(self):
        identity,_=self.app.create('receipt',{'receipt.json':raw(self.receipt)},AT)
        value=json.loads((self.app.assessments/(identity+'.json')).read_text())
        for field,changed_value in [('event_profile','legacy-pr-review-event-v1'),('operation','status')]:
            with self.subTest(field=field):
                changed=deepcopy(value);changed[field]=changed_value;other=canonical_digest(changed)
                (self.app.assessments/(other+'.json')).write_text(json.dumps(changed))
                with self.assertRaises(ValueError):self.app.inspect(other)
        event=oracle.event('',self.subject);event['pull_request']['head']['sha']='not-a-commit'
        with self.assertRaisesRegex(ValueError,'full_review_event_commit'):review_event('legacy-pr-review-event-v1',event)

    def test_receipt_contradictory_readiness_paths_and_duplicate_roles_are_rejected_by_original_rules(self):
        for kind in ['pending-execution','high-findings','noncanonical-path','duplicate-role','duplicate-validation']:
            value=deepcopy(self.receipt)
            if kind=='pending-execution':value['roles'][0].update(status='pending',execution_declared=True);value['eligible_for_human_review']=False
            elif kind=='high-findings':value['finding_counts']['open']['high']=1
            elif kind=='noncanonical-path':value['changed_paths']=['./docs/example.md']
            elif kind=='duplicate-role':value['roles'].insert(0,deepcopy(value['roles'][0]))
            else:value['validations'].append(deepcopy(value['validations'][0]))
            value.pop('receipt_digest');value['receipt_digest']=self.old['digest'](value)
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError):self.old['validate_receipt'](value)
                with self.assertRaises(ValueError):render('receipt',{'receipt.json':raw(value)},None)

    def test_oracle_source_and_schema_bytes_are_bound_to_original_git_not_new_code(self):
        from lib.functional_parity import git_read
        for name in self.contract['source_sha256']:
            path='schemas/agent-review-receipt.schema.json' if name=='receipt-schema.json' else 'scripts/lib/'+name.removesuffix('.txt')
            self.assertEqual((FIXTURES/name).read_bytes(),git_read(ROOT,'show',self.contract['v1_reference']+':'+path))

    def test_fabricated_missing_origin_is_rejected_before_retaining_bytes(self):
        before=set(self.app.inputs.iterdir())
        with self.assertRaisesRegex(ValueError,'origin'):self.app.create('receipt',{'receipt.json':raw(self.receipt)},AT,present=False)
        self.assertEqual(set(self.app.inputs.iterdir()),before)

    def test_product_cli_routes_the_command_through_the_real_application(self):
        from unittest.mock import patch
        import axiom_v2
        root=self.base/'real-cli';root.mkdir(mode=0o700);source=self.base/'real-cli-receipt.json';source.write_bytes(raw(self.receipt));out=io.StringIO()
        with patch('lib.v2_application.instance',return_value=(root,{'node_id':'cli-dispatch-node'})),redirect_stdout(out):
            self.assertEqual(axiom_v2.main(['--instance',str(root),'review-metadata','receipt','--receipt',str(source),'--at',AT]),0)
        value=json.loads(out.getvalue())
        self.assertEqual((Path(value['data_directory'])/'review-receipt.md').read_text(),self.old['receipt_block'](self.receipt)+'\n')
