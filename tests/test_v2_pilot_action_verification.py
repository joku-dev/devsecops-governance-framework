"""Whole original fresh action verification, complete histories and no substituted validator."""
from pathlib import Path
from datetime import datetime as ActualDatetime
from unittest.mock import patch
import ast,copy,hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_pilot_action_intake as seed
from test_v2_personal_channel_programs import snapshot
from lib.pilot_action_verification_context import execute
from lib.pilot_action_verification import PilotActionVerification
from lib.providers.personal_channel_capture import LegacyPersonalChannelCapture
from lib.providers.pilot_action_verification_protocol import LegacyActionVerificationProtocol,NativeActionVerificationTransport,ReplayActionVerificationTransport
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.pilot_run_intake_io import ReplayRunIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.pilot_run_intake_ports import transaction_name,ledger
from lib.requirement_validation_budget import InputAdmissionError
from jsonschema import Draft202012Validator

FIXTURE=ROOT/'tests/fixtures/v2-action-verification-history'
AT='2026-09-13T15:00:30Z'
WRAPPER='''import json,sys
from datetime import datetime as NativeDatetime
import lib.governance_lifecycle.personal_probe as probe
from lib.governance_lifecycle.pilot_actions import verify_new_actions
class Clock:
 @staticmethod
 def now(zone):return NativeDatetime.fromisoformat(sys.argv[2].replace('Z','+00:00')).astimezone(zone)
probe.datetime=Clock
options={} if sys.argv[3]=='null' else {'checked_at':json.loads(sys.argv[3])}
print(json.dumps(verify_new_actions('.',sys.argv[1],**options)))
'''

def git(root,*args):
    env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1')
    return subprocess.check_output(['git','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-C',str(root),*args],env=env)

def commit(root):
    git(root,'add','--all');git(root,'-c','user.name=Isolated AXIOM fixture','-c','user.email=fixture@invalid.example','-c','commit.gpgsign=false','commit','--quiet','-m','Immutable fixture base')
    return git(root,'rev-parse','HEAD').decode().strip()

