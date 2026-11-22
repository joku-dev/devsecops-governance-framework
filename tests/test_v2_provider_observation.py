"""Complete immutable observation main/models over controlled identical native ports."""
from pathlib import Path
from types import SimpleNamespace
from contextlib import redirect_stdout,redirect_stderr
import argparse,ast,copy,hashlib,io,json,os,shutil,subprocess,sys,tempfile,unittest
from datetime import datetime,timezone
import re,yaml
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.provider_observation import ProviderObservation
from lib.providers.provider_observation_assurance import LegacyProviderAssurance
from lib.providers.provider_observation_legacy import PrivateSecurityModules
from lib.providers.operations import SCM
from lib.providers.transports import Reader,BoundedAudit,encoded
from lib.providers.self_security_capture import SecurityCollector,CRITICAL_CODEOWNER_PATHS
from lib.self_security import observed_values
from lib.provider_errors import AccessFailure
from lib.private_credentials import check_private_file
from lib.consumer_intake_store import atomic_json
from lib.portable.contracts import canonical_digest,endpoint,repository_key,valid_id
from lib.requirement_validation_budget import InputAdmissionError

FIXTURE=ROOT/'tests/fixtures/v2-provider-observation-original';AT='2026-11-15T12:00:00+00:00';REV='a'*40


def original_functions(label,namespace):
    source=ast.parse((FIXTURE/(label+'.txt')).read_bytes());functions=[copy.deepcopy(n) for n in source.body if isinstance(n,ast.FunctionDef)]
    if label=='runtime':functions=[n for n in functions if n.name=='read_json']
    exec(compile(ast.fix_missing_locations(ast.Module(body=functions,type_ignores=[])),'immutable_complete_'+label,'exec'),namespace)
    return namespace


def parser_port(argv):
    def factory(*args,**options):
        options['prog']='observe_provider_assurance.py';parser=argparse.ArgumentParser(*args,**options);parse=parser.parse_args;parser.parse_args=lambda values=None:parse(argv if values is None else values);return parser
    return SimpleNamespace(ArgumentParser=factory)


def data_profile(provider):
    instance={'github':'https://github.com','gitlab':'https://gitlab.example.test','bitbucket-dc':'https://bitbucket.example.test'}[provider];path={'github':'owner/repo','gitlab':'group/project','bitbucket-dc':'PROJ/repo'}[provider];native={'github':'1','gitlab':'2','bitbucket-dc':'3'}[provider]
    return {'scm':{'provider':provider,'instance':instance,'native_id':native,'path':path},'api_url':'https://api.github.com' if provider=='github' else instance,'platform_version':None,'edition':None}


