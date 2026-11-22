"""Complete original atomic helper: real POSIX effects and original failure order."""
from pathlib import Path
from unittest.mock import patch
import ast,copy,errno,hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.intake_atomic_json import IntakeAtomicJSON

FIXTURE=ROOT/'tests/fixtures/v2-intake-atomic-json-original'
RAW=(FIXTURE/'consumer_intake_store.txt').read_bytes()
FUNCTION=next(n for n in ast.parse(RAW).body if isinstance(n,ast.FunctionDef) and n.name=='atomic_json')


def canonical_ast(value):
    """Retain every semantic AST field; 3.11 has no empty type_params field."""
    if isinstance(value,ast.AST):
        fields={key:canonical_ast(child) for key,child in ast.iter_fields(value)}
        if isinstance(value,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            fields.setdefault('type_params',[])
        return {'kind':type(value).__name__,'fields':fields}
    if isinstance(value,list):return [canonical_ast(child) for child in value]
    return value


def ast_digest(node):
    return hashlib.sha256(json.dumps(canonical_ast(node),sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()


class NativeFixture:
    """Inert observer around actual owned temporary files, never a live service."""
    def __init__(self,root,failure=None):
        self.root,self.failure=root,failure
        self.calls=[];self.descriptors={};self.handles=[];self.write_count=0
    def files(self):
        return {p.relative_to(self.root).as_posix():{'kind':'directory' if p.is_dir() else 'file',
            'mode':p.stat().st_mode&511,**({} if p.is_dir() else {'bytes':p.read_bytes()})}
            for p in sorted(self.root.rglob('*'))}
    def event(self,operation,arguments,callback):
        before=self.files();value=error=None
        try:value=callback();return value
        except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)};raise
        finally:self.calls.append({'operation':operation,'arguments':arguments,'result':value,'error':error,'before':before,'after':self.files()})
    def fail(self,operation,path):
        if self.failure==operation:raise OSError(errno.EIO,'Explicit isolated '+operation+' failure',str(path))
    def path(self,value):return value if isinstance(value,NativePath) else NativePath(self,Path(value))
    def mkstemp(self,*,dir):
        def effect():
            self.fail('mkstemp',dir)
            with patch('tempfile._get_candidate_names',return_value=iter(['axiomfixture'])):fd,name=tempfile.mkstemp(dir=os.fspath(dir))
            token=len(self.descriptors)+1;self.descriptors[token]={'fd':fd,'path':name};return {'descriptor':token,'temporary':name}
        value=self.event('mkstemp',{'directory':str(dir)},effect);return value['descriptor'],value['temporary']
    def fdopen(self,descriptor,mode):
        def effect():
            self.fail('fdopen',self.descriptors[descriptor]['path']);handle=os.fdopen(self.descriptors[descriptor]['fd'],mode);self.handles.append(handle);self.descriptors[descriptor]['handle']=handle
        self.event('fdopen',{'descriptor':descriptor,'mode':mode},effect)
        return NativeStream(self,descriptor,self.descriptors[descriptor]['handle'])
    def fsync(self,descriptor):
        def effect():self.fail('fsync',self.descriptors[descriptor]['path']);return os.fsync(self.descriptors[descriptor]['fd'])
        return self.event('fsync',{'descriptor':descriptor},effect)
    def chmod(self,path,mode):
        def effect():self.fail('chmod',path);return os.chmod(path,mode)
        return self.event('chmod',{'path':str(path),'mode':mode},effect)
    def replace(self,source,target):
        def effect():self.fail('replace',source);return os.replace(source,target)
        return self.event('replace',{'source':str(source),'target':str(target)},effect)
    def release(self):
        # Original fdopen failures can leave an opened descriptor. This is test
        # teardown, explicitly outside the original execution and its observations.
        for row in self.descriptors.values():
            if 'handle' in row:
                if not row['handle'].closed:row['handle'].close()
            else:
                try:os.close(row['fd'])
                except OSError as error:
                    if error.errno!=errno.EBADF:raise


class NativePath:
    def __init__(self,owner,value):self.owner,self.value=owner,value
    def __str__(self):return str(self.value)
    def __fspath__(self):return str(self.value)
    @property
    def parent(self):return NativePath(self.owner,self.value.parent)
    def mkdir(self,**options):
        def effect():self.owner.fail('mkdir',self.value);return self.value.mkdir(**options)
        return self.owner.event('mkdir',{'path':str(self),'options':options},effect)
    def unlink(self,**options):
        def effect():self.owner.fail('cleanup-unlink',self.value);return self.value.unlink(**options)
        return self.owner.event('unlink',{'path':str(self),'options':options},effect)


class NativeStream:
    def __init__(self,owner,token,stream):self.owner,self.token,self.stream=owner,token,stream
    def __enter__(self):return self
    def __exit__(self,kind,error,tb):
        def effect():self.stream.close();self.owner.fail('close',self.owner.descriptors[self.token]['path'])
        return self.owner.event('stream-close',{'descriptor':self.token},effect)
    def write(self,text):
        self.owner.write_count+=1
        def effect():
            if self.owner.failure=='write' and self.owner.write_count==6:
                self.stream.write(text[:max(1,len(text)//2)]);self.stream.flush();self.owner.fail('write',self.owner.descriptors[self.token]['path'])
            return self.stream.write(text)
        return self.owner.event('stream-write',{'descriptor':self.token,'text':text},effect)
    def flush(self):
        def effect():self.owner.fail('flush',self.owner.descriptors[self.token]['path']);return self.stream.flush()
        return self.owner.event('stream-flush',{'descriptor':self.token},effect)
    def fileno(self):
        def effect():assert self.stream.fileno()==self.owner.descriptors[self.token]['fd'];return self.token
        return self.owner.event('stream-fileno',{'descriptor':self.token},effect)


class WholeIntakeAtomicJSON(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old);temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name).resolve()/'work';self.root.mkdir(mode=0o700)
    def compare(self,*,failure=None,existing=False,mode=0o600,value=None,kind='file'):
        value={'text':'Größe\n\u0000','many':[1,True,None,{'b':'nested','a':0}]} if value is None else value
        observed=[]
        for side in ('original','ported'):
            if self.root.exists():shutil.rmtree(self.root)
            self.root.mkdir(mode=0o700);target=self.root/'nested/candidate.json'
            if existing:
                target.parent.mkdir(mode=0o700)
                if kind=='directory':target.mkdir(mode=0o700);(target/'untouched').write_bytes(b'owned earlier data')
                else:target.write_bytes(b'Previous target\n');target.chmod(0o400)
            native=NativeFixture(self.root,failure);returned=error=None
            try:
                if side=='original':
                    namespace={'Path':native.path,'os':native,'tempfile':native,'json':json};tree=ast.Module(body=[copy.deepcopy(FUNCTION)],type_ignores=[]);exec(compile(ast.fix_missing_locations(tree),'immutable_whole_atomic_json','exec'),namespace);call=namespace['atomic_json']
                else:call=IntakeAtomicJSON(path_factory=native.path,native=native,temporary=native).atomic_json
                try:returned=call(target,value,mode)
                except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
                observed.append({'returned':returned,'error':error,'events':native.calls,'files':native.files()})
            finally:native.release()
        self.assertEqual(observed[0],observed[1]);return observed[1]
    def test_complete_original_function_ast_and_immutable_source_contract(self):
        contract=json.loads((FIXTURE/'contract.json').read_bytes());self.assertEqual(contract['v1_reference'],'6b557fefe295b58272d2271326576ca3a3687197');self.assertEqual(contract['v1_path'],'scripts/lib/consumer_intake_store.py');self.assertEqual(subprocess.check_output(['git','show',contract['v1_reference']+':'+contract['v1_path']],cwd=ROOT),RAW);self.assertEqual(hashlib.sha256(RAW).hexdigest(),contract['sha256']);self.assertEqual(ast_digest(FUNCTION),contract['complete_original_function_canonical_AST_sha256']);tree=ast.parse((ROOT/'scripts/lib/intake_atomic_json.py').read_bytes());ported=next(n for n in tree.body if isinstance(n,ast.ClassDef));node=copy.deepcopy(next(n for n in ported.body if isinstance(n,ast.FunctionDef) and n.name=='atomic_json'));node.args.args.pop(0)
        class Restore(ast.NodeTransformer):
            def visit_Attribute(self,n):
                if isinstance(n.value,ast.Name) and n.value.id=='self' and n.attr in {'path_factory','native','temporary'}:return ast.copy_location(ast.Name({'path_factory':'Path','native':'os','temporary':'tempfile'}[n.attr],n.ctx),n)
                return self.generic_visit(n)
        self.assertEqual(ast.dump(Restore().visit(node),include_attributes=False),ast.dump(FUNCTION,include_attributes=False))
    def test_real_nested_parent_and_atomic_json_bytes_order_mode_and_cleanup(self):
        value=self.compare();self.assertIsNone(value['error']);self.assertEqual(value['files']['nested/candidate.json']['mode'],0o600);self.assertTrue(value['files']['nested/candidate.json']['bytes'].endswith(b'\n'));self.assertEqual(set(value['files']),{'nested','nested/candidate.json'});ops=[v['operation'] for v in value['events']];self.assertLess(ops.index('stream-flush'),ops.index('fsync'));self.assertLess(ops.index('fsync'),ops.index('stream-close'));self.assertLess(ops.index('stream-close'),ops.index('chmod'));self.assertLess(ops.index('chmod'),ops.index('replace'));self.assertEqual(ops[-1],'unlink')
    def test_existing_read_only_target_is_replaced_with_exact_original_new_mode(self):
        value=self.compare(existing=True);self.assertIsNone(value['error']);self.assertNotEqual(value['files']['nested/candidate.json']['bytes'],b'Previous target\n');self.assertEqual(value['files']['nested/candidate.json']['mode'],0o600)
    def test_explicit_nondefault_original_mode_is_retained_by_helper(self):
        self.assertEqual(self.compare(mode=0o640)['files']['nested/candidate.json']['mode'],0o640)
    def test_mkdir_and_mkstemp_errors_precede_any_stream_or_cleanup(self):
        for failure in ('mkdir','mkstemp'):
            with self.subTest(failure=failure):
                value=self.compare(failure=failure);self.assertEqual(value['error']['type'],'OSError');self.assertFalse(any(e['operation'] in ('fdopen','unlink') for e in value['events']))
    def test_fdopen_failure_keeps_original_final_unlink_and_original_descriptor_teardown_boundary(self):
        value=self.compare(failure='fdopen',existing=True);self.assertIsNotNone(value['error']);self.assertEqual(value['events'][-1]['operation'],'unlink');self.assertEqual(value['files']['nested/candidate.json']['bytes'],b'Previous target\n')
    def test_partial_write_then_native_close_and_final_unlink_preserve_previous_target(self):
        value=self.compare(failure='write',existing=True);self.assertEqual(value['error']['type'],'OSError');self.assertEqual(value['files']['nested/candidate.json']['bytes'],b'Previous target\n');self.assertFalse(any('tmpaxiomfixture' in name for name in value['files']));self.assertTrue(any(e['operation']=='stream-write' and e['error'] is not None and bool(e['after'].get('nested/tmpaxiomfixture',{}).get('bytes')) for e in value['events']))
    def test_flush_fsync_close_and_chmod_failures_do_not_replace_previous_target(self):
        for failure in ('flush','fsync','close','chmod'):
            with self.subTest(failure=failure):
                value=self.compare(failure=failure,existing=True);self.assertIsNotNone(value['error']);self.assertEqual(value['files']['nested/candidate.json']['bytes'],b'Previous target\n');self.assertFalse(any(e['operation']=='replace' for e in value['events']));self.assertEqual(value['events'][-1]['operation'],'unlink')
    def test_native_replace_failure_preserves_previous_target_and_removes_temporary(self):
        value=self.compare(failure='replace',existing=True);self.assertIsNotNone(value['error']);self.assertEqual(value['files']['nested/candidate.json']['bytes'],b'Previous target\n');self.assertEqual(set(value['files']),{'nested','nested/candidate.json'})
    def test_real_directory_replace_error_keeps_directory_contents_and_cleans_temporary(self):
        value=self.compare(existing=True,kind='directory');self.assertEqual(value['error']['type'],'IsADirectoryError');self.assertEqual(value['files']['nested/candidate.json/untouched']['bytes'],b'owned earlier data');self.assertFalse(any('tmpaxiomfixture' in name for name in value['files']))
    def test_final_cleanup_failure_after_successful_replace_retains_visible_new_target(self):
        value=self.compare(failure='cleanup-unlink',existing=True);self.assertIsNotNone(value['error']);self.assertNotEqual(value['files']['nested/candidate.json']['bytes'],b'Previous target\n');self.assertEqual(value['events'][-2]['operation'],'replace')
    def test_original_json_type_and_circular_failures_close_stream_and_remove_temporary(self):
        circular={};circular['circular']=circular
        for payload in ({'x':object()},circular):
            with self.subTest(kind=type(payload).__name__):
                value=self.compare(value=payload,existing=True);self.assertIsNotNone(value['error']);self.assertEqual(value['files']['nested/candidate.json']['bytes'],b'Previous target\n');self.assertEqual(value['events'][-1]['operation'],'unlink')
