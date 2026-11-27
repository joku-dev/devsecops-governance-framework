"""Unchanged original action preparation, original guards and source-free replay."""
from pathlib import Path
from unittest.mock import patch
from datetime import datetime as NativeDatetime
import ast,copy,hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from jsonschema import Draft202012Validator
from lib.pilot_action_preparation_context import execute
from lib.providers.pilot_action_preparation_clock import NativePreparationClock
from lib.pilot_action_preparation_clock import ReplayPreparationClock
from lib.providers.personal_channel_exclusive import NativeExclusive
from lib.personal_channel_exclusive import ReplayExclusive
from lib.personal_channel_private import PrivateExclusive
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.synthetic_lifecycle_io import ReplayIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
from lib.repository_lifecycle.actions import LifecyclePilotActions
from lib.providers.retained_argparse import capture_context
import test_v2_personal_channel_programs as reference

FIXTURE=ROOT/'tests/fixtures/v2-pilot-action-preparation-original'
CONTRACT=json.loads((FIXTURE/'contract.json').read_bytes())
AT='2026-11-15T12:00:00Z'

class FrozenDatetime:
    @staticmethod
    def now(zone):return NativeDatetime.fromisoformat(AT.replace('Z','+00:00')).astimezone(zone)

class WholePilotActionPreparation(unittest.TestCase):
    def setUp(self):
        fixture=reference.WholePersonalChannelPrograms();fixture.setUp();self.addCleanup(fixture.doCleanups);self.fixture=fixture
    def compare(self,kind='normal',native=False,api=False,*,history=None):
        data,_,tools=self.fixture.fixture(prefix=False)
        at=AT
        if history is not None:
            owner=data.parent/('history-'+str(self.fixture.serial));owner.mkdir(mode=0o700);moved=owner/('prototype-data-'+history);shutil.move(str(data),moved);data=moved
            helper=FIXTURE/'build_mock_history.py';self.assertEqual(hashlib.sha256(helper.read_bytes()).hexdigest(),CONTRACT['injected_history_builder']['sha256']);shutil.copyfile(helper,owner/'build_mock_history.py')
            original_helper=(FIXTURE/'original_test_actions.py.txt').read_bytes();self.assertEqual(hashlib.sha256(original_helper).hexdigest(),CONTRACT['additional_immutable_original_test_helper']['sha256'])
            (data/'tests').mkdir(mode=0o700);(data/'tests/original_test_actions.py').write_bytes(original_helper)
            build=subprocess.run([sys.executable,'-B',str(owner/'build_mock_history.py'),str(data),history],capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=180)
            self.assertEqual(build.returncode,0,build.stderr[-4000:]);description=json.loads(build.stdout);self.assertFalse(description['official_state']);self.assertEqual(description['transport'],'injected_test_transport')
            actions=sorted((data/'governance/lifecycle/pilot-actions/transactions').glob('*.json'))
            if kind=='progress':
                for path in actions[1:]:path.unlink()
            elif kind=='closure':actions[-1].unlink()
            at='2026-09-13T15:01:00Z'
        program=data/'scripts/prepare_lifecycle_pilot_action.py';raw=(FIXTURE/'prepare_lifecycle_pilot_action.py.txt').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),CONTRACT['sha256']);program.write_bytes(raw)
        body={'kind':'role_withdrawal','reason':'Explicit synthetic request; never current consent or authority.'}
        def ref(value):
            from lib.result_ledger import canonical_digest
            return {'id':value['transaction_id'],'digest':canonical_digest(value)}
        if kind in ('pass-decision','decision','stale-decision'):
            latest=json.loads(sorted((data/'governance/lifecycle/live-validation/transactions').glob('*.json'))[-1].read_bytes())
            body={'kind':'decision','failure_ref':ref(latest),'supersedes_ref':None,
                  'plan':{'action':'Synthetic preview only','owner_id':'github-user:81616324','target_at':'2026-11-16T12:00:00Z','work_url':'https://github.com/joku-dev/devsecops-governance-framework/issues/900000'}}
            if kind=='stale-decision':at=AT
        if kind in ('progress','closure','withdraw-decision','withdraw-closure'):
            actions=[json.loads(p.read_bytes()) for p in sorted((data/'governance/lifecycle/pilot-actions/transactions').glob('*.json'))]
            if kind=='progress':body={'kind':'progress','decision_ref':ref(actions[0]),'progress':'in_progress','evidence_note':'Synthetic preparation test; no work or approval claimed.'}
            elif kind=='closure':
                receipt=json.loads(sorted((data/'governance/lifecycle/live-validation/transactions').glob('*.json'))[-1].read_bytes())
                body={'kind':'closure','decision_ref':ref(actions[0]),'progress_ref':ref(actions[-1]),'passing_ref':ref(receipt)}
            else:body={'kind':'withdrawal','target_ref':ref(actions[0] if kind=='withdraw-decision' else actions[-1]),'reason':'Synthetic preview only'}
        if kind=='bad-body':body={'kind':'unexpected'}
        if kind=='no-receipts':
            for p in (data/'governance/lifecycle/live-validation/transactions').glob('*.json'):p.unlink()
        body_path=data/'body.json';body_path.write_text(json.dumps(body));output=data/'request.json'
        if kind=='existing':output.write_bytes(b'opaque original bytes\x00\xff')
        if kind=='missing-parent':output=data/'missing-parent/request.json'
        if kind=='invalid-json':body_path.write_bytes(b'{')
        number=0 if kind=='bad-number' else 900001
        args=['--body',str(body_path),'--discussion-number',str(number),'--output',str(output)]
        if kind=='help':args=['--help']
        if kind=='unknown':args=['--unknown']
        if kind=='missing-option':args=['--body',str(body_path)]
        prepare_arguments={'body':body,'discussion_number':number}
        if kind=='explicit-at':prepare_arguments['created_at']=AT
        if kind=='empty-at':prepare_arguments['created_at']=''
        before=reference.snapshot(data);trace=tools/'original-clock.jsonl'
        # The only original dependency replaced is this program's datetime
        # import. Its entire source and all imported validators run unchanged.
        wrapper='''import builtins,importlib,json,runpy,sys,types
from pathlib import Path
from datetime import datetime as NativeDatetime,timezone
path=sys.argv[1];trace=Path(sys.argv[2]);api=json.loads(sys.argv[3]);arguments=json.loads(sys.argv[4]);at=sys.argv[5]
class FrozenDatetime:
 @staticmethod
 def now(zone):
  with trace.open('a') as stream:stream.write('clock\\n')
  return NativeDatetime.fromisoformat(at.replace('Z','+00:00')).astimezone(zone)
native_import=builtins.__import__
def selected(name,globals=None,locals=None,fromlist=(),level=0):
 if name=='datetime' and globals and globals.get('__file__')==path:return types.SimpleNamespace(datetime=FrozenDatetime,timezone=timezone)
 module=native_import(name,globals,locals,fromlist,level)
 if name=='lib.governance_lifecycle.pilot_actions' and globals and globals.get('__file__')==path:
  actual=module.load_context
  def observed(*args,**kw):
   value=actual(*args,**kw)
   with trace.open('a') as stream:stream.write('context-complete\\n')
   return value
  module.load_context=observed
 return module
builtins.__import__=selected
if api:
 report=importlib.import_module('prepare_lifecycle_pilot_action');print(json.dumps(report.prepare(**arguments)))
else:
 sys.argv=[path,*arguments];runpy.run_path(path,run_name='__main__')
'''
        old=subprocess.run([sys.executable,'-B','-c',wrapper,str(program),str(trace),json.dumps(api),json.dumps(prepare_arguments if api else args),at],cwd=data,capture_output=True,timeout=180,
            env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(data/'scripts'),'COLUMNS':'60','LINES':'24'})
        expected_code=2 if kind in ('unknown','missing-option') else 1 if kind in ('no-receipts','pass-decision','bad-body','bad-number','invalid-json','existing','missing-parent','stale-decision') or history in ('roles-withdrawn','quarantined') else 0
        self.assertEqual(old.returncode,expected_code,(kind,history,old.stderr[-4000:]))
        expected=reference.snapshot(data);reference.restore(data,before);old_clock=trace.read_bytes().splitlines() if trace.exists() else []
        private=data.parent/('preparation-state-'+str(self.fixture.serial));private.mkdir(mode=0o700)
        record=Record(private/'records',{'prototype':'whole action preparation'},{'prototype':True});record.append({'kind':'execution-intent'})
        mode='selected-files' if native else 'private-candidate';owner=NativeIO(record,mode=mode,cwd=str(data),private_state=private,product_root=ROOT)
        with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}):frame=capture_context()
        common={'validator_class':Draft202012Validator,'provider_factory':LegacyRepositoryLifecycleCapture,'parser_context':frame,'prepare_arguments':prepare_arguments if api else None}
        phases=[];load_context=LifecyclePilotActions.load_context
        def observed_context(*args,**kw):
            value=load_context(*args,**kw);phases.append(b'context-complete');return value
        class SelectedDatetime:
            @staticmethod
            def now(zone):phases.append(b'clock');return NativeDatetime.fromisoformat(at.replace('Z','+00:00')).astimezone(zone)
        with patch('lib.providers.pilot_action_preparation_clock.datetime',SelectedDatetime),patch('subprocess.Popen',side_effect=AssertionError('No provider program in preparation')),patch.object(LifecyclePilotActions,'load_context',observed_context):
            actual=execute(str(data),str(data),args,owner,**common,exclusive_factory=NativeExclusive if native else PrivateExclusive,clock_factory=NativePreparationClock)
        self.assertFalse(record.capture_incomplete);self.assertEqual(actual['exit_code'],old.returncode,(actual,old.stderr[-4000:]))
        if api and old.returncode==0:self.assertEqual(actual['return_value'],json.loads(old.stdout));self.assertEqual(actual['stdout'],'')
        else:self.assertEqual(actual['stdout'].encode(),old.stdout)
        if actual['kernel_exception'] is None:self.assertEqual(actual['stderr'].encode(),old.stderr)
        else:
            error=actual['kernel_exception'];self.assertTrue(old.stderr.endswith((error['type']+': '+error['message']+'\n').encode()),(actual,old.stderr[-4000:]))
        clock_calls=[row for row in [json.loads(p.read_bytes())['value'] for p in sorted((record.root/'events').glob('*.json'))] if row.get('kind')=='intent' and row.get('action')=='pilot-action-preparation-clock']
        self.assertEqual(len(clock_calls),old_clock.count(b'clock'));self.assertEqual(phases,old_clock)
        if native:self.assertEqual(reference.snapshot(data),expected)
        else:
            self.assertEqual(reference.snapshot(data),before);files,dirs=map(dict,before)
            for name,value in owner.projected_changes.items():
                relative=Path(name).relative_to(data).as_posix()
                if value['kind']=='file':files[relative]=((record.blobs/value['content']['sha256']).read_bytes(),value['mode'])
                elif value['kind']=='directory':dirs[relative]=value['mode']
                else:self.fail(value)
            self.assertEqual((files,dirs),expected)
        record.finish('complete',{'exit_code':actual['exit_code'],'kernel_result':actual},owner.touched)
        _,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
        def inert(ref):
            value=cache[ref['sha256']];self.assertEqual(hashlib.sha256(value).hexdigest(),ref['sha256']);self.assertEqual(len(value),ref['bytes']);seen.add(ref['sha256']);return value
        shutil.rmtree(data);shutil.rmtree(tools);replay=ReplayIO(events,inert,mode,str(data))
        with patch('os.open',side_effect=AssertionError('No native input/output')),patch('subprocess.Popen',side_effect=AssertionError('No process')),patch('lib.providers.pilot_action_preparation_clock.datetime',side_effect=AssertionError('No native clock')):
            replayed=execute(str(data),str(data),args,replay,**common,exclusive_factory=ReplayExclusive if native else PrivateExclusive,clock_factory=ReplayPreparationClock);replay.finish()
        self.assertEqual(replayed,actual);self.assertEqual(replay.files,owner.files);self.assertEqual(replay.writes,owner.writes);self.assertEqual(replay.projected_changes,owner.projected_changes);self.assertEqual(seen,set(cache))
        for sha in seen:blob({'sha256':sha,'bytes':len(cache[sha])})
        self.assertTrue(closed())

    def test_original_whole_main_role_request_output_statement_both_modes_then_pure_replay(self):
        for native in (False,True):
            with self.subTest(native=native):self.compare(native=native)
    def test_original_prepare_API_default_explicit_and_empty_created_at_both_modes(self):
        for kind in ('normal','explicit-at','empty-at'):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare(kind,native,api=True)
    def test_original_output_existence_and_missing_parent_preserve_errors_and_no_implicit_mkdir(self):
        for kind in ('existing','missing-parent'):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare(kind,native)
    def test_original_parser_help_unknown_and_missing_required_option_both_modes(self):
        for kind in ('help','unknown','missing-option'):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare(kind,native)
    def test_original_no_receipt_pass_no_finding_body_schema_and_json_guards_both_modes(self):
        for kind in ('no-receipts','pass-decision','bad-body','bad-number','invalid-json'):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare(kind,native)

    def test_whole_original_decision_progress_closure_and_withdrawals_over_validated_injected_histories(self):
        for kind,history in (('decision','reopened'),('progress','closed'),('closure','closed'),('withdraw-decision','closed'),('withdraw-closure','closed')):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare(kind,native,history=history)

    def test_original_quarantine_withdrawn_roles_and_stale_evidence_remain_errors_in_both_modes(self):
        for kind,history in (('normal','roles-withdrawn'),('decision','quarantined'),('stale-decision','reopened')):
            for native in (False,True):
                with self.subTest(kind=kind,native=native):self.compare(kind,native,history=history)

    def test_entire_original_prepare_and_main_AST_after_only_explicit_ports(self):
        original=ast.parse((FIXTURE/'prepare_lifecycle_pilot_action.py.txt').read_bytes())
        whole=ast.parse((ROOT/'scripts/lib/pilot_action_preparation.py').read_bytes());cls=next(n for n in whole.body if isinstance(n,ast.ClassDef))
        old=next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name=='prepare')
        current=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='prepare'))
        self.assertEqual(current.args.args.pop(0).arg,'self')
        self.assertEqual(ast.unparse(current.body[0]),'if repo is _OMITTED:\n    repo = self.root');current.body.pop(0)
        self.assertEqual(ast.unparse(current.args.kw_defaults[0]),'_OMITTED');current.args.kw_defaults[0]=copy.deepcopy(old.args.kw_defaults[0])
        clock=copy.deepcopy(next(n.value.values[1] for n in old.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='at' for t in n.targets)))
        bindings={'self.context.actions.load_context':'load_context','self.context.actions.required_role':'required_role','self.context.actions.validate_context':'validate_context',
                  'self.context.contracts.require':'require','self.context.preparation.revision_ref':'revision_ref','self.context.kernel.transaction_ref':'transaction_ref',
                  'self.context.adapter.strict_json':'strict_json','self.context.adapter.json_bytes':'json_bytes','self.context.personal.statement_body':'statement_body',
                  'self.argument_parser':'argparse.ArgumentParser','self.description':'__doc__','self.Path':'Path','self.prepare':'prepare'}
        class Restore(ast.NodeTransformer):
            def visit_Attribute(self,node):
                name=ast.unparse(node)
                return ast.copy_location(ast.parse(bindings[name],mode='eval').body,node) if name in bindings else self.generic_visit(node)
            def visit_Call(self,node):
                name=ast.unparse(node.func)
                if name=='self.clock':
                    assert not node.args and not node.keywords;return copy.deepcopy(clock)
                if name=='parser.parse_args':assert len(node.args)==1 and ast.unparse(node.args[0])=='self.argv' and not node.keywords;node.args=[]
                return self.generic_visit(node)
        self.assertEqual(ast.dump(Restore().visit(current),include_attributes=False),ast.dump(old,include_attributes=False))
        guard=next(n for n in original.body if isinstance(n,ast.If));expected=ast.Module(body=copy.deepcopy(guard.body),type_ignores=[])
        main=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='main'));self.assertEqual(main.args.args.pop(0).arg,'self')
        converted=ast.Module(body=[Restore().visit(n) for n in main.body],type_ignores=[])
        self.assertEqual(ast.dump(converted,include_attributes=False),ast.dump(expected,include_attributes=False))

if __name__=='__main__':unittest.main(verbosity=2)
