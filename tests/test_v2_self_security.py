"""Whole immutable-V1 reports/markdown over explicit observations; no live APIs."""
from copy import deepcopy
from importlib.machinery import SourceFileLoader
import ast,hashlib,importlib.util,json
from pathlib import Path
import sys,unittest
import yaml
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib import self_security as current

ORIGINAL_SHA='c825703be300f4f4f9e5407645b210d56348987dd5dc437375ecc047f48a7c60'
CASES=[]


class OriginalSecurityDecisions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=ROOT/'tests/fixtures/v2-self-security-original/assess_governance_repository_security.py.txt'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==ORIGINAL_SHA
        loader=SourceFileLoader('immutable_V1_self_security',str(path));spec=importlib.util.spec_from_loader(loader.name,loader)
        cls.original=importlib.util.module_from_spec(spec);loader.exec_module(cls.original)
        cls.model=yaml.safe_load((ROOT/'model/controls/governance-repository-security.yaml').read_text())
        cls.observation=json.loads((ROOT/'docs/examples/governance-repository-security-observation.example.json').read_bytes())
    def compare(self,observation=None,model=None):
        observation=deepcopy(self.observation if observation is None else observation);model=deepcopy(self.model if model is None else model)
        before=deepcopy((observation,model))
        try:expected=self.original.assess(model,observation)
        except Exception as error:
            with self.assertRaises(type(error)):current.assess(model,observation)
            CASES.append({'expected_exception':type(error).__name__,'whole_report_completed':False});return None
        actual=current.assess(model,observation)
        self.assertEqual(actual,expected)
        self.assertEqual(current.render_markdown(actual),self.original.render_markdown(expected))
        self.assertEqual((observation,model),before)
        self.assertFalse(actual['enforcement_change_authorized']);self.assertEqual(actual['enforcement'],'report_only')
        self.assertEqual(actual['decision_boundary'],{'blocks_pull_requests':False,'changes_repository_settings':False,'changes_released_baselines':False})
        CASES.append({'status':actual['overall_status'],'criteria':len(actual['criteria']),'failed':actual['summary']['fail'],
            'whole_report_equal':True,'whole_markdown_equal':True,
            'report_SHA256':hashlib.sha256((json.dumps(actual,indent=2)+'\n').encode()).hexdigest()})
        return actual
    def test_six_complete_business_functions_match_original_AST(self):
        old=ast.parse((ROOT/'tests/fixtures/v2-self-security-original/assess_governance_repository_security.py.txt').read_bytes())
        new=ast.parse((ROOT/'scripts/lib/self_security.py').read_bytes())
        for name in ('evidence_refs','observed_values','criterion_detail','remediation_steps','assess','render_markdown'):
            a=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name==name)
            b=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(ast.dump(a,include_attributes=False),ast.dump(b,include_attributes=False),name)
    def test_all_sixteen_criteria_pass_without_authority(self):
        report=self.compare();self.assertEqual(report['summary'],{'criteria':16,'pass':16,'fail':0,'critical_failures':0,'high_failures':0})
    def test_every_single_control_failure_has_exact_detail_priority_references_and_markdown(self):
        changes=(('repository','branch_protected',False,'GRS-001'),('repository','required_approving_reviews',1,'GRS-002'),
         ('repository','required_status_checks',[],'GRS-003'),('repository','force_push_blocked',False,'GRS-004'),
         ('repository','signed_changes_required',False,'GRS-005'),('security_features','secret_scanning','disabled','GRS-006'),
         ('security_features','secret_scanning_push_protection','disabled','GRS-007'),('security_features','dependabot_security_updates','disabled','GRS-008'),
         ('security_features','codeql_workflow_present',False,'GRS-009'),('actions','sha_pinning_required',False,'GRS-010'),
         ('actions','default_workflow_permissions','write','GRS-011'),('ownership','missing_critical_paths',['/scripts/'],'GRS-012'),
         ('actions','direct_main_write_workflows',['.github/workflows/unreviewed.yml'],'GRS-013'),
         ('release_integrity','unverified_release_tags',['l1-baseline-v1.1.3'],'GRS-014'),
         ('security_features','private_vulnerability_reporting',False,'GRS-015'),('actions','allowed_actions','all','GRS-016'))
        for group,key,value,identifier in changes:
            with self.subTest(criterion=identifier):
                observation=deepcopy(self.observation);observation[group][key]=value;report=self.compare(observation)
                self.assertEqual([c['id'] for c in report['criteria'] if c['status']=='fail'],[identifier])
    def test_two_reviews_alone_do_not_claim_codeowner_and_last_push_protection(self):
        for field in ('code_owner_review_required','last_push_approval_required'):
            for value in (False,None,1,'true'):
                with self.subTest(field=field,value=value):
                    observation=deepcopy(self.observation);observation['repository'][field]=value
                    self.assertIn('GRS-002',[c['id'] for c in self.compare(observation)['criteria'] if c['status']=='fail'])
    def test_unknown_admin_facts_and_raw_api_errors_preserve_complete_original_wire(self):
        observation=deepcopy(self.observation);observation['api_errors']=['repos/owner/repo/branches/main/protection: denied (HTTP403)']
        observation['repository']={};observation['security_features']={};observation['actions']={};observation['ownership']={};observation['release_integrity']={}
        report=self.compare(observation)
        self.assertEqual(report['observation']['api_errors'],observation['api_errors'])
        # Preserve original truthy/empty defaults rather than invent stricter facts.
        self.assertEqual(current.observed_values(observation),self.original.observed_values(observation))
    def test_combined_remediation_prerequisites_and_stable_priority_order(self):
        observation=deepcopy(self.observation)
        observation['actions'].update(direct_main_write_workflows=['unsafe'],sha_pinning_required=False,allowed_actions='all')
        observation['repository'].update(branch_protected=False,signed_changes_required=False)
        observation['release_integrity']['unverified_release_tags']=['old']
        report=self.compare(observation);self.assertEqual([r['priority'] for r in report['next_steps']],sorted(r['priority'] for r in report['next_steps']))
    def test_custom_models_reordering_duplicates_unknown_key_and_empty_model_keep_original_semantics(self):
        for criteria in (list(reversed(self.model['criteria'])),[self.model['criteria'][0]]*2,[],[{'key':'unknown','id':'custom','severity':'low','title':'unknown'}]):
            with self.subTest(criteria=len(criteria)):
                model=deepcopy(self.model);model['criteria']=deepcopy(criteria);self.compare(model=model)
    def test_original_malformed_observation_exceptions_are_not_successful_empty_reports(self):
        for observation in (None,[],{'repository':None},{'repository':{'required_approving_reviews':None}},
                {'actions':{'third_party_unpinned_refs':None}}, {'ownership':None},{'release_integrity':None}):
            with self.subTest(observation=observation):
                if observation is None:
                    with self.assertRaises(AttributeError):current.assess(self.model,None)
                else:self.compare(observation)
    def test_opaque_observation_extensions_unicode_and_provided_instant_are_preserved(self):
        observation=deepcopy(self.observation);observation.update(observed_at='2026-11-15T12:00:00Z',extra={'unicode':'Änderungsrisiko','declared':True})
        report=self.compare(observation);self.assertEqual(report['observation']['extra'],observation['extra'])


