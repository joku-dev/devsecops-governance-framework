"""Whole immutable V1 functions/CLIs and closed private/native reconstruction."""
from pathlib import Path
from unittest.mock import patch
import ast,copy,hashlib,io,json,os,shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.lifecycle_candidate_preparation_context import execute,compose,PROGRAMS
from lib.providers.synthetic_lifecycle_storage import Record,read_record,encode
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.synthetic_lifecycle_io import ReplayIO
from lib.synthetic_lifecycle_application import closed_validator
from lib.providers.retained_argparse import capture_context
from lib.requirement_validation_budget import InputAdmissionError
FIXTURE=ROOT/'tests/fixtures/v2-lifecycle-candidate-preparation-original';CONTRACT=json.loads((FIXTURE/'contract.json').read_bytes());AT='2026-09-13T12:01:00Z'

def snapshot(root):
    return ({p.relative_to(root).as_posix():(p.read_bytes(),p.stat().st_mode&511) for p in root.rglob('*') if p.is_file()},
            {p.relative_to(root).as_posix():p.stat().st_mode&511 for p in root.rglob('*') if p.is_dir()})

def restore(root,before):
    files,dirs=before
    for p in sorted(root.rglob('*'),key=lambda p:len(p.parts),reverse=True):
        name=p.relative_to(root).as_posix()
        if p.is_dir():
            if name not in dirs:p.rmdir()
        elif name not in files:p.unlink()
    for name,(raw,mode) in files.items():
        p=root/name
        if p.read_bytes()!=raw:p.write_bytes(raw)
        p.chmod(mode)
    for name,mode in dirs.items():(root/name).chmod(mode)

