"""Whole V1 publisher vs real isolated Git branch/commit/local-push and fake POST.

Lifecycle gates are explicit stand-ins in this orchestration suite. The full
lifecycle gate integration, record/replay, runtime CLI and installed acceptance
remain separate obligations; no real GitHub request is made here.
"""
from pathlib import Path
from types import SimpleNamespace,ModuleType
from unittest.mock import patch
from contextlib import redirect_stdout,redirect_stderr
import argparse,hashlib,io,json,os,shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
from lib.providers.operational_publication_native import native_publisher
from lib.requirement_validation_budget import InputAdmissionError
FIXTURE=ROOT/'tests/fixtures/v2-operational-publisher-original'
REPOSITORY='example/project';RUN='42';ATTEMPT='1';AT='2026-11-15T12:00:00+00:00'
class WholeOperationalPublisherNative(unittest.TestCase):
 def setUp(self):
  previous=os.umask(0o077);self.addCleanup(os.umask,previous);tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.base=Path(tmp.name).resolve();self.seed=self.base/'seed';self.seed.mkdir(mode=0o700)
  self.env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','LD_','DYLD_'))};self.env.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_AUTHOR_DATE=AT,GIT_COMMITTER_DATE=AT,PYTHONDONTWRITEBYTECODE='1')
  self.git(self.seed,'init','--initial-branch=main');self.git(self.seed,'config','gc.auto','0');self.git(self.seed,'config','maintenance.auto','false')
  files={'README.md':'UNCHANGED source\n','status/repository-results-index.json':'{}\n','status/architecture-results-index.json':'{}\n','status/typed-evidence-results-index.json':'{}\n','generated/reports/portfolio-onboarding-status.json':'{}\n','status/governance-lifecycle-live.json':'{}\n','status/governance-lifecycle-closure-index.json':'{}\n','status/results/historical.json':'{"historical":true}\n'}
  for name,text in files.items():p=self.seed/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
  self.git(self.seed,'add','.');self.git(self.seed,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-qm','Identical isolated base');self.initial=self.git(self.seed,'rev-parse','HEAD').strip()
  self.serial=0
 def git(self,root,*args):return subprocess.check_output(['git','-C',str(root),'-c','core.hooksPath=/dev/null',*args],env=self.env,stderr=subprocess.PIPE).decode()
 def fixture(self,side):
  side=str(self.serial)+'-'+side;origin=self.base/(side+'-origin.git');source=self.base/(side+'-source');self.git(self.base,'clone','--bare',str(self.seed),str(origin));self.git(self.base,'clone',str(origin),str(source));origin.chmod(0o700);source.chmod(0o700);self.git(source,'config','gc.auto','0');self.git(source,'config','maintenance.auto','false')
  tools=self.base/(side+'-provider');tools.mkdir(mode=0o700);(tools/'gh').write_text('#!'+sys.executable+'\n'+'''from pathlib import Path
import json,sys
root=Path(__file__).parent;command=sys.argv[1:];assert command[:3]==['api','--method','POST'] and command[-2:]==['--input','-'];data=sys.stdin.read();payload=json.loads(data)
with (root/'calls.jsonl').open('a') as f:f.write(json.dumps({'arguments':command,'raw_input':data,'payload':payload})+'\\n')
mode=(root/'mode').read_text()
if mode=='fail-pr' and command[3].endswith('/pulls'):sys.stderr.write('explicit fake PR failure\\n');sys.exit(7)
if mode=='fail-dispatch' and '/actions/workflows/' in command[3]:sys.stderr.write('explicit fake dispatch failure\\n');sys.exit(8)
if command[3].endswith('/pulls'):
 if mode=='malformed':print('{')
 elif mode=='empty':print('  ')
 else:print(json.dumps({'number':123,'html_url':'https://github.com/example/project/pull/123','fixture_only':True}))
else:sys.stdout.write('')
''');(tools/'gh').chmod(0o700);(tools/'mode').write_text('normal');output=self.base/(side+'-output');summary=self.base/(side+'-summary');output.write_text('earlier=retained\n');summary.write_text('Earlier retained summary\n');env={**self.env,'PATH':str(tools)+os.pathsep+self.env['PATH'],'GITHUB_OUTPUT':str(output),'GITHUB_STEP_SUMMARY':str(summary),'GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY':REPOSITORY,'GITHUB_RUN_ID':RUN,'GITHUB_RUN_ATTEMPT':ATTEMPT};return source,origin,tools,output,summary,env
 def old(self,root):
  contract=json.loads((FIXTURE/'contract.json').read_bytes());raw=(FIXTURE/'publish_operational_update.py.txt').read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),contract['files']['scripts/publish_operational_update.py']['sha256']);ns={'__file__':str(root/'scripts/publish_operational_update.py'),'__name__':'immutable_original'};exec(compile(raw,ns['__file__'],'exec'),ns);return ns
 def snapshot(self,root):return {str(p.relative_to(root)):(p.read_bytes(),p.stat().st_mode&511) for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts}
 def compare(self,scope='portfolio',kind='normal',main=False):
  self.serial+=1;results=[]
  for side in ('original','v2'):
   root,origin,tools,output,summary,env=self.fixture(side);target={'portfolio':'generated/reports/portfolio-onboarding-status.json','devsecops':'status/repository-results-index.json','architecture':'status/architecture-results-index.json','typed-evidence':'status/typed-evidence-results-index.json','lifecycle-pilot':'status/governance-lifecycle-live.json','lifecycle-synthetic':'status/governance-lifecycle-closure-index.json'}[scope]
   if kind!='no-change':(root/target).write_text('{"candidate":"explicit fixture"}\n')
   if kind=='out-of-scope':(root/'README.md').write_text('EXPLICIT OUT OF SCOPE\n')
   if kind=='ignored-generated':(root/'generated/not-allowlisted.txt').write_text('Ignored unrelated report\n')
   if kind=='append-only':(root/'status/results/historical.json').write_text('{"historical":"changed"}\n')
   if kind=='new-ledger':p=root/'status/results/new snapshot.json';p.write_text('{"new":true}\n')
   if kind=='symlink':p=root/target;p.unlink();p.symlink_to(root/'README.md')
   if kind=='deleted-projection':(root/target).unlink()
   if kind=='unreviewed-ancestor':self.git(root,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','--allow-empty','-qm','Unreviewed source commit')
   if kind in ('fail-pr','fail-dispatch','malformed','empty'):(tools/'mode').write_text(kind)
   if kind=='existing-branch':self.git(root,'branch',f'automation/{scope}/{RUN}-{ATTEMPT}')
   if kind=='unprotected-main':env['GITHUB_REF']='refs/heads/unreviewed'
   if kind=='explicit-author':env.update(GIT_AUTHOR_NAME='Explicit fixture author',GIT_AUTHOR_EMAIL='explicit-author@example.invalid',GIT_COMMITTER_NAME='Explicit fixture committer',GIT_COMMITTER_EMAIL='explicit-committer@example.invalid')
   trace=[]
   def gate(name,result=None):
    def run(*args,**kw):
     trace.append({'name':name,'arguments':[str(v) if isinstance(v,Path) else v for v in args[1:]],'keywords':kw})
     if kind=='gate-failure':raise ValueError('Explicit original gate failure')
     return result
    return run
   gates=SimpleNamespace(validate_publication=gate('publication',{'live_activation_approved':False}),check_accepted_prefix=gate('prefix',3),validate_pilot=gate('pilot',{}),validate_overview=gate('overview',{'whole_overview':'explicit fixture'}),validate_viewer=gate('viewer'))
   out,err=io.StringIO(),io.StringIO();returned=error=signal=None;observations=[]
   with redirect_stdout(out),redirect_stderr(err),patch.dict(os.environ,env,clear=True):
    try:
     if side=='original':
      ns=self.old(root);fake={}
      for name,values in [('lib.governance_lifecycle.operating_acceptance',{'validate_publication':gates.validate_publication}),('validate_governance_lifecycle_ledger',{'check_accepted_prefix':gates.check_accepted_prefix,'validate_pilot':gates.validate_pilot}),('generate_governance_lifecycle_overview',{'validate_overview':gates.validate_overview}),('generate_governance_lifecycle_viewer',{'validate_viewer':gates.validate_viewer})]:m=ModuleType(name);m.__dict__.update(values);fake[name]=m
      with patch.dict(sys.modules,fake),patch.object(sys,'argv',['publish_operational_update.py','--scope',scope]):returned=ns['main']() if main else ns['publish'](root,scope=scope,repository=REPOSITORY,run_id=RUN,attempt=ATTEMPT)
     else:
      pub,process=native_publisher(root,scope=scope,repository=REPOSITORY,run_id=RUN,attempt=ATTEMPT,gates=gates,argv=['--scope',scope],environment=env,provider_executable=str(tools/'gh'),local_origin_root=self.base);returned=pub.main() if main else pub.publish(root,scope=scope,repository=REPOSITORY,run_id=RUN,attempt=ATTEMPT);observations=process.observations
    except SystemExit as caught:signal=caught.code
    except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
   calls=[] if not (tools/'calls.jsonl').exists() else [json.loads(row) for row in (tools/'calls.jsonl').read_text().splitlines()];branch=self.git(root,'branch','--show-current').strip();head=self.git(root,'rev-parse','HEAD').strip();refs=self.git(origin,'show-ref','--heads').splitlines();staged=self.git(root,'diff','--cached','--name-only','-z');results.append({'returned':returned,'exception':error,'exit_signal':signal,'stdout':out.getvalue(),'stderr':err.getvalue(),'source':self.snapshot(root),'branch':branch,'head':head,'remote_refs':refs,'staged':staged,'calls':calls,'output':output.read_bytes(),'summary':summary.read_bytes(),'gates':trace})
   if side=='v2' and error is None and kind not in ('no-change','unprotected-main'):
    self.assertTrue(observations);self.assertTrue(all(v['observation']['terminal_observed'] for v in observations));self.assertTrue(any(v['original_arguments'][:2]==['git','push'] for v in observations))
  self.assertEqual(results[1],results[0],(scope,kind,results[1].get('exception'),results[0].get('exception')));return results[1]
 def test_entire_portfolio_branch_commit_local_push_PR_dispatch_and_both_append_outputs(self):
  v=self.compare();self.assertIsNone(v['exception']);self.assertEqual(len(v['calls']),4);self.assertTrue(v['branch'].startswith('automation/portfolio/'));self.assertEqual(v['staged'],'');self.assertEqual(v['output'],b'earlier=retained\npull_request_url=https://github.com/example/project/pull/123\nbranch=automation/portfolio/42-1\n')
 def test_all_six_original_scopes_retain_whole_orchestration_and_gate_order(self):
  for scope in ('devsecops','architecture','typed-evidence','lifecycle-pilot','lifecycle-synthetic'):
   with self.subTest(scope=scope):
    v=self.compare(scope);self.assertIsNone(v['exception']);self.assertEqual([x['name'] for x in v['gates']],['publication'] if scope=='lifecycle-pilot' else ['prefix','pilot','overview','viewer'] if scope=='lifecycle-synthetic' else [])
 def test_no_change_has_no_branch_commit_provider_call_or_output_append(self):
  v=self.compare(kind='no-change');self.assertIsNone(v['exception']);self.assertIsNone(v['returned']);self.assertEqual(v['branch'],'main');self.assertEqual(v['calls'],[]);self.assertEqual(v['output'],b'earlier=retained\n')
 def test_out_of_scope_and_symlink_reject_before_new_branch(self):
  for kind in ('out-of-scope','symlink'):
   with self.subTest(kind=kind):v=self.compare(kind=kind);self.assertEqual(v['exception']['type'],'ValueError');self.assertEqual(v['branch'],'main');self.assertEqual(v['calls'],[])
 def test_historical_ledger_is_append_only_and_new_paths_are_allowed(self):
  v=self.compare('devsecops','append-only');self.assertEqual(v['exception']['type'],'ValueError');v=self.compare('devsecops','new-ledger');self.assertIsNone(v['exception'])
 def test_unrelated_generated_report_omitted_and_deleted_projection_preserved(self):
  for kind in ('ignored-generated','deleted-projection'):
   with self.subTest(kind=kind):self.assertIsNone(self.compare(kind=kind)['exception'])
 def test_unreviewed_ancestor_and_existing_branch_keep_original_failures(self):
  for kind in ('unreviewed-ancestor','existing-branch'):
   with self.subTest(kind=kind):v=self.compare(kind=kind);self.assertEqual(v['exception']['type'],'CalledProcessError');self.assertEqual(v['calls'],[])
 def test_provider_and_dispatch_failures_preserve_already_pushed_partial_effects(self):
  for kind in ('fail-pr','fail-dispatch','malformed','empty'):
   with self.subTest(kind=kind):
    v=self.compare(kind=kind);self.assertIsNotNone(v['exception']);self.assertNotEqual(v['head'],self.initial);self.assertEqual(v['branch'],'automation/portfolio/42-1');self.assertTrue(any(v['head'] in row and 'automation/' in row for row in v['remote_refs']))
 def test_gate_failure_prevents_source_commit_push_and_provider_POST(self):
  for scope in ('lifecycle-pilot','lifecycle-synthetic'):
   with self.subTest(scope=scope):v=self.compare(scope,'gate-failure');self.assertEqual(v['exception'],{'type':'ValueError','message':'Explicit original gate failure'});self.assertEqual(v['branch'],'main');self.assertEqual(v['calls'],[])
 def test_explicit_original_Git_actor_environment_is_preserved_as_metadata_not_personal_consent(self):
  self.assertIsNone(self.compare(kind='explicit-author')['exception'])
 def test_whole_original_main_protected_ref_success_and_rejection(self):
  v=self.compare(main=True);self.assertEqual(v['returned'],0);v=self.compare(kind='unprotected-main',main=True);self.assertEqual(v['exit_signal'],2);self.assertEqual(v['calls'],[]);self.assertEqual(v['branch'],'main')
if __name__=='__main__':unittest.main(verbosity=2)
