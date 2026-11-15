"""Synthetic contract fixtures, not live provider or operational acceptance."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from lib.portable.adapters import API, ProviderError, collect_context, scm_facts
from lib.portable.contracts import canonical_digest, context_errors, endpoint, execution_key, repository_key, validate
from lib.portable.runtime import baseline, evaluate, gate, prepare_evidence, opa_evaluate, source_digest

OPA = ROOT/'.venv-validation/bin/opa'
if not OPA.exists():
    import shutil
    OPA = Path(shutil.which('opa')) if shutil.which('opa') else OPA
SHA = 'a'*40
AT = '2026-11-15T12:00:00Z'


def context(provider='github-actions'):
    scm = {'github-actions':'github','gitlab-ci':'gitlab','bamboo':'bitbucket-dc'}[provider]
    return {'schema_version':'1.0.0', 'scm':{'provider':scm,'instance':'https://scm.example','native_id':'42',
            'path':'group/subgroup/repo' if scm=='gitlab' else 'group/repo','url':'https://scm.example/group/repo'},
            'ci':{'provider':provider,'instance':'https://ci.example','run_id':'PROJ-PLAN-42' if provider=='bamboo' else '42',
                  'job_id':'PLAN-JOB' if provider=='bamboo' else 'job-42','attempt':1,'event':'push','native_reference':'fixture'},
            'revision':{'tested':SHA,'source':SHA,'target':None,'branch':'trunk','mode':'branch'},'change_request':None,
            'capabilities':{name:{'status':'available','source':'synthetic_unit_fixture','value':value} for name,value in
                            [('direct_push_allowed',False),('protected_branch',True),('review_required',True)]},'synthetic':True,'governance':{'baseline_id':baseline()[1]['id'],'baseline_digest':baseline()[1]['digest'],
              'domain':'devsecops','scope':'pipeline-l1','runtime_version':'1.0.0','adapter_version':'1.0.0','runtime_source_digest':source_digest()}}


class Files(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder=Path(self.temporary.name)
        artifact=self.folder/'artifact.bin'
        artifact.write_bytes(b'explicitly synthetic contract test artifact')
        digest=hashlib.sha256(artifact.read_bytes()).hexdigest()
        (self.folder/'sbom.json').write_text(json.dumps({'bomFormat':'CycloneDX','specVersion':'1.5','components':[],
              'metadata':{'component':{'type':'application','name':'fixture','hashes':[{'alg':'SHA-256','content':digest}]}}}))
        self.scan={'scanner':'unit-fixture-scanner','max_severity':'none','findings':[],'artifact_sha256':digest}
        self.write_scan()

    def write_scan(self):
        (self.folder/'scan.json').write_text(json.dumps(self.scan))

    def evidence(self, ctx=None):
        return prepare_evidence(ctx or context(),self.folder,'artifact.bin','sbom.json','scan.json')

    def result(self, ctx=None):
        ctx=ctx or context()
        payload,subjects=self.evidence(ctx)
        return evaluate(ctx,payload,subjects,opa=OPA,at=AT)

    def test_real_opa_three_provider_decision_parity(self):
        results=[self.result(context(provider)) for provider in ('github-actions','gitlab-ci','bamboo')]
        for result in results:
            self.assertEqual(result['execution'],'complete')
            self.assertEqual(result['decision'],'pass')
            self.assertEqual(result['evidence_trust'],'unverified')
            self.assertFalse(result['full_baseline_assessment'])
            self.assertEqual(gate(result),0)
            self.assertIsNone(result['enforcement_observation']['blocks_merge'])
        for result in results[1:]:
            self.assertEqual(result['checks'],results[0]['checks'])
            self.assertEqual(result['controls'],results[0]['controls'])

    def test_finding_changes_gate_not_decision(self):
        self.scan.update(max_severity='critical',findings=[{'severity':'critical','id':'fixture-critical'}])
        self.write_scan()
        result=self.result()
        self.assertEqual(result['execution'],'complete')
        self.assertEqual(result['decision'],'fail')
        self.assertEqual(gate(result,'report-only'),0)
        # A synthetic fixture cannot become a live blocking pass/fail claim.
        self.assertEqual(gate(result,'block-on-error'),2)
        result['context']['synthetic']=False
        result['context_digest']=canonical_digest(result['context'])
        self.assertEqual(gate(result,'block-on-error'),1)

    def test_rego_critical_requirement_cannot_be_weakened_by_threshold(self):
        self.scan.update(max_severity='critical',findings=[{'severity':'critical','id':'fixture-critical'}])
        self.write_scan()
        ctx=context();payload,subjects=self.evidence(ctx)
        result=evaluate(ctx,payload,subjects,opa=OPA,at=AT,max_severity='critical')
        self.assertEqual(result['decision'],'fail')
        control=next(row for row in result['controls'] if row['control_id']=='DSCB-L1-REQ-010')
        self.assertTrue(any('fixture-critical' in text for text in control['policy_findings']))

    def test_synthetic_context_never_grants_blocking_success(self):
        self.assertEqual(gate(self.result(),'block-on-error'),2)

    def test_unknown_direct_push_is_incomplete_even_in_report_only(self):
        ctx=context()
        ctx['capabilities']['direct_push_allowed']={'status':'missing','source':'not_collected','value':None}
        result=self.result(ctx)
        self.assertEqual(result['execution'],'incomplete')
        self.assertEqual(result['decision'],'not_evaluated')
        self.assertEqual(gate(result),2)

    def test_unknown_identity_cannot_pass(self):
        for area,key in [('scm','native_id'),('revision','tested'),('ci','run_id')]:
            ctx=context();ctx[area][key]='unknown'
            result=self.result(ctx)
            self.assertEqual(result['decision'],'not_evaluated')
            self.assertEqual(gate(result),2)

    def test_missing_artifact_or_security_file(self):
        (self.folder/'sbom.json').unlink()
        with self.assertRaises(ValueError):self.evidence()

    def test_placeholder_objects_and_scanner_rejected(self):
        (self.folder/'sbom.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'invalid_sbom'):self.evidence()

    def test_forged_scan_summary_is_not_silently_none(self):
        self.scan['findings']=[{'id':'fixture-critical','severity':'critical'}];self.write_scan()
        with self.assertRaisesRegex(ValueError,'scan_summary_mismatch'):self.evidence()

    def test_scan_wrong_artifact_binding(self):
        self.scan['artifact_sha256']='0'*64;self.write_scan()
        with self.assertRaisesRegex(ValueError,'scan_artifact_binding'):self.evidence()

    def test_unbound_sbom_is_finding_not_pass(self):
        data=json.loads((self.folder/'sbom.json').read_text())
        data['metadata']['component']['hashes']=[]
        (self.folder/'sbom.json').write_text(json.dumps(data))
        self.assertEqual(self.result()['decision'],'fail')

    def test_context_baseline_and_runtime_bindings_cannot_be_declared_away(self):
        for name in ('baseline_digest','runtime_source_digest'):
            ctx=context();ctx['governance'][name]='0'*64
            payload,subjects=self.evidence(ctx)
            result=evaluate(ctx,payload,subjects,opa=OPA,at=AT)
            self.assertEqual(result['decision'],'not_evaluated')
            self.assertEqual(gate(result),2)

    def test_mode_and_threshold_are_strict(self):
        ctx=context();payload,subjects=self.evidence(ctx)
        for overrides in ({'mode':'typo'},{'mode':'waiver-required'},{'max_severity':'nonsense'}):
            with self.assertRaises(ValueError):evaluate(ctx,payload,subjects,opa=OPA,at=AT,**overrides)

    def test_result_tampering_and_empty_checks_rejected(self):
        result=self.result()
        result['context']['revision']['tested']='b'*40
        with self.assertRaises(ValueError):gate(result)
        result=self.result();result['checks']=[]
        with self.assertRaises(ValueError):gate(result)

    def test_run_cli_writes_all_outputs_and_refuses_reuse(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('portable_cli_under_test',ROOT/'scripts/governance_runtime.py')
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        profile=self.folder/'profile.json';profile.write_text('{}')
        output=self.folder/'output'
        argv=['run','--ci','github-actions','--profile',str(profile),'--checkout',str(self.folder),
              '--artifact','artifact.bin','--sbom','sbom.json','--scan','scan.json',
              '--output-directory',str(output),'--opa',str(OPA),'--at',AT]
        with patch.object(cli,'collect_context',return_value=context()),patch.object(cli,'checked_out_revision',return_value=SHA):
            collision=self.folder/'collision';collision.mkdir()
            original_context=collision/'context.json';original_context.write_bytes(b'preserve prior evidence')
            blocked=list(argv);blocked[blocked.index('--output-directory')+1]=str(collision)
            self.assertEqual(cli.main(blocked),2)
            self.assertEqual(original_context.read_bytes(),b'preserve prior evidence')
            self.assertEqual(cli.main(argv),0)
            original=(output/'result.json').read_bytes()
            self.assertEqual(cli.main(argv),2)
            self.assertEqual((output/'result.json').read_bytes(),original)
        for name in ('context.json','evaluation-input.json','result.json','diagnostics.json'):
            self.assertTrue((output/name).is_file())

    def test_cli_gate_rejects_result_for_another_checkout(self):
        path=self.folder/'result.json';path.write_text(json.dumps(self.result()))
        proc=subprocess.run([sys.executable,str(ROOT/'scripts/governance_runtime.py'),'gate',
            '--result',str(path),'--checkout',str(ROOT)],capture_output=True,text=True)
        self.assertEqual(proc.returncode,2)

    def test_no_automatic_pass_of_manual_controls(self):
        payload,_=self.evidence()
        self.assertEqual(payload['pipeline']['status'],'in_progress')
        self.assertIsNone(payload['pipeline']['security_gates']['enforced'])
        rows={row['control_id']:row for row in self.result()['controls']}
        self.assertEqual(rows['DSCB-L1-REQ-001']['status'],'not_evaluated')
        self.assertEqual(rows['DSCB-L1-REQ-016']['status'],'not_evaluated')

    def test_unverified_opa_never_executed(self):
        fake=self.folder/'opa';fake.write_text('untrusted binary')
        with patch('lib.portable.runtime.subprocess.run',side_effect=AssertionError('must not execute')):
            with self.assertRaisesRegex(ValueError,'opa_checksum_mismatch'):
                opa_evaluate({},self.folder,fake)

    def test_declared_waiver_cannot_grant_critical_exception(self):
        ctx=context();payload,subjects=self.evidence(ctx)
        payload['waivers']=[{'id':'fake','status':'approved','expired':False}]
        result=evaluate(ctx,payload,subjects,opa=OPA,at=AT)
        self.assertEqual(result['decision'],'not_evaluated')
        self.assertIn('waiver_authority_not_resolved',result['diagnostics'])

    def test_normalized_input_cannot_override_collected_branch_fact(self):
        ctx=context();payload,subjects=self.evidence(ctx)
        payload['repository']['protected_branch']=False
        result=evaluate(ctx,payload,subjects,opa=OPA,at=AT)
        self.assertEqual(result['decision'],'not_evaluated')
        self.assertEqual(gate(result),2)

    def test_duplicate_json_keys_are_ambiguous_input(self):
        from lib.portable.runtime import read_json
        path=self.folder/'ambiguous.json';path.write_text('{"max_severity":"critical","max_severity":"none"}')
        with self.assertRaisesRegex(ValueError,'duplicate_json_key'):read_json(path)

    def test_missing_policy_does_not_turn_into_an_empty_success(self):
        with self.assertRaisesRegex(ValueError,'invalid_opa_result'):
            opa_evaluate({},self.folder,OPA)

    def test_cli_technical_error_keeps_redacted_diagnostics(self):
        (self.folder/'context.json').write_text('{invalid')
        (self.folder/'input.json').write_text('{}')
        result=subprocess.run([sys.executable,str(ROOT/'scripts/governance_runtime.py'),'evaluate',
            '--context',str(self.folder/'context.json'),'--input',str(self.folder/'input.json'),
            '--output',str(self.folder/'result.json'),'--opa',str(OPA)],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertFalse((self.folder/'result.json').exists())
        self.assertEqual(json.loads((self.folder/'result.diagnostics.json').read_text())['execution'],'error')


    def test_native_collection_to_real_opa_parity(self):
        results=[]
        for provider in ('github-actions','gitlab-ci','bamboo'):
            profile=AdapterTests().profile(provider)
            if provider=='github-actions':
                env={'GITHUB_SHA':SHA,'GITHUB_REF_NAME':'trunk','GITHUB_RUN_ID':'42','GITHUB_JOB':'job-42',
                     'GITHUB_RUN_ATTEMPT':'1','GITHUB_EVENT_NAME':'push','GITHUB_REPOSITORY_ID':'42'}
                responses=[{'id':42},{'name':'trunk','protected':True},
                    {'enforce_admins':{'enabled':True},'required_pull_request_reviews':{'required_approving_review_count':1,
                     'bypass_pull_request_allowances':{'users':[],'teams':[],'apps':[]}}}]
            elif provider=='gitlab-ci':
                env={'CI_COMMIT_SHA':SHA,'CI_COMMIT_BRANCH':'trunk','CI_PIPELINE_ID':'42','CI_JOB_ID':'job-42',
                     'CI_PROJECT_ID':'42','CI_PIPELINE_SOURCE':'push'}
                responses=[{'id':42,'path_with_namespace':profile['scm']['path']},{'name':'trunk','protected':True},
                    [{'id':1,'name':'trunk','push_access_levels':[{'access_level':0}]}],
                    [{'rule_type':'regular','approvals_required':1,'protected_branches':[]}]]
            else:
                env={'bamboo_planRepository_revision':SHA,'bamboo_planRepository_branchName':'trunk',
                     'bamboo_buildResultKey':'PROJ-PLAN-42','bamboo_buildKey':'PROJ-PLAN-JOB'}
                responses=[{'id':42},{'isLastPage':True,'values':[{'type':'pull-request-only',
                    'matcher':{'id':'refs/heads/trunk','type':{'id':'BRANCH'}},'users':[],'groups':[],'accessKeys':[]}]},
                    {'com.atlassian.bitbucket.server.bundled-hooks.requiredApproversMergeHook':{'enabled':True,'count':1}}]
            with patch('lib.portable.adapters.checked_out_revision',return_value=SHA):
                ctx=collect_context(provider,profile,env,self.folder,api=NativeSCMFacts.API(responses))
            ctx['synthetic']=True
            payload,subjects=self.evidence(ctx)
            result=evaluate(ctx,payload,subjects,opa=OPA,at=AT)
            self.assertEqual(result['execution'],'complete')
            self.assertEqual(result['decision'],'pass')
            results.append(result)
        for result in results[1:]:
            self.assertEqual(result['controls'],results[0]['controls'])
            self.assertEqual(result['checks'],results[0]['checks'])


class IdentityTests(unittest.TestCase):
    def test_provider_instance_native_id_separation(self):
        value=context()['scm']
        keys={repository_key(value),repository_key({**value,'provider':'gitlab'}),
              repository_key({**value,'instance':'https://other.example'}),repository_key({**value,'native_id':'43'})}
        self.assertEqual(len(keys),4)
        self.assertEqual(repository_key(value),repository_key({**value,'path':'renamed/repository'}))
        self.assertEqual(repository_key(value),repository_key({**value,'instance':'https://SCM.EXAMPLE:443/'}))

    def test_opaque_bamboo_and_gitlab_subgroups(self):
        self.assertRegex(execution_key(context('bamboo')),r'^[a-f0-9]{64}$')
        self.assertFalse(context_errors(context('gitlab-ci')))

    def test_full_and_static_opa_builds_are_explicitly_pinned(self):
        import re
        from lib.portable.runtime import approved_opa_hashes,read_json
        original=set(re.findall(r'^OPA_\w+_SHA256=([a-f0-9]{64})$',(ROOT/'scripts/validation-toolchain.env').read_text(),re.M))
        approved=approved_opa_hashes('1.18.2')
        self.assertTrue(original <= approved)
        for build in read_json(ROOT/'config/portable-runtime-compatibility.json')['additional_opa_builds']:
            self.assertEqual(build['version'],'1.18.2')
            self.assertIn(build['sha256'],approved)
        with self.assertRaisesRegex(ValueError,'invalid_opa_build_registry'):
            approved_opa_hashes('0.0.0')

    def test_endpoint_credentials_and_non_https_rejected(self):
        for value in ['http://scm.example','https://user:secret@scm.example','https://scm.example/api','https://scm.example?token=secret']:
            with self.assertRaises(ValueError):endpoint(value)

    def test_provider_network_boundary_rejects_insecure_config(self):
        with self.assertRaises(ProviderError):API('http://localhost','secret','gitlab')

    def test_result_schema_rejects_unknown_execution(self):
        ctx=context();ctx['ci']['provider']='another-ci'
        with self.assertRaises(ValidationError):validate('context',ctx)


class AdapterTests(unittest.TestCase):
    def profile(self, provider):
        return {'schema_version':'1.0.0','scm':{**context(provider)['scm'],'api_url':'https://api.example','token_env':'TEST_TOKEN'},
                'ci':{'provider':provider,'instance':'https://ci.example','event':'push'},
                'governance':{key:context(provider)['governance'][key] for key in ('baseline_id','baseline_digest','domain','scope')}}

    def test_api_failure_does_not_fabricate_branch_safety(self):
        api=type('API',(),{'get':lambda self,path:(_ for _ in ()).throw(ProviderError('provider_http_403'))})()
        for provider in ('github-actions','gitlab-ci','bamboo'):
            facts=scm_facts(self.profile(provider)['scm'],'trunk',api)
            self.assertTrue(all(value['value'] is None and value['status']=='error' for value in facts.values()))

    def test_gitlab_merged_results_uses_checked_out_commit(self):
        env={'CI_PIPELINE_ID':'pipeline-1','CI_JOB_ID':'job-2','CI_COMMIT_SHA':SHA,'CI_PIPELINE_SOURCE':'merge_request_event',
             'CI_MERGE_REQUEST_EVENT_TYPE':'merged_result','CI_MERGE_REQUEST_SOURCE_BRANCH_NAME':'feature',
             'CI_MERGE_REQUEST_SOURCE_BRANCH_SHA':'b'*40,'CI_MERGE_REQUEST_TARGET_BRANCH_SHA':'c'*40,
             'CI_MERGE_REQUEST_TARGET_BRANCH_NAME':'trunk','CI_MERGE_REQUEST_IID':'7',
             'CI_MERGE_REQUEST_SOURCE_PROJECT_ID':'41','CI_MERGE_REQUEST_TARGET_PROJECT_ID':'42'}
        with patch('lib.portable.adapters.checked_out_revision',return_value=SHA),patch('lib.portable.adapters.scm_facts',return_value=context()['capabilities']):
            actual=collect_context('gitlab-ci',self.profile('gitlab-ci'),env,ROOT,api=object())
        self.assertEqual(actual['revision']['tested'],SHA)
        self.assertEqual(actual['revision']['source'],'b'*40)
        self.assertEqual(actual['revision']['target'],'c'*40)
        self.assertEqual(actual['revision']['mode'],'merge-result')
        self.assertFalse(context_errors(actual))

    def test_checkout_mismatch_never_uses_declared_sha(self):
        env={'bamboo_planRepository_revision':'b'*40}
        with patch('lib.portable.adapters.checked_out_revision',return_value=SHA):
            with self.assertRaisesRegex(ValueError,'checkout_does_not_match_run'):
                collect_context('bamboo',self.profile('bamboo'),env,ROOT,api=object())

    def test_github_pull_request_head_and_merge_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            event=Path(directory)/'event.json'
            event.write_text(json.dumps({'number':7,'pull_request':{'merge_commit_sha':SHA,
                'head':{'sha':'b'*40,'ref':'feature','repo':{'id':41}},
                'base':{'sha':'c'*40,'ref':'trunk','repo':{'id':42}}}}))
            env={'GITHUB_EVENT_PATH':str(event),'GITHUB_EVENT_NAME':'pull_request','GITHUB_SHA':SHA,
                 'GITHUB_RUN_ID':'42','GITHUB_JOB':'gate','GITHUB_RUN_ATTEMPT':'1'}
            for checked,mode in [(SHA,'merge-result'),('b'*40,'source-head')]:
                with patch('lib.portable.adapters.checked_out_revision',return_value=checked),patch('lib.portable.adapters.scm_facts',return_value=context()['capabilities']):
                    actual=collect_context('github-actions',self.profile('github-actions'),env,ROOT,api=object())
                self.assertEqual(actual['revision']['tested'],checked)
                self.assertEqual(actual['revision']['source'],'b'*40)
                self.assertEqual(actual['revision']['mode'],mode)
                self.assertFalse(context_errors(actual))

    def test_bamboo_can_compose_with_gitlab_scm(self):
        profile=self.profile('gitlab-ci')
        profile['ci']['provider']='bamboo'
        env={'bamboo_buildResultKey':'PROJ-PLAN-42','bamboo_buildKey':'PROJ-PLAN-JOB',
             'bamboo_planRepository_revision':SHA,'bamboo_planRepository_branchName':'trunk'}
        with patch('lib.portable.adapters.checked_out_revision',return_value=SHA),patch('lib.portable.adapters.scm_facts',return_value=context()['capabilities']):
            actual=collect_context('bamboo',profile,env,ROOT,api=object())
        self.assertEqual(actual['scm']['provider'],'gitlab')
        self.assertEqual(actual['ci']['provider'],'bamboo')
        self.assertEqual(actual['ci']['run_id'],'PROJ-PLAN-42')

    def test_no_provider_environment_or_network_in_core(self):
        import ast
        for name in ('runtime.py','contracts.py'):
            tree=ast.parse((ROOT/'scripts/lib/portable'/name).read_text())
            imports=[node.module or '' for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
            imports += [alias.name for node in ast.walk(tree) if isinstance(node,ast.Import) for alias in node.names]
            self.assertFalse(any(value.startswith(('urllib.request','requests','os','adapters')) for value in imports))
            text=(ROOT/'scripts/lib/portable'/name).read_text()
            self.assertFalse(any(isinstance(node,ast.Attribute) and node.attr in ('environ','getenv') for node in ast.walk(tree)))
            self.assertNotIn('https://github.com',text)

class NativeSCMFacts(unittest.TestCase):
    """Recorded API-shaped fixtures exercise acquisition, not just context labels."""
    class API:
        def __init__(self, values): self.values=iter(values)
        def get(self,path): return next(self.values)

    def test_github_classic_protection_requires_admin_enforcement_and_no_bypass(self):
        profile=AdapterTests().profile('github-actions')['scm']
        protection={'enforce_admins':{'enabled':True},'required_pull_request_reviews':{
            'required_approving_review_count':1,'bypass_pull_request_allowances':{'users':[],'teams':[],'apps':[]}}}
        facts=scm_facts(profile,'trunk',self.API([{'id':42},{'name':'trunk','protected':True},protection]))
        self.assertIs(facts['direct_push_allowed']['value'],False)
        protection['enforce_admins']['enabled']=False
        facts=scm_facts(profile,'trunk',self.API([{'id':42},{'name':'trunk','protected':True},protection,[]]))
        self.assertIsNone(facts['direct_push_allowed']['value'])

    def test_gitlab_all_matching_rules_are_evaluated(self):
        profile=AdapterTests().profile('gitlab-ci')['scm']
        project={'id':42,'path_with_namespace':profile['path']}
        rules=[{'id':1,'name':'trunk','push_access_levels':[{'access_level':0}]},
               {'id':2,'name':'*','push_access_levels':[{'access_level':40}]}]
        facts=scm_facts(profile,'trunk',self.API([project,{'name':'trunk','protected':True},rules,[{'rule_type':'regular','approvals_required':1,'protected_branches':[]}]]))
        self.assertIs(facts['direct_push_allowed']['value'],True)
        facts=scm_facts(profile,'trunk',self.API([project,{'name':'trunk','protected':True},rules[:1],[{'rule_type':'regular','approvals_required':1,'protected_branches':[]}]]))
        self.assertIs(facts['direct_push_allowed']['value'],False)

    def test_bitbucket_exact_pull_request_rule_without_exemptions(self):
        profile=AdapterTests().profile('bamboo')['scm']
        rule={'type':'pull-request-only','matcher':{'id':'refs/heads/trunk','type':{'id':'BRANCH'}},
              'users':[],'groups':[],'accessKeys':[]}
        data={'values':[rule],'isLastPage':True}
        facts=scm_facts(profile,'trunk',self.API([{'id':42},data,{'com.atlassian.bitbucket.server.bundled-hooks.requiredApproversMergeHook':{'enabled':True,'count':1}}]))
        self.assertIs(facts['direct_push_allowed']['value'],False)
        rule['users']=[{'id':9}]
        facts=scm_facts(profile,'trunk',self.API([{'id':42},data,{'com.atlassian.bitbucket.server.bundled-hooks.requiredApproversMergeHook':{'enabled':True,'count':1}}]))
        self.assertIsNone(facts['direct_push_allowed']['value'])

    def test_different_native_repository_is_not_accepted(self):
        profile=AdapterTests().profile('github-actions')['scm']
        facts=scm_facts(profile,'trunk',self.API([{'id':43}]))
        self.assertTrue(all(row['status']=='error' and row['value'] is None for row in facts.values()))

class GithubRulesetTests(unittest.TestCase):
    def test_active_exact_branch_ruleset_without_bypass_is_supported(self):
        profile=AdapterTests().profile('github-actions')['scm']
        class API:
            def get(self,path):
                if path.endswith('/protection'):raise ProviderError('provider_http_404')
                if '/rules/branches/' in path:return [{'type':'pull_request','ruleset_id':7,'ruleset_source_type':'Repository'}]
                if '/rulesets/' in path:return {'id':7,'enforcement':'active','bypass_actors':[],
                    'rules':[{'type':'pull_request','parameters':{'required_approving_review_count':1}}]}
                if '/branches/' in path:return {'name':'trunk','protected':True}
                return {'id':42}
        facts=scm_facts(profile,'trunk',API())
        self.assertIs(facts['direct_push_allowed']['value'],False)
        self.assertIs(facts['review_required']['value'],True)

class ContractSafety(unittest.TestCase):
    def test_credential_url_never_survives_context_validation(self):
        ctx=context();ctx['scm']['url']='https://user:secret@scm.example/repo'
        with self.assertRaises(ValidationError):validate('context',ctx)
        ctx=context();ctx['ci']['native_reference']='https://ci.example/run?token=secret'
        with self.assertRaises(ValueError):validate('context',ctx)

    def test_schema_malformed_provider_response_is_not_success(self):
        profile=AdapterTests().profile('github-actions')['scm']
        facts=scm_facts(profile,'trunk',NativeSCMFacts.API([{'id':42},[]]))
        self.assertTrue(all(row['status']=='error' for row in facts.values()))

    def test_profile_contract_is_strict_and_has_no_inline_secret(self):
        profile=AdapterTests().profile('gitlab-ci')
        validate('profile',profile)
        profile['scm']['token']='not-allowed'
        with self.assertRaises(ValidationError):validate('profile',profile)
