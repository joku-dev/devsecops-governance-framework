"""Whole original self-security native effects with owned local Git/fake API only."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import redirect_stdout,redirect_stderr
import copy,hashlib,io,json,os,shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.self_security_publication import SelfSecurityPublisher,REPORT_JSON,VIEWER_DATA,VIEWER_PROJECTED_KEYS,ALLOWED_PATHS
from lib.providers.self_security_publication_profile import LegacySelfSecurityPublicationProfile
from lib.providers.self_security_publication_api import LegacySelfSecurityPublicationAPI
from lib.providers.self_security_publication_process import NativeSelfSecurityPublicationProcess
from test_v2_self_security_publication import ORIGINAL,report
PROFILE=LegacySelfSecurityPublicationProfile();AT='2026-11-15T12:00:00+00:00';REPOSITORY='owner/repo'


class SelfSecurityNativeFixture(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old);temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.base=Path(temporary.name).resolve();self.seed=self.base/'seed';self.seed.mkdir(mode=0o700);self.environment={**os.environ,'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null','GIT_CONFIG_NOSYSTEM':'1','GIT_AUTHOR_DATE':AT,'GIT_COMMITTER_DATE':AT,'PYTHONDONTWRITEBYTECODE':'1'};self.serial=0
        self.git(self.seed,'init','--initial-branch=main');self.git(self.seed,'config','gc.auto','0');self.git(self.seed,'config','maintenance.auto','false');(self.seed/'.gitignore').write_text('generated/viewer/app/data.json\n');(self.seed/'README.md').write_text('Accepted source stays unchanged\n');self.write(self.seed,report('findings',at='2026-11-14T12:00:00Z'));self.git(self.seed,'add','--all');self.git(self.seed,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-qm','Explicit synthetic baseline');self.initial=self.git(self.seed,'rev-parse','HEAD').strip()
    def git(self,root,*args):return subprocess.check_output(['git','-C',str(root),'-c','core.hooksPath=/dev/null',*args],env=self.environment,stderr=subprocess.PIPE).decode()
    def write(self,root,value):
        paths={REPORT_JSON:json.dumps(value,indent=2)+'\n',next(p for p in ALLOWED_PATHS if p.endswith('.md')):value['overall_status']+' at '+value['observed_at']+'\n',VIEWER_DATA:json.dumps({'repository_security':{**{k:value[k] for k in VIEWER_PROJECTED_KEYS},'source_file':REPORT_JSON}})}
        for name,raw in paths.items():p=root/name;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);p.write_text(raw)
    def fixture(self,side,kind='normal'):
        label=str(self.serial)+'-'+side;origin=self.base/(label+'-origin.git');source=self.base/(label+'-source');self.git(self.base,'clone','--bare',str(self.seed),str(origin));self.git(self.base,'clone',str(origin),str(source));self.git(source,'config','gc.auto','0');self.git(source,'config','maintenance.auto','false');tools=self.base/(label+'-tools');tools.mkdir(mode=0o700);self.write(source,report('findings',at='2026-11-14T12:00:00Z'));state={'prs':[{'number':7,'html_url':'https://github.com/owner/repo/pull/7'}] if kind in ('existing','existing-advanced','existing-no-branch','existing-fail') else [],'mode':kind};(tools/'state.json').write_text(json.dumps(state))
        if kind in ('existing','existing-advanced','stale-branch','existing-fail'):
            self.git(source,'switch','-c',PROFILE.branch);self.write(source,report('earlier-branch'));self.git(source,'add','--',*sorted(ALLOWED_PATHS));self.git(source,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-qm','Explicit prior proposal');self.git(source,'push','origin','HEAD:refs/heads/'+PROFILE.branch);self.git(source,'switch','main')
        if kind=='existing-advanced':
            (source/'README.md').write_text('New accepted main source\n');self.git(source,'add','--','README.md');self.git(source,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-qm','Explicit main advancement');self.git(source,'push','origin','HEAD:refs/heads/main')
        if kind!='no-change':self.write(source,report('findings' if kind=='timestamp-only' else 'pass'))
        if kind=='api-errors':
            value=report();value['observation']['api_errors']=['Explicit unavailable fact'];self.write(source,value)
        if kind=='out-of-scope':(source/'README.md').write_text('Unselected source modification\n')
        program='''import json,sys
from pathlib import Path
b=Path(__file__).resolve().parent;args=sys.argv[1:];assert args[:2]==['api','--method'];assert len(args) in (4,6);method,endpoint=args[2:4];payload=json.load(sys.stdin) if len(args)==6 else None
if len(args)==6:assert args[4:]==['--input','-']
state=json.loads((b/'state.json').read_text());mode=state['mode']
with (b/'calls.jsonl').open('a') as out:out.write(json.dumps([method,endpoint,payload],sort_keys=True)+'\\n')
if mode in ('fail-pr','existing-fail') and method in ('POST','PATCH') and '/pulls' in endpoint:sys.stderr.write('Explicit fake proposal failure\\n');sys.exit(9)
if mode=='fail-dispatch' and 'consumer-lifecycle-guard.yml' in endpoint:sys.stderr.write('Explicit fifth dispatch failure\\n');sys.exit(8)
if method=='GET':print(json.dumps(state['prs']))
elif '/pulls' in endpoint:print(json.dumps({} if mode=='empty-pr' else {'number':7,'html_url':'https://github.com/owner/repo/pull/7'}))
''';tool=tools/'gh';tool.write_text('#!'+sys.executable+'\n'+program);tool.chmod(0o700);output=self.base/(label+'-output');summary=self.base/(label+'-summary');output.write_text('old=kept\n');summary.write_text('Old summary\n');env={**self.environment,'PATH':str(tools)+os.pathsep+os.environ['PATH'],'GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY':REPOSITORY,'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'2','GITHUB_OUTPUT':str(output),'GITHUB_STEP_SUMMARY':str(summary)}
        if kind=='bad-ref':env['GITHUB_REF']='refs/heads/feature'
        return source,origin,tools,output,summary,env
    def snapshot(self,root):return {p.relative_to(root).as_posix():(p.read_bytes(),p.stat().st_mode&511) for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts}


class WholeSelfSecurityPublicationNative(unittest.TestCase):
    def setUp(self):self.case=SelfSecurityNativeFixture();self.case.setUp();self.addCleanup(self.case.doCleanups)
    def compare(self,kind='normal',main=True):
        c=self.case;values=[]
        for side in ('original','ported'):
            root,origin,tools,output,summary,env=c.fixture(side,kind);out,err=io.StringIO(),io.StringIO();returned=error=signal=None
            with patch.dict(os.environ,env,clear=True),redirect_stdout(out),redirect_stderr(err):
                try:
                    if side=='original':
                        ns={'__name__':'immutable_self_security_publisher','__file__':str(root/'scripts/publish_self_security_refresh.py')};exec(compile(ORIGINAL.read_bytes(),'immutable_self_security_publisher','exec'),ns);ns['ROOT']=root;returned=ns['main']() if main else ns['publish'](root,repository=REPOSITORY,run_id='123',attempt='2')
                    else:
                        process=NativeSelfSecurityPublicationProcess(root,repository=REPOSITORY,run_id='123',attempt='2',profile=PROFILE,environment=env,provider_executable=str(tools/'gh'),local_origin_root=c.base);kernel=SelfSecurityPublisher(root,path_factory=Path,process=process,api=LegacySelfSecurityPublicationAPI(process,PROFILE),profile=PROFILE,environment=env);returned=kernel.main() if main else kernel.publish(root,repository=REPOSITORY,run_id='123',attempt='2')
                except SystemExit as caught:signal={'type':'SystemExit','value':caught.code}
                except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
            values.append({'returned':returned,'error':error,'signal':signal,'stdout':out.getvalue(),'stderr':err.getvalue(),'files':c.snapshot(root),'head':c.git(root,'rev-parse','HEAD'),'branch':c.git(root,'branch','--show-current'),'refs':c.git(origin,'show-ref','--heads'),'staged':c.git(root,'diff','--cached','--name-only','-z'),'calls':(tools/'calls.jsonl').read_bytes() if (tools/'calls.jsonl').exists() else b'','output':output.read_bytes(),'summary':summary.read_bytes()})
        self.assertEqual(values[0],values[1],(kind,values[0]['error'],values[1]['error']));return values[1]
    def test_full_original_main_reset_clean_restore_commit_push_GET_POST_five_dispatches_and_appends(self):
        value=self.compare();self.assertIsNone(value['error']);self.assertEqual(len(value['calls'].splitlines()),7);self.assertEqual(value['branch'].strip(),PROFILE.branch);self.assertEqual(value['staged'],'');self.assertNotEqual(value['head'].strip(),self.case.initial)
    def test_existing_proposal_is_updated_by_merge_and_PATCH_without_force(self):
        value=self.compare('existing');self.assertIsNone(value['error']);self.assertTrue(any(json.loads(r)[0]=='PATCH' for r in value['calls'].splitlines()))
    def test_existing_proposal_merges_advanced_main_before_report_restore_without_force(self):
        value=self.compare('existing-advanced');self.assertIsNone(value['error']);self.assertEqual(value['files']['README.md'][0],b'New accepted main source\n');self.assertTrue(any(json.loads(r)[0]=='PATCH' for r in value['calls'].splitlines()))
    def test_no_change_and_observation_clock_only_never_open_an_update(self):
        for i,kind in enumerate(('no-change','timestamp-only')):
            self.case.serial+=i+1
            with self.subTest(kind=kind):
                value=self.compare(kind);self.assertIsNone(value['error']);self.assertEqual(value['head'].strip(),self.case.initial);self.assertFalse(any(json.loads(r)[0] in ('POST','PATCH') for r in value['calls'].splitlines()))
    def test_incomplete_observation_out_of_scope_and_stale_branch_fail_before_commit(self):
        for i,kind in enumerate(('api-errors','out-of-scope','stale-branch','existing-no-branch')):
            self.case.serial+=i+1
            with self.subTest(kind=kind):self.assertIsNotNone(self.compare(kind)['error'])
    def test_partial_post_or_fifth_dispatch_failure_keeps_original_pushed_state(self):
        for i,kind in enumerate(('fail-pr','existing-fail','fail-dispatch','empty-pr')):
            self.case.serial+=i+1
            with self.subTest(kind=kind):
                value=self.compare(kind);self.assertIsNotNone(value['error']);self.assertEqual(value['branch'].strip(),PROFILE.branch)
    def test_direct_original_publish_and_main_ref_failure_are_preserved(self):
        self.assertIsNone(self.compare(main=False)['error']);self.case.serial+=1;self.assertEqual(self.compare('bad-ref')['signal'],{'type':'SystemExit','value':'Self-security publication must run from protected main'})
