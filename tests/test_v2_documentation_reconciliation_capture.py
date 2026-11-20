"""Whole original execution, lazy file/Git capture and removed-source replay."""
from pathlib import Path
import copy,hashlib,json,os,shutil,subprocess,sys,unittest
from contextlib import nullcontext
from unittest.mock import patch
Q=Path(__file__).resolve().parents[1];B=Q/'tests';sys.path[:0]=[str(Q/'scripts'),str(B)]
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.synthetic_lifecycle_io import ReplayIO
from lib.synthetic_lifecycle_context import LifecyclePaths
from lib.requirement_validation_replay import IntegrityError
from lib.documentation_reconciliation_ports import execute
from lib.providers.documentation_reconciliation_git import NativeGit
from lib.documentation_reconciliation_git import ReplayGit
import test_v2_documentation_reconciliation_core as original

class CapturedOriginal(unittest.TestCase):
    setUp=original.WholeOriginal.setUp
    fixture=original.WholeOriginal.fixture
    # The eight direct-original tests are retained by inheritance. These
    # additional whole-CLI comparisons exercise the explicit capture/replay.
    def capture(self,root,args,mode='private-candidate',expected=0,retain=None,fault=None):
        before=original.snapshot(root)
        command=[sys.executable,'-B',str(root/'scripts'/original.FILENAME),*args]
        if fault is not None:
            command=[sys.executable,'-B','-c','import sys;sys.path.insert(0,sys.argv.pop(1));from _documentation_append_fault_fixture import run_original;run_original()',str(B),fault,str(root/'scripts'/original.FILENAME),*args]
        old=subprocess.run(command,cwd=self.parent,capture_output=True,timeout=30,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        self.assertEqual(old.returncode,expected,old.stderr[-2500:]);after=original.snapshot(root);original.restore(root,before)
        private=self.parent/('private-'+str(self.serial));private.mkdir(mode=0o700)
        record=Record(private/'records',{'prototype':'whole documentation reconciliation','argv':args,'mode':mode},{'prototype':True,'not_product_acceptance':True});record.append({'kind':'execution-intent'})
        inputs=NativeIO(record,mode=mode,cwd=str(root),private_state=private,product_root=Q)
        if fault is not None:from _documentation_append_fault_fixture import inject
        with inject(fault) if fault is not None else nullcontext():
            kernel=execute(str(root),str(root),args,inputs,NativeGit)
        self.assertEqual(kernel['exit_code'],old.returncode,kernel);self.assertEqual(kernel['stdout'].encode(),old.stdout)
        if kernel['kernel_exception'] is None:self.assertEqual(kernel['stderr'].encode(),old.stderr)
        else:
            error=kernel['kernel_exception'];self.assertTrue(old.stderr.decode().endswith(error['type']+': '+error['message']+'\n'),(error,old.stderr[-2500:]))
        if mode=='selected-files':self.assertEqual(original.snapshot(root),after)
        else:
            self.assertEqual(original.snapshot(root),before);files,dirs=dict(before[0]),dict(before[1])
            for name,node in inputs.projected_changes.items():
                relative=str(Path(name).relative_to(root))
                if node['kind']=='file':files[relative]=(inputs.projection.resolve(node['content']),node['mode'])
                elif node['kind']=='directory':dirs[relative]=node['mode']
                elif node['kind']=='missing':files.pop(relative,None);dirs.pop(relative,None)
                else:self.fail('Unexpected model node')
            self.assertEqual((files,dirs),after)
        self.assertFalse(record.capture_incomplete);record.finish('complete',kernel,inputs.touched)
        _,_,_,events,_,_=read_record(record.root);blobs={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
        def blob(ref):
            raw=blobs[ref['sha256']];self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);self.assertEqual(len(raw),ref['bytes']);seen.add(ref['sha256']);return raw
        replay=ReplayIO(events,blob,mode,str(root));hidden=root.parent/('removed-'+root.name);root.rename(hidden)
        try:
            with (patch('os.open',side_effect=AssertionError('No native source/files')),
                  patch('pathlib.Path.read_bytes',side_effect=AssertionError('No native source')),
                  patch('subprocess.Popen',side_effect=AssertionError('No native Git/programs')),
                  patch('socket.create_connection',side_effect=AssertionError('No network'))):
                replayed=execute(str(root),str(root),args,replay,ReplayGit)
            self.assertEqual(replayed,kernel);self.assertEqual(replay.files,inputs.files);self.assertEqual(replay.projected_changes,inputs.projected_changes);self.assertEqual(replay.touched,inputs.touched);replay.finish();self.assertEqual(seen,set(blobs))
        finally:hidden.rename(root)
        if retain is not None:
            destination=self.parent/'retained-current'/retain
            destination.parent.mkdir(mode=0o700,exist_ok=True)
            shutil.copytree(record.root,destination)
        return kernel,inputs,events,blobs

    def test_captured_whole_original_main_both_modes_and_both_git_formats(self):
        for fmt in ('sha1','sha256'):
            for mode in ('private-candidate','selected-files'):
                with self.subTest(fmt=fmt,mode=mode):root,args=self.fixture(fmt);self.capture(root,args,mode)

    def test_captured_original_invalid_reference_body_and_partial_document_errors(self):
        for case in ('reference','body','catalog','regex'):
            for mode in ('private-candidate','selected-files'):
                with self.subTest(case=case,mode=mode):
                    root,args=self.fixture()
                    if case=='reference':args+=['--base','no-such-reference']
                    elif case=='body':args+=['--body-file',str(root/'missing-body.txt')]
                    elif case=='catalog':(root/'docs/operations/guides/repository-function-catalog.md').unlink()
                    else:
                        (root/'README.md').write_text('<!-- DOCS_REFRESH_LATEST:start -->\nold\n<!-- DOCS_REFRESH_LATEST:end -->\n');args+=['--body','## Summary\n- bad \\q\n']
                    self.capture(root,args,mode,1)

    def test_retained_positive_and_original_regex_error_cases_for_portable_peer_replay(self):
        for mode in ('private-candidate','selected-files'):
            for case in ('positive','regex'):
                root,args=self.fixture()
                if case=='regex':
                    (root/'README.md').write_text('<!-- DOCS_REFRESH_LATEST:start -->\nold\n<!-- DOCS_REFRESH_LATEST:end -->\n');args+=['--body','## Summary\n- bad \\q\n']
                self.capture(root,args,mode,0 if case=='positive' else 1,retain=mode+'-'+case)

    def test_resealed_process_intent_identity_stream_budget_and_terminal_mutations_fail_closed(self):
        for attack in ('bool-intent','source-program','owner','source-moved','budget','zero-error','boolean-code','zero-error-before-decode'):
            with self.subTest(attack=attack):
                root,args=self.fixture();kernel,inputs,events,blobs=self.capture(root,args)
                events=copy.deepcopy(events);blobs=dict(blobs);seen=set()
                token=next(i for i,row in enumerate(events) if row.get('action')=='documentation-local-git')
                returned=events[token+1];wire=json.loads(blobs[returned['value']['sha256']])
                if attack=='bool-intent':events[token]['arguments']['check']=1
                elif attack=='source-program':wire['program']['resolved']=str(root/'selected-git')
                elif attack=='owner':wire['program']['uid']=wire['source_before']['uid']+100000
                elif attack=='source-moved':wire['source_after']['identity'][1]+=1
                elif attack=='budget':wire['observation']['stream_budget_exceeded']=True
                elif attack=='zero-error':wire['return_error']={'type':'CalledProcessError','message':'forged'}
                elif attack=='boolean-code':wire['returncode']=False;wire['observation']['returncode']=False
                else:
                    raw=b'\xff';sha=hashlib.sha256(raw).hexdigest();blobs[sha]=raw;wire['stdout']={'sha256':sha,'bytes':1};wire['effective_encoding']='utf-8';wire['return_error']={'type':'CalledProcessError','message':'forged before invalid decoding'}
                raw=(json.dumps(wire,ensure_ascii=True,separators=(',',':'))+'\n').encode();sha=hashlib.sha256(raw).hexdigest();blobs[sha]=raw;returned['value']={'sha256':sha,'bytes':len(raw)}
                def blob(ref):
                    data=blobs[ref['sha256']];self.assertEqual(len(data),ref['bytes']);self.assertEqual(hashlib.sha256(data).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return data
                replay=ReplayIO(events,blob,'private-candidate',str(root))
                with patch('subprocess.Popen',side_effect=AssertionError('No native Git')):
                    with self.assertRaises(IntegrityError):execute(str(root),str(root),args,replay,ReplayGit)

    def test_captured_help_and_parser_need_no_selected_data_git_or_file_observations(self):
        for args,code in ((['--help'],0),(['--unknown'],2)):
            root,_=self.fixture();kernel,inputs,events,blobs=self.capture(root,args,expected=code)
            self.assertEqual(len(events),3);self.assertFalse(blobs);self.assertEqual(inputs.files,{})

if __name__=='__main__':os.umask(0o077);unittest.main(verbosity=2)
