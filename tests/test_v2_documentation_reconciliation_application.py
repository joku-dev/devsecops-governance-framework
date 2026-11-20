"""Current source/node-bound whole-program records and inert portable replay."""
from pathlib import Path
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
import hashlib,importlib.util,io,json,shutil,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_documentation_reconciliation_core as reference
from lib.documentation_reconciliation_application import generate,inspect,run,request_valid,PROFILE
from lib.documentation_reconciliation_ports import read_record,current_source
from lib.portable.runtime import source_digest
from lib.providers.retained_argparse import capture_context
from lib.functional_parity import git_read
from lib.requirement_validation_budget import InputAdmissionError
from lib.portable import runtime

class DocumentationApplication(unittest.TestCase):
    def setUp(self):
        self.reference=reference.WholeOriginal('test_original_bad_git_reference_fails_without_writing_outputs')
        self.reference.setUp();self.addCleanup(self.reference.doCleanups)
        self.data,self.args=self.reference.fixture();self.instance=self.data.parent/'instance';self.instance.mkdir(mode=0o700)
        self.settings={'node_id':'d'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}

    def generate(self,native=False,args=None,**extra):
        return generate({'source_worktree':str(self.data),'legacy_arguments':self.args if args is None else args,
            'write_selected_files':native,**extra},self.instance,self.settings)

    def test_whole_original_private_and_native_records_keep_full_outputs_streams_and_source_effects(self):
        before=reference.snapshot(self.data)
        for native in (False,True):
            receipt,result=self.generate(native=native)
            self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0)
            self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred'])
            checked=inspect(receipt['record_root'],node=self.settings)
            self.assertTrue(checked['retained_declared_replay_consistent']);self.assertTrue(result['successful_outputs'])
            self.assertEqual(result['kernel_result']['stdout'],'documentation refresh required\n')
            if not native:self.assertEqual(reference.snapshot(self.data),before);self.assertTrue(result['private_projected_changes'])
            else:self.assertTrue((self.data/'generated/reports/documentation-refresh-audit.md').is_file());self.assertFalse(result['private_projected_changes'])

    def test_native_source_deleted_replay_and_foreign_instance_inspection_rejected(self):
        receipt,result=self.generate(native=True,args=[*self.args,'--github-output',str(self.data/'caller-output')])
        self.assertEqual(receipt['state'],'complete');shutil.rmtree(self.data)
        with patch('subprocess.Popen',side_effect=AssertionError('No programs in replay')),patch('lib.documentation_reconciliation_application.NativeIO',side_effect=AssertionError('No selected files in replay')):
            checked=inspect(receipt['record_root'])
        self.assertEqual(checked['successful_outputs'],result['successful_outputs']);self.assertFalse(checked['native_source_or_exports_repeated'])
        with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'a'*32})

    def test_help_and_parser_require_no_selected_files_git_or_append(self):
        for args,code in ((['--help'],0),(['--unknown'],2)):
            with patch('lib.documentation_reconciliation_application.NativeGit.context',side_effect=AssertionError('No selected Git')):
                receipt,result=self.generate(args=args,source_worktree='/no-such-documentation-source')
            self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],code)
            self.assertFalse(result['successful_outputs']);self.assertFalse(result['private_projected_changes'])
            request,source,retained,events,blob,closed=read_record(receipt['record_root']);self.assertEqual(len(events),3)
            self.assertEqual(inspect(receipt['record_root'])['original_exit_signal'],{'type':'SystemExit','value':code})

    def test_original_nonzero_git_result_is_complete_but_technical_capture_failure_has_no_original_verdict(self):
        receipt,result=self.generate(args=[*self.args,'--base','no-such-original-reference'])
        self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],1)
        self.assertEqual(result['kernel_result']['kernel_exception']['type'],'CalledProcessError')
        with patch('lib.documentation_reconciliation_application.NativeGit.run',side_effect=InputAdmissionError('injected capture unavailable')):
            incomplete,result=self.generate()
        self.assertEqual(incomplete['state'],'incomplete');self.assertIsNone(incomplete['original_exit_code']);self.assertEqual(incomplete['exit_code'],2)
        self.assertFalse(inspect(incomplete['record_root'])['retained_declared_replay_consistent'])

    def test_native_late_append_directory_error_retains_prior_documents_and_partial_indication(self):
        directory=self.data/'caller-directory';directory.mkdir()
        receipt,result=self.generate(native=True,args=[*self.args,'--github-output',str(directory)])
        self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],1);self.assertTrue(receipt['source_effects_may_be_partial'])
        self.assertEqual(result['kernel_result']['kernel_exception']['type'],'IsADirectoryError');self.assertEqual(len(result['successful_outputs']),4)
        self.assertEqual((self.data/'generated/reports/documentation-refresh-audit.md').read_bytes(),read_record(receipt['record_root'])[4](result['successful_outputs'][str(self.data/'generated/reports/documentation-refresh-audit.md')]))
        self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_request_types_allow_original_multiline_body_but_reject_wrong_profile_boolean_version_and_nul(self):
        request={'schema_version':1,'profile':PROFILE,'source_label':str(self.data),'cwd_label':str(self.data),'argv':self.args,'export_mode':'private-candidate','parser_context':capture_context()}
        self.assertEqual(request_valid(request),request)
        for key,value in (('schema_version',True),('profile','different'),('argv',['--body','bad\0body']),('export_mode',False)):
            with self.assertRaises(ValueError):request_valid({**request,key:value})

    def test_resealed_metadata_authority_whole_result_and_extra_blob_mutations_rejected(self):
        for attack in ('source','node','authority','whole-result','extra-blob'):
            receipt,result=self.generate();root=Path(receipt['record_root'])
            name='source.json' if attack in ('source','node') else 'result.json';file=root/name;value=json.loads(file.read_bytes())
            if attack=='source':value['source_digest']='0'*64
            elif attack=='node':value['node_context']['node_id']='0'*32
            elif attack=='authority':value['official_acceptance']=0
            elif attack=='whole-result':value['result']['kernel_result']['stdout']='forged\n'
            else:
                raw=b'unreferenced data';(root/'blobs'/hashlib.sha256(raw).hexdigest()).write_bytes(raw)
            file.write_text(json.dumps(value)+'\n')
            with self.assertRaises(ValueError,msg=attack):inspect(root,node=self.settings if attack=='node' else None)

    def test_actual_cli_receipt_format_and_unknown_option_return_original_parser_values(self):
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            code=run(['generate','--profile',PROFILE,'--source-worktree',str(self.data),'--','--unknown'],self.instance,self.settings)
        value=json.loads(out.getvalue());self.assertEqual(code,2);self.assertEqual(value['state'],'complete');self.assertEqual(value['original_exit_code'],2)

    def test_source_only_compatibility_retains_all_original_bytes_context_and_is_excluded_from_product(self):
        fixture=ROOT/'tests/fixtures/v2-documentation-reconciliation-original/original.py.txt'
        adapter=ROOT/'scripts/lib/providers/legacy_documentation_reconciliation.py';self.assertEqual(adapter.read_bytes(),fixture.read_bytes())
        spec=importlib.util.spec_from_file_location('reconcile_documentation_after_merge',ROOT/'scripts/reconcile_documentation_after_merge.py')
        module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'reconcile_documentation_after_merge':module}):
            spec.loader.exec_module(module);facade=sys.modules['reconcile_documentation_after_merge']
            self.assertEqual(facade.ROOT,ROOT);self.assertEqual(facade.README,ROOT/'README.md');self.assertEqual(facade.clean_summary('## Summary\n- keep me','title'),['keep me'])
        selected=json.loads((ROOT/'config/axiom-v2-distribution.json').read_bytes())['python_files']
        self.assertNotIn(str(adapter.relative_to(ROOT)),selected);self.assertNotIn('scripts/reconcile_documentation_after_merge.py',selected)
        bridge=ROOT/'scripts/lib/providers/documentation_reconciliation_compatibility.py'
        self.assertNotIn(str(bridge.relative_to(ROOT)),selected)
        digest=source_digest()
        original_digest=runtime.file_digest
        with patch('lib.portable.runtime.file_digest',side_effect=lambda p: (_ for _ in ()).throw(AssertionError('Excluded source adapter or bridge read')) if p in (adapter,bridge) else original_digest(p)):
            self.assertEqual(source_digest(),digest)

    def test_replaced_native_stream_descriptor_is_not_closed_by_host_release(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from lib.providers.documentation_reconciliation_append import NativeAppend
        stream=SimpleNamespace(closed=False,fileno=lambda:123,close=Mock())
        selected=NativeAppend.__new__(NativeAppend);selected.stream=stream;selected.fd_identity=(1,2)
        selected.owner=SimpleNamespace(record=SimpleNamespace(capture_incomplete=False))
        with patch('os.fstat',return_value=SimpleNamespace(st_dev=9,st_ino=9)):
            with self.assertRaisesRegex(InputAdmissionError,'descriptor_replaced'):selected.release()
        stream.close.assert_not_called();self.assertTrue(selected.owner.record.capture_incomplete)

if __name__=='__main__':unittest.main(verbosity=2)
