"""Whole original typed wrapper plus original publisher over identical bound ports."""
from pathlib import Path
from types import ModuleType,SimpleNamespace
from unittest.mock import patch
from contextlib import redirect_stdout,redirect_stderr
import argparse,ast,copy,hashlib,io,json,os,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.typed_publication import TypedEvidencePublisher,ADDITIONAL_LEDGERS,LEDGERS,SCOPES
from lib.operational_publication import LEDGERS as BASE_LEDGERS,SCOPES as BASE_SCOPES
from lib.providers.operational_publication_profile import LegacyOperationalPublicationProfile
from lib.providers.operational_publication_api import LegacyOperationalPublicationAPI
from lib.providers.typed_publication_protocol import LegacyTypedPublisherProtocol
from lib.requirement_validation_budget import InputAdmissionError
from test_v2_consumer_publication import Fixture as ConsumerFixture
TYPED=ROOT/'tests/fixtures/v2-typed-publication-original/publish_typed_evidence_assurance_update.txt'
GENERIC=ROOT/'tests/fixtures/v2-operational-publisher-original/publish_operational_update.py.txt'
PROFILE=LegacyOperationalPublicationProfile()


class TypedFixture(ConsumerFixture):
    def __init__(self,root,kind,scope):
        super().__init__(root,kind)
        self.selected=[name+'new.json' for name in ADDITIONAL_LEDGERS]
        if scope=='portfolio':self.selected=['generated/reports/portfolio-onboarding-status.json']
        if kind=='no-change':self.selected=[]
        if kind=='out-of-scope':self.selected=['README.md']
        if kind=='ignored-generated':self.selected=['generated/unrelated.txt']
        if kind=='historical':self.selected=[ADDITIONAL_LEDGERS[0]+'old.json']
    def run(self,command,**options):
        if command[0]=='git' and command[1:3]==['cat-file','-e']:
            self.calls.append(('process',command,{k:str(v) if isinstance(v,Path) else v for k,v in options.items()}));return SimpleNamespace(returncode=0 if self.kind=='historical' else 128,stdout=b'',stderr=b'')
        return super().run(command,**options)


