"""Actual local-Git V1/V2 whole-wire comparisons and stale/tampered private state."""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT/'scripts'))
from lib import review_git, review_planning as logic
from lib.review_planning_application import ReviewPlanningContext, run, wire
from lib.provider_ports import review_plan_profile
from lib.portable.contracts import canonical_digest
from lib.review_metadata_application import FLAGS

spec = importlib.util.spec_from_file_location('original_review_planning', ROOT/'tests/acceptance/v1_review_planning_oracle.py')
oracle = importlib.util.module_from_spec(spec); spec.loader.exec_module(oracle)
DIRECTORY = ROOT/'tests/fixtures/v2-review-planning'; METADATA = ROOT/'tests/fixtures/v2-review-metadata'
PROFILE = 'legacy-role-review-v1'; AT = '2026-11-17T14:00:00Z'; GOAL = 'Synthetic whole-wire review fixture'


def complete(plan):
    value = logic.results_template(plan)
    for row, task in zip(value['reviews'], plan['reviews']):
        row.update(status='completed', executor='synthetic fixture', provider='synthetic fixture', summary='Declared synthetic review; no actual review execution',
            outputs={k:'synthetic declared output' for k in task['required_output']}, reviewed_paths=task['scope'],
            reviewed_roles=[t['role_id'] for t in plan['reviews'][:-1]] if row['role_id']=='repo-steward' else [])
    for row in value['validations']: row.update(status='passed', evidence='Synthetic declaration, not a test execution')
    return value


