"""Whole original operating helpers with real Git, fake GET and complete model replay."""
from pathlib import Path
from datetime import datetime as ActualDatetime
from unittest.mock import patch
import ast,copy,hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_personal_channel_programs as fixture
from test_v2_pilot_action_verification import git,commit
from lib.operating_verification_context import execute
from lib.providers.personal_channel_capture import LegacyPersonalChannelCapture
from lib.providers.operating_verification_protocol import NativeOperatingVerificationTransport,ReplayOperatingVerificationTransport,LegacyOperatingVerificationProtocol
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.pilot_run_intake_io import ReplayRunIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.pilot_run_intake_ports import ledger,transaction_name
from lib.requirement_validation_budget import InputAdmissionError
from jsonschema import Draft202012Validator

FIXTURE=ROOT/'tests/fixtures/v2-operating-verification-original'
AT='2026-11-15T12:00:00Z';FUTURE='2026-11-15T12:10:00Z'
CAPTURES='generated/reports/lifecycle-operating-acceptance';INDEX='status/governance-lifecycle-live.json'
WRAPPER='''import json,sys
from datetime import datetime as NativeDatetime
import lib.governance_lifecycle.personal_probe as probe
import lib.governance_lifecycle.operating_acceptance as op
class Clock:
 @staticmethod
 def now(zone):return NativeDatetime.fromisoformat(sys.argv[2].replace('Z','+00:00')).astimezone(zone)
probe.datetime=Clock
operation,at=sys.argv[4],json.loads(sys.argv[3])
if operation=='verify-new-captures':result=op.verify_new_captures('.',sys.argv[1],checked_at=at)
elif operation=='collect':result=op.collect('.',captured_at=at)
else:result=op.verify_provider('.')
print(json.dumps(result))
'''

