"""Complete original self-security publication over controlled identical effects."""
from pathlib import Path
from types import SimpleNamespace
from contextlib import redirect_stdout,redirect_stderr
import copy,hashlib,io,json,os,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
from lib.self_security_publication import SelfSecurityPublisher,REPORT_JSON,VIEWER_DATA,VIEWER_PROJECTED_KEYS,ALLOWED_PATHS
from lib.providers.self_security_publication_profile import LegacySelfSecurityPublicationProfile
from lib.providers.self_security_publication_api import LegacySelfSecurityPublicationAPI
ORIGINAL=ROOT/'tests/fixtures/v2-self-security-publication-original/publish_self_security_refresh.txt';PROFILE=LegacySelfSecurityPublicationProfile()


def report(status='pass',at='2026-11-15T12:00:00Z'):
    return {'repository_id':'owner/repo','observed_at':at,'profile_version':'fixture','enforcement':'report_only','overall_status':status,'summary':{'pass':13,'fail':0 if status=='pass' else 3},'risk_statement':'Explicit synthetic fixture','criteria':[],'next_steps':[],'decision_boundary':'No authority transfer','observation':{'observed_at':at,'repository':{'branch_protected':True},'api_errors':[]}}


class Effects:
    def __init__(self,root,kind):
        self.root,self.kind,self.calls=root,kind,[];self.selected=sorted(ALLOWED_PATHS);self.diff_calls=0;self.current=report();self.previous=report('findings')
        if kind=='timestamp-only':self.previous=report(at='2026-11-14T12:00:00Z')
        if kind=='no-change':self.selected=[]
        if kind=='markdown-only':self.selected=[next(x for x in ALLOWED_PATHS if x.endswith('.md'))]
        if kind=='out-of-scope':self.selected=['model/unselected.yaml']
        if kind=='api-errors':self.current['observation']['api_errors']=['Explicit missing permission']
        if kind=='legacy-404':self.current['observation']['api_errors']=['repos/owner/repo/branches/main/protection: '+PROFILE.expected_legacy_protection_404]
        self.environment={'GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY':'owner/repo','GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'2','GITHUB_OUTPUT':str(root.parent/'output'),'GITHUB_STEP_SUMMARY':str(root.parent/'summary')}
        if kind=='bad-ref':self.environment['GITHUB_REF']='refs/heads/feature'
        for name in (REPORT_JSON,VIEWER_DATA,*ALLOWED_PATHS):
            p=root/name;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
            if name==REPORT_JSON:p.write_text(json.dumps(self.current))
            elif name==VIEWER_DATA:p.write_text(json.dumps({'repository_security':{**{k:self.current[k] for k in VIEWER_PROJECTED_KEYS},'source_file':REPORT_JSON}}))
            else:p.write_text('Explicit current Markdown\n')
        if kind=='bad-viewer':(root/VIEWER_DATA).write_text('{}')
        for name in ('output','summary'):(root.parent/name).write_text('Earlier metadata\n')
    def run(self,command,**options):
        self.calls.append(('process',list(command),{k:str(v) if isinstance(v,Path) else v for k,v in options.items()}));args=command[1:];code=0;out=''
        if command[0]=='gh':return SimpleNamespace(returncode=0,stdout=json.dumps(self.api(command[3],command[4],None if options['input'] is None else json.loads(options['input']))),stderr='')
        if args[:2]==['diff','--name-only']:
            self.diff_calls+=1;selected=[] if self.kind=='no-valid-restaged' and self.diff_calls>1 else self.selected;out='\0'.join(selected)+('\0' if selected else '')
        elif args[:2]==['ls-files','--others']:out=''
        elif args[:2]==['diff','--cached']:out='\0'.join(['wrong.json'] if self.kind=='staged-mismatch' else self.selected)+'\0'
        elif args[:1]==['ls-remote']:code=0 if self.kind in ('existing','stale-branch','existing-pr-failure') else 2
        elif args[:1]==['show']:out=json.dumps(self.previous);code=1 if self.kind=='missing-prior-report' else 0
        elif args==['rev-parse','HEAD']:out='a'*40+'\n'
        return SimpleNamespace(returncode=code,stdout=out,stderr='')
    def api(self,method,endpoint,payload=None):
        self.calls.append(('api',method,endpoint,copy.deepcopy(payload)))
        if method=='GET':
            if self.kind=='query-object':return {}
            if self.kind=='query-multiple':return [{'number':7},{'number':8}]
            if self.kind in ('existing','existing-no-branch','existing-pr-failure'):return [{'number':7,'html_url':'https://github.com/owner/repo/pull/7'}]
            return []
        if self.kind in ('pr-failure','existing-pr-failure') and '/pulls' in endpoint:raise ValueError('PR operation failed after push')
        if self.kind=='dispatch-failure' and 'dependency-review' in endpoint:raise ValueError('Later dispatch failed')
        if self.kind=='empty-pr' and '/pulls' in endpoint:return {}
        return {'number':7,'html_url':'https://github.com/owner/repo/pull/7'} if '/pulls' in endpoint else {}


class WholeSelfSecurityPublication(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old);temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name).resolve();self.root=self.base/'source';self.root.mkdir(mode=0o700)
    def compare(self,kind='normal',invocation='publish',subject=None):
        results=[]
        for side in ('original','ported'):
            effects=Effects(self.root,kind);out,err=io.StringIO(),io.StringIO();value=error=signal=None;target={'repository':'owner/repo','run_id':'123','attempt':'2',**(subject or {})}
            with redirect_stdout(out),redirect_stderr(err):
                if side=='original':
                    ns={'__name__':'immutable_self_security_publisher','__file__':str(self.root/'scripts/publish_self_security_refresh.py')};exec(compile(ORIGINAL.read_bytes(),'immutable_self_security_publisher','exec'),ns);ns.update(ROOT=self.root,subprocess=effects,os=SimpleNamespace(environ=effects.environment));run=lambda:ns['main']() if invocation=='main' else ns['publish'](self.root,**target)
                else:
                    kernel=SelfSecurityPublisher(self.root,path_factory=Path,process=effects,api=LegacySelfSecurityPublicationAPI(effects,PROFILE),profile=PROFILE,environment=effects.environment);run=lambda:kernel.main() if invocation=='main' else kernel.publish(self.root,**target)
                try:value=run()
                except SystemExit as caught:signal={'type':'SystemExit','value':caught.code}
                except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
            results.append({'value':value,'error':error,'signal':signal,'stdout':out.getvalue(),'stderr':err.getvalue(),'calls':effects.calls,'files':{p.relative_to(self.root).as_posix():p.read_bytes() for p in self.root.rglob('*') if p.is_file()},'output':(self.base/'output').read_bytes(),'summary':(self.base/'summary').read_bytes()})
        self.assertEqual(results[0],results[1]);return results[1]
    def test_entire_original_material_publication_keeps_all_five_dispatches_then_both_appends(self):
        value=self.compare();self.assertIsNone(value['error']);api=[r for r in value['calls'] if r[0]=='api'];self.assertEqual(len(api),7);dependency=next(r for r in api if '/dependency-review.yml/' in r[2]);self.assertEqual(dependency[3]['inputs'],{'base_ref':'main','head_ref':PROFILE.branch})
    def test_whole_original_main_validates_the_viewer_and_protected_main_ref(self):
        self.assertEqual(self.compare(invocation='main')['value'],0);self.assertIsNotNone(self.compare('bad-viewer',invocation='main')['error']);self.assertIsNotNone(self.compare('bad-ref',invocation='main')['signal'])
    def test_original_existing_PR_update_and_merge_path_is_preserved(self):
        value=self.compare('existing');self.assertIsNone(value['error']);self.assertTrue(any(r[0]=='api' and r[1]=='PATCH' for r in value['calls']));self.assertTrue(any(r[0]=='process' and 'merge' in r[1] for r in value['calls']))
    def test_original_timestamp_only_and_no_change_never_propose_a_new_update(self):
        for kind in ('timestamp-only','no-change'):
            with self.subTest(kind=kind):
                value=self.compare(kind);self.assertIsNone(value['value']);self.assertFalse(any(r[0]=='api' and r[1] in ('POST','PATCH') for r in value['calls']))
    def test_original_scope_report_api_and_branch_query_failures_remain_exact(self):
        for kind in ('markdown-only','out-of-scope','api-errors','query-object','query-multiple','existing-no-branch','stale-branch','no-valid-restaged','staged-mismatch'):
            with self.subTest(kind=kind):self.assertIsNotNone(self.compare(kind)['error'])
        self.assertIsNone(self.compare('legacy-404')['error'])
    def test_original_partial_POST_dispatch_and_invalid_PR_failures_keep_effect_order(self):
        for kind in ('pr-failure','existing-pr-failure','dispatch-failure','empty-pr'):
            with self.subTest(kind=kind):self.assertIsNotNone(self.compare(kind)['error'])
    def test_original_repository_run_and_attempt_validation_are_not_inferred(self):
        for subject in ({'repository':'a/b/c'},{'run_id':'0'},{'attempt':'-1'}):
            with self.subTest(subject=subject):self.assertEqual(self.compare(subject=subject)['error']['type'],'ValueError')
    def test_normalization_and_blocking_error_helpers_match_every_original_value(self):
        ns={'__name__':'immutable_self_security_publisher','__file__':str(self.root/'scripts/publish_self_security_refresh.py')};exec(compile(ORIGINAL.read_bytes(),'immutable_self_security_publisher','exec'),ns);kernel=SelfSecurityPublisher(self.root,path_factory=Path,process=None,api=None,profile=PROFILE,environment={});values=[report(),report(at='2026-11-16T00:00:00Z'),{'observation':None},{'observation':{'api_errors':['x',PROFILE.expected_legacy_protection_404],'repository':{'branch_protected':False}}}]
        for value in values:
            before=copy.deepcopy(value);self.assertEqual(kernel.normalized_report(value),ns['normalized_report'](value));self.assertEqual(kernel.blocking_api_errors(value),ns['blocking_api_errors'](value));self.assertEqual(before,value)
        self.assertEqual(kernel.materially_equal(values[0],values[1]),ns['materially_equal'](values[0],values[1]))