class WholeCandidatePreparation(unittest.TestCase):
    def setUp(self):
        previous=os.umask(0o077);self.addCleanup(os.umask,previous)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.parent=Path(self.temp.name).resolve();self.serial=0
        self.oracle={}
        for name,row in CONTRACT['oracle_files'].items():
            raw=(FIXTURE/row['fixture']).read_bytes();self.assertEqual(len(raw),row['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256']);self.assertEqual(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),row['git_blob']);self.oracle[name]=raw

    def fixture(self,program):
        self.serial+=1;root=self.parent/('source-'+str(self.serial));root.mkdir(mode=0o700)
        for name,raw in self.oracle.items():
            path=Path(name);self.assertFalse(path.is_absolute());self.assertNotIn('..',path.parts);p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(0o700 if CONTRACT['oracle_files'][name]['git_mode']=='100755' else 0o600)
        directory=root/'docs/examples/lifecycle-candidates';args=['--report',str(directory/(program+'-report.json')),'--context',str(directory/(program+'-context.json')),'--output',str(root/'generated/reports/lifecycle-candidates/result.json'),'--evaluated-at',AT]
        return root,args

    def compare(self,program,root,args,*,native=False,expected=0,cwd=None,columns=80):
        cwd=root if cwd is None else cwd;before=snapshot(root);env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':str(columns),'LINES':'24'}
        old=subprocess.run([sys.executable,'-B',str(root/'scripts'/PROGRAMS[program][0]),*args],cwd=cwd,capture_output=True,timeout=30,env=env)
        self.assertEqual(old.returncode,expected,old.stderr[-2500:]);after=snapshot(root);restore(root,before)
        private=self.parent/('private-'+str(self.serial));private.mkdir(mode=0o700)
        with patch.dict(os.environ,env):frame=capture_context()
        request={'prototype':'full diagnostic candidate preparation; not product acceptance','program':program,'argv':args,'parser_context':frame};record=Record(private/'records',request,{'prototype':True});record.append({'kind':'execution-intent','request':request});mode='selected-files' if native else 'private-candidate';owner=NativeIO(record,mode=mode,cwd=str(cwd),private_state=private,product_root=ROOT)
        kernel=execute(str(root),str(cwd),program,args,owner,validator_class=closed_validator(owner,{'resources':[]}),parser_context=frame)
        self.assertEqual(kernel['exit_code'],old.returncode,kernel);self.assertEqual(kernel['stdout'].encode(),old.stdout)
        if kernel['kernel_exception'] is None:self.assertEqual(kernel['stderr'].encode(),old.stderr)
        else:
            error=kernel['kernel_exception'];self.assertTrue(old.stderr.decode().endswith(error['type']+': '+error['message']+'\n'),(error,old.stderr[-2500:]))
        if native:self.assertEqual(snapshot(root),after)
        else:
            self.assertEqual(snapshot(root),before);files,dirs=copy.deepcopy(before)
            for name,value in owner.projected_changes.items():
                path=Path(name)
                if not path.is_relative_to(root):continue
                relative=path.relative_to(root).as_posix()
                if value['kind']=='file':files[relative]=(owner.projection.resolve(value['content']),value['mode'])
                elif value['kind']=='directory':dirs[relative]=value['mode']
                elif value['kind']=='missing':files.pop(relative,None);dirs.pop(relative,None)
                else:self.fail(value)
            self.assertEqual((files,dirs),after)
        self.assertFalse(record.capture_incomplete);record.finish('complete',kernel,owner.touched);_,_,retained,events,_,_=read_record(record.root);blobs={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
        def blob(ref):
            raw=blobs[ref['sha256']];self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);self.assertEqual(len(raw),ref['bytes']);seen.add(ref['sha256']);return raw
        shutil.rmtree(root);replay=ReplayIO(events,blob,mode,str(cwd))
        with patch.dict(os.environ,{'COLUMNS':'180'}),patch('shutil.get_terminal_size',side_effect=AssertionError('No terminal')),patch('subprocess.Popen',side_effect=AssertionError('No programs')),patch('lib.providers.synthetic_lifecycle_io.NativeIO.read',side_effect=AssertionError('No selected input')),patch('lib.providers.synthetic_lifecycle_output.NativeOutput.mkdir_one',side_effect=AssertionError('No output effects')),patch('lib.providers.synthetic_lifecycle_output.NativeOutput.write_chunk',side_effect=AssertionError('No output effects')):
            actual=execute(str(root),str(cwd),program,args,replay,validator_class=closed_validator(replay,{'resources':[]}),parser_context=frame);replay.finish()
        self.assertEqual(actual,kernel);self.assertEqual(replay.touched,retained['touched_files']);self.assertEqual(seen,set(blobs));return kernel,after,events

    def test_all_seven_original_function_ASTs_and_complete_source_lineage(self):
        actual=ast.parse((ROOT/'scripts/lib/lifecycle_candidate_preparation.py').read_bytes());count=0;lines=0
        for name,row in CONTRACT['files'].items():
            raw=(FIXTURE/(Path(name).name+'.txt')).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256']);self.assertEqual(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),row['git_blob']);lines+=len(raw.splitlines())
        for name,row in CONTRACT['classes'].items():
            cls=next(n for n in actual.body if isinstance(n,ast.ClassDef) and n.name==name);original=ast.parse((FIXTURE/(Path(row['source']).name+'.txt')).read_bytes());reverse={target:source for source,target in row['global_bindings'].items()}
            class Restore(ast.NodeTransformer):
                def visit_Attribute(self,node):
                    value=ast.unparse(node)
                    if value=='self.argument_parser':return ast.parse('argparse.ArgumentParser',mode='eval').body
                    if value in reverse:return ast.Name(id=reverse[value],ctx=ast.Load())
                    return self.generic_visit(node)
                def visit_Name(self,node):return ast.Name(id=reverse[node.id],ctx=ast.Load()) if isinstance(node.ctx,ast.Load) and node.id in reverse else node
                def visit_Call(self,node):
                    node=self.generic_visit(node)
                    if isinstance(node.func,ast.Attribute) and node.func.attr=='parse_args' and len(node.args)==1 and ast.unparse(node.args[0])=='self.argv':node.args=[]
                    return node
            for fn in cls.body:
                if not isinstance(fn,ast.FunctionDef) or fn.name=='__init__':continue
                fn=Restore().visit(copy.deepcopy(fn));self.assertEqual(fn.args.args.pop(0).arg,'self')
                if fn.name=='write_candidates':
                    prologue=fn.body.pop(0);self.assertEqual(ast.unparse(prologue),'if adapter is adapt_devsecops:\n    adapter = self.adapter')
                expected=next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name==fn.name);self.assertEqual(ast.dump(fn,include_attributes=False),ast.dump(expected,include_attributes=False));count+=1
        self.assertEqual(count,7);self.assertEqual(lines,161)
        matrix=json.loads((ROOT/'config/axiom-v2-functional-parity.json').read_bytes())
        for row in matrix['entrypoints']:
            if row['v1_path'] in CONTRACT['files']:
                self.assertEqual(row['v1_sha256'],CONTRACT['files'][row['v1_path']]['sha256']);self.assertEqual(row['v1_git_blob'],CONTRACT['files'][row['v1_path']]['git_blob'])

    def test_both_complete_programs_preserve_all_example_bytes_and_diagnostic_authority_both_modes(self):
        for program in PROGRAMS:
            for native in (False,True):
                with self.subTest(program=program,native=native):
                    root,args=self.fixture(program);kernel,after,_=self.compare(program,root,args,native=native)
                    raw=after[0]['generated/reports/lifecycle-candidates/result.json'][0];self.assertEqual(raw,after[0]['docs/examples/lifecycle-candidates/'+program+'-candidates.json'][0]);value=json.loads(raw)
                    self.assertFalse(value['official_state']);self.assertEqual(value['enforcement'],'report_only');self.assertEqual(value['trust_status'],'unverified');self.assertEqual(value['acceptance_status'],'not_evaluated');self.assertEqual(len(value['acceptance_gaps']),5)
                    self.assertTrue(all(row['granularity']==('control' if program=='devsecops' else 'gate') for row in value['candidates']))

    def test_original_context_digest_future_time_and_summary_rejections_both_programs_and_modes(self):
        for program in PROGRAMS:
            for attack in ('digest','future','summary','duplicate'):
                for native in (False,True):
                    with self.subTest(program=program,attack=attack,native=native):
                        root,args=self.fixture(program);report=Path(args[1]);context=Path(args[3]);value=json.loads(report.read_bytes());frame=json.loads(context.read_bytes())
                        if attack=='digest':frame['report_sha256']='0'*64
                        elif attack=='future':args[-1]='2026-09-13T11:59:59Z'
                        else:
                            if attack=='summary':value['summary']['total_controls' if program=='devsecops' else 'gate_count']=999
                            else:
                                items=value['controls' if program=='devsecops' else 'gates'];field='control_id' if program=='devsecops' else 'id';items[1][field]=items[0][field]
                            raw=(json.dumps(value)+'\n').encode();report.write_bytes(raw);frame['report_sha256']=hashlib.sha256(raw).hexdigest()
                        context.write_text(json.dumps(frame)+'\n');self.compare(program,root,args,native=native,expected=1)

    def test_original_output_input_overlap_and_nondiagnostic_root_path_guards_both_modes(self):
        for program in PROGRAMS:
            for attack in ('overlap','unapproved'):
                for native in (False,True):
                    root,args=self.fixture(program);args[5]=args[1] if attack=='overlap' else str(root/'unapproved/result.json');kernel,after,_=self.compare(program,root,args,native=native,expected=1);self.assertEqual(kernel['kernel_exception']['type'],'ContractError')

    def test_original_missing_input_and_directory_output_errors_both_modes(self):
        for program in PROGRAMS:
            for attack in ('missing','directory'):
                for native in (False,True):
                    root,args=self.fixture(program)
                    if attack=='missing':Path(args[1]).unlink()
                    else:target=Path(args[5]);target.mkdir(parents=True)
                    self.compare(program,root,args,native=native,expected=1)

    def test_full_original_parser_help_unknown_empty_streams_with_no_data_at_three_widths(self):
        for program in PROGRAMS:
            for columns in (40,80,120):
                for args,code in ((['--help'],0),(['--unknown'],2),([],2)):
                    root,_=self.fixture(program);kernel,_,events=self.compare(program,root,args,expected=code,columns=columns);self.assertEqual(len(events),3);self.assertEqual(kernel['original_exit_signal'],{'type':'SystemExit','value':code})

    def test_demo_report_with_nonsynthetic_context_is_rejected_without_claiming_real_evidence(self):
        for native in (False,True):
            root,args=self.fixture('devsecops');path=Path(args[3]);value=json.loads(path.read_bytes());value['synthetic']=False;path.write_text(json.dumps(value)+'\n');kernel,_,_=self.compare('devsecops',root,args,native=native,expected=1);self.assertEqual(kernel['kernel_exception']['message'],'Demo report requires declared synthetic context')

    def test_original_relative_paths_and_explicit_non_synthetic_context_remain_unverified(self):
        for program in PROGRAMS:
            for native in (False,True):
                root,args=self.fixture(program);context=Path(args[3]);value=json.loads(context.read_bytes());value['synthetic']=False
                if program=='devsecops':
                    report=Path(args[1]);body=json.loads(report.read_bytes());body['run_context']['source']='workflow';raw=(json.dumps(body)+'\n').encode();report.write_bytes(raw);value['report_sha256']=hashlib.sha256(raw).hexdigest()
                context.write_text(json.dumps(value)+'\n')
                for pos in (1,3,5):args[pos]=str(Path(args[pos]).relative_to(root))
                kernel,after,_=self.compare(program,root,args,native=native);value=json.loads(after[0]['generated/reports/lifecycle-candidates/result.json'][0]);self.assertFalse(value['source']['context']['synthetic']);self.assertEqual(value['trust_status'],'unverified');self.assertFalse(value['official_state'])

if __name__=='__main__':unittest.main(verbosity=2)
