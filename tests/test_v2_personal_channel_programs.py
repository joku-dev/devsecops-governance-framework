"""Whole original programs over immutable histories and explicit fake GET transport."""
from pathlib import Path
from contextlib import redirect_stdout,redirect_stderr
import argparse,ast,copy,hashlib,io,json,os,shutil,subprocess,sys,tempfile,unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
from jsonschema import Draft202012Validator
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.providers.personal_channel_capture import LegacyPersonalChannelCapture
from lib.personal_channel_collection import PersonalProbeCollection
from lib.personal_channel_programs import PersonalStatementProgram,PersonalChannelCheckProgram,PersonalChannelEvidenceProgram
from lib.retained_argparse import parser_base,formatter_factory
from lib.providers.retained_argparse import capture_context

FIXTURE=ROOT/'tests/fixtures/v2-personal-channel-original'
CONTRACT=json.loads((FIXTURE/'contract.json').read_bytes())
AT='2026-11-15T12:00:00Z'
NAMES={'statement':'generate_personal_channel_probe.py','check':'check_lifecycle_personal_channel.py','evidence':'generate_personal_channel_evidence.py'}

def snapshot(root):
    return ({p.relative_to(root).as_posix():(p.read_bytes(),p.stat().st_mode&511) for p in root.rglob('*') if p.is_file()},
            {p.relative_to(root).as_posix():p.stat().st_mode&511 for p in root.rglob('*') if p.is_dir()})

def restore(root,before):
    files,dirs=before
    for p in sorted(root.rglob('*'),key=lambda p:len(p.parts),reverse=True):
        key=p.relative_to(root).as_posix()
        if p.is_dir():
            if key not in dirs:p.rmdir()
        elif key not in files:p.unlink()
    for name,(raw,mode) in files.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(mode)
    for name,mode in dirs.items():(root/name).chmod(mode)

class FakeFetch:
    def __init__(self,config):self.config=config;self.calls=[];self.pages=0;self.clocks=0
    def __call__(self,endpoint):
        self.calls.append(endpoint)
        if endpoint==self.config['endpoint']:return self.config['issue'].encode()
        assert endpoint.startswith(self.config['endpoint']+'/comments?per_page=100&page=')
        self.pages+=1;kind=self.config['kind']
        if kind=='race' and self.pages==2:return b'[]'
        if kind=='not-list':return b'{}'
        if kind=='page-budget':return json.dumps([{}]*100).encode()
        if kind=='invalid-json':return b'{'
        return self.config['comments'].encode()
    def clock(self):self.clocks+=1;return AT

