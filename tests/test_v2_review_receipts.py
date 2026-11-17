"""Real original receipt-file/log effects and whole allowlisted wires; no fake agent execution."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stdout,redirect_stderr
import io
import shutil
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
import threading

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib import review_receipts as logic,review_receipt_files as effects
from lib.review_receipts_application import ReviewReceiptContext
from lib.review_metadata_application import FLAGS
from lib.portable.contracts import canonical_digest
from lib import review_git,review_planning
from lib.provider_ports import review_plan_profile

spec=importlib.util.spec_from_file_location('original_receipt_plan',ROOT/'tests/acceptance/v1_review_planning_oracle.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
spec=importlib.util.spec_from_file_location('original_receipt_functions',ROOT/'tests/acceptance/v1_review_receipts_oracle.py')
receipt_oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(receipt_oracle)
PLANNING=ROOT/'tests/fixtures/v2-review-planning';METADATA=ROOT/'tests/fixtures/v2-review-metadata';DIRECTORY=ROOT/'tests/fixtures/v2-review-receipts';AT='2026-11-17T14:00:00Z';LATER='2026-11-18T14:00:00Z'


class ReceiptEffects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.files=oracle.target_files(PLANNING)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name).resolve();self.repo=self.base/'target'
        self.base_commit=oracle.repository_from_files(self.repo,self.files)
        path=self.repo/'docs/review-example.md';path.write_text('committed branch change\n');path.chmod(0o644)
        oracle.git(self.repo,'add','--all');oracle.git(self.repo,'commit','-qm','reviewed branch change')
        self.original=oracle.OriginalReview(PLANNING,METADATA,self.repo);self.addCleanup(self.original.close)
        self.plan,_,_,_=self.original.prepare(self.base_commit,'Private synthetic receipt review goal');self.results=oracle.declared_results(self.plan)
        self.schema=json.loads((METADATA/'receipt-schema.json').read_text());self.result_schema=json.loads((ROOT/'schemas/axiom-v2-review-results.schema.json').read_text())
        self.old=receipt_oracle.load(self.original,METADATA,DIRECTORY)
        self.new_output=self.base/'new/receipt.json';self.old_output=self.base/'old/receipt.json';self.new_log=self.base/'new/usage.jsonl';self.old_log=self.base/'old/usage.jsonl'
        self.receipt=self.old.build_receipt(self.repo,self.plan,self.results,recorded_at=AT)
        self.instance=self.base/'instance';self.instance.mkdir(mode=0o700);self.app=ReviewReceiptContext(self.instance,{'node_id':'receipt-export-fixture'})
        self.plan_raw=(json.dumps(self.plan,indent=2,sort_keys=True)+'\n').encode();self.results_raw=(json.dumps(self.results,indent=2,sort_keys=True)+'\n').encode()

    def project(self,results=None,at=AT):return logic.build_receipt(self.plan,results or self.results,at,self.schema,self.result_schema)

    def export(self,at=AT,usage=True):return self.app.export(self.repo,self.plan_raw,self.results_raw,self.new_output,self.new_log if usage else None,at,'legacy-role-review-v1')

    def test_original_complete_receipt_projection_and_wire(self):
        self.assertEqual(self.project(),self.receipt)
        self.old.write_receipt(self.repo,self.old_output,self.receipt)
        self.assertEqual(logic.receipt_bytes(self.project()),self.old_output.read_bytes())

    def test_pending_failed_and_high_finding_receipts_preserve_original_readiness(self):
        pending=self.original.review.results_template(self.plan);failed=deepcopy(self.results);failed['reviews'][0]['status']='failed'
        high=deepcopy(self.results);high['reviews'][0]['findings']=[{'severity':'high','path':'docs/review-example.md','issue':'private finding text','status':'open'}]
        for value in (pending,failed,high):
            with self.subTest(status=value['reviews'][0]['status']):
                receipt=self.project(value);self.assertEqual(receipt,self.old.build_receipt(self.repo,self.plan,value,recorded_at=AT));self.assertFalse(receipt['eligible_for_human_review'])

    def test_explicit_and_baseless_scope_do_not_export(self):
        for changes in ({'selection_mode':'explicit_paths'},{'base_commit':None}):
            plan={**self.plan,**changes}
            with self.assertRaises(ValueError):logic.build_receipt(plan,self.results,AT,self.schema,self.result_schema)
            with self.assertRaises(ValueError):self.old.build_receipt(self.repo,plan,self.results,recorded_at=AT)

    def test_first_export_and_usage_append_match_original_complete_file_bytes(self):
        selected,before,after,created,path=effects.write_receipt(self.new_output,self.receipt,self.schema,[self.repo,ROOT])
        old=self.old.write_receipt(self.repo,self.old_output,self.receipt);self.assertEqual(selected,old);self.assertIsNone(before);self.assertTrue(created)
        self.assertEqual(after,self.old_output.read_bytes());self.assertEqual(path.read_bytes(),after)
        before,after,appended,path=effects.append_usage(self.new_log,selected,self.schema,[self.repo,ROOT]);self.assertIsNone(before)
        self.assertEqual(appended,self.old.append_review_usage(self.repo,self.old_log,old));self.assertEqual(after,self.old_log.read_bytes());self.assertEqual(path.read_bytes(),after)

    def test_retry_preserves_first_time_receipt_and_one_log_event(self):
        for at in (AT,LATER):
            candidate=self.project(at=at);selected,_,_,_,_=effects.write_receipt(self.new_output,candidate,self.schema,[self.repo,ROOT]);old=self.old.write_receipt(self.repo,self.old_output,candidate)
            self.assertEqual(selected,old);self.assertEqual(selected['recorded_at'],AT)
            _,_,appended,_=effects.append_usage(self.new_log,selected,self.schema,[self.repo,ROOT]);self.assertEqual(appended,self.old.append_review_usage(self.repo,self.old_log,old))
            self.assertEqual(self.new_output.read_bytes(),self.old_output.read_bytes());self.assertEqual(self.new_log.read_bytes(),self.old_log.read_bytes())
        self.assertEqual(len(logic.parse_usage(self.new_log.read_bytes(),self.schema)),1)

    def test_different_explicit_output_preserves_existing_log_event(self):
        effects.append_usage(self.new_log,self.receipt,self.schema,[self.repo,ROOT]);self.old.append_review_usage(self.repo,self.old_log,self.receipt)
        later=self.project(at=LATER);selected,_,_,_,_=effects.write_receipt(self.new_output,later,self.schema,[self.repo,ROOT]);self.assertEqual(selected['recorded_at'],LATER)
        before=self.new_log.read_bytes();_,after,appended,_=effects.append_usage(self.new_log,selected,self.schema,[self.repo,ROOT]);self.assertFalse(appended);self.assertEqual(after,before)
        self.assertFalse(self.old.append_review_usage(self.repo,self.old_log,selected));self.assertEqual(after,self.old_log.read_bytes())

    def test_conflicting_review_never_overwrites_existing_receipt(self):
        effects.write_receipt(self.new_output,self.receipt,self.schema,[self.repo,ROOT]);self.old.write_receipt(self.repo,self.old_output,self.receipt)
        other=deepcopy(self.results);other['reviews'][0]['summary']='another private result';candidate=self.project(other);before=self.new_output.read_bytes()
        with self.assertRaisesRegex(ValueError,'different_review'):effects.write_receipt(self.new_output,candidate,self.schema,[self.repo,ROOT])
        with self.assertRaises(ValueError):self.old.write_receipt(self.repo,self.old_output,candidate)
        self.assertEqual(self.new_output.read_bytes(),before)

    def test_existing_receipt_format_and_mode_are_preserved(self):
        self.new_output.parent.mkdir();self.new_output.write_text(json.dumps(self.receipt)+'\n');self.new_output.chmod(0o644);before=self.new_output.read_bytes()
        selected,raw,after,created,_=effects.write_receipt(self.new_output,self.project(at=LATER),self.schema,[self.repo,ROOT])
        self.assertEqual(raw,before);self.assertEqual(after,before);self.assertFalse(created);self.assertEqual(self.new_output.stat().st_mode&0o777,0o644)

    def test_legacy_duplicate_and_malformed_logs_are_unchanged_on_error(self):
        self.new_log.parent.mkdir()
        for raw in (b'{"selected_agents":[]}\n',(json.dumps(self.receipt)+'\n').encode()*2,b'not JSON\n'):
            self.new_log.write_bytes(raw)
            with self.assertRaises(Exception):effects.append_usage(self.new_log,self.receipt,self.schema,[self.repo,ROOT])
            self.assertEqual(self.new_log.read_bytes(),raw);self.assertFalse(self.new_log.with_name(self.new_log.name+'.lock').exists())

    def test_lock_is_not_removed_or_bypassed(self):
        self.new_log.parent.mkdir();lock=self.new_log.with_name(self.new_log.name+'.lock');lock.write_text('another exporter')
        with self.assertRaisesRegex(ValueError,'locked'):effects.append_usage(self.new_log,self.receipt,self.schema,[self.repo,ROOT])
        self.assertEqual(lock.read_text(),'another exporter');self.assertFalse(self.new_log.exists())

    def test_new_file_modes_and_private_created_directories(self):
        path=self.base/'several/new/private/receipt.json';effects.write_receipt(path,self.receipt,self.schema,[self.repo,ROOT])
        self.assertEqual(path.stat().st_mode&0o777,0o600)
        for parent in (path.parent,path.parent.parent,path.parent.parent.parent):self.assertEqual(parent.stat().st_mode&0o777,0o700)

    def test_checkout_symlink_and_directory_destinations_reject(self):
        with self.assertRaises(ValueError):effects.write_receipt(self.repo/'receipt.json',self.receipt,self.schema,[self.repo,ROOT])
        self.new_output.parent.mkdir();self.new_output.symlink_to(self.base/'outside')
        with self.assertRaisesRegex(ValueError,'symlink'):effects.write_receipt(self.new_output,self.receipt,self.schema,[self.repo,ROOT])
        with self.assertRaisesRegex(ValueError,'regular_file'):effects.write_receipt(self.new_output.parent,self.receipt,self.schema,[self.repo,ROOT])

    def test_summary_and_private_field_exclusion_match_original(self):
        text=json.dumps(self.receipt);self.assertNotIn('Private synthetic receipt review goal',text);self.assertNotIn('synthetic declared output',text);self.assertNotIn('synthetic fixture',text)
        raw=(json.dumps(self.receipt)+'\n').encode();self.assertEqual(logic.usage_summary(raw,self.schema),self.old.summarize_review_usage([self.receipt]))
        self.assertEqual(logic.usage_summary(b'',self.schema),self.old.summarize_review_usage([]))

    def test_unterminated_existing_log_preserves_prefix_and_separates_new_event(self):
        self.new_log.parent.mkdir();raw=json.dumps(self.receipt).encode();self.new_log.write_bytes(raw)
        _,after,appended,_=effects.append_usage(self.new_log,self.receipt,self.schema,[self.repo,ROOT]);self.assertFalse(appended);self.assertEqual(after,raw)
        other=deepcopy(self.results);other['reviews'][0]['summary']='different result';receipt=self.project(other)
        before,after,appended,_=effects.append_usage(self.new_log,receipt,self.schema,[self.repo,ROOT]);self.assertEqual(before,raw);self.assertTrue(appended)
        self.assertEqual(after,raw+b'\n'+(json.dumps(receipt,sort_keys=True)+'\n').encode());self.assertEqual(len(self.old.load_review_usage(self.new_log)),2)

    def test_application_actual_export_and_summary_complete_original_wires(self):
        plan_file=self.base/'plan.json';results_file=self.base/'results.json';plan_file.write_bytes(self.plan_raw);results_file.write_bytes(self.results_raw);stdout=io.StringIO()
        with redirect_stdout(stdout):self.assertEqual(self.old.main(['--plan',plan_file,'--results',results_file,'--output',self.old_output,'--usage-log',self.old_log],recorded_at=AT),0)
        value=self.export()
        self.assertTrue(value['target_current_state_rechecked']);self.assertTrue(value['external_files_rechecked']);self.assertTrue(value['receipt_created']);self.assertTrue(value['usage_appended'])
        self.assertEqual(self.new_output.read_bytes(),self.old_output.read_bytes());self.assertEqual(self.new_log.read_bytes(),self.old_log.read_bytes())
        directory=Path(value['data_directory']);self.assertEqual((directory/'review-receipt.json').read_bytes(),self.old_output.read_bytes())
        self.assertEqual((directory/'review-export-result.json').read_text(),stdout.getvalue())
        stdout=io.StringIO()
        with redirect_stdout(stdout):self.assertEqual(self.old.main(['--summary','--usage-log',self.old_log],recorded_at=AT),0)
        summary=self.app.summary(self.new_log,AT);self.assertEqual((Path(summary['data_directory'])/'review-usage-summary.json').read_text(),stdout.getvalue())

    def test_application_retries_preserve_receipt_first_time_and_one_usage_snapshot(self):
        first=self.export();second=self.export(LATER);self.assertTrue(first['receipt_created']);self.assertFalse(second['receipt_created']);self.assertFalse(second['usage_appended'])
        self.assertEqual(json.loads(self.new_output.read_bytes())['recorded_at'],AT);self.assertEqual(len(self.old.load_review_usage(self.new_log)),1)
        self.assertNotEqual(first['assessment_id'],second['assessment_id']);self.assertEqual(first['receipt_id'],second['receipt_id'])

    def test_application_export_without_usage_does_not_create_log(self):
        value=self.export(usage=False);self.assertFalse(value['usage_appended']);self.assertFalse(self.new_log.exists());self.assertTrue(value['receipt_file_exported'])

    def test_application_incomplete_results_can_export_original_readiness_false(self):
        pending=self.original.review.results_template(self.plan);self.results_raw=(json.dumps(pending)+'\n').encode()
        value=self.export();self.assertFalse(value['declared_ready']);self.assertEqual(json.loads(self.new_output.read_bytes()),self.old.build_receipt(self.repo,self.plan,pending,recorded_at=AT))

    def test_application_real_product_cli_node_plan_route(self):
        import axiom_v2
        policy=review_plan_profile('legacy-role-review-v1');facts,raw=review_git.capture(self.repo,self.base_commit,[],policy)
        prepared=self.app.planning.create('prepare','legacy-role-review-v1',facts,raw,self.plan['user_goal'],AT)
        source=self.base/'results.json';source.write_bytes(self.results_raw);out=io.StringIO()
        with patch('lib.v2_application.instance',return_value=(self.instance,{'node_id':'receipt-export-fixture'})),redirect_stdout(out):
            code=axiom_v2.main(['--instance',str(self.instance),'review-receipts','export','--repo',str(self.repo),'--plan',prepared['assessment_id'],'--results',str(source),'--output',str(self.new_output),'--usage-log',str(self.new_log),'--profile','legacy-role-review-v1','--at',AT])
        self.assertEqual(code,0);value=json.loads(out.getvalue());self.assertTrue(value['receipt_file_exported']);self.assertEqual(self.new_output.read_bytes(),logic.receipt_bytes(self.receipt))

    def test_application_offline_replay_after_target_and_all_caller_files_disappear(self):
        value=self.export();self.new_output.unlink();self.new_log.unlink();shutil.rmtree(self.repo)
        inspected=self.app.inspect(value['assessment_id']);self.assertTrue(inspected['retained_complete_outputs_reverified']);self.assertFalse(inspected['target_current_state_rechecked']);self.assertFalse(inspected['external_files_rechecked'])
        self.assertEqual((Path(inspected['data_directory'])/'review-receipt.json').read_bytes(),logic.receipt_bytes(self.receipt))
        for key in FLAGS:self.assertIs(inspected[key],False)

    def test_application_missing_summary_retains_absence_and_empty_original_report(self):
        value=self.app.summary(self.base/'missing.jsonl',AT);manifest,files=self.app.input_data(value['input_id'])
        self.assertEqual(manifest['presence_before'],{'usage':False});self.assertEqual(files,{'usage.jsonl':b''})
        self.assertEqual((Path(value['data_directory'])/'review-usage-summary.json').read_text(),json.dumps(self.old.summarize_review_usage([]),indent=2)+'\n')

    def test_application_stale_head_dirty_worktree_and_untracked_files_do_not_export(self):
        target=self.repo/'docs/review-example.md';saved=target.read_bytes()
        for kind in ('dirty','untracked','head'):
            with self.subTest(kind=kind):
                if kind=='dirty':target.write_text('uncommitted\n')
                elif kind=='untracked':(self.repo/'untracked').write_text('untracked\n')
                else:target.write_text('committed advance\n');oracle.git(self.repo,'add','--all');oracle.git(self.repo,'commit','-qm','advance')
                with self.assertRaises(ValueError):self.export()
                self.assertFalse(self.new_output.exists());self.assertFalse(self.new_log.exists());self.assertEqual(list(self.app.assessments.iterdir()),[])
                if kind=='dirty':target.write_bytes(saved)
                if kind=='untracked':(self.repo/'untracked').unlink()

    def test_application_partial_receipt_when_usage_locked_retries_without_overwrite(self):
        self.new_log.parent.mkdir();lock=self.new_log.with_name(self.new_log.name+'.lock');lock.write_text('live exporter')
        with self.assertRaisesRegex(ValueError,'locked'):self.export()
        self.assertEqual(self.new_output.read_bytes(),logic.receipt_bytes(self.receipt));self.assertEqual(list(self.app.assessments.iterdir()),[])
        lock.unlink();value=self.export(LATER);self.assertFalse(value['receipt_created']);self.assertTrue(value['usage_appended']);self.assertEqual(json.loads(self.new_output.read_bytes())['recorded_at'],AT)

    def test_application_private_artifact_input_and_resealed_authority_reject(self):
        value=self.export();artifact=Path(value['data_directory'])/'review-receipt.json';saved=artifact.read_bytes();artifact.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'output_changed'):self.app.inspect(value['assessment_id'])
        artifact.write_bytes(saved);root=self.app.inputs/value['input_id'];source=root/'results.json';saved=source.read_bytes();source.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'input_changed'):self.app.inspect(value['assessment_id'])
        source.write_bytes(saved);record=json.loads((self.app.assessments/(value['assessment_id']+'.json')).read_text())
        for key in ['node_id',*FLAGS,'receipt_created']:
            changed=deepcopy(record);changed[key]='foreign-node' if key=='node_id' else not changed[key];other=canonical_digest(changed);(self.app.assessments/(other+'.json')).write_text(json.dumps(changed))
            with self.subTest(key=key):
                with self.assertRaises(ValueError):self.app.inspect(other)

    def test_application_summary_cannot_be_relabelled_as_external_export(self):
        value=self.app.summary(self.base/'missing.jsonl',AT);record=json.loads((self.app.assessments/(value['assessment_id']+'.json')).read_text());record['receipt_file_exported']=True
        other=canonical_digest(record);(self.app.assessments/(other+'.json')).write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'output_manifest_changed'):self.app.inspect(other)

    def test_product_cli_schema_error_omits_private_input_for_export_and_check(self):
        import axiom_v2
        policy=review_plan_profile('legacy-role-review-v1');facts,raw=review_git.capture(self.repo,self.base_commit,[],policy)
        prepared=self.app.planning.create('prepare','legacy-role-review-v1',facts,raw,self.plan['user_goal'],AT)
        plan_file=self.base/'plan.json';plan_file.write_bytes(self.plan_raw);bad=self.base/'bad-results.json';bad.write_text('{"private_review_text":"DO_NOT_DISCLOSE_REVIEW_TEXT"}')
        for arguments in [
            ['review-receipts','export','--repo',str(self.repo),'--plan-file',str(plan_file),'--results',str(bad),'--output',str(self.new_output),'--profile','legacy-role-review-v1','--at',AT],
            ['review-plan','check','--repo',str(self.repo),'--plan',prepared['assessment_id'],'--results',str(bad),'--at',AT]]:
            out=io.StringIO();error=io.StringIO()
            with patch('lib.v2_application.instance',return_value=(self.instance,{'node_id':'receipt-export-fixture'})),redirect_stdout(out),redirect_stderr(error):code=axiom_v2.main(['--instance',str(self.instance),*arguments])
            self.assertEqual(code,2);self.assertEqual(out.getvalue(),'');self.assertNotIn('DO_NOT_DISCLOSE_REVIEW_TEXT',error.getvalue());self.assertEqual(json.loads(error.getvalue())['diagnostics'],['invalid_review_result_schema'])
        self.assertFalse(self.new_output.exists());self.assertEqual(list(self.app.assessments.iterdir()),[])

    def test_node_plan_cannot_be_used_as_origin_of_a_different_review_goal(self):
        policy=review_plan_profile('legacy-role-review-v1');facts,raw=review_git.capture(self.repo,self.base_commit,[],policy)
        prepared=self.app.planning.create('prepare','legacy-role-review-v1',facts,raw,self.plan['user_goal'],AT)
        other=deepcopy(self.plan);other['user_goal']='another private review goal';other['plan_digest']=self.original.review.digest({k:v for k,v in other.items() if k!='plan_digest'})
        results=oracle.declared_results(other)
        with self.assertRaisesRegex(ValueError,'node_plan_contracts_stale'):
            self.app.export(self.repo,json.dumps(other).encode(),json.dumps(results).encode(),self.new_output,self.new_log,AT,'legacy-role-review-v1',node_plan=prepared['assessment_id'])
        self.assertFalse(self.new_output.exists());self.assertFalse(self.new_log.exists())

    def test_input_receipt_and_usage_budgets_fail_before_external_effects(self):
        with patch('lib.review_receipts_application.MAX_PLAN',8):
            with self.assertRaisesRegex(ValueError,'input_budget'):self.export()
        self.assertFalse(self.new_output.exists())
        with patch('lib.review_receipts.MAX_RECEIPT',8):
            with self.assertRaisesRegex(ValueError,'byte_budget'):self.export()
        self.assertFalse(self.new_output.exists())
        self.new_log.parent.mkdir()
        with patch('lib.review_receipts.MAX_LOG',8):
            with self.assertRaisesRegex(ValueError,'byte_budget'):effects.append_usage(self.new_log,self.receipt,self.schema,[self.repo,ROOT])
        self.assertFalse(self.new_log.exists());self.assertFalse(self.new_log.with_name(self.new_log.name+'.lock').exists())

    def test_export_inspect_does_not_trust_resealed_before_presence_or_extra_members(self):
        value=self.export();root=self.app.inputs/value['input_id'];extra=root/'extra';extra.write_text('unrecorded')
        with self.assertRaisesRegex(ValueError,'members_changed'):self.app.inspect(value['assessment_id'])
        extra.unlink();manifest,files=self.app.input_data(value['input_id']);changed=deepcopy(manifest);changed['presence_before']['receipt']=True
        identity=self.app.capture_input(changed,files)
        record=json.loads((self.app.assessments/(value['assessment_id']+'.json')).read_text());record['input_id']=identity;other=canonical_digest(record);(self.app.assessments/(other+'.json')).write_text(json.dumps(record))
        with self.assertRaises(Exception):self.app.inspect(other)

    def test_nonreceipt_existing_destination_never_leaks_private_json_in_cli_error(self):
        import axiom_v2
        plan=self.base/'plan.json';results=self.base/'results.json';plan.write_bytes(self.plan_raw);results.write_bytes(self.results_raw);self.new_output.parent.mkdir();self.new_output.write_text('{"private_text":"DO_NOT_DISCLOSE_EXISTING_FILE"}')
        original=self.new_output.read_bytes();out=io.StringIO();error=io.StringIO()
        with patch('lib.v2_application.instance',return_value=(self.instance,{'node_id':'receipt-export-fixture'})),redirect_stdout(out),redirect_stderr(error):
            code=axiom_v2.main(['--instance',str(self.instance),'review-receipts','export','--repo',str(self.repo),'--plan-file',str(plan),'--results',str(results),'--output',str(self.new_output),'--profile','legacy-role-review-v1','--at',AT])
        self.assertEqual(code,2);self.assertEqual(out.getvalue(),'');self.assertNotIn('DO_NOT_DISCLOSE_EXISTING_FILE',error.getvalue());self.assertEqual(json.loads(error.getvalue())['diagnostics'],['invalid_review_receipt_input']);self.assertEqual(self.new_output.read_bytes(),original)

    def test_conflicting_projection_for_same_id_never_changes_usage_bytes(self):
        changed=deepcopy(self.receipt);changed['roles'][0]['execution_kind']='human';changed['receipt_digest']=self.old.build_receipt.__globals__['digest']({k:v for k,v in changed.items() if k!='receipt_digest'})
        self.old.validate_receipt(changed);self.new_log.parent.mkdir();raw=(json.dumps(changed,sort_keys=True)+'\n').encode();self.new_log.write_bytes(raw)
        with self.assertRaisesRegex(ValueError,'conflicting'):effects.append_usage(self.new_log,self.receipt,self.schema,[self.repo,ROOT])
        with self.assertRaises(ValueError):self.old.append_review_usage(self.repo,self.new_log,self.receipt)
        self.assertEqual(self.new_log.read_bytes(),raw)

    def test_concurrent_exporter_observes_real_lock_and_retry_adds_no_duplicate(self):
        inside=threading.Event();release=threading.Event();original=logic.usage_projection
        def hold(*args):
            inside.set();self.assertTrue(release.wait(5));return original(*args)
        with ThreadPoolExecutor(max_workers=1) as executor,patch('lib.review_receipts.usage_projection',side_effect=hold):
            future=executor.submit(effects.append_usage,self.new_log,self.receipt,self.schema,[self.repo,ROOT])
            try:
                self.assertTrue(inside.wait(5))
                with self.assertRaisesRegex(ValueError,'locked'):effects.append_usage(self.new_log,self.receipt,self.schema,[self.repo,ROOT])
            finally:release.set()
            self.assertTrue(future.result(timeout=5)[2])
        _,_,appended,_=effects.append_usage(self.new_log,self.project(at=LATER),self.schema,[self.repo,ROOT]);self.assertFalse(appended);self.assertEqual(len(self.old.load_review_usage(self.new_log)),1)

    def test_original_main_and_receipt_sources_are_bound_to_frozen_git(self):
        from lib.functional_parity import git_read
        ref='6b557fefe295b58272d2271326576ca3a3687197'
        self.assertEqual((DIRECTORY/'record_agent_review.py.txt').read_bytes(),git_read(ROOT,'show',ref+':scripts/record_agent_review.py'))