class WholeTypedPublication(unittest.TestCase):
    def setUp(self):
        import tempfile
        old=os.umask(0o077);self.addCleanup(os.umask,old);temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.base=Path(temporary.name).resolve();self.root=self.base/'source';self.root.mkdir(mode=0o700)
    def compare(self,kind='normal',invocation='main',scope='typed-evidence',argv=None):
        results=[]
        for side in ('original','ported'):
            fixture=TypedFixture(self.root,kind,scope)
            for name in ('output','summary'):(self.base/name).write_text('Earlier metadata\n')
            if kind=='bad-ref':fixture.environment['GITHUB_REF']='refs/heads/feature'
            out,err=io.StringIO(),io.StringIO();value=error=signal=None;arguments=['--scope',scope] if argv is None else argv
            with redirect_stdout(out),redirect_stderr(err):
                if side=='original':
                    publisher=ModuleType('publish_operational_update');publisher.__file__=str(self.root/'scripts/publish_operational_update.py');exec(compile(GENERIC.read_bytes(),'immutable_publisher','exec'),publisher.__dict__);publisher.ROOT=self.root;publisher.subprocess=fixture;publisher.os=SimpleNamespace(environ=fixture.environment)
                    wrapper={'__name__':'immutable_typed_publisher','__file__':str(self.root/'scripts/publish_typed_evidence_assurance_update.py')}
                    with patch.dict(sys.modules,{'publish_operational_update':publisher}):exec(compile(TYPED.read_bytes(),'immutable_typed_publisher','exec'),wrapper)
                    def run():
                        if invocation=='configure':return wrapper['configure']()
                        if invocation=='configure-twice':wrapper['configure']();return wrapper['configure']()
                        if invocation=='main':
                            with patch.object(sys,'argv',['publish_typed_evidence_assurance_update.py',*arguments]):return wrapper['main']()
                        wrapper['configure']();return publisher.publish(self.root,scope=scope,repository='owner/repo',run_id='123',attempt='2')
                else:
                    publisher=TypedEvidencePublisher(self.root,path_factory=Path,process=fixture,api=LegacyOperationalPublicationAPI(fixture,PROFILE),gates=fixture.gates,profile=PROFILE,environment=fixture.environment,argument_parser=lambda **kw:argparse.ArgumentParser(prog='publish_typed_evidence_assurance_update.py',**kw),argv=arguments)
                    def run():
                        if invocation=='configure':return publisher.configure()
                        if invocation=='configure-twice':publisher.configure();return publisher.configure()
                        if invocation=='main':return publisher.main()
                        publisher.configure();return publisher.publish(self.root,scope=scope,repository='owner/repo',run_id='123',attempt='2')
                try:value=run()
                except SystemExit as caught:signal={'type':'SystemExit','value':caught.code}
                except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
            results.append({'value':value,'error':error,'signal':signal,'stdout':out.getvalue(),'stderr':err.getvalue(),'calls':fixture.calls,'output':(self.base/'output').read_bytes(),'summary':(self.base/'summary').read_bytes(),'ledgers':publisher.LEDGERS,'scopes':publisher.SCOPES})
        self.assertEqual(results[0],results[1]);return results[1]
    def test_whole_typed_main_publishes_all_three_additional_append_only_ledgers(self):
        result=self.compare();self.assertEqual(result['value'],0);self.assertIsNone(result['error']);self.assertEqual(len([x for x in result['calls'] if x[0]=='api']),4);self.assertTrue(all(path in result['ledgers'] for path in ADDITIONAL_LEDGERS));self.assertEqual(len([x for x in result['calls'] if x[0]=='process' and x[1][1:3]==['cat-file','-e']]),3)
    def test_exact_original_configure_side_effects_and_repeat_semantics_are_isolated(self):
        before=(copy.deepcopy(BASE_LEDGERS),copy.deepcopy(BASE_SCOPES))
        once=self.compare(invocation='configure');twice=self.compare(invocation='configure-twice');self.assertEqual(once['value'],None);self.assertEqual(once['calls'],[]);self.assertEqual(twice['ledgers'],(*BASE_LEDGERS,*ADDITIONAL_LEDGERS,*ADDITIONAL_LEDGERS));self.assertEqual((BASE_LEDGERS,BASE_SCOPES),before)
    def test_original_configured_direct_publisher_and_other_original_scope_are_preserved(self):
        self.assertIsNone(self.compare(invocation='publish')['error']);self.assertIsNone(self.compare(scope='portfolio')['error'])
    def test_original_help_required_scope_invalid_scope_and_protected_main_guard(self):
        for kind,args in [('normal',['--help']),('normal',[]),('normal',['--scope','no-such-scope']),('bad-ref',['--scope','typed-evidence'])]:
            with self.subTest(kind=kind,args=args):self.compare(kind,argv=args)
    def test_original_no_change_scope_append_only_fetch_and_staging_failures(self):
        for kind in ('no-change','out-of-scope','ignored-generated','historical','fetch-failure','staged-mismatch'):
            with self.subTest(kind=kind):self.compare(kind)
    def test_original_partial_POST_failure_keeps_already_ordered_Git_effects(self):self.assertIsNotNone(self.compare('pr-failure')['error'])
    def test_typed_native_protocol_accepts_only_exact_extended_paths_and_original_branch(self):
        protocol=LegacyTypedPublisherProtocol(str(self.root),scope='typed-evidence',repository='owner/repo',run_id='123',attempt='2');options={'cwd':self.root,'capture_output':True,'text':True,'check':True}
        spec=protocol.request(['git','add','--',*[name+'new.json' for name in ADDITIONAL_LEDGERS]],options);self.assertEqual(spec['kind'],'git')
        for command in (['git','add','--','status/unselected/new.json'],['git','push','origin','HEAD:refs/heads/main']):
            with self.subTest(command=command),self.assertRaises(InputAdmissionError):protocol.request(command,options)
        for name in ADDITIONAL_LEDGERS:self.assertFalse(protocol.request(['git','cat-file','-e','HEAD:'+name+'new.json'],{'cwd':self.root,'capture_output':True,'check':False})['text'])
    def test_all_original_typed_functions_and_full_path_admission_AST_are_retained(self):
        contract=json.loads((TYPED.parent/'contract.json').read_bytes());self.assertEqual(hashlib.sha256(TYPED.read_bytes()).hexdigest(),contract['sha256']);original={n.name:n for n in ast.parse(TYPED.read_bytes()).body if isinstance(n,ast.FunctionDef)};core=ast.parse((ROOT/'scripts/lib/typed_publication.py').read_bytes());klass=next(n for n in core.body if isinstance(n,ast.ClassDef))
        class Restore(ast.NodeTransformer):
            def visit_Attribute(self,n):
                if isinstance(n.value,ast.Name) and n.value.id=='self' and n.attr in ('SCOPES','LEDGERS'):return ast.Attribute(value=ast.Name(id='publisher',ctx=ast.Load()),attr=n.attr,ctx=n.ctx)
                if ast.unparse(n)=='super().main':return ast.parse('publisher.main',mode='eval').body
                if ast.unparse(n)=='self.configure':return ast.Name(id='configure',ctx=ast.Load())
                return self.generic_visit(n)
        for name in ('configure','main'):
            fn=copy.deepcopy(next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name==name));fn.args.args=fn.args.args[1:];self.assertEqual(ast.dump(Restore().visit(fn)),ast.dump(original[name]))
        generic=ast.parse((ROOT/'scripts/lib/operational_publication.py').read_bytes());generic_class=next(n for n in generic.body if isinstance(n,ast.ClassDef))
        class RestorePathRules(ast.NodeTransformer):
            def visit_Attribute(self,n):
                if isinstance(n.value,ast.Name) and n.value.id=='self' and n.attr in ('SCOPES','LEDGERS'):return ast.Name(id=n.attr,ctx=n.ctx)
                return self.generic_visit(n)
        for name in ('allowed','selected_paths'):
            oldfn=next(n for n in generic_class.body if isinstance(n,ast.FunctionDef) and n.name==name);newfn=copy.deepcopy(next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name==name));self.assertEqual(ast.dump(oldfn),ast.dump(RestorePathRules().visit(newfn)))
        self.assertEqual(tuple(SCOPES),tuple(BASE_SCOPES))
        for stem,parent,method in [('protocol','LegacyPublisherProtocol','request'),('process','NativeOperationalPublicationProcess','admit_git')]:
            old=ast.parse((ROOT/f'scripts/lib/providers/operational_publication_{stem}.py').read_bytes());new=ast.parse((ROOT/f'scripts/lib/providers/typed_publication_{stem}.py').read_bytes());oldfn=next(n for n in ast.walk(old) if isinstance(n,ast.FunctionDef) and n.name==method);newfn=next(n for n in ast.walk(new) if isinstance(n,ast.FunctionDef) and n.name==method)
            for n in ast.walk(newfn):
                if isinstance(n,ast.ImportFrom) and n.module=='lib.typed_publication':n.module='lib.operational_publication'
            self.assertEqual(ast.dump(oldfn),ast.dump(newfn))