def routes(provider):
    profile=data_profile(provider);scm=profile['scm'];route='/repos/owner/repo' if provider=='github' else '/projects/2' if provider=='gitlab' else '/rest/api/latest/projects/PROJ/repos/repo';metadata={'id':int(scm['native_id']),'default_branch':'main'}
    if provider=='github':metadata.update(full_name='owner/repo',visibility='private',security_and_analysis={key:{'status':'enabled'} for key in ('secret_scanning','secret_scanning_push_protection','dependabot_security_updates')})
    elif provider=='gitlab':metadata.update(path_with_namespace='group/project',only_allow_merge_if_pipeline_succeeds=True,only_allow_merge_if_all_discussions_are_resolved=True)
    else:metadata.update(project={'key':'PROJ'},slug='repo')
    if provider=='github':change={'number':7,'state':'open','merged_at':None,'html_url':'https://github.com/owner/repo/pull/7','head':{'repo':{'id':1},'ref':'feature','sha':REV},'base':{'repo':{'id':1},'ref':'main'}}
    elif provider=='gitlab':change={'iid':7,'state':'opened','web_url':'https://gitlab.example.test/group/project/-/merge_requests/7','source_project_id':2,'target_project_id':2,'source_branch':'feature','target_branch':'main','sha':REV}
    else:change={'id':7,'state':'OPEN','links':{'self':[{'href':'https://bitbucket.example.test/projects/PROJ/repos/repo/pull-requests/7'}]},'fromRef':{'repository':{'id':3},'id':'refs/heads/feature','latestCommit':REV},'toRef':{'repository':{'id':3},'id':'refs/heads/main'},'reviewers':[{'user':{'id':10,'type':'NORMAL'},'status':'APPROVED','lastReviewedCommit':REV}]}
    target=route+('/pulls/' if provider=='github' else '/merge_requests/' if provider=='gitlab' else '/pull-requests/')+'7';rows={route:metadata,target:change}
    if provider=='github':rows.update({target+'/reviews?per_page=100&page=1':[{'id':1,'user':{'id':10,'type':'User'},'state':'APPROVED','commit_id':REV},{'id':2,'user':{'id':10,'type':'User'},'state':'DISMISSED','commit_id':REV},{'id':3,'user':{'id':11,'type':'Bot'},'state':'APPROVED','commit_id':REV}],route+'/git/ref/heads/main':{'object':{'sha':REV}},route+'/branches/main/protection':{'required_pull_request_reviews':{'required_approving_review_count':1},'allow_force_pushes':{'enabled':False},'allow_deletions':{'enabled':False}},route+'/branches/main/protection/required_signatures':{'enabled':True},route+'/actions/permissions':{'allowed_actions':'selected','sha_pinning_required':True},route+'/actions/permissions/workflow':{'default_workflow_permissions':'read'},route+'/private-vulnerability-reporting':{'enabled':True},route+'/rules/branches/main':[]})
    elif provider=='gitlab':rows.update({target+'/approvals':{'approved_by':[{'user':{'id':10,'bot':False}},{'user':{'id':11,'bot':True}}]},route+'/repository/branches/main':{'name':'main','commit':{'id':REV},'protected':True}})
    else:rows[route+'/default-branch']={'latestCommit':REV}
    return rows,target


