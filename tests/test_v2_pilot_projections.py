"""Whole immutable pilot projections, exact streams/files and closed history replay."""
from pathlib import Path
from unittest.mock import patch
import ast,copy,hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.pilot_projection_context import execute,PROGRAMS
from lib.pilot_projection_ports import NativeIO,Record,read_record,encode,captured_provider,AUTHORITY
from lib.synthetic_lifecycle_application import closed_validator,result_value
from lib.synthetic_lifecycle_io import ReplayIO
from lib.v2_boundary import violations
from lib.requirement_validation_budget import InputAdmissionError
import test_v2_synthetic_ledger_core as file_oracle
B=ROOT/'tests/fixtures/v2-pilot-projection-original';CONTRACT=json.loads((B/'contract.json').read_bytes())

class WholePilotProjection(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.parent=Path(self.temp.name).resolve();self.source=self.parent/'data';self.source.mkdir(mode=0o700)
        self.original_files={}
        for name,row in CONTRACT['sources'].items():
            raw=(B/row['fixture']).read_bytes();self.assertEqual(len(raw),row['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256']);self.assertEqual(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),row['git_blob']);self.original_files[name]=raw
            target=self.source/name;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);target.write_bytes(raw);target.chmod(0o600)
        self.serial=0

    def original(self,program,args=()):
        return subprocess.run([sys.executable,'-B',str(self.source/'scripts'/PROGRAMS[program][0]),*args],cwd=self.source,capture_output=True,timeout=120,env={**os.environ,'PYTHONPATH':str(self.source/'scripts'),'PYTHONDONTWRITEBYTECODE':'1'})

    def compare(self,program,args=(),native=False,expected=0):
        before=file_oracle.snapshot(self.source);process=self.original(program,args);self.assertEqual(process.returncode,expected,process.stderr[-3000:]);after=file_oracle.snapshot(self.source);file_oracle.restore(self.source,before)
        self.serial+=1;private=self.parent/f'private-{self.serial}';private.mkdir(mode=0o700)
        request={'profile':'whole original diagnostic projection prototype','program':program,'argv':list(args)};record=Record(private/'records',request,{'prototype':True});record.append({'kind':'execution-intent','request':request});mode='selected-files' if native else 'private-candidate';owner=NativeIO(record,mode=mode,cwd=str(self.source),private_state=private,product_root=ROOT)
        kernel=execute(str(self.source),str(self.source),program,list(args),owner,validator_class=closed_validator(owner,{'resources':[]}),provider_factory=captured_provider('legacy-lifecycle-capture-v1'));self.assertEqual(kernel['exit_code'],expected,kernel);self.assertEqual(kernel['stdout'].encode(),process.stdout)
        if kernel['kernel_exception'] is None:self.assertEqual(kernel['stderr'].encode(),process.stderr)
        else:
            error=kernel['kernel_exception'];self.assertTrue(process.stderr.decode().endswith(error['type']+': '+error['message']+'\n'),(kernel,process.stderr))
        if native:self.assertEqual(file_oracle.snapshot(self.source),after)
        else:
            self.assertEqual(file_oracle.snapshot(self.source),before)
            files,dirs=copy.deepcopy(before)
            for path,node in owner.projected_changes.items():
                relative=str(Path(path).relative_to(self.source))
                if node['kind']=='file':files[relative]=((record.blobs/node['content']['sha256']).read_bytes(),node['mode'])
                elif node['kind']=='directory':dirs[relative]=node['mode']
                elif node['kind']=='missing':files.pop(relative,None);dirs.pop(relative,None)
                else:self.fail('Unknown projected node')
            self.assertEqual((files,dirs),after)
        result=result_value(kernel,owner);record.finish('complete',result,owner.touched)
        _,_,retained,events,blob,closed=read_record(record.root);self.assertEqual(events[0],{'kind':'opened',**AUTHORITY});self.assertEqual(events[1],{'kind':'execution-intent','request':request});replay=ReplayIO(events,blob,mode,str(self.source))
        with patch('subprocess.Popen',side_effect=AssertionError('No original program')),patch('lib.providers.synthetic_lifecycle_io.NativeIO.read',side_effect=AssertionError('No selected source')):
            again=execute(str(self.source),str(self.source),program,list(args),replay,validator_class=closed_validator(replay,{'resources':[]}),provider_factory=captured_provider('legacy-lifecycle-capture-v1'));replay.finish()
        self.assertEqual(encode(result_value(again,replay)),encode(retained['result']));self.assertEqual(replay.touched,retained['touched_files']);self.assertTrue(closed());return kernel,after,record.root

    def test_complete_both_original_programs_history_reports_and_ignored_argv_both_modes(self):
        for program in PROGRAMS:
            for native in (False,True):
                for args in ([],['--help','--unknown','ignored']):
                    with self.subTest(program=program,native=native,args=args):
                        kernel,after,_=self.compare(program,args,native);self.assertIsNone(kernel['kernel_exception'])
                        index=json.loads(after[0]['status/governance-lifecycle-'+('pilot-actions' if program=='actions' else 'live-validation')+'.json'][0]);self.assertFalse(index['official_state']);self.assertFalse(index['live_activation_approved']);self.assertEqual(index['enforcement'],'report_only')
                        if program=='actions':self.assertEqual(index['finding_state'],'no_finding');self.assertEqual(index['counts']['actions'],0)
                        else:self.assertEqual(index['counts']['receipts'],2)

    def test_original_index_is_written_before_missing_report_directory_error_both_modes(self):
        for program in PROGRAMS:
            for native in (False,True):
                index_name='status/governance-lifecycle-'+('pilot-actions' if program=='actions' else 'live-validation')+'.json';(self.source/index_name).write_bytes(b'stale index before original main');directory=self.source/'generated/reports';backup=self.parent/f'reports-{self.serial}';shutil.move(str(directory),backup)
                try:kernel,after,_=self.compare(program,native=native,expected=1);self.assertEqual(kernel['kernel_exception']['type'],'FileNotFoundError');self.assertNotEqual(after[0][index_name][0],b'stale index before original main');self.assertIn('generated/reports/',kernel['kernel_exception']['message'])
                finally:shutil.move(str(backup),directory)

    def test_changed_operating_role_and_receipt_bytes_keep_original_errors(self):
        targets=[self.source/'model/governance/lifecycle/live-operating/00000001.json',self.source/'model/governance/lifecycle/live-pilot/role-bindings/00000001.json',next((self.source/'governance/lifecycle/live-validation/transactions').glob('*.json'))]
        for target in targets:
            raw=target.read_bytes();value=json.loads(raw)
            if 'revision' in value:value['revision']=999
            else:value['transaction_id']='transaction:'+'0'*64
            target.write_text(json.dumps(value))
            try:
                for native in (False,True):self.compare('actions',native=native,expected=1)
            finally:target.write_bytes(raw)

    def test_unknown_program_and_capture_profile_are_not_silently_replaced(self):
        with self.assertRaisesRegex(ValueError,'capture_profile'):captured_provider('unknown')
        with self.assertRaisesRegex(InputAdmissionError,'program_not_supported'):execute('/absent','/absent','unknown',[],object(),validator_class=object(),provider_factory=object())

    def test_complete_main_bodies_and_inherited_original_functions_are_retained(self):
        actual=ast.parse((ROOT/'scripts/lib/pilot_projection_programs.py').read_bytes());classes={n.name:n for n in actual.body if isinstance(n,ast.ClassDef)}
        mapping={'self.root':'ROOT','self.INDEX':'INDEX','self.REPORT':'REPORT','self.context.actions.project_actions':'project_actions','self.context.adapter.json_bytes':'json_bytes','self.context.admission.project_receipts':'project_receipts','self.context.store.load_transactions':'load_transactions','self.context.admission.VALIDATION_LEDGER':'VALIDATION_LEDGER','self.context.admission.load_operating':'load_operating','self.render':'render'}
        class Restore(ast.NodeTransformer):
            def visit_Attribute(self,node):
                text=ast.unparse(node)
                if text in mapping:return ast.copy_location(ast.Name(mapping[text],node.ctx),node)
                return self.generic_visit(node)
        for program,cls in (('actions','PilotActionProgram'),('validation','PilotValidationProgram')):
            tree=ast.parse(self.original_files['scripts/'+PROGRAMS[program][0]]);new=copy.deepcopy(classes[cls].body[0]);self.assertEqual(new.name,'main');new.args.args.pop(0);new=Restore().visit(new)
            if program=='validation':old=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');self.assertEqual(ast.dump(new,include_attributes=False),ast.dump(old,include_attributes=False))
            else:
                guard=tree.body[-1];self.assertIsInstance(guard,ast.If);self.assertEqual([ast.dump(n,include_attributes=False) for n in new.body],[ast.dump(n,include_attributes=False) for n in guard.body])
        for name in ('pilot_projection_programs.py','pilot_projection_context.py','pilot_projection_application.py'):
            self.assertEqual(violations('scripts/lib/'+name,(ROOT/'scripts/lib'/name).read_text()),[])

if __name__=='__main__':unittest.main(verbosity=2)
