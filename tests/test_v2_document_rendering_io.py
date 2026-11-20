"""Whole original real document data through captured text ports and no-tool replay."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy,errno,hashlib,json,os,shutil,sys,tempfile,unittest,yaml
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_document_rendering as whole
from lib.document_rendering_context import execute
from lib.document_rendering_io import ReplayIO
from lib.providers.document_rendering_io import Data,Output
from lib.providers.sbom_export_storage import Record,read_record,encode
from lib.requirement_validation_budget import InputAdmissionError


class NoTool:
    """Explicit controlled absence, not a claim about a native executable."""
    def __init__(self,record,output):self.record,self.output=record,output
    def which(self,name):
        self.output.gate.which(name)
        value=self.record.perform('document-tool-find',{'name':name},lambda:{'path':None,'identity':None,'context':None})
        self.output.gate.found(value['path']);return value['path']
    def run(self,*args,**kwargs):raise AssertionError('Explicit controlled absence never invokes a tool')


class WholeDocumentFileIO(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.work=Path(temporary.name).resolve();self.data=self.work/'data';self.data.mkdir(mode=0o700)
        for name in ('model/documents/governance-documents.yaml','model/documents/governance-document-rendering.yaml'):
            p=self.data/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)
        self.catalog=self.data/'model/documents/governance-documents.yaml';self.profiles=self.data/'model/documents/governance-document-rendering.yaml'
        self.documents=yaml.safe_load(self.catalog.read_bytes())['documents']
        for row in self.documents:
            if row['type'] in ('policy','directive'):
                p=self.data/row['repository_path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/row['repository_path'],p)
        self.private=self.work/'private';self.private.mkdir(mode=0o700)
    def files(self):return {str(p):p.read_bytes() for p in self.data.rglob('*') if p.is_file() and not p.is_symlink()}
    def save_catalog(self):self.catalog.write_text(yaml.safe_dump({'documents':self.documents},sort_keys=False))
    def original(self,args=()):
        with patch.multiple(whole.original,ROOT=self.data,CATALOG_PATH=self.catalog,RENDERING_PATH=self.profiles,OUT_DIR=self.data/'generated/documents'),patch.object(whole.original.shutil,'which',lambda name:None),patch.object(sys,'argv',['render_governance_documents.py',*args]):return whole.capture(whole.original.main)
    def recorded(self,mode='selected-files',args=(),failure=None):
        request={'profile':'controlled-no-tool','source_label':str(self.data),'argv':list(args),'export_mode':mode}
        record=Record(self.private/'records',request,{'declared_test_source':True});record.append({'kind':'execution-intent','request':request})
        output=Output(record,mode,str(self.data),self.private,ROOT);data=Data(record,output,self.private);tools=NoTool(record,output)
        kernel=error=None
        try:
            if failure is None:kernel=execute(str(self.data),list(args),data,output,tools)
            else:
                with patch.object(output,'write_chunk',failure):kernel=execute(str(self.data),list(args),data,output,tools)
        except Exception as value:error=value
        value=None if kernel is None else {'exit_code':kernel['exit_code'],'kernel_result':kernel,'successful_outputs':output.files,'successful_writes':output.writes}
        record.finish('incomplete' if error else 'complete',value,output.touched,error)
        return record.root,kernel,output,error
    def replay(self,root):
        request,source,retained,events,blob,closed=read_record(root);io=ReplayIO(events,blob,request['export_mode'],request['source_label'])
        with patch('subprocess.Popen',side_effect=AssertionError('No native program in replay')),patch('lib.providers.document_rendering_io.Data.read',side_effect=AssertionError('No native source in replay')),patch('lib.providers.document_rendering_io.Output.write_text',side_effect=AssertionError('No native output in replay')):
            kernel=execute(request['source_label'],request['argv'],io,io,io)
        io.finish();self.assertEqual(kernel,retained['result']['kernel_result']);self.assertEqual(io.files,retained['result']['successful_outputs']);self.assertEqual(io.writes,retained['result']['successful_writes']);self.assertEqual(io.touched,retained['touched_files']);self.assertTrue(closed())
        return io,kernel
    def compare(self,mode='selected-files'):
        before=self.files();dirs=[p.relative_to(self.data) for p in self.data.rglob('*') if p.is_dir()]
        expected=self.original();expected_files=self.files()
        generated=self.data/'generated'
        if generated.exists():generated.rename(self.work/'original-generated')
        for directory in dirs:(self.data/directory).mkdir(parents=True,exist_ok=True)
        for name,raw in before.items():Path(name).write_bytes(raw)
        root,kernel,output,error=self.recorded(mode)
        self.assertIsNone(error)
        actual={'exit':kernel['exit_code'],'error':kernel['kernel_exception'],'stdout':kernel['stdout'],'stderr':kernel['stderr']}
        self.assertEqual(actual,expected)
        if mode=='private-candidate':self.assertEqual(self.files(),before)
        else:self.assertEqual(self.files(),expected_files)
        _,_,_,_,blob,_=read_record(root)
        self.assertEqual({name:blob(ref) for name,ref in output.files.items()},
            {name:raw for name,raw in expected_files.items() if name not in before or raw!=before[name]})
        self.replay(root)
        return root,kernel,output
    def test_whole_real_models_all_MD_HTML_bytes_private_projection(self):self.compare('private-candidate')
    def test_whole_real_models_all_native_bytes_and_directory_effects(self):self.compare()
    def test_private_source_can_read_own_prior_projected_markdown_export(self):
        selected=[row for row in self.documents if row['type'] in ('policy','directive')]
        selected[1]['repository_path']='generated/documents/'+selected[0]['id'].lower()+'.rendered.md';self.save_catalog()
        self.compare('private-candidate')
    def test_native_source_can_read_own_prior_export_without_stale_input_verdict(self):
        selected=[row for row in self.documents if row['type'] in ('policy','directive')]
        selected[1]['repository_path']='generated/documents/'+selected[0]['id'].lower()+'.rendered.md';self.save_catalog()
        self.compare()
    def test_duplicate_ids_preserve_all_ordered_writes_and_final_bytes(self):
        selected=[row for row in self.documents if row['type'] in ('policy','directive')]
        selected[1]['id']=selected[0]['id'];self.save_catalog()
        _,_,output=self.compare();self.assertEqual(len(output.writes),4);self.assertEqual(len(output.files),2)
    def test_html_error_after_later_MD_preserves_whole_original_prior_files(self):
        selected=[row for row in self.documents if row['type'] in ('policy','directive')]
        selected[1]['title']=7;self.save_catalog();_,kernel,output=self.compare()
        self.assertEqual(kernel['kernel_exception']['type'],'AttributeError');self.assertEqual(len(output.files),3)
    def test_missing_later_source_keeps_original_error_and_prior_outputs(self):
        selected=[row for row in self.documents if row['type'] in ('policy','directive')]
        (self.data/selected[1]['repository_path']).unlink();_,kernel,output=self.compare()
        self.assertEqual(kernel['kernel_exception']['type'],'FileNotFoundError');self.assertEqual(len(output.files),2)
    def test_native_directory_error_preserves_original_first_file(self):
        selected=next(row for row in self.documents if row['type'] in ('policy','directive'))
        target=self.data/'generated/documents'/(selected['id'].lower()+'.html');target.mkdir(parents=True)
        _,kernel,output=self.compare();self.assertEqual(kernel['kernel_exception']['type'],'IsADirectoryError');self.assertEqual(len(output.files),1)
    def test_actual_controlled_seven_byte_prefix_is_reconstructed_without_export(self):
        first=next(row for row in self.documents if row['type'] in ('policy','directive'));name=self.data/'generated/documents'/(first['id'].lower()+'.rendered.md');original_write=Path.write_text
        def original_failure(path,text,*a,**kwargs):
            if path==name:
                with path.open('w',encoding='utf-8') as stream:stream.write(text[:7]);stream.flush()
                raise OSError(errno.ENOSPC,'No space left on device')
            return original_write(path,text,*a,**kwargs)
        with patch.object(Path,'write_text',original_failure):expected=self.original()
        original_bytes=name.read_bytes();(self.data/'generated').rename(self.work/'original-generated')
        calls=[]
        def failure(fd,view):
            calls.append(len(view))
            if len(calls)==1:return os.write(fd,view[:7])
            raise OSError(errno.ENOSPC,'No space left on device')
        root,kernel,output,error=self.recorded(failure=failure)
        self.assertIsNone(error);self.assertEqual(kernel['exit_code'],1)
        self.assertEqual({'exit':1,'error':kernel['kernel_exception'],'stdout':kernel['stdout'],'stderr':kernel['stderr']},expected)
        self.assertEqual(name.read_bytes(),original_bytes);self.assertEqual(len(original_bytes),7)
        shutil.rmtree(self.data);self.replay(root)
    def parent_conflict(self,mode,nested):
        rows=[row for row in self.documents if row['type'] in ('policy','directive')]
        previous=rows[1]['id'];rows[1]['id']=rows[0]['id'].lower()+'.rendered.md/'+('nested/' if nested else '')+'child'
        profiles=yaml.safe_load(self.profiles.read_bytes());profiles['render_profiles'][rows[1]['id']]=profiles['render_profiles'].pop(previous)
        self.profiles.write_text(yaml.safe_dump(profiles,sort_keys=False));self.save_catalog()
        _,kernel,_=self.compare(mode)
        self.assertEqual(kernel['kernel_exception']['type'],'NotADirectoryError' if nested else 'FileExistsError')
    def test_private_mkdir_cannot_replace_own_projected_file(self):self.parent_conflict('private-candidate',False)
    def test_native_mkdir_cannot_replace_own_written_file(self):self.parent_conflict('selected-files',False)
    def test_private_nested_mkdir_cannot_traverse_own_projected_file(self):self.parent_conflict('private-candidate',True)
    def test_native_nested_mkdir_cannot_traverse_own_written_file(self):self.parent_conflict('selected-files',True)
    def test_own_export_disappearing_before_a_later_source_read_is_incomplete(self):
        selected=[row for row in self.documents if row['type'] in ('policy','directive')]
        selected[1]['repository_path']='generated/documents/'+selected[0]['id'].lower()+'.rendered.md';self.save_catalog()
        old=NoTool.which;calls=[]
        def removed(tool,name):
            result=old(tool,name)
            if not calls:Path(tool.output.gate.md).unlink();calls.append(True)
            return result
        with patch.object(NoTool,'which',removed):root,kernel,output,error=self.recorded()
        self.assertIsNone(kernel);self.assertIsInstance(error,InputAdmissionError)
        self.assertEqual(read_record(root)[2]['state'],'incomplete')
    def test_private_source_overlap_is_incomplete_not_original_verdict(self):
        selected=next(row for row in self.documents if row['type'] in ('policy','directive'))
        selected['repository_path']=str(self.private/'secret.md');self.save_catalog()
        root,kernel,output,error=self.recorded();self.assertIsNone(kernel);self.assertIsInstance(error,InputAdmissionError)
        self.assertEqual(read_record(root)[2]['state'],'incomplete')

if __name__=='__main__':unittest.main()