class WholePersonalChannelPrograms(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old)
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.parent=Path(tmp.name).resolve();self.serial=0

    def fixture(self,*,prefix=True,kind='normal'):
        self.serial+=1;root=self.parent/('data-'+str(self.serial));root.mkdir(mode=0o700)
        for name,row in CONTRACT['oracle_files'].items():
            raw=(FIXTURE/row['fixture']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256']);self.assertEqual(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),row['git_blob'])
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(0o600)
        request=json.loads((root/'model/governance/lifecycle/personal-channel/00000001.json').read_bytes())
        if prefix:
            # Explicit original valid historical prefix in an isolated fixture;
            # the original repository and its real history are never changed.
            ledger=root/'governance/lifecycle/live-validation/transactions';found=False
            for p in sorted(ledger.glob('*.json')):
                if found:p.unlink()
                elif json.loads(p.read_bytes())['transaction_id']==request['receipt_head_ref']['id']:found=True
            self.assertTrue(found)
        captured=json.loads((root/'generated/reports/lifecycle-personal-channel/00000001.json').read_bytes())
        config={'endpoint':f"repos/{request['repository_id']}/issues/{request['discussion_number']}",
                'issue':captured['issue_response'],'comments':captured['comment_pages_before'][0],'kind':kind}
        tools=self.parent/('fake-transport-'+str(self.serial));tools.mkdir(mode=0o700);(tools/'config.json').write_text(json.dumps(config))
        fake='''import json,sys
from pathlib import Path
b=Path(__file__).resolve().parent;c=json.loads((b/'config.json').read_bytes());args=sys.argv[1:]
assert args[:5]==['api','--hostname','github.com','--method','GET'] and len(args)==6
endpoint=args[5];p=b/'calls.jsonl'
with p.open('a') as h:h.write(json.dumps(endpoint)+'\\n')
rows=p.read_text().splitlines();pages=sum('/comments?' in json.loads(x) for x in rows)
if endpoint==c['endpoint']:raw=c['issue'].encode()
else:
 assert endpoint.startswith(c['endpoint']+'/comments?per_page=100&page=')
 raw=b'[]' if c['kind']=='race' and pages==2 else b'{}' if c['kind']=='not-list' else json.dumps([{}]*100).encode() if c['kind']=='page-budget' else b'{' if c['kind']=='invalid-json' else c['comments'].encode()
sys.stdout.buffer.write(raw)
'''
        gh=tools/'gh';gh.write_text('#!'+sys.executable+'\n'+fake);gh.chmod(0o700)
        return root,config,tools

    def compare(self,program,root,config,tools,args=(),*,expected=0):
        before=snapshot(root)
        wrapper='''import runpy,sys
from datetime import datetime as NativeDatetime
import lib.governance_lifecycle.personal_probe as probe
class FrozenDatetime:
 @staticmethod
 def now(zone):return NativeDatetime.fromisoformat("2026-11-15T12:00:00+00:00").astimezone(zone)
probe.datetime=FrozenDatetime
path=sys.argv[1];sys.argv=sys.argv[1:]
runpy.run_path(path,run_name="__main__")
'''
        old=subprocess.run([sys.executable,'-B','-c',wrapper,str(root/'scripts'/NAMES[program]),*args],cwd=root,capture_output=True,timeout=120,
            env={**os.environ,'PYTHONPATH':str(root/'scripts'),'PYTHONDONTWRITEBYTECODE':'1','PATH':str(tools)+os.pathsep+os.environ['PATH'],'COLUMNS':'60','LINES':'24'})
        self.assertEqual(old.returncode,expected,old.stderr[-3000:]);after=snapshot(root);restore(root,before)
        fake=FakeFetch(config);context=RepositoryLifecycle(root,validator_class=Draft202012Validator,path_factory=Path,
            provider_factory=lambda c:LegacyPersonalChannelCapture(c,fetch=fake,clock=fake.clock))
        collector=PersonalProbeCollection(context)
        if program=='statement':kernel=PersonalStatementProgram(root,context,path_factory=Path)
        elif program=='evidence':kernel=PersonalChannelEvidenceProgram(root,context,path_factory=Path,process=subprocess,collector=collector)
        else:
            with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}):frame=capture_context()
            kernel=PersonalChannelCheckProgram(root,context,path_factory=Path,argument_parser=lambda **kw:parser_base(frame)(prog=NAMES[program],formatter_class=formatter_factory(frame),**kw),argv=list(args),collector=collector)
        out,err=io.StringIO(),io.StringIO();error=signal=None;code=0
        with redirect_stdout(out),redirect_stderr(err):
            try:kernel.main()
            except SystemExit as caught:code=caught.code;signal=caught.code
            except Exception as caught:code=1;error={'type':type(caught).__name__,'message':str(caught)}
        self.assertEqual(code,old.returncode,(error,old.stderr[-3000:]));self.assertEqual(out.getvalue().encode(),old.stdout)
        if error is None:self.assertEqual(err.getvalue().encode(),old.stderr)
        else:self.assertTrue(old.stderr.decode().endswith(error['type']+': '+error['message']+'\n'),(error,old.stderr[-3000:]))
        self.assertEqual(snapshot(root),after)
        calls=tools/'calls.jsonl';original_calls=[json.loads(x) for x in calls.read_text().splitlines()] if calls.is_file() else []
        self.assertEqual(fake.calls,original_calls)
        self.assertEqual(fake.clocks,1 if original_calls and error is None and program=='check' and '--replay' not in args else 0)
        return kernel,error,fake

    def test_statement_and_evidence_complete_original_main_guards_ignore_argv(self):
        for program in ('statement','evidence'):
            for args in ([],['--help','--unknown']):
                with self.subTest(program=program,args=args):self.compare(program,*self.fixture(),args)

    def test_whole_new_capture_and_previous_capture_keep_bytes_and_query_order(self):
        for previous in (False,True):
            root,cfg,tools=self.fixture();output=root/'generated/reports/lifecycle-personal-channel/new.json';args=['--output',str(output)]
            if previous:args+=['--previous-capture',str(root/'generated/reports/lifecycle-personal-channel/00000001.json')]
            _,_,fake=self.compare('check',root,cfg,tools,args);value=json.loads(output.read_bytes())
            self.assertFalse(value['result']['official_state']);self.assertFalse(value['result']['live_activation_approved']);self.assertFalse(value['result']['remediation_or_closure_authorized']);self.assertEqual(value['capture_method'],'github_api_get_via_gh');self.assertEqual(len(fake.calls),3)

    def test_whole_original_replay_and_invalid_combined_options(self):
        for bad in (False,True):
            root,cfg,tools=self.fixture();args=['--replay',str(root/'generated/reports/lifecycle-personal-channel/00000001.json')]
            if bad:args+=['--output',str(root/'forbidden')]
            self.compare('check',root,cfg,tools,args,expected=1 if bad else 0)

    def test_original_help_unknown_and_missing_output(self):
        for args,code in ((['--help'],0),(['--unknown'],2),([],1)):
            with self.subTest(args=args):self.compare('check',*self.fixture(),args,expected=code)

    def test_current_head_and_output_guards_keep_original_errors_without_fetch(self):
        for kind in ('stale','existing','outside-diagnostic'):
            root,cfg,tools=self.fixture(prefix=kind!='stale')
            output=root/'generated/reports/lifecycle-personal-channel/00000001.json' if kind=='existing' else root/'wrong-output.json' if kind=='outside-diagnostic' else root/'generated/reports/lifecycle-personal-channel/new.json'
            self.compare('check',root,cfg,tools,['--output',str(output)],expected=1)

    def test_race_nonlist_invalid_json_and_page_budget_keep_original_failures(self):
        for kind in ('race','not-list','invalid-json','page-budget'):
            with self.subTest(kind=kind):
                root,cfg,tools=self.fixture(kind=kind);_,error,fake=self.compare('check',root,cfg,tools,['--output',str(root/'generated/reports/lifecycle-personal-channel/new.json')],expected=1)
                self.assertIsNotNone(error);self.assertEqual(fake.clocks,0)

    def test_complete_new_capture_verification_keeps_original_git_selection_and_provider_comparison(self):
        for kind in ('accepted','new','provider-disagreement'):
            with self.subTest(kind=kind):
                root,cfg,tools=self.fixture()
                capture=root/'generated/reports/lifecycle-personal-channel/00000001.json';raw=capture.read_bytes()
                if kind!='accepted':capture.unlink()
                def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.STDOUT)
                git('init','--initial-branch=fixture');git('add','--all');git('-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null','-c','user.name=AXIOM isolated original test','-c','user.email=fixture@invalid.example','commit','--quiet','-m','Private original fixture base')
                if kind!='accepted':capture.write_bytes(raw);capture.chmod(0o600)
                if kind=='provider-disagreement':cfg={**cfg,'comments':'[]'};(tools/'config.json').write_text(json.dumps(cfg))
                before=snapshot(root)
                wrapper='''from pathlib import Path
import json
from datetime import datetime as NativeDatetime
import lib.governance_lifecycle.personal_probe as probe
import generate_personal_channel_evidence as report
class FrozenDatetime:
 @staticmethod
 def now(zone):return NativeDatetime.fromisoformat("2026-11-15T12:00:00+00:00").astimezone(zone)
probe.datetime=FrozenDatetime
print(json.dumps(report.verify_new_captures(Path.cwd(),"HEAD")))
'''
                old=subprocess.run([sys.executable,'-B','-c',wrapper],cwd=root,capture_output=True,timeout=120,env={**os.environ,'PYTHONPATH':str(root/'scripts'),'PYTHONDONTWRITEBYTECODE':'1','PATH':str(tools)+os.pathsep+os.environ['PATH']})
                self.assertEqual(old.returncode,1 if kind=='provider-disagreement' else 0,old.stderr[-2000:]);self.assertEqual(snapshot(root),before)
                fake=FakeFetch(cfg);context=RepositoryLifecycle(root,validator_class=Draft202012Validator,path_factory=Path,provider_factory=lambda c:LegacyPersonalChannelCapture(c,fetch=fake,clock=fake.clock))
                kernel=PersonalChannelEvidenceProgram(root,context,path_factory=Path,process=subprocess,collector=PersonalProbeCollection(context))
                if kind=='provider-disagreement':
                    with self.assertRaisesRegex(ValueError,'Personal channel provider state differs') as caught:kernel.verify_new_captures(root,'HEAD')
                    self.assertTrue(old.stderr.decode().endswith(type(caught.exception).__name__+': '+str(caught.exception)+'\n'))
                else:self.assertEqual(kernel.verify_new_captures(root,'HEAD'),json.loads(old.stdout))
                self.assertEqual(snapshot(root),before)
                original=[json.loads(x) for x in (tools/'calls.jsonl').read_text().splitlines()] if (tools/'calls.jsonl').is_file() else []
                self.assertEqual(fake.calls,original);self.assertEqual(fake.clocks,0 if kind=='accepted' else 1)

    def test_check_main_is_the_complete_original_function_after_only_explicit_bindings(self):
        raw=(FIXTURE/CONTRACT['sources']['scripts/check_lifecycle_personal_channel.py']['fixture']).read_bytes()
        old=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='main')
        cls=next(n for n in ast.parse((ROOT/'scripts/lib/personal_channel_programs.py').read_bytes()).body if isinstance(n,ast.ClassDef) and n.name=='PersonalChannelCheckProgram');new=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='main'));self.assertEqual(new.args.args.pop(0).arg,'self')
        bindings={'self.argument_parser':'argparse.ArgumentParser','self.Path':'Path','self.description':'__doc__','self.context.contracts.require':'require','self.context.adapter.strict_json':'strict_json','self.context.adapter.json_bytes':'json_bytes','self.context.personal.replay_probe_snapshot':'replay_probe_snapshot','self.collector.collect_probe':'collect_probe','self.root':'ROOT','self.REQUEST':'REQUEST'}
        class Restore(ast.NodeTransformer):
            def visit_Attribute(self,node):
                name=ast.unparse(node)
                return ast.copy_location(ast.parse(bindings[name],mode='eval').body,node) if name in bindings else self.generic_visit(node)
            def visit_Call(self,node):
                if ast.unparse(node.func)=='parser.parse_args':self_args=node.args;assert len(self_args)==1 and ast.unparse(self_args[0])=='self.argv';node.args=[]
                return self.generic_visit(node)
        self.assertEqual(ast.dump(Restore().visit(new),include_attributes=False),ast.dump(old,include_attributes=False))

if __name__=='__main__':unittest.main(verbosity=2)
