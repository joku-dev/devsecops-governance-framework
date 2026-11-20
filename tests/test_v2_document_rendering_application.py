"""Whole renderer application records, generation boundaries and no-native replay."""
from contextlib import redirect_stdout,redirect_stderr
import hashlib,io,json,shutil,sys,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_document_rendering_io as original
from lib.document_rendering_application import generate,inspect,run,PROFILE,request_valid
from lib.document_rendering_ports import read_record,encode,current_source
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read


class WholeDocumentApplication(unittest.TestCase):
    def setUp(self):
        self.fixture=original.WholeDocumentFileIO('test_whole_real_models_all_MD_HTML_bytes_private_projection')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups);self.data=self.fixture.data
        self.instance=self.fixture.private
        self.settings={'node_id':'e'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
    def execute(self,*,native=False,args=(),**extra):
        return generate({'source_worktree':str(self.data),'write_selected_reports':native,
            'tool_path':'/axiom-explicitly-absent-pandoc','legacy_arguments':list(args),**extra},self.instance,self.settings)
    def expected(self,args=()):
        value=self.fixture.original(args)
        return {'exit_code':value['exit'],'kernel_exception':value['error'],'stdout':value['stdout'],'stderr':value['stderr'],'original_exit_signal':None}
    def test_private_and_native_whole_original_streams_all_four_files_and_declared_authority(self):
        for native in (False,True):
            with self.subTest(native=native):
                before=self.fixture.files();expected=self.expected()
                shutil.rmtree(self.data/'generated')
                receipt,result=self.execute(native=native)
                self.assertEqual(receipt['state'],'complete');self.assertEqual(result['kernel_result'],expected)
                if not native:self.assertEqual(self.fixture.files(),before)
                self.assertEqual(len(result['successful_outputs']),4);self.assertEqual(len(result['successful_writes']),4)
                self.assertFalse(result['observed_tool_outputs']);self.assertFalse(receipt['official_acceptance'])
                checked=inspect(receipt['record_root']);self.assertTrue(checked['retained_declared_replay_consistent'])
                self.assertFalse(checked['native_source_tool_or_exports_repeated'])
    def test_original_help_zero_unknown_selected_zero_and_numeric_parse_two_are_complete(self):
        for args,code in ((['--help'],0),(['--document-id','unknown'],0),(['--unknown'],2)):
            with self.subTest(args=args):
                receipt,result=self.execute(args=args)
                self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],code)
                self.assertFalse(result['successful_writes']);self.assertEqual(inspect(receipt['record_root'])['original_exit_code'],code)
    def test_later_missing_source_is_original_error_with_prior_files_and_replay(self):
        rows=[r for r in self.fixture.documents if r['type'] in ('policy','directive')]
        (self.data/rows[1]['repository_path']).unlink();expected=self.expected();shutil.rmtree(self.data/'generated')
        receipt,result=self.execute(native=True)
        self.assertEqual(receipt['state'],'complete');self.assertEqual(result['kernel_result'],expected)
        self.assertEqual(receipt['original_exit_code'],1);self.assertEqual(len(result['successful_writes']),2)
        self.assertEqual(inspect(receipt['record_root'])['kernel_exception']['type'],'FileNotFoundError')
    def test_private_input_is_incomplete_without_original_verdict(self):
        row=next(r for r in self.fixture.documents if r['type'] in ('policy','directive'))
        row['repository_path']=str(self.instance/'secret.md');self.fixture.save_catalog()
        receipt,result=self.execute();self.assertEqual(receipt['state'],'incomplete')
        self.assertIsNone(receipt['original_exit_code']);self.assertIsNone(result)
        self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
    def test_deleted_source_replay_and_foreign_node_inspect_never_execute_native_ports(self):
        receipt,_=self.execute(native=True);shutil.rmtree(self.data)
        with patch('subprocess.Popen',side_effect=AssertionError('No process')),patch('lib.document_rendering_application.Data',side_effect=AssertionError('No source')),patch('lib.document_rendering_application.Output',side_effect=AssertionError('No export')):
            self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
        with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'f'*32})
    def test_application_cli_receipt_legacy_streams_inspect_and_no_instance_replay(self):
        base=['generate','--profile',PROFILE,'--source-worktree',str(self.data),'--tool-path','/axiom-explicitly-absent-pandoc']
        stdout,stderr=io.StringIO(),io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):code=run(base,self.instance,self.settings)
        self.assertEqual(code,0);receipt=json.loads(stdout.getvalue())
        for mode in ('inspect','replay'):
            stdout=io.StringIO()
            with redirect_stdout(stdout):code=run([mode,'--record',receipt['record_root']],*([] if mode=='replay' else [self.instance,self.settings]))
            self.assertEqual(code,0);self.assertTrue(json.loads(stdout.getvalue())['retained_declared_replay_consistent'])
        expected=self.expected();stdout,stderr=io.StringIO(),io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):code=run([*base,'--format','legacy'],self.instance,self.settings)
        self.assertEqual(code,0);self.assertEqual(stdout.getvalue(),expected['stdout']);self.assertEqual(stderr.getvalue(),expected['stderr'])
    def reseal(self,root,events,value):
        previous='0'*64
        for index,row in enumerate(events):
            raw=encode({'sequence':index,'previous':previous,'value':row});(root/'events'/f'{index:04}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
        value['event_count']=len(events);value['event_tip']=previous;(root/'result.json').write_bytes(encode(value))
    def test_product_authority_request_result_and_context_tampering_are_rejected(self):
        for attack in ('source','authority','request','result','lookup-context'):
            with self.subTest(attack=attack):
                receipt,_=self.execute();root=Path(receipt['record_root']);request,source,value,events,blob,_=read_record(root)
                if attack=='source':source['source_digest']='0'*64;(root/'source.json').write_bytes(encode(source))
                elif attack=='authority':value['official_acceptance']=True;(root/'result.json').write_bytes(encode(value))
                elif attack=='request':request['tool_path']='/forged';(root/'request.json').write_bytes(encode(request))
                elif attack=='result':value['result']['kernel_result']['stdout']+='forged';(root/'result.json').write_bytes(encode(value))
                else:
                    token=next(r['operation'] for r in events if r.get('kind')=='intent' and r.get('action')=='document-tool-find')
                    row=next(r for r in events if r.get('kind')=='returned' and r.get('operation')==token)
                    captured=json.loads(blob(row['value']));captured['context']['PATH']='/forged';raw=encode(captured)
                    ref={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};(root/'blobs'/ref['sha256']).write_bytes(raw);row['value']=ref;self.reseal(root,events,value)
                with self.assertRaises((ValueError,TypeError,KeyError)):inspect(root)
    def test_request_validation_rejects_nonfinite_timeout_control_args_and_unknown_keys(self):
        receipt,_=self.execute();request=read_record(receipt['record_root'])[0]
        for change in ({'tool_timeout':float('nan')},{'tool_timeout':True},{'tool_timeout':0},{'tool_timeout':601},{'argv':['\0']},{'tool_path':'a\0b'},{'source_date_epoch':7},{'extra':False}):
            with self.subTest(change=change),self.assertRaises(ValueError):request_valid({**request,**change})
    def test_source_generation_and_runtime_drift_rejected_before_record_or_export(self):
        for change in ({'source_revision':'0'*40},{'runtime_source_digest':'0'*64},{'node_id':'invalid'}):
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'document_rendering_node_'):current_source({**self.settings,**change})
        self.assertFalse((self.instance/'state').exists())
    def test_native_export_into_installed_product_is_incomplete_and_changes_no_product_file(self):
        target=ROOT/'generated/documents';before={str(p):p.read_bytes() for p in target.rglob('*') if p.is_file()}
        receipt,result=self.execute(native=True,source_worktree=str(ROOT))
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(result);self.assertIsNone(receipt['original_exit_code'])
        self.assertEqual(before,{str(p):p.read_bytes() for p in target.rglob('*') if p.is_file()})
    def test_original_exception_legacy_cli_prints_structured_failure_without_invented_traceback(self):
        (self.data/'model/documents/governance-documents.yaml').unlink();stdout,stderr=io.StringIO(),io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):
            code=run(['generate','--profile',PROFILE,'--source-worktree',str(self.data),'--tool-path','/axiom-explicitly-absent-pandoc','--format','legacy'],self.instance,self.settings)
        self.assertEqual(code,1);self.assertFalse(stdout.getvalue())
        self.assertEqual(json.loads(stderr.getvalue())['type'],'FileNotFoundError');self.assertNotIn('Traceback',stderr.getvalue())
    def test_actual_controlled_tool_application_retains_all_six_outputs_in_both_modes(self):
        import test_v2_document_rendering_tools as tools
        case=tools.WholeDocumentToolIO('test_actual_native_whole_original_tool_and_all_export_bytes');case.setUp();self.addCleanup(case.doCleanups)
        case.binary('full');self.data=case.data
        for native in (False,True):
            with self.subTest(native=native):
                receipt,result=self.execute(native=native,tool_path=str(case.program.parent))
                self.assertEqual(receipt['state'],'complete');self.assertEqual(result['exit_code'],0)
                self.assertEqual(len(result['successful_outputs']),4);self.assertEqual(len(result['observed_tool_outputs']),2)
                self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
    def test_actual_tool_timeout_is_incomplete_with_prior_text_writes_and_no_original_verdict(self):
        import test_v2_document_rendering_tools as tools
        case=tools.WholeDocumentToolIO('test_actual_native_whole_original_tool_and_all_export_bytes');case.setUp();self.addCleanup(case.doCleanups)
        case.binary('timeout');self.data=case.data
        receipt,result=self.execute(native=True,tool_path=str(case.program.parent),tool_timeout=1)
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertIsNone(result)
        self.assertTrue(any(p.suffix=='.html' for p in (self.data/'generated/documents').iterdir()))
        _,_,retained,events,_,_=read_record(receipt['record_root'])
        self.assertTrue(any(row.get('kind')=='document-tool-after' and row['process']['timed_out'] for row in events))
        self.assertEqual(retained['exception_type'],'InputAdmissionError')


if __name__=='__main__':unittest.main()
