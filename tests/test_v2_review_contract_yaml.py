"""Original SafeLoader contracts, complete review wires and bounded alias attacks."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from lib import review_planning as logic, review_committed
from lib.providers import review_dispatch as dispatch_source
from lib.provider_ports import review_commit_profile
from lib.review_planning_application import ReviewPlanningContext, run, wire
from lib.review_receipts_application import ReviewReceiptContext
from lib.review_pr_application import ReviewPRContext


def module(name, path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


oracle=module('yaml_plan_original',ROOT/'tests/acceptance/v1_review_planning_oracle.py')
receipt_oracle=module('yaml_receipt_original',ROOT/'tests/acceptance/v1_review_receipts_oracle.py')
metadata_oracle=module('yaml_metadata_original',ROOT/'tests/acceptance/v1_review_metadata_oracle.py')
pr_oracle=module('yaml_pr_original',ROOT/'tests/acceptance/v1_review_pr_oracle.py')
FIXTURE=ROOT/'tests/fixtures/v2-review-planning';METADATA=ROOT/'tests/fixtures/v2-review-metadata'
PROFILE='legacy-role-review-v1';AT='2026-11-17T23:00:00Z';GOAL='Synthetic original YAML contract compatibility'


class ReviewContractYaml(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name).resolve()
        self.instance=self.base/'node';self.instance.mkdir(mode=0o700);self.settings={'node_id':'synthetic-yaml-contract-node'}

    def repository(self, kind='scalar', object_format='sha1'):
        root=self.base/(kind+'-'+object_format);root.mkdir()
        for name,row in oracle.target_files(FIXTURE).items():
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(row['bytes']);path.chmod(row['mode'])
        path=root/'docs/review-example.md';path.parent.mkdir(exist_ok=True);path.write_text('original\n');path.chmod(0o644)
        oracle.contract_variant(root,kind)
        oracle.git(root,'init','-q','-b','main','--object-format='+object_format)
        oracle.git(root,'add','--all');oracle.git(root,'commit','-qm','synthetic YAML base')
        base=oracle.git(root,'rev-parse','HEAD');path.write_text('committed proposal\n');oracle.git(root,'add','--all');oracle.git(root,'commit','-qm','synthetic YAML proposal')
        return root,base

    def cli(self,*arguments):
        out=io.StringIO()
        with redirect_stdout(out):self.assertEqual(run(list(map(str,arguments)),self.instance,self.settings),0)
        return json.loads(out.getvalue())

    def test_whole_original_plan_external_check_dispatch_receipt_and_committed_pr_for_native_formats(self):
        for object_format in ('sha1','sha256'):
            for kind in ('scalar','sequence','mapping','safe-values'):
                with self.subTest(object_format=object_format,kind=kind):
                    root,base=self.repository(kind,object_format);old=oracle.OriginalReview(FIXTURE,METADATA,root)
                    try:
                        plan,dispatch,template,text=old.prepare(base,GOAL)
                        goal=self.base/'goal.txt';goal.write_text(GOAL)
                        prepared=self.cli('prepare','--repo',root,'--base-commit',base,'--goal-file',goal,'--profile',PROFILE,'--at',AT)
                        expected={'review-plan.json':wire(plan),'review-dispatch.json':wire(dispatch),'review-results-template.json':wire(template),'review-dispatch.md':text.encode()}
                        self.assertEqual({name:(Path(prepared['data_directory'])/name).read_bytes() for name in expected},expected)
                        planfile=self.base/'plan.json';resultsfile=self.base/'results.json';results=oracle.declared_results(plan);planfile.write_bytes(wire(plan));resultsfile.write_bytes(wire(results))
                        checked=self.cli('check-file','--repo',root,'--plan-file',planfile,'--results',resultsfile,'--profile',PROFILE,'--at',AT)
                        stdout=io.StringIO()
                        with redirect_stdout(stdout):self.assertEqual(old.check_files(FIXTURE,planfile,resultsfile),0)
                        self.assertEqual((Path(checked['data_directory'])/'review-check.json').read_text(),stdout.getvalue())
                        facts,raw=dispatch_source.capture(root,base,[],'legacy-role-dispatch-v1');roles,routing=dispatch_source.validate(facts,raw,'legacy-role-dispatch-v1')
                        from lib.providers.review_planning import review_dispatch_profile
                        self.assertEqual(logic.dispatch(facts['changed_paths'],roles,routing,review_dispatch_profile('legacy-role-dispatch-v1')),dispatch)
                        receipt=receipt_oracle.load(old,METADATA,ROOT/'tests/fixtures/v2-review-receipts')
                        location=self.base/(kind+'-'+object_format+'-exports');before=location/'old/receipt.json';log=location/'old/usage.jsonl';stdout=io.StringIO()
                        with redirect_stdout(stdout):self.assertEqual(receipt.main(['--plan',planfile,'--results',resultsfile,'--output',before,'--usage-log',log],recorded_at=AT),0)
                        context=ReviewReceiptContext(self.instance,self.settings);after=location/'new/receipt.json';new_log=location/'new/usage.jsonl'
                        exported=context.export(root,wire(plan),wire(results),after,new_log,AT,PROFILE)
                        self.assertEqual(before.read_bytes(),after.read_bytes());self.assertEqual(log.read_bytes(),new_log.read_bytes())
                        self.assertEqual((Path(exported['data_directory'])/'review-export-result.json').read_text(),stdout.getvalue())
                        facts,raw=review_committed.capture(root,base,plan['head_commit'],review_commit_profile(PROFILE));subject=review_committed.subject(facts,raw,review_commit_profile(PROFILE))
                        original=pr_oracle.load(old,METADATA,metadata_oracle)
                        event=metadata_oracle.event(original['receipt_block'](json.loads(before.read_text())),subject);report=original['inspect_pr'](root,event)
                        pr=ReviewPRContext(self.instance,self.settings);status=pr.create(root,wire(event),AT,PROFILE,'legacy-pr-review-event-v1')
                        self.assertEqual((Path(status['data_directory'])/'review-status.json').read_bytes(),(json.dumps(report,indent=2)+'\n').encode())
                        self.assertEqual((Path(status['data_directory'])/'review-status.md').read_text(),original['render_status'](report))
                        self.assertEqual(report['status'],'declared_complete')
                    finally:old.close()

    def test_safe_non_json_extensions_remain_inert_and_match_original_native_types(self):
        root,_=self.repository('safe-values');old=oracle.OriginalReview(FIXTURE,METADATA,root)
        try:
            original=old.review.ROLE_CONTRACTS['repo-steward']['extension'];new=logic.yaml_object((root/'.agents/roles/repo-steward.yaml').read_bytes())['extension']
            for name in ('date','binary','labels'):self.assertEqual(new[name],original[name]);self.assertIs(type(new[name]),type(original[name]))
            self.assertTrue(math.isnan(new['nonfinite']) and math.isnan(original['nonfinite']))
        finally:old.close()

    def test_recursive_aliases_reject_before_value_construction(self):
        for raw in (b'a: &a [*a]\n',b'a: &a {self: *a}\n'):
            with patch.object(logic.ContractLoader,'construct_object') as construct:
                with self.assertRaisesRegex(ValueError,'review_contract_recursive_alias_not_supported'):logic.yaml_object(raw)
                construct.assert_not_called()

    def test_alias_expansion_is_bounded_before_value_construction(self):
        raw=b'a: &a [x,x,x,x]\nb: &b [*a,*a,*a,*a]\nc: &c [*b,*b,*b,*b]\nd: [*c,*c,*c,*c]\n'
        with patch.object(logic,'MAX_CONTRACT_NODES',50),patch.object(logic.ContractLoader,'construct_object') as construct:
            with self.assertRaisesRegex(ValueError,'review_contract_expanded_node_budget'):logic.yaml_object(raw)
            construct.assert_not_called()
        raw=b'a: &a '+b'x'*100+b'\nb: [*a,*a,*a,*a]\n'
        with patch.object(logic,'MAX_CONTRACT_EXPANDED_BYTES',300),patch.object(logic.ContractLoader,'construct_object') as construct:
            with self.assertRaisesRegex(ValueError,'review_contract_expanded_byte_budget'):logic.yaml_object(raw)
            construct.assert_not_called()

    def test_composition_alias_depth_node_and_input_limits(self):
        with patch.object(logic,'MAX_CONTRACT_ALIASES',1):
            with self.assertRaisesRegex(ValueError,'review_contract_alias_budget'):logic.yaml_object(b'a: &a x\nb: [*a,*a]\n')
        with patch.object(logic,'MAX_CONTRACT_DEPTH',8):
            with self.assertRaisesRegex(ValueError,'review_contract_depth_budget'):logic.yaml_object(b'a: '+b'['*9+b'x'+b']'*9)
            with self.assertRaisesRegex(ValueError,'review_contract_depth_budget'):logic.yaml_object(b'a: &a [[[[x]]]]\nb: [[[*a]]]\n')
        with patch.object(logic,'MAX_CONTRACT_NODES',3):
            with self.assertRaisesRegex(ValueError,'review_contract_node_budget'):logic.yaml_object(b'a: [x,y]\n')
        with patch.object(logic,'MAX_CONTRACT_BYTES',3):
            with self.assertRaisesRegex(ValueError,'review_contract_byte_budget'):logic.yaml_object(b'a: x')

    def test_duplicate_alias_keys_and_unsafe_tags_stay_rejected(self):
        for raw in (b'a: one\na: two\n',b'? &name a\n: first\n? *name\n: second\n',b'a: !!python/object/apply:os.system [echo-should-never-run]\n'):
            with patch('os.system') as execute:
                with self.assertRaises(ValueError):logic.yaml_object(raw)
                execute.assert_not_called()

    def test_aliases_cannot_grant_authority_or_bypass_required_contract_fields(self):
        root,base=self.repository();goal=self.base/'goal.txt';goal.write_text(GOAL)
        protocol=root/'.agents/review-protocol.yaml';saved=protocol.read_bytes()
        protocol.write_bytes(saved.replace(b'&no_authority false',b'&no_authority true'))
        with self.assertRaisesRegex(ValueError,'review_protocol_cannot_grant_authority'):
            self.cli('prepare','--repo',root,'--base-commit',base,'--goal-file',goal,'--profile',PROFILE,'--at',AT)
        protocol.write_bytes(saved);role=root/'.agents/roles/repo-steward.yaml';role.write_bytes(role.read_bytes()+b'validations: &missing []\n')
        with self.assertRaisesRegex(ValueError,'review_contract_unique_string_keys_required'):
            self.cli('prepare','--repo',root,'--base-commit',base,'--goal-file',goal,'--profile',PROFILE,'--at',AT)

    def test_retained_alias_bytes_replay_after_target_deletion_and_tamper_rejects(self):
        root,base=self.repository('mapping');goal=self.base/'goal.txt';goal.write_text(GOAL)
        prepared=self.cli('prepare','--repo',root,'--base-commit',base,'--goal-file',goal,'--profile',PROFILE,'--at',AT)
        self.assertEqual(prepared['schema_version'],1)
        shutil.rmtree(root);goal.unlink();context=ReviewPlanningContext(self.instance,self.settings)
        self.assertTrue(context.inspect(prepared['assessment_id'])['retained_complete_outputs_reverified'])
        self.assertFalse(context.inspect(prepared['assessment_id'])['target_current_state_rechecked'])
        manifest,_,_,_,_=context.input_data(prepared['input_id']);name=next(k for k in manifest['files'] if k.startswith('blobs/'))
        (context.inputs/prepared['input_id']/name).write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError,'review_planning_input_changed'):context.inspect(prepared['assessment_id'])

    def test_merge_key_semantics_remain_original_rejection(self):
        root,_=self.repository();old=oracle.OriginalReview(FIXTURE,METADATA,root)
        try:
            path=self.base/'merge.yaml';path.write_bytes(b'base: &base {x: y}\ncopy: {<<: *base}\n')
            with self.assertRaises(ValueError):old.review.load_yaml(path)
            with self.assertRaisesRegex(ValueError,'invalid_review_contract'):logic.yaml_object(path.read_bytes())
        finally:old.close()


if __name__=='__main__':unittest.main()