class OriginalSecurityCapture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OriginalSecurityDecisions.setUpClass();cls.original=OriginalSecurityDecisions.original
    def test_every_native_endpoint_is_read_once_in_original_order_and_complete_observation_matches(self):
        from lib.providers.self_security_capture import SecurityCollector,request_paths
        from unittest.mock import patch
        import tempfile
        repository='owner/repo';paths=request_paths(repository)
        metadata={'visibility':'private','default_branch':'develop','security_and_analysis':{'secret_scanning':{'status':'enabled'}}}
        protection={'required_pull_request_reviews':{'required_approving_review_count':1},'required_status_checks':{'checks':[{'context':'z'},{'context':'a'}]}}
        rules=[{'type':'pull_request','parameters':{'required_approving_review_count':2,'require_code_owner_review':True,'require_last_push_approval':True}},
               {'type':'required_status_checks','parameters':{'required_status_checks':[{'context':'a'},{'context':'b'}]}},
               {'type':'required_signatures'},{'type':'deletion'},{'type':'non_fast_forward'}]
        scenarios=[[(metadata,None),(protection,None),({'enabled':True},None),({'allowed_actions':'selected','sha_pinning_required':True},None),
                   ({'default_workflow_permissions':'read','can_approve_pull_request_reviews':False},None),({'enabled':True},None),(rules,None)],
                   [(None,path+': denied') for path in paths],
                   [(None,None),([],None),([],None),([],None),([],None),([],None),({},None)],
                   [(metadata,None),({},None),({'enabled':False},None),({},None),({},None),({},None),([],None)]]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);wf=root/'.github/workflows';wf.mkdir(parents=True)
            for name,text in {'z.yaml':'permissions:\n  contents: write\nuses: third/action@main\n',
                'a.yml':'permissions:\n  contents: read\nuses: third/action@'+'a'*40+'\n',
                'codeql.yml':'steps:\nuses: joku-dev/first@main\nuses: ./local@main\n',
                'review.yml':'permissions:\n  contents: write\nrun: python3 scripts/publish_operational_update.py --scope portfolio\n',
                'unsafe.yml':'permissions:\n  contents: write\nrun: python3 scripts/publish_self_security_refresh.py\ngit push\n',
                'ignored.txt':'uses: unknown@main'}.items():(wf/name).write_text(text)
            (root/'.github/CODEOWNERS').write_text('/scripts/ @owner\n');(root/'.github/dependabot.yml').write_text('version: 2\n')
            release={'tag_assessments':[{'tag':'x','status':'unverified'}],'unverified_release_tags':['x'],'verification_errors':['retained native failure']}
            for responses in scenarios:
                with self.subTest(responses=responses):
                    native_calls=[];old_calls=[]
                    def native(path):native_calls.append(path);return deepcopy(responses[paths.index(path)])
                    def old(path):old_calls.append(path);return deepcopy(responses[paths.index(path)])
                    with patch.object(self.original,'ROOT',root),patch.object(self.original,'gh_api',side_effect=old),patch.object(self.original,'tag_verification',return_value=release):
                        expected=self.original.collect_live(repository,'arbitrary-original-observed-at')
                    actual=SecurityCollector(root,native,release).collect_live(repository,'arbitrary-original-observed-at')
                    self.assertEqual(actual,expected);self.assertEqual(native_calls,paths);self.assertEqual(old_calls,paths)
                    self.assertEqual(current.assess(OriginalSecurityDecisions.model,actual),self.original.assess(OriginalSecurityDecisions.model,expected))
    def test_request_repository_cannot_select_another_endpoint_or_inject_query(self):
        from lib.providers.self_security_capture import request_paths
        for value in ('a/b/c','../x','a/..','a/b?query','a/b#frag','a\\b/c','https://other','a/b\n',''):
            with self.subTest(value=value),self.assertRaises(ValueError):request_paths(value)


if __name__=='__main__':unittest.main()
