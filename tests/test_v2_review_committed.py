"""Real committed Git scope and contract union, compared with original native V1 functions."""
import ast
from contextlib import redirect_stdout,redirect_stderr
from copy import deepcopy
import importlib.util
import json
import io
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
import yaml
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib import review_committed as current,review_metadata
from lib.provider_ports import review_commit_profile,review_event
from lib.review_pr_application import ReviewPRContext
from lib.review_metadata_application import FLAGS
from lib.portable.contracts import canonical_digest

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

oracle=module('original_committed_plan',ROOT/'tests/acceptance/v1_review_planning_oracle.py')
metadata_oracle=module('original_committed_metadata',ROOT/'tests/acceptance/v1_review_metadata_oracle.py')
PLANNING=ROOT/'tests/fixtures/v2-review-planning';METADATA=ROOT/'tests/fixtures/v2-review-metadata'


class CommittedReview(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)/'target'
        self.base=oracle.repository_from_files(self.root,oracle.target_files(PLANNING));self.commit_change()
        self.original=oracle.OriginalReview(PLANNING,METADATA,self.root);self.addCleanup(self.original.close)
        _,self.old=metadata_oracle.load(METADATA);routing=sys.modules[self.original.package+'.agent_routing']
        self.old.update(tempfile=tempfile,SHA=re.compile(r'^(?:[0-9a-f]{40}|[0-9a-f]{64})$'),git_output=self.original.review.git_output,
            load_role_contracts=routing.load_role_contracts,load_routing_contract=routing.load_routing_contract,routing_reasons_for_contract=routing.routing_reasons_for_contract)
        tree=ast.parse((METADATA/'agent_review_status.py.txt').read_bytes());names={'committed_scope','expected_reviews'}
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names];self.assertEqual(len(nodes),2)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'frozen_original_native_pr','exec'),self.old)
        self.profile=review_commit_profile('legacy-role-review-v1');self.schema=json.loads((METADATA/'receipt-schema.json').read_text())
        self.instance=Path(self.temp.name)/'instance';self.instance.mkdir(mode=0o700);self.app=ReviewPRContext(self.instance,{'node_id':'committed-review-fixture'})

    def event_raw(self,body=''):
        return json.dumps(metadata_oracle.event(body,self.expected())).encode()

    def create(self,raw=None):
        return self.app.create(self.root,self.event_raw() if raw is None else raw,'2026-11-17T16:30:00Z','legacy-role-review-v1','legacy-pr-review-event-v1')

    def commit_change(self):
        (self.root/'docs/review-example.md').write_text('committed branch change\n');oracle.git(self.root,'add','--all');oracle.git(self.root,'commit','-qm','reviewed branch change');self.head=oracle.git(self.root,'rev-parse','HEAD')

    def capture(self):return current.capture(self.root,self.base,self.head,self.profile)

    def expected(self):
        ancestor,paths=self.old['committed_scope'](self.root,self.base,self.head)
        return {'target_commit':self.base,'head_commit':self.head,'merge_base_commit':ancestor,'changed_paths':paths,
            'target':self.old['expected_reviews'](self.root,self.base,paths),'proposed':self.old['expected_reviews'](self.root,self.head,paths)}

    def test_actual_scope_contracts_and_original_whole_status_wires(self):
        facts,raw=self.capture();subject=current.subject(facts,raw,self.profile);self.assertEqual(subject,self.expected())
        receipt=metadata_oracle.receipt(self.old);roles=sorted(set(subject['target']['roles'])|set(subject['proposed']['roles'])-{'repo-steward'})
        roles=[r for r in roles if r!='repo-steward']+['repo-steward'];commands=sorted(set(subject['target']['validations'])|set(subject['proposed']['validations']))
        receipt.update(head_commit=self.head,base_commit=subject['merge_base_commit'],changed_paths=subject['changed_paths'],roles=[{'role_id':r,'status':'completed','execution_kind':'role_lens','execution_declared':True} for r in roles],validations=[{'command':c,'status':'passed'} for c in commands]);metadata_oracle.seal(receipt,self.old)
        stale=deepcopy(receipt);stale['head_commit']='a'*40;metadata_oracle.seal(stale,self.old)
        incomplete=deepcopy(receipt);incomplete['eligible_for_human_review']=False;incomplete['roles'][0].update(status='pending',execution_declared=False);metadata_oracle.seal(incomplete,self.old)
        for expected,body in [('missing',''),('declared_complete',self.old['receipt_block'](receipt)),('incomplete',self.old['receipt_block'](incomplete)),('stale',self.old['receipt_block'](stale)),('invalid','<!-- agent-review-receipt:start -->bad<!-- agent-review-receipt:end -->')]:
            with self.subTest(status=expected):
                event=metadata_oracle.event(body,subject);old=self.old['inspect_pr'](self.root,event);new=review_metadata.status_from_subject(review_event('legacy-pr-review-event-v1',event),subject,self.schema)
                self.assertEqual(old['status'],expected);self.assertEqual(new,old);self.assertEqual(review_metadata.render_status(new),self.old['render_status'](old))

    def test_target_only_role_remains_in_required_union(self):
        routing=self.root/'.agents/routing/governance-agent-routing.yaml';original=yaml.safe_load(routing.read_text())
        role=yaml.safe_load((self.root/'.agents/roles/repo-steward.yaml').read_text());role.update(id='synthetic-reviewer',skill='synthetic-reviewer')
        path=self.root/'.agents/roles/synthetic-reviewer.yaml';path.write_text(yaml.safe_dump(role));skill=self.root/'.agents/skills/synthetic-reviewer/SKILL.md';skill.parent.mkdir();skill.write_text('Synthetic test contract only.\n')
        target=deepcopy(original);target['always_select'].append('synthetic-reviewer');routing.write_text(yaml.safe_dump(target));oracle.git(self.root,'add','--all');oracle.git(self.root,'commit','-qm','target extra requirement');self.base=oracle.git(self.root,'rev-parse','HEAD')
        routing.write_text(yaml.safe_dump(original));self.commit_change();facts,raw=self.capture();value=current.subject(facts,raw,self.profile);self.assertEqual(value,self.expected());self.assertIn('synthetic-reviewer',value['target']['roles']);self.assertNotIn('synthetic-reviewer',value['proposed']['roles'])

    def test_original_committed_role_filename_patterns_remain_observable(self):
        routing=self.root/'.agents/routing/governance-agent-routing.yaml';data=yaml.safe_load(routing.read_text());role=yaml.safe_load((self.root/'.agents/roles/repo-steward.yaml').read_text());role['skill']='synthetic-reviewer'
        skill=self.root/'.agents/skills/synthetic-reviewer/SKILL.md';skill.parent.mkdir();skill.write_text('Synthetic metadata only.\n')
        for name in ('-synthetic','synthetic--reviewer'):
            role['id']=name;(self.root/('.agents/roles/'+name+'.yaml')).write_text(yaml.safe_dump(role));data['always_select'].append(name)
        routing.write_text(yaml.safe_dump(data));self.commit_change();facts,raw=self.capture();value=current.subject(facts,raw,self.profile);self.assertEqual(value,self.expected());self.assertIn('-synthetic',value['proposed']['roles']);self.assertIn('synthetic--reviewer',value['proposed']['roles'])

    def test_dirty_checkout_and_unrelated_current_head_do_not_change_committed_scope(self):
        before=self.capture();(self.root/'untracked').write_text('irrelevant working tree\n');(self.root/'docs/review-example.md').write_text('dirty\n');self.assertEqual(self.capture(),before)
        oracle.git(self.root,'add','--all');oracle.git(self.root,'commit','-qm','unrelated later current head');self.assertEqual(self.capture(),before);self.assertEqual(current.subject(*before,self.profile),self.expected())

    def test_original_native_observer_does_not_require_execution_protocol(self):
        (self.root/'.agents/review-protocol.yaml').unlink();self.commit_change();facts,raw=self.capture();self.assertEqual(current.subject(facts,raw,self.profile),self.expected())

    def test_renames_and_unicode_paths_preserve_both_original_paths(self):
        oracle.git(self.root,'mv','docs/review-example.md','docs/review renamed ü.md');oracle.git(self.root,'commit','-qm','rename only');self.head=oracle.git(self.root,'rev-parse','HEAD');facts,raw=self.capture()
        self.assertEqual(current.subject(facts,raw,self.profile),self.expected());self.assertEqual(facts['changed_paths'],['docs/review renamed ü.md','docs/review-example.md'])

    def test_nonregular_and_oversize_contracts_reject_like_original(self):
        path=self.root/'.agents/routing/governance-agent-routing.yaml';saved=path.read_bytes()
        for kind in ('symlink','oversize'):
            if path.is_symlink():path.unlink()
            if kind=='symlink':path.unlink();path.symlink_to('../review-protocol.yaml')
            else:path.write_bytes(saved+b'\n#'+b'x'*65536)
            oracle.git(self.root,'add','--all');oracle.git(self.root,'commit','-qm',kind);self.head=oracle.git(self.root,'rev-parse','HEAD')
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError):self.capture()
                with self.assertRaises(ValueError):self.old['expected_reviews'](self.root,self.head,['docs/review-example.md'])

    def test_retained_source_listing_scope_and_membership_tampering_reject(self):
        facts,raw=self.capture();name=next(n for n in raw if n.startswith('proposed/'))
        for changed in ({**raw,name:raw[name]+b'changed'}, {**raw,'scope.bin':raw['scope.bin']*2}, {**raw,'target-tree.bin':raw['target-tree.bin'].rstrip(b'\0')}, {**raw,'extra':b'extra'}):
            with self.assertRaises((ValueError,TypeError,KeyError)):current.subject(facts,changed,self.profile)

    def test_only_exact_existing_commit_objects_are_accepted(self):
        blob=oracle.git(self.root,'rev-parse','HEAD:docs/review-example.md')
        for revision in ('HEAD','--help','a'*39,'a'*40,blob):
            with self.subTest(revision=revision):
                with self.assertRaises(ValueError):current.capture(self.root,revision,self.head,self.profile)

    def test_sha256_git_commits_and_blob_integrity(self):
        root=Path(self.temp.name)/'sha256';root.mkdir()
        for name,row in oracle.target_files(PLANNING).items():
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(row['bytes']);path.chmod(row['mode'])
        oracle.git(root,'init','-q','-b','main','--object-format=sha256');oracle.git(root,'add','--all');oracle.git(root,'commit','-qm','base');base=oracle.git(root,'rev-parse','HEAD')
        (root/'example.txt').write_text('new\n');oracle.git(root,'add','--all');oracle.git(root,'commit','-qm','head');head=oracle.git(root,'rev-parse','HEAD');self.assertEqual(len(head),64)
        facts,raw=current.capture(root,base,head,self.profile);subject=current.subject(facts,raw,self.profile);ancestor,paths=self.old['committed_scope'](root,base,head)
        self.assertEqual((subject['merge_base_commit'],subject['changed_paths']),(ancestor,paths))
        for side,revision in [('target',base),('proposed',head)]:self.assertEqual(subject[side],self.old['expected_reviews'](root,revision,paths))
        event=metadata_oracle.event('',subject);value=self.app.create(root,json.dumps(event).encode(),'2026-11-17T16:30:00Z','legacy-role-review-v1','legacy-pr-review-event-v1')
        self.assertEqual((Path(value['data_directory'])/'review-status.json').read_text(),json.dumps(self.old['inspect_pr'](root,event),indent=2)+'\n')

    def test_empty_diff_and_deduplicated_both_commit_snapshots_preserve_original(self):
        self.base=self.head;facts,raw=self.capture();self.assertEqual(facts['changed_paths'],[]);self.assertEqual(current.subject(facts,raw,self.profile),self.expected())
        value=self.create();report=json.loads((Path(value['data_directory'])/'review-status.json').read_text());self.assertEqual(report,self.old['inspect_pr'](self.root,json.loads(self.event_raw())));self.assertEqual(report['required_roles'],[])

    def test_malformed_and_resealed_fact_types_and_object_formats_reject(self):
        facts,raw=self.capture()
        for mutation in ({**facts,'target':None},{**facts,'schema_version':True},{**facts,'target_commit':'a'*64}):
            with self.assertRaises(ValueError):current.subject(mutation,raw,self.profile)
        for name in ('scope.bin','target-tree.bin'):
            with self.assertRaises(ValueError):current.subject(facts,{**raw,name:raw[name]+b'\0'},self.profile)
        skill=self.root/'.agents/skills/repo-steward/SKILL.md';skill.write_bytes(b'');oracle.git(self.root,'add','--all');oracle.git(self.root,'commit','-qm','empty skill data');self.head=oracle.git(self.root,'rev-parse','HEAD');facts,raw=self.capture()
        self.assertEqual(current.subject(facts,raw,self.profile),self.expected());changed=deepcopy(facts);changed['proposed']['files']['.agents/skills/repo-steward/SKILL.md']['bytes']=False
        with self.assertRaisesRegex(ValueError,'file_record'):current.subject(changed,raw,self.profile)

    def test_application_complete_original_wires_and_offline_replay(self):
        raw=self.event_raw();expected=self.old['inspect_pr'](self.root,json.loads(raw));value=self.create(raw)
        self.assertTrue(value['local_committed_scope_rechecked']);self.assertEqual(value['declared_status'],'missing')
        files=Path(value['data_directory']);self.assertEqual((files/'review-status.json').read_text(),json.dumps(expected,indent=2)+'\n');self.assertEqual((files/'review-status.md').read_text(),self.old['render_status'](expected))
        shutil.rmtree(self.root);inspected=self.app.inspect(value['assessment_id']);self.assertFalse(inspected['local_committed_scope_rechecked']);self.assertTrue(inspected['retained_complete_outputs_reverified'])
        for name in FLAGS:self.assertIs(inspected[name],False)

    def test_application_dirty_working_tree_is_irrelevant_to_committed_status(self):
        raw=self.event_raw();first=self.create(raw);(self.root/'docs/review-example.md').write_text('dirty after event\n');(self.root/'untracked').write_text('untracked\n');second=self.create(raw)
        self.assertEqual(first,second);self.assertEqual(len(list(self.app.assessments.iterdir())),1)

    def test_application_nonstring_and_large_body_preserve_original_invalid_status(self):
        for body in ({'private':'PRIVATE_BODY_SENTINEL'},'x'*(1048576+1)):
            raw=self.event_raw(body);old=self.old['inspect_pr'](self.root,json.loads(raw));self.assertEqual(old['status'],'invalid');value=self.create(raw)
            self.assertEqual((Path(value['data_directory'])/'review-status.json').read_text(),json.dumps(old,indent=2)+'\n');self.assertNotIn('PRIVATE_BODY_SENTINEL',json.dumps(value))

    def test_actual_product_cli_routes_and_caller_file_deletion(self):
        import axiom_v2
        source=Path(self.temp.name)/'event.json';source.write_bytes(self.event_raw());stdout=io.StringIO()
        arguments=['--instance',str(self.instance),'review-pr','status','--repo',str(self.root),'--event',str(source),'--profile','legacy-role-review-v1','--event-profile','legacy-pr-review-event-v1','--at','2026-11-17T16:30:00Z']
        with patch('lib.v2_application.instance',return_value=(self.instance,{'node_id':'committed-review-fixture'})),redirect_stdout(stdout):code=axiom_v2.main(arguments)
        self.assertEqual(code,0);value=json.loads(stdout.getvalue());source.unlink();self.assertEqual(self.app.inspect(value['assessment_id'])['declared_status'],'missing')

    def test_application_tampered_inputs_outputs_and_resealed_flags_reject(self):
        value=self.create();artifact=Path(value['data_directory'])/'review-status.json';saved=artifact.read_bytes();artifact.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'output_changed'):self.app.inspect(value['assessment_id'])
        artifact.write_bytes(saved);source=self.app.inputs/value['input_id']/'event.json';saved=source.read_bytes();source.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'input_changed'):self.app.inspect(value['assessment_id'])
        source.write_bytes(saved);record=json.loads((self.app.assessments/(value['assessment_id']+'.json')).read_text())
        for key in [*FLAGS,'declared_status','node_id']:
            changed=deepcopy(record);changed[key]='declared_complete' if key=='declared_status' else 'foreign-node' if key=='node_id' else True;other=canonical_digest(changed);(self.app.assessments/(other+'.json')).write_text(json.dumps(changed))
            with self.subTest(key=key):
                with self.assertRaises(ValueError):self.app.inspect(other)

    def test_application_event_and_total_budgets_prevent_assessment(self):
        with patch('lib.review_pr_application.MAX_EVENT',8):
            with self.assertRaisesRegex(ValueError,'event_budget'):self.create()
        with patch('lib.review_pr_application.MAX_TOTAL',8):
            with self.assertRaisesRegex(ValueError,'capture_budget'):self.create()
        self.assertEqual(list(self.app.assessments.iterdir()),[]);self.assertEqual(list(self.app.inputs.iterdir()),[])

    def test_actual_cli_invalid_envelope_does_not_disclose_private_input(self):
        import axiom_v2
        source=Path(self.temp.name)/'event.json';source.write_text('{"pull_request":null,"private":"PRIVATE_EVENT_SENTINEL"}');stdout=io.StringIO();stderr=io.StringIO()
        with patch('lib.v2_application.instance',return_value=(self.instance,{'node_id':'committed-review-fixture'})),redirect_stdout(stdout),redirect_stderr(stderr):
            code=axiom_v2.main(['--instance',str(self.instance),'review-pr','status','--repo',str(self.root),'--event',str(source),'--profile','legacy-role-review-v1','--event-profile','legacy-pr-review-event-v1','--at','2026-11-17T16:30:00Z'])
        self.assertEqual(code,2);self.assertEqual(stdout.getvalue(),'');self.assertNotIn('PRIVATE_EVENT_SENTINEL',stderr.getvalue());self.assertEqual(json.loads(stderr.getvalue())['diagnostics'],['invalid_review_event_envelope']);self.assertEqual(list(self.app.assessments.iterdir()),[])
