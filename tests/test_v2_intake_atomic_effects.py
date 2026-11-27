"""Native durable atomic IO and whole-helper replay with no filesystem or processes."""
from pathlib import Path
from unittest.mock import patch
import copy,errno,hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.intake_atomic_ports import Record,read_record,program,native
from lib.intake_atomic_effects import AtomicScope,ReplayAtomicEffects
from lib.providers.intake_atomic_effects import NativeAtomicEffects
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError


class Faults(NativeAtomicEffects):
    failure=None
    def invoke(self,operation,args,effect):
        if operation=='write':self.write_calls=getattr(self,'write_calls',0)+1
        if self.failure==operation and (operation!='write' or self.write_calls==6):
            if operation=='write':
                row=self.descriptors[args['descriptor']];row['stream'].write(args['text'][:max(1,len(args['text'])//2)]);row['stream'].flush()
            elif operation=='close':effect()
            raise OSError(errno.EIO,'Explicit isolated '+operation+' failure')
        return effect()


class AtomicEffectsExecution(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old);tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.base=Path(tmp.name).resolve();self.output=self.base/'selected';self.output.mkdir(mode=0o700);self.state=self.base/'records';self.state.mkdir(mode=0o700);self.value={'items':[1,True,None,{'text':'Größe\n\u0000'}]};self.target=self.output/'candidate.json'
    def capture(self,*,failure=None,value=None,existing=False,target_directory=False):
        if existing:
            self.target.unlink(missing_ok=True);self.target.write_bytes(b'Previous target\n');self.target.chmod(0o400)
        if target_directory:self.target.mkdir(mode=0o700);(self.target/'untouched').write_bytes(b'Owned previous content')
        request={'profile':'test-whole-atomic-helper','scope_root':str(self.output),'cwd':str(self.output),'targets':['candidate.json','native-capture.json']};record=Record(self.state,request,{'test_context':'supporting atomic helper; no installed acceptance'});record.append({'kind':'execution-intent','request':request});scope=AtomicScope(str(self.output),request['targets'],cwd=request['cwd']);effects=Faults(scope,record,forbidden_roots=(ROOT,));effects.failure=failure;error=None
        try:
            try:program(effects).atomic_json('candidate.json',self.value if value is None else value)
            except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
        finally:resources=effects.release_resources()
        result={'exit_code':0 if error is None else 1,'error':error};state='incomplete' if record.capture_incomplete else 'complete';record.finish(state,result,{});request,source,retained,events,blob,closed=read_record(record.root);self.assertEqual(state,retained['state']);return effects,record,result,resources,request,events,blob,closed
    def replay(self,captured,*,value=None):
        effects,record,result,resources,request,events,blob,closed=captured;cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};pure=ReplayAtomicEffects(effects.scope,events[2:-1],lambda ref:cache[ref['sha256']]);moved=self.base.with_name(self.base.name+'-absent');self.base.rename(moved)
        try:
            error=None
            with patch('os.open',side_effect=AssertionError('No filesystem replay')),patch('subprocess.Popen',side_effect=AssertionError('No program replay')):
                try:program(pure).atomic_json('candidate.json',self.value if value is None else value)
                except (IntegrityError,InputAdmissionError):raise
                except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
                pure.finish()
            self.assertEqual(error,result['error']);self.assertEqual(pure.state.current,effects.state.current)
        finally:moved.rename(self.base)
        for name,raw in cache.items():self.assertEqual(blob({'sha256':name,'bytes':len(raw)}),raw)
        self.assertTrue(closed());return pure
    def test_whole_original_helper_real_atomic_replace_and_inert_full_replay(self):
        c=self.capture();self.assertEqual(c[2],{'exit_code':0,'error':None});self.assertEqual(self.target.read_bytes(),(json.dumps(self.value,sort_keys=True,indent=2)+'\n').encode());self.assertEqual(self.target.stat().st_mode&511,0o600);self.assertFalse(c[3]['required']);self.replay(c)
    def test_read_only_previous_target_is_replaced_and_directory_error_is_replayed(self):
        c=self.capture(existing=True);self.assertIsNone(c[2]['error']);self.replay(c)
        self.target.unlink();c=self.capture(target_directory=True);self.assertEqual(c[2]['error']['type'],'IsADirectoryError');self.assertEqual((self.target/'untouched').read_bytes(),b'Owned previous content');self.replay(c)
    def test_write_flush_fsync_close_chmod_and_replace_errors_keep_old_target_and_replay(self):
        for failure in ('write','flush','fsync','close','chmod','replace'):
            with self.subTest(failure=failure):
                c=self.capture(failure=failure,existing=True);self.assertEqual(c[2]['error']['type'],'OSError');self.assertEqual(self.target.read_bytes(),b'Previous target\n');self.replay(c)
    def test_failed_final_unlink_after_real_replace_leaves_the_new_target_and_replays(self):
        c=self.capture(failure='unlink',existing=True);self.assertEqual(c[2]['error']['type'],'OSError');self.assertNotEqual(self.target.read_bytes(),b'Previous target\n');self.replay(c)
    def test_json_type_error_still_closes_partial_stream_and_unlinks_before_replay(self):
        value={'unsupported':object()};c=self.capture(existing=True,value=value);self.assertEqual(c[2]['error']['type'],'TypeError');self.assertEqual(self.target.read_bytes(),b'Previous target\n');self.replay(c,value=value)
    def test_fdopen_failure_keeps_original_error_but_extra_resource_teardown_marks_capture_incomplete(self):
        c=self.capture(failure='fdopen',existing=True);self.assertEqual(c[2]['error']['type'],'OSError');self.assertTrue(c[1].capture_incomplete);self.assertTrue(c[3]['required']);self.assertEqual(self.target.read_bytes(),b'Previous target\n');self.replay(c)
    def test_changed_stream_text_and_forged_flushed_bytes_are_rejected(self):
        c=self.capture();effects,record,result,resources,request,events,blob,closed=c;cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};changed=copy.deepcopy(events[2:-1]);row=next(v for v in changed if v['kind']=='intake-atomic-intent' and v['operation']=='write');row['arguments']['text']='forged'
        with patch('os.open',side_effect=AssertionError('No source replay')),self.assertRaisesRegex(IntegrityError,'intent_changed'):program(ReplayAtomicEffects(effects.scope,changed,lambda ref:cache[ref['sha256']])).atomic_json('candidate.json',self.value)
        changed=copy.deepcopy(events[2:-1]);index=next(i for i,v in enumerate(changed) if v['kind']=='intake-atomic-intent' and v['operation']=='flush');changed[index+1]['after']['files'][next(iter(effects.temps))]['content']={'sha256':hashlib.sha256(b'forged').hexdigest(),'bytes':6};changed[index+1]['after']['files'][next(iter(effects.temps))]['stat']['bytes']=6;cache[hashlib.sha256(b'forged').hexdigest()]=b'forged'
        with patch('os.open',side_effect=AssertionError('No source replay')),self.assertRaisesRegex(IntegrityError,'flushed_bytes_changed'):program(ReplayAtomicEffects(effects.scope,changed,lambda ref:cache[ref['sha256']])).atomic_json('candidate.json',self.value)
    def test_outside_target_private_record_overlap_and_unselected_members_are_rejected(self):
        record=Record(self.state,{'prototype':True},{'no_authority':True});scope=AtomicScope(str(self.output),['candidate.json'],cwd=str(self.output))
        with self.assertRaises(InputAdmissionError):NativeAtomicEffects(scope,record,forbidden_roots=(self.base,))
        (self.output/'unexpected').write_bytes(b'Unselected data')
        with self.assertRaises(InputAdmissionError):NativeAtomicEffects(scope,record,forbidden_roots=(ROOT,))
        self.assertEqual((self.output/'unexpected').read_bytes(),b'Unselected data')
    def test_initial_root_open_or_stat_failure_marks_capture_incomplete_and_closes_owned_fd(self):
        from contextlib import contextmanager
        missing=self.base/'missing-output'
        record=Record(self.state,{'prototype':'missing-root'},{'no_authority':True})
        scope=AtomicScope(str(missing),['candidate.json'],cwd=str(self.output))
        with self.assertRaisesRegex(InputAdmissionError,'initial_observation_failed'):
            NativeAtomicEffects(scope,record,forbidden_roots=(ROOT,))
        self.assertTrue(record.capture_incomplete);self.assertFalse(missing.exists())
        record=Record(self.state,{'prototype':'failed-initial-stat'},{'no_authority':True})
        scope=AtomicScope(str(self.output),['candidate.json'],cwd=str(self.output));held=[]
        @contextmanager
        def anchor(root):
            descriptor=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);held.append(descriptor)
            try:yield descriptor
            finally:os.close(descriptor)
        with patch('lib.providers.intake_atomic_effects.held_root',anchor),patch('lib.providers.intake_atomic_effects.os.fstat',side_effect=OSError(errno.EIO,'Initial stat unavailable')):
            with self.assertRaisesRegex(InputAdmissionError,'initial_observation_failed'):
                NativeAtomicEffects(scope,record,forbidden_roots=(ROOT,))
        self.assertTrue(record.capture_incomplete);self.assertEqual(len(held),1)
        with self.assertRaises(OSError) as caught:os.fstat(held[0])
        self.assertEqual(caught.exception.errno,errno.EBADF)
    def test_completion_loss_after_native_write_does_not_retry_or_publish_a_verdict(self):
        record=Record(self.state,{'prototype':True},{'no_authority':True});scope=AtomicScope(str(self.output),['candidate.json'],cwd=str(self.output));effects=NativeAtomicEffects(scope,record,forbidden_roots=(ROOT,));append=record.append;lost=False;flushes=0;pending=None
        def lose(row):
            nonlocal lost,flushes,pending
            if row.get('kind')=='intake-atomic-intent':
                pending=row['operation']
                if pending=='flush':flushes+=1
            if row.get('kind')=='intake-atomic-outcome' and pending=='flush':lost=True
            if lost:raise OSError('Isolated journal completion loss')
            return append(row)
        record.append=lose
        try:
            with self.assertRaises(Exception):program(effects).atomic_json('candidate.json',self.value)
            self.assertTrue(lost);self.assertTrue(record.capture_incomplete);self.assertEqual(flushes,1);self.assertFalse(self.target.exists());temporary=list(self.output.glob('tmp*'));self.assertEqual(len(temporary),1);self.assertEqual(temporary[0].read_bytes(),(json.dumps(self.value,sort_keys=True,indent=2)+'\n').encode())
        finally:effects.release_resources()
        with self.assertRaises(ValueError):record.finish('complete',{'exit_code':0},{})

    def test_original_pre_try_mkstemp_failure_and_failed_stream_enter_are_replayed(self):
        for operation in ('mkstemp','enter'):
            with self.subTest(operation=operation):
                c=self.capture(failure=operation,existing=True);self.assertEqual(c[2]['error']['type'],'OSError');self.assertEqual(self.target.read_bytes(),b'Previous target\n');self.replay(c)
    def test_forged_file_identity_and_boolean_argument_type_do_not_pass_replay(self):
        c=self.capture();effects,record,result,resources,request,events,blob,closed=c;cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};changed=copy.deepcopy(events[2:-1]);row=next(v for v in changed if v['kind']=='intake-atomic-intent' and v['operation']=='mkdir');row['arguments']['parents']=1
        with patch('os.open',side_effect=AssertionError('No source replay')),self.assertRaisesRegex(IntegrityError,'intent_changed'):program(ReplayAtomicEffects(effects.scope,changed,lambda ref:cache[ref['sha256']])).atomic_json('candidate.json',self.value)
        changed=copy.deepcopy(events[2:-1]);index=next(i for i,v in enumerate(changed) if v['kind']=='intake-atomic-intent' and v['operation']=='write');row=changed[index+1]['after']['files'][next(iter(effects.temps))];row['identity'][1]+=1
        with patch('os.open',side_effect=AssertionError('No source replay')),self.assertRaisesRegex(IntegrityError,'stream_file_identity_changed'):program(ReplayAtomicEffects(effects.scope,changed,lambda ref:cache[ref['sha256']])).atomic_json('candidate.json',self.value)
    def test_missing_retained_bytes_are_integrity_failure_not_an_original_io_error(self):
        c=self.capture();effects,record,result,resources,request,events,blob,closed=c
        def absent(ref):raise FileNotFoundError(errno.ENOENT,'Isolated retained byte loss')
        with patch('os.open',side_effect=AssertionError('No source replay')),self.assertRaisesRegex(IntegrityError,'retained_blob_unavailable'):program(ReplayAtomicEffects(effects.scope,events[2:-1],absent)).atomic_json('candidate.json',self.value)
    def test_mandatory_final_audit_write_after_failed_candidate_uses_a_distinct_atomic_operation(self):
        request={'scope_root':str(self.output),'cwd':str(self.output),'targets':['candidate.json','native-capture.json']};record=Record(self.state,request,{'test_only':True});record.append({'kind':'execution-intent','request':request});scope=AtomicScope(str(self.output),request['targets'],cwd=request['cwd']);effects=Faults(scope,record,forbidden_roots=(ROOT,));effects.failure='write';audit=[{'path':'/explicit-read','response':{'candidate':True}}]
        try:
            with self.assertRaises(OSError):program(effects).atomic_json('candidate.json',self.value)
            effects.failure=None;program(effects).atomic_json('native-capture.json',audit)
        finally:resources=effects.release_resources()
        self.assertFalse(resources['required']);self.assertFalse(self.target.exists());self.assertEqual(json.loads((self.output/'native-capture.json').read_bytes()),audit);record.finish('complete',{'exit_code':1},{})
        _,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};pure=ReplayAtomicEffects(scope,events[2:-1],lambda ref:cache[ref['sha256']]);moved=self.base.with_name(self.base.name+'-absent');self.base.rename(moved)
        try:
            with patch('os.open',side_effect=AssertionError('No source replay')),patch('subprocess.Popen',side_effect=AssertionError('No programs')):
                with self.assertRaises(OSError):program(pure).atomic_json('candidate.json',self.value)
                program(pure).atomic_json('native-capture.json',audit);pure.finish()
            self.assertEqual(pure.state.current,effects.state.current)
        finally:moved.rename(self.base)
        for name,raw in cache.items():self.assertEqual(blob({'sha256':name,'bytes':len(raw)}),raw)
        self.assertTrue(closed())
    def test_actual_native_backend_matches_entire_immutable_original_helper_on_real_files_and_directory_error(self):
        import ast
        from test_v2_intake_atomic_json import FUNCTION
        for kind in ('new','read-only','directory'):
            values=[]
            for side in ('original','captured'):
                shutil.rmtree(self.output);self.output.mkdir(mode=0o700)
                if kind=='read-only':self.target.write_bytes(b'Previous target\n');self.target.chmod(0o400)
                elif kind=='directory':self.target.mkdir(mode=0o700);(self.target/'untouched').write_bytes(b'Owned previous content')
                error=returned=None;effects=None
                with patch('tempfile._get_candidate_names',return_value=iter(['abcdefgh'])):
                    try:
                        if side=='original':
                            namespace={'Path':Path,'os':os,'tempfile':tempfile,'json':json};exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(FUNCTION)],type_ignores=[])),'immutable_original_atomic_helper','exec'),namespace);returned=namespace['atomic_json'](self.target,self.value)
                        else:
                            record=Record(self.state,{'case':kind},{'test_only':True});scope=AtomicScope(str(self.output),['candidate.json'],cwd=str(self.output));effects=NativeAtomicEffects(scope,record,forbidden_roots=(ROOT,));returned=program(effects).atomic_json(str(self.target),self.value)
                    except Exception as caught:error={'type':type(caught).__name__,'message':str(caught)}
                    finally:
                        if effects is not None:self.assertFalse(effects.release_resources()['required'])
                files={p.relative_to(self.output).as_posix():{'mode':p.stat().st_mode&511,'data':None if p.is_dir() else p.read_bytes()} for p in sorted(self.output.rglob('*'))}
                values.append({'return_value':returned,'error':error,'whole_files_modes_and_bytes':files})
            with self.subTest(kind=kind):self.assertEqual(values[0],values[1])