class ReviewPlanning(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.files = oracle.target_files(DIRECTORY)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.base = Path(self.temp.name).resolve()
        self.repo = self.base/'target'; self.revision = oracle.repository_from_files(self.repo, self.files)
        self.instance = self.base/'instance'; self.instance.mkdir(mode=0o700); self.app = ReviewPlanningContext(self.instance, {'node_id':'review-plan-fixture-node'})
        self.policy = review_plan_profile(PROFILE); self.goal = self.base/'goal.txt'; self.goal.write_text(GOAL)
        self.edit('docs/review-example.md', 'changed\n')

    def edit(self, name, text):
        path = self.repo/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text); path.chmod(0o644)

    def original(self):
        value = oracle.OriginalReview(DIRECTORY, METADATA, self.repo); self.addCleanup(value.close); return value

    def prepare(self, paths=None, base=True):
        facts, raw = review_git.capture(self.repo, self.revision if base else None, paths or [], self.policy)
        plan, dispatch = logic.plan(facts, raw, GOAL, self.policy)
        value = self.app.create('prepare', PROFILE, facts, raw, GOAL, AT)
        return value, plan, dispatch

    def cli(self, *arguments, expected=0):
        out = io.StringIO()
        with redirect_stdout(out): self.assertEqual(run(list(map(str, arguments)), self.instance, {'node_id':'review-plan-fixture-node'}), expected)
        return json.loads(out.getvalue())

    def test_actual_original_plan_template_dispatch_and_markdown_whole_wires(self):
        self.edit('model/controls/synthetic.yaml', 'synthetic: true\n'); self.edit('docs/governance/source-documents/synthetic.md', 'synthetic\n')
        value, plan, dispatch = self.prepare(); old = self.original(); original, old_dispatch, template, text = old.prepare(self.revision, GOAL)
        self.assertEqual(plan, original); self.assertEqual(dispatch, old_dispatch); self.assertEqual(logic.results_template(plan), template)
        expected = {'review-plan.json':wire(original), 'review-dispatch.json':wire(old_dispatch), 'review-results-template.json':wire(template), 'review-dispatch.md':text.encode()}
        self.assertEqual({n:p.read_bytes() for n in expected for p in [Path(value['data_directory'])/n]}, expected)

    def test_staged_undone_untracked_deleted_renamed_unicode_newline_paths_match_original(self):
        self.edit('docs/staged.md','staged\n'); oracle.git(self.repo,'add','docs/staged.md'); (self.repo/'docs/staged.md').unlink()
        oracle.git(self.repo,'mv','docs/review-example.md','docs/Prüfung\nrenamed.md'); self.edit('docs/untracked space.md','untracked\n')
        _, plan, _ = self.prepare(); old, _, _, _ = self.original().prepare(self.revision, GOAL); self.assertEqual(plan, old)
        self.assertIn('docs/review-example.md', plan['changed_files']); self.assertIn('docs/staged.md', plan['changed_files']); self.assertIsNone(plan['source_fingerprints']['docs/staged.md'])
        self.assertIn('docs/Prüfung\nrenamed.md', plan['changed_files'])

    def test_committed_branch_and_uncommitted_union_match_original(self):
        oracle.git(self.repo,'add','--all'); oracle.git(self.repo,'commit','-qm','branch change'); self.edit('tests/untracked.py','synthetic = True\n')
        _, plan, _ = self.prepare(); self.assertEqual(plan, self.original().prepare(self.revision, GOAL)[0])

    def test_explicit_selection_and_baseless_worktree_match_original(self):
        for paths, base in [(['docs/review-example.md'],True), (['docs/review-example.md/'],True), (None,False)]:
            with self.subTest(paths=paths,base=base):
                _, plan, _ = self.prepare(paths,base); self.assertEqual(plan,self.original().prepare(self.revision if base else None,GOAL,paths)[0])

    def test_complete_and_incomplete_check_results_match_actual_original_functions(self):
        value, plan, _ = self.prepare(); old = self.original(); pending = logic.results_template(plan); ready = complete(plan)
        high = deepcopy(ready); high['reviews'][0]['findings']=[{'severity':'high','path':'docs/review-example.md','issue':'synthetic unresolved finding','status':'open'}]
        missing_output = deepcopy(ready); missing_output['reviews'][0]['outputs']={}
        for results in [pending,ready,high,missing_output]:
            with self.subTest(ready=results['reviews'][0]['status']):
                source=self.base/'results.json';source.write_bytes(wire(results)); expected=old.review.check_results(self.repo,plan,results)
                checked=self.cli('check','--repo',self.repo,'--plan',value['assessment_id'],'--results',source,'--at',AT,expected=0 if expected['eligible_for_human_review'] else 1)
                self.assertEqual((Path(checked['data_directory'])/'review-check.json').read_bytes(),wire(expected));self.assertTrue(checked['target_current_state_rechecked'])
                self.assertFalse(self.app.inspect(checked['assessment_id'])['target_current_state_rechecked'])

    def test_results_schema_digest_roles_validations_and_steward_guards(self):
        self.edit('model/controls/synthetic.yaml','synthetic: true\n')
        value,plan,_=self.prepare(); original=complete(plan)
        for kind in ['digest','role','duplicate-validation','missing-steward-accounting']:
            results=deepcopy(original)
            if kind=='digest':results['plan_digest']='0'*64
            elif kind=='role':results['reviews'].reverse()
            elif kind=='duplicate-validation':results['validations'].append(results['validations'][0])
            else:results['reviews'][-1]['reviewed_roles']=[]
            source=self.base/'results.json';source.write_bytes(wire(results))
            with self.subTest(kind=kind):
                if kind=='missing-steward-accounting':self.cli('check','--repo',self.repo,'--plan',value['assessment_id'],'--results',source,'--at',AT,expected=1)
                else:
                    with self.assertRaises(ValueError):self.cli('check','--repo',self.repo,'--plan',value['assessment_id'],'--results',source,'--at',AT)

    def test_changed_source_index_modes_or_contract_reject_fresh_check(self):
        value,plan,_=self.prepare();source=self.base/'results.json';source.write_bytes(wire(complete(plan)))
        file=self.repo/'docs/review-example.md';saved=file.read_bytes()
        for kind in ['source','index','mode','contract','new-path']:
            with self.subTest(kind=kind):
                skill=self.repo/'.agents/skills/repo-steward/SKILL.md';skill_saved=skill.read_bytes()
                if kind=='source':file.write_text('new revision\n')
                elif kind=='index':oracle.git(self.repo,'add','docs/review-example.md')
                elif kind=='mode':file.chmod(0o755)
                elif kind=='contract':skill.write_bytes(skill_saved+b'changed\n')
                else:self.edit('docs/another.md','new\n')
                with self.assertRaisesRegex(ValueError,'stale'):self.cli('check','--repo',self.repo,'--plan',value['assessment_id'],'--results',source,'--at',AT)
                file.write_bytes(saved);file.chmod(0o644);skill.write_bytes(skill_saved)
                if kind=='index':oracle.git(self.repo,'reset','-q','HEAD','--','docs/review-example.md')
                if kind=='new-path':(self.repo/'docs/another.md').unlink()

    def test_changed_head_rejects_even_with_same_declared_results(self):
        value,plan,_=self.prepare();oracle.git(self.repo,'add','--all');oracle.git(self.repo,'commit','-qm','advance head')
        source=self.base/'results.json';source.write_bytes(wire(complete(plan)))
        with self.assertRaisesRegex(ValueError,'stale'):self.cli('check','--repo',self.repo,'--plan',value['assessment_id'],'--results',source,'--at',AT)

    def test_unselected_role_or_optional_native_contract_drift_is_bound(self):
        value,plan,_=self.prepare(['docs/review-example.md']);self.edit('.codex/agents/repo-steward.toml','changed data, never executed\n')
        source=self.base/'results.json';source.write_bytes(wire(complete(plan)))
        with self.assertRaisesRegex(ValueError,'stale'):self.cli('check','--repo',self.repo,'--plan',value['assessment_id'],'--results',source,'--at',AT)

    def test_offline_inspection_rederives_after_target_and_caller_deletion(self):
        value,_,_=self.prepare();shutil.rmtree(self.repo);self.goal.unlink();inspected=self.app.inspect(value['assessment_id'])
        self.assertTrue(inspected['retained_complete_outputs_reverified']);self.assertFalse(inspected['target_current_state_rechecked'])
        for flag in FLAGS:self.assertIs(inspected[flag],False)

    def test_checked_result_survives_target_and_results_deletion_without_live_claim(self):
        value,plan,_=self.prepare();source=self.base/'results.json';source.write_bytes(wire(complete(plan)))
        checked=self.cli('check','--repo',self.repo,'--plan',value['assessment_id'],'--results',source,'--at',AT)
        source.unlink();shutil.rmtree(self.repo);self.assertTrue(self.app.inspect(checked['assessment_id'])['retained_complete_outputs_reverified'])
        self.assertFalse(self.app.inspect(checked['assessment_id'])['target_current_state_rechecked'])

    def test_unselected_role_contract_changes_are_not_silently_accepted(self):
        value,plan,_=self.prepare(['docs/review-example.md']);path=self.repo/'.agents/roles/source-document-intake.yaml'
        path.write_bytes(path.read_bytes()+b'\n# synthetic contract change\n');source=self.base/'results.json';source.write_bytes(wire(complete(plan)))
        with self.assertRaisesRegex(ValueError,'stale'):self.cli('check','--repo',self.repo,'--plan',value['assessment_id'],'--results',source,'--at',AT)

    def test_state_inside_target_is_rejected_before_recursive_capture(self):
        inside=self.repo/'private-instance';inside.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError,'outside_target'):
            run(['prepare','--repo',str(self.repo),'--base-commit',self.revision,'--goal-file',str(self.goal),'--profile',PROFILE,'--at',AT],inside,{'node_id':'nested-node'})

    def test_tampered_artifact_and_resealed_output_manifest_reject(self):
        value,_,_=self.prepare();artifact=Path(value['data_directory'])/'review-plan.json';saved=artifact.read_bytes();artifact.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'output_changed'):self.app.inspect(value['assessment_id'])
        artifact.write_bytes(saved);record=json.loads((self.app.assessments/(value['assessment_id']+'.json')).read_text());record['files']['review-plan.json']['sha256']='0'*64
        other=canonical_digest(record);(self.app.assessments/(other+'.json')).write_bytes(wire(record))
        with self.assertRaisesRegex(ValueError,'output_manifest_changed'):self.app.inspect(other)

    def test_private_input_bytes_members_and_foreign_node_or_authority_reject(self):
        value,_,_=self.prepare();root=self.app.inputs/value['input_id'];extra=root/'blobs/extra';extra.write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError,'members_changed'):self.app.inspect(value['assessment_id'])
        extra.unlink();file=next((root/'blobs').iterdir());saved=file.read_bytes();file.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'input_changed'):self.app.inspect(value['assessment_id'])
        file.write_bytes(saved);stored=json.loads((self.app.assessments/(value['assessment_id']+'.json')).read_text())
        for key in ['node_id',*FLAGS]:
            changed=deepcopy(stored);changed[key]='another-node' if key=='node_id' else True;other=canonical_digest(changed);(self.app.assessments/(other+'.json')).write_bytes(wire(changed))
            with self.subTest(key=key):
                with self.assertRaises(ValueError):self.app.inspect(other)

    def test_symlink_leaf_and_parent_escape_and_git_metadata_paths_reject(self):
        outside=self.base/'outside';outside.write_text('private synthetic bytes');file=self.repo/'docs/review-example.md';file.unlink();file.symlink_to(outside)
        with self.assertRaises((ValueError,OSError)):self.prepare()
        file.unlink();self.edit('docs/review-example.md','changed\n');(self.repo/'alias').symlink_to(self.repo/'docs',target_is_directory=True)
        with self.assertRaises((ValueError,OSError)):self.prepare(['alias/review-example.md'])
        with self.assertRaises(ValueError):self.prepare(['.git/config'])
        with self.assertRaisesRegex(ValueError,'regular_file_required'):self.prepare(['docs/'])
        with self.assertRaises(ValueError):self.original().prepare(self.revision,GOAL,['docs/'])

    def test_missing_target_contracts_fail_without_inventing_consumer_contracts(self):
        shutil.rmtree(self.repo/'.agents')
        with self.assertRaisesRegex(ValueError,'target_role_contracts_required'):self.prepare()

    def test_hardened_git_ignores_caller_overrides_and_target_execution_hooks(self):
        marker=self.base/'unexpected-execution';script=self.base/'hook';script.write_text('#!/bin/sh\ntouch '+str(marker)+'\n');script.chmod(0o755)
        oracle.git(self.repo,'config','core.fsmonitor',script);oracle.git(self.repo,'config','diff.external',script)
        with patch.dict(os.environ,{'GIT_DIR':str(self.base/'invalid'),'GIT_INDEX_FILE':str(self.base/'invalid-index'),'GIT_CONFIG_COUNT':'1','GIT_CONFIG_KEY_0':'core.fsmonitor','GIT_CONFIG_VALUE_0':str(script)}):self.prepare()
        self.assertFalse(marker.exists())

    def test_git_output_and_time_budgets_reject(self):
        with self.assertRaisesRegex(ValueError,'output_budget'):review_git.git(self.repo,'show','HEAD:AGENTS.md',limit=8)
        with self.assertRaisesRegex(ValueError,'timeout'):review_git.git(self.repo,'status','--porcelain',timeout=0)

    def test_corrupted_index_mapping_rejects_before_private_persistence(self):
        facts,raw=review_git.capture(self.repo,self.revision,[],self.policy);facts['index_entries']=list(facts['index_entries'])
        before=set(self.app.assessments.iterdir())
        with self.assertRaisesRegex(ValueError,'index_members_changed'):self.app.create('prepare',PROFILE,facts,raw,GOAL,AT)
        self.assertEqual(set(self.app.assessments.iterdir()),before)

    def test_contract_duplicate_alias_authority_and_protocol_guards(self):
        file=self.repo/'.agents/review-protocol.yaml';saved=file.read_bytes()
        for raw in [saved+b'purpose: duplicate\n',b'a: &a [1]\nb: *a\n',saved.replace(b'final_role: repo-steward',b'final_role: governance-analyst'),saved.replace(b'independent_human_approval: false',b'independent_human_approval: true')]:
            file.write_bytes(raw)
            with self.assertRaises(ValueError):self.prepare()
        file.write_bytes(saved)

    def test_invalid_goal_empty_scope_revision_and_capacity_create_no_assessment(self):
        before=set(self.app.assessments.iterdir())
        with self.assertRaises(ValueError):review_git.capture(self.repo,'main',[],self.policy)
        with patch('lib.review_git.MAX_FILE',8):
            with self.assertRaisesRegex(ValueError,'budget'):self.prepare()
        facts,raw=review_git.capture(self.repo,self.revision,[],self.policy)
        with self.assertRaises(ValueError):self.app.create('prepare',PROFILE,facts,raw,'',AT)
        self.assertEqual(set(self.app.assessments.iterdir()),before)

    def test_real_product_cli_prepare_uses_local_git_but_no_review_execution(self):
        import axiom_v2
        out=io.StringIO()
        with patch('lib.v2_application.instance',return_value=(self.instance,{'node_id':'review-plan-fixture-node'})),redirect_stdout(out):
            self.assertEqual(axiom_v2.main(['--instance',str(self.instance),'review-plan','prepare','--repo',str(self.repo),'--base-commit',self.revision,'--goal-file',str(self.goal),'--profile',PROFILE,'--at',AT]),0)
        value=json.loads(out.getvalue());self.assertTrue(value['target_current_state_rechecked']);self.assertFalse(value['agent_execution_verified'])

    def test_frozen_oracle_and_target_program_bytes_match_original_git(self):
        from lib.functional_parity import git_read
        contract=json.loads((DIRECTORY/'contract.json').read_text());ref=contract['v1_reference']
        self.assertEqual((DIRECTORY/'dispatch.py.txt').read_bytes(),git_read(ROOT,'show',ref+':scripts/dispatch_governance_agents.py'))
        for name,row in self.files.items():self.assertEqual(row['bytes'],git_read(ROOT,'show',ref+':'+name))