class WholeOperatingVerification(unittest.TestCase):
    def setUp(self):
        c=fixture.WholePersonalChannelPrograms();c.setUp();self.addCleanup(c.doCleanups);self.fixture=c

    def selected(self,kind='normal'):
        root,config,tools=self.fixture.fixture(prefix=False)
        contract=json.loads((FIXTURE/'contract.json').read_bytes())
        for name,row in contract['files'].items():
            raw=(FIXTURE/row['fixture']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256']);p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(root/'scripts'),'PATH':str(tools)+os.pathsep+os.environ['PATH']}
        prepare='''import json,sys
from lib.governance_lifecycle.adapter import json_bytes
from lib.governance_lifecycle.personal_probe import statement_body
from lib.governance_lifecycle import operating_acceptance as op
p=op.Path(op.REQUEST_PATH);value=json.loads(p.read_bytes());value['implementation_manifest']=op.manifest('.');p.write_bytes(json_bytes(value))
print(json.dumps({'request':value,'statement':statement_body(value,disposition=sys.argv[1])}))
'''
        p=subprocess.run([sys.executable,'-B','-c',prepare,'reject' if kind=='inactive-rejection' else 'approve'],cwd=root,env=env,capture_output=True,timeout=180);self.assertEqual(p.returncode,0,p.stderr[-3000:]);made=json.loads(p.stdout);request=made['request'];repo=request['repository_id'];number=request['discussion_number']
        comment={'id':900000001,'body':made['statement'],'user':{'id':81616324,'type':'User'},'performed_via_github_app':None,'issue_url':f'https://api.github.com/repos/{repo}/issues/{number}','html_url':f'https://github.com/{repo}/pull/{number}#issuecomment-900000001','created_at':'2026-11-15T11:59:59Z','updated_at':'2026-11-15T11:59:59Z'}
        config.update(endpoint=f'repos/{repo}/issues/{number}',issue=json.dumps({'number':number,'html_url':f'https://github.com/{repo}/pull/{number}','pull_request':{'url':'explicit simulated test discussion'}}),comments=json.dumps([comment]),kind='normal')
        (tools/'config.json').write_text(json.dumps(config));gh=tools/'gh';raw=gh.read_text();at=raw.index('import json,sys');gh.write_text(raw[:at]+"import sys\nsys.stderr.buffer.write(b'opaque\\xffoperating-provider\\r\\n');sys.stderr.buffer.flush()\n"+raw[at:]);gh.chmod(0o700)
        make='''import sys
from lib.governance_lifecycle.adapter import json_bytes
from lib.governance_lifecycle import operating_acceptance as op
root=op.Path('.');snapshot=op.collect(root,captured_at=sys.argv[1]);directory=root/op.CAPTURES;directory.mkdir(parents=True);(directory/'00000001.json').write_bytes(json_bytes(snapshot))
index=op.projection(root);path=root/op.INDEX;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(json_bytes(index));print(index['live_activation_approved'])
'''
        p=subprocess.run([sys.executable,'-B','-c',make,FUTURE if kind=='future' else AT],cwd=root,env=env,capture_output=True,timeout=180);self.assertEqual(p.returncode,0,p.stderr[-4000:]);self.assertEqual(p.stdout.strip(),b'False' if kind=='inactive-rejection' else b'True')
        if kind in ('changed-new','withdrawn-provider'):comment['body']='Explicit simulated provider deletion';config['comments']=json.dumps([comment]);(tools/'config.json').write_text(json.dumps(config))
        calls=tools/'calls.jsonl';calls.unlink()
        git(root,'init','--initial-branch=isolated-operating-verification');git(root,'config','gc.auto','0');git(root,'config','maintenance.auto','false')
        capture=root/CAPTURES/'00000001.json';capture_raw=capture.read_bytes();index=root/INDEX;index_raw=index.read_bytes()
        if kind in ('normal','future','manifest-changed','changed-new','inactive-rejection'):capture.unlink()
        if kind=='missing-index':index.unlink()
        elif kind in ('changed-index','withdrawn-provider'):index.write_bytes(b'Explicit previous projection\r\n\xff')
        base=commit(root)
        if not capture.exists():capture.write_bytes(capture_raw)
        index.write_bytes(index_raw)
        if kind=='manifest-changed':
            p=root/'requirements-validation.txt';p.write_bytes(p.read_bytes()+b'\nExplicit simulated implementation change\n')
        return root,tools,'missing-operating-base' if kind=='bad-base' else base

    def compare(self,kind='normal',native=True,checked_at=None,operation='verify-new-captures'):
        root,tools,base=self.selected(kind);before=fixture.snapshot(root);calls=tools/'calls.jsonl';env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(root/'scripts'),'PATH':str(tools)+os.pathsep+os.environ['PATH']}
        old=subprocess.run([sys.executable,'-B','-c',WRAPPER,base,AT,json.dumps(checked_at),operation],cwd=root,env=env,capture_output=True,timeout=180)
        expected=1 if kind in ('future','manifest-changed','changed-new','withdrawn-provider','bad-base') else 0
        self.assertEqual(old.returncode,expected,(kind,old.stderr[-4000:]));self.assertEqual(fixture.snapshot(root),before);queries=calls.read_bytes() if calls.exists() else b''
        if calls.exists():calls.unlink()
        state=root.parent/('operating-state-'+root.name);state.mkdir(mode=0o700);record=Record(state/'records',{'prototype':'whole operating verifier'},{'prototype':True});record.append({'kind':'execution-intent'})
        mode='selected-files' if native else 'private-candidate';owner=NativeRunIO(record,mode=mode,cwd=str(root),private_state=state,product_root=ROOT,ledger=ledger(str(root)),transaction_name=transaction_name)
        class Clock:
            @staticmethod
            def now(zone):return ActualDatetime.fromisoformat(AT.replace('Z','+00:00')).astimezone(zone)
        common={'validator_class':Draft202012Validator,'provider_factory':lambda context,port:LegacyPersonalChannelCapture(context,fetch=port.fetch,clock=port.clock),'checked_at':checked_at,'operation':operation}
        with patch('lib.providers.personal_channel_transport.datetime',Clock):actual=execute(str(root),str(root),base,owner,**common,transport_factory=lambda io,path,emit:NativeOperatingVerificationTransport(io,path,emit_stderr=emit,provider_executable=str(tools/'gh')))
        self.assertFalse(record.capture_incomplete);self.assertEqual(actual['exit_code'],old.returncode,actual);self.assertEqual(actual['stdout'],'')
        raw_stderr=b''.join((record.blobs/part['blob']['sha256']).read_bytes() if 'blob' in part else part['text'].encode() for part in actual['stderr_parts']);self.assertTrue(old.stderr.startswith(raw_stderr))
        if expected:
            error=actual['kernel_exception'];self.assertTrue(old.stderr.endswith((error['type']+': '+error['message']+'\n').encode()),(actual,old.stderr[-3000:]))
            wanted={'future':'Operating acceptance capture is future-dated','manifest-changed':'Implementation changed after acceptance request','changed-new':'New operating acceptance differs from GitHub','withdrawn-provider':'Operating acceptance changed or was withdrawn at GitHub; capture the correction first'}
            if kind in wanted:self.assertEqual(error['message'],wanted[kind])
        else:self.assertEqual(actual['return_value'],json.loads(old.stdout));self.assertEqual(old.stderr,raw_stderr)
        self.assertEqual(fixture.snapshot(root),before);self.assertEqual(calls.read_bytes() if calls.exists() else b'',queries)
        record.finish('complete',{'exit_code':actual['exit_code'],'kernel_result':actual},owner.touched)
        _,_,_,events,blob,closed=read_record(record.root)
        runs=[(i,row) for i,row in enumerate(events) if row.get('kind')=='intent' and row.get('action')=='personal-read-process' and row['arguments']['kind']=='git-run']
        if kind in ('accepted','changed-index','missing-index','withdrawn-provider') and operation=='verify-new-captures':
            self.assertEqual(len(runs),1)
            wire=json.loads(blob(events[runs[0][0]+1]['value']));self.assertIsNone(wire['original_error']);self.assertIsNone(wire['effective_encoding']);self.assertIsNone(wire['signal_context'])
            if kind=='missing-index':self.assertNotEqual(wire['returncode'],0);self.assertTrue(blob(wire['stderr']));self.assertNotIn(blob(wire['stderr']),raw_stderr)
        cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
        def inert(ref):
            raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return raw
        shutil.rmtree(root);shutil.rmtree(tools);replay=ReplayRunIO(events,inert,mode,str(root),ledger=ledger(str(root)),transaction_name=transaction_name)
        with patch('os.open',side_effect=AssertionError('No selected IO')),patch('subprocess.Popen',side_effect=AssertionError('No Git/provider')),patch('lib.providers.personal_channel_transport.datetime',side_effect=AssertionError('No native clock')):
            pure=execute(str(root),str(root),base,replay,**common,transport_factory=lambda io,path,emit:ReplayOperatingVerificationTransport(io,path,emit_stderr=emit));replay.finish()
        self.assertEqual(pure,actual);self.assertEqual(replay.files,owner.files);self.assertEqual(replay.writes,owner.writes);self.assertEqual(seen,set(cache))
        for key,raw in cache.items():blob({'sha256':key,'bytes':len(raw)})
        self.assertTrue(closed())

    def test_all_three_whole_original_function_ASTs_only_declared_ports(self):
        original=ast.parse((fixture.FIXTURE/fixture.CONTRACT['oracle_files']['scripts/lib/governance_lifecycle/operating_acceptance.py']['fixture']).read_bytes())
        cls=next(n for n in ast.parse((ROOT/'scripts/lib/operating_verification.py').read_bytes()).body if isinstance(n,ast.ClassDef))
        names={'self.Path':'Path','self.context.operating.request':'request','self.context.operating.captures':'captures','self.context.provider.collect_bound':'collect_bound','self.context.operating.assess':'assess','self.context.operating.prior_comments':'prior_comments','self.context.contracts.require':'require','self.context.operating.proof':'proof','self.context.operating.effective':'effective','self.context.operating.CAPTURES':'CAPTURES','self.context.operating.INDEX':'INDEX','self.context.operating.projection':'projection','self.context.operating.manifest':'manifest','self.context.contracts.timestamp':'timestamp','self.git.check_output':'subprocess.check_output','self.git.run':'subprocess.run','self.collect':'collect','self.verify_provider':'verify_provider'}
        class Restore(ast.NodeTransformer):
            def visit_Attribute(self,node):return ast.copy_location(ast.parse(names[ast.unparse(node)],mode='eval').body,node) if ast.unparse(node) in names else self.generic_visit(node)
        for name in ('collect','verify_provider','verify_new_captures'):
            old=next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name==name);new=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name));self.assertEqual(new.args.args.pop(0).arg,'self')
            if new.args.defaults:
                self.assertEqual(ast.unparse(new.args.defaults[0]),'_OMITTED');self.assertEqual(ast.unparse(new.body.pop(0)),'if repo is _OMITTED:\n    repo = self.root');new.args.defaults=copy.deepcopy(old.args.defaults)
            self.assertEqual(ast.dump(Restore().visit(new),include_attributes=False),ast.dump(old,include_attributes=False))

    def test_new_capture_and_already_accepted_capture_whole_model_both_modes(self):
        for kind in ('normal','accepted'):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare(kind,native)

    def test_changed_or_missing_base_index_rechecks_provider_even_without_new_capture(self):
        for kind in ('changed-index','missing-index'):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare(kind,native,checked_at=AT)

    def test_future_capture_changed_implementation_and_changed_new_statement_rejected(self):
        for kind in ('future','manifest-changed','changed-new'):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare(kind,native)

    def test_withdrawal_detected_when_publishing_changed_effective_index(self):
        for native in (False,True):
            with self.subTest(native=native):self.compare('withdrawn-provider',native)

    def test_inactive_rejected_capture_keeps_original_no_provider_activation_branch(self):
        for native in (False,True):
            with self.subTest(native=native):self.compare('inactive-rejection',native)

    def test_whole_collect_and_verify_provider_APIs_default_and_explicit_capture_time(self):
        for operation in ('collect','verify-provider'):
            for native in (False,True):
                with self.subTest(operation=operation,native=native):self.compare('accepted',native,operation=operation)

    def test_missing_Git_base_original_check_output_error_distinct_from_captured_run(self):
        for native in (False,True):
            with self.subTest(native=native):self.compare('bad-base',native)

    def test_protocol_rejects_other_git_objects_options_and_provider_writes(self):
        p=LegacyOperatingVerificationProtocol();root='/retained/source';good={'command':['git','show','HEAD:'+INDEX],'cwd':root,'capture_output':True}
        self.assertFalse(p.request('git-run',good,root,root)['text'])
        for bad in ({**good,'command':['git','show','HEAD:other-path']},{**good,'command':['git','show','--exec=bad:'+INDEX]},{**good,'capture_output':1},{**good,'cwd':'/other'},{**good,'text':True}):
            with self.assertRaises(InputAdmissionError):p.request('git-run',bad,root,root)
        with self.assertRaises(InputAdmissionError):p.request('get',{'endpoint':'repos/owner/repo/issues/1','method':'POST'},root,root)