class WholeProviderObservation(unittest.TestCase):
    def setUp(self):
        previous=os.umask(0o077);self.addCleanup(os.umask,previous);temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.base=Path(temporary.name).resolve();self.source=self.base/'static-product';self.source.mkdir(mode=0o700)
        model=self.source/'model/controls/governance-repository-security.yaml';model.parent.mkdir(mode=0o700,parents=True);model.write_bytes(subprocess.check_output(['git','show','6b557fefe295b58272d2271326576ca3a3687197:model/controls/governance-repository-security.yaml'],cwd=ROOT))
        config=self.source/'.github';(config/'workflows').mkdir(mode=0o700,parents=True);(config/'workflows/codeql.yml').write_text('permissions:\n  contents: read\njobs:\n  check:\n    steps:\n      - uses: actions/checkout@'+'a'*40+'\n');(config/'CODEOWNERS').write_text('\n'.join(p+' @explicit-fixture-owner' for p in CRITICAL_CODEOWNER_PATHS));(config/'dependabot.yml').write_text('version: 2\n')
    def compare(self,provider='github',action='reviews',case='normal'):
        results=[]
        for side in ('original','ported'):
            work=self.base/'work'
            if work.exists():shutil.rmtree(work)
            work.mkdir(mode=0o700);profile=data_profile(provider)
            if case=='extra-profile-key':profile['unexpected']=True
            if case=='long-version':profile['platform_version']='v'*201
            if case=='bad-issuer':profile['api_url']='https://other.example.test'
            if case=='bad-endpoint':profile['api_url']='http://untrusted.example.test'
            config=work/'profile.json';config.write_text(json.dumps(profile));config.chmod(0o644 if case=='public-profile' else 0o600);credential=work/'credential';credential.write_text('explicit-synthetic-test-secret\n');credential.chmod(0o644 if case=='public-credential' else 0o600);output=work/'output';rows,target=routes(provider);calls=[];gets=0;git_calls=[]
            if case=='existing-output':output.mkdir(mode=0o700)
            class CaptureReader(Reader):
                def get(this,path):
                    nonlocal gets
                    this.url(path);gets+=1;calls.append(path)
                    if case=='get-error' and ('reviews?' in path or path.endswith('/approvals') or path.endswith('/default-branch')):raise AccessFailure('http_403',False)
                    value=copy.deepcopy(rows[path])
                    if case=='review-moved' and path==target and calls.count(path)>1:
                        if provider=='github':value['head']['sha']='b'*40
                        elif provider=='gitlab':value['sha']='b'*40
                        else:value['fromRef']['latestCommit']='b'*40
                    return value
            def git(command,**options):
                git_calls.append({'command':command,'cwd':str(options['cwd']),**{k:v for k,v in options.items() if k!='cwd'}})
                return ('b'*40+'\n' if case=='installed-mismatch' else REV+'\n') if command==['git','rev-parse','HEAD'] else (b' M scripts/changed.py\0' if case=='dirty-product' else b'')
            report={'release_tags':['fixture-release'],'unverified_release_tags':[],'direct_verified_release_tags':['fixture-release'],'legacy_manifest_verified_tags':[]}
            loader=PrivateSecurityModules(self.source,collector_factory=lambda get:SecurityCollector(self.source,get,lambda:copy.deepcopy(report)),observed_values=observed_values)
            model=LegacyProviderAssurance(self.source,process=SimpleNamespace(check_output=git),loader=loader)
            if side=='original':
                env={'re':re,'yaml':yaml,'urlsplit':urlsplit,'canonical_digest':canonical_digest,'endpoint':endpoint,'repository_key':repository_key,'valid_id':valid_id,'AccessFailure':AccessFailure,'SCM':SCM,'encoded':encoded,'ROOT':self.source,'PROVIDERS':{'github','gitlab','bitbucket-dc'},'SHA':re.compile(r'(?:[a-f0-9]{40}|[a-f0-9]{64})\Z'),'subprocess':SimpleNamespace(check_output=git),'importlib':loader};original_functions('assurance',env);capture_reviews,capture_security=env['capture_reviews'],env['capture_security']
            else:capture_reviews,capture_security=model.capture_reviews,model.capture_security
            argv=[action,'--profile',str(config),'--credential-file',str(credential),'--revision',REV,'--output-root',str(output)]
            if action=='reviews' and case!='missing-change':argv+=['--change-id','7']
            parser=parser_port(argv);clock=SimpleNamespace(now=lambda tz:datetime.fromisoformat(AT));out,err=io.StringIO(),io.StringIO();returned=error=signal=None
            read=original_functions('runtime',{'Path':Path,'json':json})['read_json']
            if side=='original':
                namespace={'argparse':parser,'datetime':clock,'timezone':timezone,'json':json,'os':os,'Path':Path,'atomic_json':atomic_json,'read_json':read,'check_private_file':check_private_file,'capture_reviews':capture_reviews,'capture_security':capture_security,'BoundedAudit':BoundedAudit,'Reader':CaptureReader,'__doc__':ast.get_docstring(ast.parse((FIXTURE/'entrypoint.txt').read_bytes()))};original_functions('entrypoint',namespace);run=namespace['main']
            else:run=ProviderObservation(path_factory=Path,native=os,argparse_port=parser,reader_type=CaptureReader,audit_type=BoundedAudit,private_check=check_private_file,capture_reviews=capture_reviews,capture_security=capture_security,atomic_json=atomic_json,datetime_port=clock).main
            with redirect_stdout(out),redirect_stderr(err):
                try:returned=run()
                except SystemExit as caught:signal={'type':'SystemExit','value':caught.code}
                except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
            files={p.relative_to(output).as_posix():{'bytes':p.read_bytes(),'mode':p.stat().st_mode&511} for p in output.rglob('*') if p.is_file()} if output.exists() else None
            results.append({'returned':returned,'error':error,'signal':signal,'stdout':out.getvalue(),'stderr':err.getvalue(),'files':files,'GET_attempts':calls,'static_Git_reads':git_calls,'private_module_instances':len(loader.modules)})
        self.assertEqual(results[0],results[1],(provider,action,case,results[0]['error'],results[1]['error']));return results[1]
    def test_whole_original_reviews_for_all_three_providers_preserve_latest_actor_and_unknown_binding(self):
        for provider,participants in (('github',1),('gitlab',0),('bitbucket-dc',1)):
            with self.subTest(provider=provider):
                value=self.compare(provider);self.assertIsNone(value['error']);candidate=json.loads(value['files']['candidate.json']['bytes']);self.assertEqual(candidate['latest_bound_approval_participants'],participants);self.assertFalse(candidate['role_approval']);self.assertFalse(candidate['live_authority']);self.assertEqual(set(value['files']),{'candidate.json','native-capture.json'})
    def test_whole_original_security_for_all_three_providers_keeps_every_criterion_and_unknown_equivalence(self):
        for provider in ('github','gitlab','bitbucket-dc'):
            with self.subTest(provider=provider):
                value=self.compare(provider,'security');self.assertIsNone(value['error']);candidate=json.loads(value['files']['candidate.json']['bytes']);self.assertTrue(candidate['criteria']);self.assertFalse(candidate['official_acceptance']);self.assertIsNone(candidate['blocks_merge']);self.assertEqual(candidate['observed_at'],AT)
    def test_native_review_revision_change_still_writes_preceding_audit_and_no_candidate(self):
        for provider in ('github','gitlab','bitbucket-dc'):
            with self.subTest(provider=provider):
                value=self.compare(provider,case='review-moved');self.assertEqual(value['error']['message'],'review_changed_during_capture');self.assertEqual(set(value['files']),{'native-capture.json'})
    def test_get_failure_keeps_successful_preceding_reads_in_mandatory_final_audit(self):
        for provider,action in (('github','reviews'),('gitlab','reviews'),('bitbucket-dc','security')):
            with self.subTest(provider=provider):
                value=self.compare(provider,action,'get-error');self.assertEqual(value['error']['type'],'AccessFailure');audit=json.loads(value['files']['native-capture.json']['bytes']);self.assertEqual(len(audit),len(value['GET_attempts'])-1);self.assertNotIn('candidate.json',value['files'])
    def test_missing_change_parser_exit_inside_try_keeps_empty_final_audit(self):
        value=self.compare(case='missing-change');self.assertEqual(value['signal'],{'type':'SystemExit','value':2});self.assertEqual(json.loads(value['files']['native-capture.json']['bytes']),[])
    def test_profile_schema_version_and_private_permissions_fail_before_output_creation(self):
        for case in ('extra-profile-key','long-version','public-profile','public-credential'):
            with self.subTest(case=case):self.assertIsNone(self.compare(case=case)['files'])
    def test_issuer_mismatch_has_final_audit_but_bad_endpoint_constructor_precedes_try(self):
        value=self.compare(case='bad-issuer');self.assertEqual(value['error']['message'],'assurance_api_issuer_mismatch');self.assertEqual(json.loads(value['files']['native-capture.json']['bytes']),[])
        value=self.compare(case='bad-endpoint');self.assertEqual(value['error']['type'],'ValueError');self.assertEqual(value['files'],{})
    def test_existing_output_root_is_not_overwritten(self):
        value=self.compare(case='existing-output');self.assertEqual(value['error']['type'],'FileExistsError');self.assertEqual(value['files'],{})
    def test_github_dirty_or_other_installed_revision_keeps_all_criteria_not_proven_without_legacy_loading(self):
        for case in ('dirty-product','installed-mismatch'):
            with self.subTest(case=case):
                value=self.compare('github','security',case);candidate=json.loads(value['files']['candidate.json']['bytes']);self.assertTrue(all(row['status']=='not_proven' for row in candidate['criteria']));self.assertEqual(value['private_module_instances'],0)