class WholePilotActionVerification(unittest.TestCase):
    def setUp(self):
        case=seed.WholePilotActionIntake();case.setUp();self.addCleanup(case.doCleanups);self.fixture=case

    def selected(self,kind='normal'):
        root,tools,_=self.fixture.selected('normal');parent=root.parent
        contract=json.loads((FIXTURE/'contract.json').read_bytes())
        original=(FIXTURE/'original_test_actions.py.txt').read_bytes();builder=(FIXTURE/'build_history.py.txt').read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(),contract['original_sha256']);self.assertEqual(hashlib.sha256(builder).hexdigest(),contract['builder_sha256'])
        (root/'tests').mkdir(exist_ok=True);(root/'tests/original_test_actions.py').write_bytes(original)
        program=parent/'build-action-verification-history.py';program.write_bytes(builder)
        scenario={'stale-head':'reopened','future':'future','unclaimed':'unclaimed-capture','withdrawal':'closure-withdrawn','role-withdrawal':'roles-withdrawn'}.get(kind,'closed')
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(root/'scripts')}
        old=subprocess.run([sys.executable,'-B',str(program),str(root),scenario],capture_output=True,env=env,timeout=180)
        self.assertEqual(old.returncode,0,old.stderr[-4000:])
        responses=json.loads((parent/'provider-responses.json').read_bytes())
        actions=sorted((root/'governance/lifecycle/pilot-actions/transactions').glob('*.json'));last=json.loads(actions[-1].read_bytes())
        endpoint=f"repos/{last['request']['repository_id']}/issues/{last['request']['discussion_number']}"
        target=endpoint
        if kind in ('changed-decision','changed-progress'):
            selected=next(json.loads(p.read_bytes()) for p in actions if json.loads(p.read_bytes())['request']['body']['kind']==('decision' if kind=='changed-decision' else 'progress'))
            if kind=='changed-progress':selected=json.loads(actions[-2].read_bytes())
            target=f"repos/{selected['request']['repository_id']}/issues/{selected['request']['discussion_number']}"
        if kind in ('changed-current','changed-decision','changed-progress'):
            key=target+'/comments?per_page=100&page=1';comments=json.loads(responses[key]);comments[0]['body']+='\nChanged provider statement';responses[key]=json.dumps(comments)
        config={'responses':responses,'race':kind=='provider-race'};(tools/'verification-responses.json').write_text(json.dumps(config))
        fake='''import json,sys
from pathlib import Path
b=Path(__file__).resolve().parent;c=json.loads((b/'verification-responses.json').read_bytes());args=sys.argv[1:]
assert len(args)==6 and args[:5]==['api','--hostname','github.com','--method','GET']
endpoint=args[5];p=b/'calls.jsonl'
with p.open('a') as stream:stream.write(json.dumps(endpoint)+'\\n')
count=sum('/comments?' in json.loads(line) for line in p.read_text().splitlines())
sys.stderr.buffer.write(b'opaque\\xffaction-provider\\r\\n');sys.stderr.buffer.flush()
sys.stdout.buffer.write(b'[]' if c['race'] and count==2 else c['responses'][endpoint].encode())
'''
        (tools/'gh').write_text('#!'+sys.executable+'\n'+fake);(tools/'gh').chmod(0o700)
        calls=tools/'calls.jsonl'
        if calls.exists():calls.unlink()
        git(root,'init','--initial-branch=isolated-verification');git(root,'config','gc.auto','0');git(root,'config','maintenance.auto','false')
        path=actions[-1];raw=path.read_bytes();mode=path.stat().st_mode&511
        if kind!='accepted':path.unlink()
        base=commit(root)
        if kind!='accepted':path.write_bytes(raw);path.chmod(mode)
        return root,tools,'missing-original-action-base' if kind=='bad-base' else base

    def compare(self,kind='normal',native=True,checked_at=None):
        root,tools,base=self.selected(kind);before=snapshot(root);calls=tools/'calls.jsonl'
        env={**os.environ,'PYTHONPATH':str(root/'scripts'),'PATH':str(tools)+os.pathsep+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1'}
        old=subprocess.run([sys.executable,'-B','-c',WRAPPER,base,AT,json.dumps(checked_at)],cwd=root,capture_output=True,env=env,timeout=180)
        expected=0 if kind in ('normal','accepted','withdrawal','role-withdrawal') else 1
        self.assertEqual(old.returncode,expected,(kind,old.stderr[-4000:]))
        self.assertEqual(snapshot(root),before);old_calls=calls.read_bytes() if calls.exists() else b''
        if calls.exists():calls.unlink()
        state=root.parent/('verification-private-state-'+root.name);state.mkdir(mode=0o700);record=Record(state/'records',{'prototype':'whole original new-action helper'},{'prototype':True});record.append({'kind':'execution-intent'})
        mode='selected-files' if native else 'private-candidate';owner=NativeRunIO(record,mode=mode,cwd=str(root),private_state=state,product_root=ROOT,ledger=ledger(str(root)),transaction_name=transaction_name)
        class Clock:
            @staticmethod
            def now(zone):return ActualDatetime.fromisoformat(AT.replace('Z','+00:00')).astimezone(zone)
        common={'validator_class':Draft202012Validator,'provider_factory':lambda context,port:LegacyPersonalChannelCapture(context,fetch=port.fetch,clock=port.clock),'checked_at':checked_at}
        with patch('lib.providers.personal_channel_transport.datetime',Clock):
            actual=execute(str(root),str(root),base,owner,**common,transport_factory=lambda io,path,emit:NativeActionVerificationTransport(io,path,emit_stderr=emit,provider_executable=str(tools/'gh')))
        self.assertFalse(record.capture_incomplete);self.assertEqual(actual['exit_code'],expected,actual)
        raw_err=b''.join((record.blobs/part['blob']['sha256']).read_bytes() if 'blob' in part else part['text'].encode() for part in actual['stderr_parts'])
        self.assertEqual(actual['stdout'],'');self.assertTrue(old.stderr.startswith(raw_err))
        if expected:
            error=actual['kernel_exception'];self.assertTrue(old.stderr.endswith((error['type']+': '+error['message']+'\n').encode()),(kind,actual,old.stderr[-3000:]))
            messages={'changed-current':'New action differs from independently retrieved personal statement','changed-decision':'Action prerequisite was changed or withdrawn at the provider','changed-progress':'Action prerequisite was changed or withdrawn at the provider','future':'Action claims future recording time','stale-head':'New action is stale against merged evidence','unclaimed':'New action requires an actual GitHub capture','provider-race':'Personal discussion changed during capture'}
            if kind in messages:self.assertEqual(error['message'],messages[kind])
        else:self.assertEqual(actual['return_value'],json.loads(old.stdout));self.assertEqual(old.stderr,raw_err)
        self.assertEqual(snapshot(root),before);self.assertEqual(calls.read_bytes() if calls.exists() else b'',old_calls)
        record.finish('complete',{'exit_code':actual['exit_code'],'kernel_result':actual},owner.touched)
        _,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
        def inert(ref):
            raw=cache[ref['sha256']];self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);self.assertEqual(len(raw),ref['bytes']);seen.add(ref['sha256']);return raw
        shutil.rmtree(root);shutil.rmtree(tools);replay=ReplayRunIO(events,inert,mode,str(root),ledger=ledger(str(root)),transaction_name=transaction_name)
        with patch('os.open',side_effect=AssertionError('No source IO')),patch('subprocess.Popen',side_effect=AssertionError('No Git/provider')),patch('lib.providers.personal_channel_transport.datetime',side_effect=AssertionError('No native clock')):
            pure=execute(str(root),str(root),base,replay,**common,transport_factory=lambda io,path,emit:ReplayActionVerificationTransport(io,path,emit_stderr=emit));replay.finish()
        self.assertEqual(pure,actual);self.assertEqual(replay.files,owner.files);self.assertEqual(replay.writes,owner.writes);self.assertEqual(replay.projected_changes,owner.projected_changes);self.assertEqual(seen,set(cache))
        for key,raw in cache.items():blob({'sha256':key,'bytes':len(raw)})
        self.assertTrue(closed())

    def test_complete_original_function_AST_after_only_declared_ports(self):
        old=next(n for n in ast.parse((seed.FIXTURE/'pilot_actions.py.txt').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='verify_new_actions')
        cls=next(n for n in ast.parse((ROOT/'scripts/lib/pilot_action_verification.py').read_bytes()).body if isinstance(n,ast.ClassDef));new=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='verify_new_actions'));self.assertEqual(new.args.args.pop(0).arg,'self')
        names={'self.Path':'Path','self.context.actions.load_context':'load_context','self.git.check_output':'subprocess.check_output','self.context.actions.ACTION_LEDGER':'ACTION_LEDGER','self.context.contracts.require':'require','self.context.provider.collect_bound':'collect_bound','self.context.actions.assess_action_comments':'assess_action_comments','self.context.actions.proof_projection':'proof_projection','self.context.contracts.timestamp':'timestamp','self.context.kernel.transaction_ref':'transaction_ref','self.context.actions.validate_context':'validate_context','self.context.actions.state_at':'state_at','self.context.actions.prior_statements':'prior_statements'}
        class Restore(ast.NodeTransformer):
            def visit_Attribute(self,node):return ast.copy_location(ast.parse(names[ast.unparse(node)],mode='eval').body,node) if ast.unparse(node) in names else self.generic_visit(node)
        self.assertEqual(ast.dump(Restore().visit(new),include_attributes=False),ast.dump(old,include_attributes=False))

    def test_new_closure_rechecks_current_statement_and_both_prerequisites_both_modes(self):
        for native in (False,True):
            with self.subTest(native=native):self.compare(native=native)

    def test_accepted_base_does_not_recheck_new_actions_both_modes(self):
        for native in (False,True):
            with self.subTest(native=native):self.compare('accepted',native)

    def test_changed_current_decision_or_progress_statement_rejected_both_modes(self):
        for kind in ('changed-current','changed-decision','changed-progress'):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare(kind,native)

    def test_future_recording_and_stale_evidence_head_rejected_both_modes(self):
        for kind in ('future','stale-head'):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare(kind,native)

    def test_withdrawal_and_role_withdrawal_keep_original_permission_reducing_branch(self):
        for kind in ('withdrawal','role-withdrawal'):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare(kind,native)

    def test_missing_Git_base_unclaimed_capture_and_provider_race_diagnostics(self):
        for kind in ('bad-base','unclaimed','provider-race'):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare(kind,native)

    def test_explicit_and_empty_check_time_preserve_original_clock_selection(self):
        for checked_at in (AT,''):
            for native in (False,True):
                with self.subTest(native=native,checked_at=checked_at):self.compare(native=native,checked_at=checked_at)

    def test_protocol_admits_only_original_action_tree_and_personal_GET(self):
        protocol=LegacyActionVerificationProtocol();root='/retained/original/source'
        command=['git','ls-tree','-r','--name-only','accepted-base','--','governance/lifecycle/pilot-actions']
        good={'command':command,'cwd':root,'text':True}
        self.assertEqual(protocol.request('git-tree',good,root,root)['original_arguments'],command)
        for bad in ({**good,'command':['git','branch','new-branch']},{**good,'command':command[:-1]+['governance/lifecycle/live-validation']},{**good,'command':command[:4]+['--exec=untrusted',*command[5:]]},{**good,'cwd':'/another/source'},{**good,'text':1},{**good,'extra':True}):
            with self.assertRaises(InputAdmissionError):protocol.request('git-tree',bad,root,root)
        for kind,args in [('write',good),('get',{'endpoint':'repos/owner/repo/issues/1/comments?per_page=100&page=11'}),('get',{'endpoint':'repos/owner/repo/issues/1','method':'POST'})]:
            with self.assertRaises(InputAdmissionError):protocol.request(kind,args,root,root)
