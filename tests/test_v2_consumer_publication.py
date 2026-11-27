"""Whole immutable consumer publisher compared over identical controlled ports.

These are isolated protocol/model comparisons, not live publication approval.
"""
from pathlib import Path
from types import SimpleNamespace
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
import argparse,ast,copy,hashlib,io,json,os,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.consumer_publication import ConsumerPublisher,SCOPES,LEDGERS
from lib.providers.consumer_publication_profile import LegacyConsumerPublicationProfile
from lib.providers.operational_publication_api import LegacyOperationalPublicationAPI
from lib.providers.consumer_publication_protocol import LegacyConsumerPublisherProtocol
from lib.requirement_validation_budget import InputAdmissionError

ORIGINAL=ROOT/'tests/fixtures/v2-consumer-publication-original/publish_consumer_lifecycle.txt'
PROFILE=LegacyConsumerPublicationProfile()


class Fixture:
    def __init__(self,root,kind):
        self.root,self.kind,self.calls=root,kind,[];self.selected=['status/governance-consumer-lifecycle.json']
        if kind=='no-change':self.selected=[]
        if kind=='out-of-scope':self.selected=['README.md']
        if kind=='ignored-generated':self.selected=['generated/unrelated.txt']
        if kind=='historical':self.selected=['governance/consumer-lifecycle/acceptance/00000001.json']
        self.environment={'GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY':'owner/repo','GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'2','GITHUB_OUTPUT':str(root.parent/'output'),'GITHUB_STEP_SUMMARY':str(root.parent/'summary')}
        self.gates=SimpleNamespace(validate_publication=self.gate)
    def run(self,command,**options):
        self.calls.append(('process',command,{k:str(v) if isinstance(v,Path) else v for k,v in options.items()}));args=command[1:];out=''
        if command[0]=='gh':return SimpleNamespace(returncode=0,stdout=json.dumps(self.api(command[4],json.loads(options['input']))),stderr='')
        if args[:2]==['diff','--name-only']:out='\0'.join(self.selected)+('\0' if self.selected else '')
        elif args[:2]==['ls-files','--others']:out=''
        elif args[:2]==['cat-file','-e']:return SimpleNamespace(returncode=0,stdout=b'',stderr=b'')
        elif args[:2]==['diff','--cached']:out='wrong.json\0' if self.kind=='staged-mismatch' else '\0'.join(self.selected)+'\0'
        elif args==['rev-parse','refs/remotes/origin/main']:out='b'*40+'\n'
        elif args==['rev-parse','HEAD']:out='a'*40+'\n'
        if args[:1]==['fetch'] and self.kind=='fetch-failure':raise subprocess.CalledProcessError(1,command,output='',stderr='fetch failed')
        return SimpleNamespace(returncode=0,stdout=out,stderr='')
    def gate(self,root,base):
        self.calls.append(('gate',str(root),base))
        if self.kind=='gate-failure':raise ValueError('Explicit consumer acceptance validation failed')
    def api(self,endpoint,payload):
        self.calls.append(('api',endpoint,copy.deepcopy(payload)))
        if self.kind=='pr-failure' and endpoint.endswith('/pulls'):raise ValueError('PR failed after push')
        if self.kind=='fourth-dispatch-failure' and endpoint.endswith('/consumer-lifecycle-guard.yml/dispatches'):raise ValueError('Fourth dispatch failed')
        return {'html_url':'https://github.com/owner/repo/pull/7'} if endpoint.endswith('/pulls') else {}


class WholeConsumerPublication(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old);temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name).resolve();self.root=self.base/'source';self.root.mkdir(mode=0o700)
    def compare(self,kind='normal',*,invocation='publish',arguments=None,subject=None):
        values=[]
        for side in ('original','ported'):
            fixture=Fixture(self.root,kind)
            for filename in ('output','summary'):
                p=self.base/filename
                if p.exists():p.unlink()
                p.write_text('retained prefix\n')
            if kind=='missing-output-parent':fixture.environment['GITHUB_OUTPUT']=str(self.base/'missing'/'output')
            if kind=='bad-ref':fixture.environment['GITHUB_REF']='refs/heads/feature'
            if kind=='symlink':
                p=self.root/'status/governance-consumer-lifecycle.json';p.parent.mkdir(exist_ok=True)
                if not p.is_symlink():p.symlink_to(self.base/'output')
            out,err=io.StringIO(),io.StringIO();returned=error=signal=None
            args=[] if arguments is None else arguments
            subject_now={'scope':'consumer-lifecycle','repository':'owner/repo','run_id':'123','attempt':'2',**(subject or {})}
            with redirect_stdout(out),redirect_stderr(err):
                if side=='original':
                    namespace={'__name__':'immutable_consumer_publisher','__file__':str(self.root/'scripts/publish_consumer_lifecycle.py')}
                    exec(compile(ORIGINAL.read_bytes(),'immutable_consumer_publisher','exec'),namespace)
                    namespace.update(ROOT=self.root,subprocess=fixture,os=SimpleNamespace(environ=fixture.environment))
                    def run():
                        with patch.dict(sys.modules,{'lib.governance_lifecycle.consumer_acceptance':fixture.gates}):
                            if invocation=='main':
                                with patch.object(sys,'argv',['publish_consumer_lifecycle.py',*args]):return namespace['main']()
                            return namespace['publish'](self.root,api=fixture.api,**subject_now)
                else:
                    kernel=ConsumerPublisher(self.root,path_factory=Path,process=fixture,api=LegacyOperationalPublicationAPI(fixture,PROFILE) if invocation=='main' else fixture.api,gates=fixture.gates,profile=PROFILE,environment=fixture.environment,argument_parser=lambda **kw:argparse.ArgumentParser(prog='publish_consumer_lifecycle.py',**kw),argv=args)
                    def run():return kernel.main() if invocation=='main' else kernel.publish(self.root,**subject_now)
                try:returned=run()
                except SystemExit as caught:signal={'type':'SystemExit','value':caught.code}
                except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
            values.append({'returned':returned,'error':error,'signal':signal,'stdout':out.getvalue(),'stderr':err.getvalue(),'calls':fixture.calls,'output':(self.base/'output').read_bytes(),'summary':(self.base/'summary').read_bytes()})
        self.assertEqual(values[0],values[1]);return values[1]
    def test_entire_original_consumer_publish_keeps_unconditional_gate_and_four_dispatches(self):
        result=self.compare();calls=result['calls'];gate=next(i for i,v in enumerate(calls) if v[0]=='gate');switch=next(i for i,v in enumerate(calls) if v[0]=='process' and v[1][1]=='switch');self.assertLess(gate,switch);self.assertEqual(len([v for v in calls if v[0]=='api']),5);self.assertTrue(calls[-1][1].endswith('/consumer-lifecycle-guard.yml/dispatches'))
    def test_original_default_scope_in_main_does_not_become_a_required_option(self):self.assertEqual(self.compare(invocation='main')['returned'],0)
    def test_original_help_parser_and_protected_ref_errors(self):
        for kind,args in [('normal',['--help']),('normal',['--scope','portfolio']),('bad-ref',[])]:
            with self.subTest(kind=kind,args=args):self.compare(kind,invocation='main',arguments=args)
    def test_original_no_change_skips_acceptance_and_all_native_writes(self):
        result=self.compare('no-change');self.assertEqual(result['returned'],None);self.assertFalse(any(v[0] in ('gate','api') for v in result['calls']))
    def test_original_scope_repository_and_positive_run_validation(self):
        for subject in ({'scope':'portfolio'},{'repository':'bad/name/extra'},{'run_id':'0'},{'attempt':'-1'}):
            with self.subTest(subject=subject):self.assertEqual(self.compare(subject=subject)['error']['type'],'ValueError')
    def test_original_out_of_scope_ignored_generated_and_historical_append_only_decisions(self):
        for kind in ('out-of-scope','ignored-generated','historical','symlink'):
            with self.subTest(kind=kind):self.compare(kind)
    def test_original_fetch_acceptance_and_staged_failures_do_not_reach_push(self):
        for kind in ('fetch-failure','gate-failure','staged-mismatch'):
            with self.subTest(kind=kind):
                result=self.compare(kind);self.assertIsNotNone(result['error']);self.assertFalse(any(v[0]=='api' for v in result['calls']))
    def test_original_partial_failure_after_push_PR_or_fourth_dispatch_preserves_exact_effect_order(self):
        for kind in ('pr-failure','fourth-dispatch-failure','missing-output-parent'):
            with self.subTest(kind=kind):self.assertIsNotNone(self.compare(kind)['error'])
    def test_original_provider_helper_preserves_exact_POST_arguments_json_and_empty_result(self):
        for raw in ('{"html_url":"https://example.invalid/7"}',''):
            calls=[]
            def run(command,**options):calls.append((command,options));return SimpleNamespace(stdout=raw)
            ns={'__name__':'immutable_consumer_publisher','__file__':str(self.root/'scripts/publish_consumer_lifecycle.py')};exec(compile(ORIGINAL.read_bytes(),'immutable_consumer_publisher','exec'),ns);ns['subprocess']=SimpleNamespace(run=run)
            old=ns['github_api']('repos/owner/repo/pulls',{'title':'Ä'});original_calls=copy.deepcopy(calls);calls.clear();actual=LegacyOperationalPublicationAPI(SimpleNamespace(run=run),PROFILE)('repos/owner/repo/pulls',{'title':'Ä'});self.assertEqual(actual,old);self.assertEqual(calls,original_calls)
    def test_reference_bytes_and_all_six_whole_original_functions_are_retained(self):
        self.assertEqual(hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),'10eb0e76f6640b32378700f87294c3db9289eea19ec3d60a6e2458ee4806283a');self.assertEqual({v.name for v in ast.parse(ORIGINAL.read_bytes()).body if isinstance(v,ast.FunctionDef)},{'git','allowed','selected_paths','github_api','publish','main'});self.assertEqual(tuple(SCOPES),('consumer-lifecycle',));self.assertEqual(LEDGERS,('governance/consumer-lifecycle/',))
    def test_consumer_protocol_rejects_other_scopes_and_keeps_fourth_dispatch(self):
        protocol=LegacyConsumerPublisherProtocol(str(self.root),scope='consumer-lifecycle',repository='owner/repo',run_id='123',attempt='2');options={'input':json.dumps({'ref':protocol.branch}),'text':True,'capture_output':True,'check':True};command=['gh','api','--method','POST','repos/owner/repo/actions/workflows/consumer-lifecycle-guard.yml/dispatches','--input','-'];self.assertEqual(protocol.request(command,options)['kind'],'post')
        with self.assertRaises(InputAdmissionError):LegacyConsumerPublisherProtocol(str(self.root),scope='portfolio',repository='owner/repo',run_id='123',attempt='2')
        command[4]='repos/other/repo/actions/workflows/consumer-lifecycle-guard.yml/dispatches'
        with self.assertRaises(InputAdmissionError):protocol.request(command,options)
