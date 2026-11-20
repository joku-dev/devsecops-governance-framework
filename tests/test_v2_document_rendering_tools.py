"""Actual external command facts, all original outcomes, observed DOCX and replay."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import errno,hashlib,json,os,shutil,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_document_rendering as whole
import test_v2_document_rendering_io as file_cases
from lib.document_rendering_context import execute
from lib.document_rendering_io import ReplayIO
from lib.providers.document_rendering_io import Data,Output
from lib.providers.document_rendering_tools import Tools,which_at
from lib.providers.sbom_export_storage import Record,read_record,encode
from lib.requirement_validation_budget import InputAdmissionError


PROGRAMS={
 'full':"target.write_bytes(b'controlled-DOCX:'+source.read_bytes());sys.stdout.buffer.write(b'out\\r\\nline\\r');sys.stderr.write('controlled stderr')",
 'zero-missing':"pass",
 'partial-nonzero':"target.write_bytes(b'partial:'+source.read_bytes()[:7]);sys.exit(7)",
 'directory':"target.mkdir(exist_ok=True)",
 'invalid-stdio':"target.write_bytes(b'before-decode');sys.stdout.buffer.write(b'out\\r\\n');sys.stderr.buffer.write(b'bad\\xff')",
 'signal':"target.write_bytes(b'before-signal');os.kill(os.getpid(),15)",
 'timeout':"target.write_bytes(b'before-timeout');time.sleep(5)",
 'stream-budget':"target.write_bytes(b'before-stream-budget');sys.stdout.buffer.write(b'x'*300000)",
}


class WholeDocumentToolIO(unittest.TestCase):
    def setUp(self):
        self.fixture=file_cases.WholeDocumentFileIO();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.data,self.work,self.private=self.fixture.data,self.fixture.work,self.fixture.private
        self.tools=self.work/'tools';self.tools.mkdir(mode=0o700);self.program=self.tools/'pandoc'
        self.environment={**os.environ,'PATH':str(self.tools)+os.pathsep+os.defpath,'SOURCE_DATE_EPOCH':'1794744000'}
    def binary(self,kind):
        if kind=='invalid-executable':raw=b'Not an executable image\n'
        else:raw=('#!'+sys.executable+'\nfrom pathlib import Path\nimport os,sys,time\nsource=Path(sys.argv[1]);target=Path(sys.argv[3])\n'+PROGRAMS[kind]+'\n').encode()
        self.program.write_bytes(raw);self.program.chmod(0o700)
    def original(self):
        with patch.dict(os.environ,self.environment,clear=True),patch.multiple(whole.original,ROOT=self.data,CATALOG_PATH=self.fixture.catalog,RENDERING_PATH=self.fixture.profiles,OUT_DIR=self.data/'generated/documents'),patch.object(sys,'argv',['render_governance_documents.py']):return whole.capture(whole.original.main)
    def recorded(self,mode='selected-files',timeout=120):
        request={'profile':'legacy-observed-pandoc','source_label':str(self.data),'argv':[],'export_mode':mode}
        record=Record(self.private/'records',request,{'declared_test_source':True});record.append({'kind':'execution-intent','request':request})
        output=Output(record,mode,str(self.data),self.private,ROOT);data=Data(record,output,self.private)
        tools=Tools(record,output,self.private/'scratch',environment=self.environment,timeout=timeout)
        kernel=error=None
        try:kernel=execute(str(self.data),[],data,output,tools)
        except Exception as caught:error=caught
        value=None if kernel is None else {'exit_code':kernel['exit_code'],'kernel_result':kernel,'successful_outputs':output.files,'successful_writes':output.writes,'observed_tool_outputs':output.tool_files}
        state='incomplete' if error or record.capture_incomplete else 'complete';record.finish(state,value,output.touched,error)
        return record.root,kernel,output,error
    def replay(self,root):
        request,source,retained,events,blob,closed=read_record(root);io=ReplayIO(events,blob,request['export_mode'],request['source_label'])
        with patch('subprocess.Popen',side_effect=AssertionError('No external process in replay')),patch('lib.providers.document_rendering_io.Data.read',side_effect=AssertionError('No actual source in replay')),patch('lib.providers.document_rendering_io.Output.write_text',side_effect=AssertionError('No export in replay')):
            kernel=execute(request['source_label'],request['argv'],io,io,io)
        io.finish();self.assertEqual(kernel,retained['result']['kernel_result']);self.assertEqual(io.files,retained['result']['successful_outputs']);self.assertEqual(io.writes,retained['result']['successful_writes']);self.assertEqual(io.tool_files,retained['result']['observed_tool_outputs']);self.assertEqual(io.touched,retained['touched_files']);self.assertTrue(closed())
        return io,kernel
    def compare(self,kind,mode='selected-files',seed=False):
        self.binary(kind)
        if seed:
            first=next(r for r in self.fixture.documents if r['type'] in ('policy','directive'))
            p=self.data/'generated/documents'/(first['id'].lower()+'.docx');p.parent.mkdir(parents=True);p.write_bytes(b'existing-DOCX')
        before=self.fixture.files();dirs=[p.relative_to(self.data) for p in self.data.rglob('*') if p.is_dir()]
        expected=self.original();expected_files=self.fixture.files();(self.data/'generated').rename(self.work/'original-generated')
        for directory in dirs:(self.data/directory).mkdir(parents=True,exist_ok=True)
        for name,raw in before.items():Path(name).write_bytes(raw)
        root,kernel,output,error=self.recorded(mode);self.assertIsNone(error)
        self.assertEqual({'exit':kernel['exit_code'],'error':kernel['kernel_exception'],'stdout':kernel['stdout'],'stderr':kernel['stderr']},expected)
        self.assertEqual(self.fixture.files(),before if mode=='private-candidate' else expected_files)
        _,_,_,_,blob,_=read_record(root)
        actual={name:blob(ref) for name,ref in {**output.files,**output.tool_files}.items()}
        expected_outputs={name:raw for name,raw in expected_files.items() if '/generated/documents/' in name}
        self.assertEqual(actual,expected_outputs)
        self.replay(root)
        self.assertFalse(any((self.private/'scratch').iterdir()))
        return root,kernel,output
    def test_actual_native_whole_original_tool_and_all_export_bytes(self):self.compare('full')
    def test_actual_private_tool_projection_keeps_whole_original_bytes_without_source_export(self):self.compare('full','private-candidate')
    def test_original_zero_exit_missing_DOCX_is_not_invented(self):
        root,kernel,output=self.compare('zero-missing');self.assertEqual(kernel['exit_code'],0);self.assertFalse(output.tool_files)
        self.assertIn('.docx',kernel['stdout'])
    def test_private_zero_exit_missing_DOCX_is_not_invented(self):
        _,kernel,output=self.compare('zero-missing','private-candidate');self.assertEqual(kernel['exit_code'],0);self.assertFalse(output.tool_files)
    def test_original_zero_exit_keeps_existing_unwritten_DOCX(self):self.compare('zero-missing',seed=True)
    def test_private_zero_exit_keeps_existing_unwritten_DOCX(self):self.compare('zero-missing','private-candidate',seed=True)
    def test_original_nonzero_still_preserves_actual_partial_DOCX(self):
        _,kernel,output=self.compare('partial-nonzero');self.assertEqual(kernel['exit_code'],0);self.assertEqual(len(output.tool_files),2);self.assertIn('Skipped DOCX',kernel['stdout'])
    def test_private_nonzero_still_preserves_observed_partial_DOCX(self):self.compare('partial-nonzero','private-candidate')
    def test_original_zero_exit_directory_is_not_claimed_as_file(self):
        _,kernel,output=self.compare('directory');self.assertEqual(kernel['exit_code'],0);self.assertFalse(output.tool_files)
    def test_private_zero_exit_directory_is_not_claimed_as_file(self):self.compare('directory','private-candidate')
    def test_original_invalid_stdio_keeps_decode_error_after_actual_file_creation(self):
        _,kernel,output=self.compare('invalid-stdio');self.assertEqual(kernel['kernel_exception']['type'],'UnicodeDecodeError');self.assertEqual(len(output.tool_files),1)
    def test_private_invalid_stdio_keeps_decode_error_after_observed_file_creation(self):self.compare('invalid-stdio','private-candidate')
    def test_original_invalid_executable_keeps_native_start_error_and_prior_outputs(self):
        _,kernel,output=self.compare('invalid-executable');self.assertEqual(kernel['kernel_exception']['type'],'OSError');self.assertFalse(output.tool_files)
    def test_original_negative_signal_exit_is_original_optional_false(self):self.compare('signal')
    def reference_prior_tool_output(self):
        rows=[r for r in self.fixture.documents if r['type'] in ('policy','directive')]
        rows[1]['repository_path']='generated/documents/'+rows[0]['id'].lower()+'.docx';self.fixture.save_catalog()
    def test_native_source_reads_own_prior_tool_output_with_exact_original_bytes(self):
        self.reference_prior_tool_output();self.compare('full')
    def test_private_source_reads_own_prior_tool_output_from_retained_projection(self):
        self.reference_prior_tool_output();self.compare('full','private-candidate')
    def test_native_source_missing_prior_tool_output_keeps_original_read_error(self):
        self.reference_prior_tool_output();_,kernel,_=self.compare('zero-missing');self.assertEqual(kernel['kernel_exception']['type'],'FileNotFoundError')
    def test_private_source_missing_prior_tool_output_is_derived_without_native_read(self):
        self.reference_prior_tool_output();_,kernel,_=self.compare('zero-missing','private-candidate');self.assertEqual(kernel['kernel_exception']['type'],'FileNotFoundError')
    def test_actual_timeout_after_partial_output_is_incomplete_without_original_verdict(self):
        self.binary('timeout');root,kernel,output,error=self.recorded(timeout=1)
        self.assertIsNone(kernel);self.assertIsInstance(error,InputAdmissionError);self.assertIn('timeout',str(error));self.assertEqual(read_record(root)[2]['state'],'incomplete')
        self.assertTrue(output.tool_files)
        _,_,_,_,blob,_=read_record(root);self.assertTrue(all(blob(ref)==b'before-timeout' for ref in output.tool_files.values()))
    def test_actual_stream_limit_after_output_is_incomplete_without_original_verdict(self):
        self.binary('stream-budget');root,kernel,output,error=self.recorded()
        self.assertIsNone(kernel);self.assertIsInstance(error,InputAdmissionError);self.assertIn('stream_budget',str(error));self.assertEqual(read_record(root)[2]['state'],'incomplete')
        self.assertTrue(output.tool_files)
        _,_,_,_,blob,_=read_record(root);self.assertTrue(all(blob(ref)==b'before-stream-budget' for ref in output.tool_files.values()))
    def test_relative_and_empty_PATH_entries_match_original_POSIX_which(self):
        self.binary('full');env={**self.environment,'PATH':'tools:'+str(self.tools)+':'}
        previous=Path.cwd()
        try:
            os.chdir(self.work)
            with patch.dict(os.environ,env,clear=True):expected=shutil.which('pandoc')
        finally:os.chdir(previous)
        self.assertEqual(which_at('pandoc',str(self.work),env),expected);self.assertEqual(expected,'tools/pandoc')
        self.assertIsNone(which_at('pandoc',str(self.work),{**env,'PATH':''}))
    def test_caller_data_program_is_not_executed_as_a_tool(self):
        self.binary('full');folder=self.data/'tools';folder.mkdir();shutil.copyfile(self.program,folder/'pandoc');(folder/'pandoc').chmod(0o700)
        self.environment['PATH']=str(folder);root,kernel,output,error=self.recorded()
        self.assertIsNone(kernel);self.assertIsInstance(error,InputAdmissionError);self.assertIn('caller_or_private_program',str(error));self.assertEqual(read_record(root)[2]['state'],'incomplete')

if __name__=='__main__':unittest.main()
