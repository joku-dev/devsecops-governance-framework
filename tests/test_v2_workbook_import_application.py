"""Revision-bound full workbook application, actual effects and private replay."""
from contextlib import redirect_stdout,redirect_stderr
import hashlib,io,json,os,shutil,sys,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_harmonized_workbook_import as original
from lib.workbook_import_application import generate,inspect,run,PROFILE
from lib.workbook_import_ports import read_record,encode
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read


class WholeWorkbookApplication(unittest.TestCase):
    def setUp(self):
        self.fixture=original.WholeHarmonizedWorkbookImport('test_whole_real_model_all_standards_three_export_bytes_streams_and_candidate_boundaries')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups);self.data=self.fixture.data
        self.instance=self.data.parent/'instance';self.instance.mkdir(mode=0o700)
        self.settings={'node_id':'e'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
    def execute(self,*,native=False,args=None):
        return generate({'source_worktree':str(self.data),'write_selected_reports':native,
            'legacy_arguments':['--input-xlsx',str(self.fixture.xlsx)] if args is None else args},self.instance,self.settings)
    def expected(self,args):return {**self.fixture.original(args),'original_exit_signal':None}

    def test_whole_private_and_native_outputs_keep_original_all_files_streams_and_effects(self):
        args=['--input-xlsx',str(self.fixture.xlsx)]
        for native in (False,True):
            with self.subTest(native=native):
                before={str(p):p.read_bytes() for p in self.data.rglob('*') if p.is_file()}
                receipt,result=self.execute(native=native)
                self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['exit_code'],0)
                if not native:self.assertEqual({str(p):p.read_bytes() for p in self.data.rglob('*') if p.is_file()},before)
                self.assertEqual(result['kernel_result'],self.expected(args))
                self.assertEqual(receipt['source_export_requested'],native)
                request,source,value,events,blob,closed=read_record(receipt['record_root'])
                self.assertEqual({name:blob(ref) for name,ref in result['successful_outputs'].items()},
                                 {str(self.data/name):(self.data/name).read_bytes() for name in original.OUT})
                self.assertEqual(len(result['successful_writes']),3)
                checked=inspect(receipt['record_root']);self.assertTrue(checked['retained_declared_replay_consistent'])
                self.assertFalse(checked['native_source_or_exports_repeated'])

    def test_complete_numeric_exit2_is_distinct_from_incomplete_technical_exit2(self):
        receipt,result=self.execute(args=[])
        self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['exit_code'],2);self.assertEqual(receipt['original_exit_code'],2)
        self.assertEqual(inspect(receipt['record_root'])['original_exit_signal'],{'type':'SystemExit','value':2})
        receipt,result=self.execute(args=['--input-xlsx',str(self.instance/'forbidden.xlsx')])
        self.assertEqual(receipt['state'],'incomplete');self.assertEqual(receipt['exit_code'],2);self.assertIsNone(receipt['original_exit_code'])
        self.assertIsNone(result);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_deleted_inputs_and_foreign_node_never_repeat_source_output_or_native_program(self):
        receipt,_=self.execute(native=True);shutil.rmtree(self.data)
        with patch('subprocess.Popen',side_effect=AssertionError('No native program')),patch('lib.workbook_import_application.Data',side_effect=AssertionError('No selected source')),patch('lib.workbook_import_application.Output',side_effect=AssertionError('No exports')):
            self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
        node={**self.settings,'node_id':'f'*32}
        with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node=node)

    def test_original_outside_root_post_write_error_is_complete_with_all_three_writes(self):
        external=self.data.parent/'outside';args=['--input-xlsx',str(self.fixture.xlsx),'--report-md',str(external/'report.md')]
        expected=self.expected(args);receipt,result=self.execute(native=True,args=args)
        self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['exit_code'],1);self.assertEqual(result['kernel_result'],expected)
        self.assertEqual(len(result['successful_writes']),3)
        checked=inspect(receipt['record_root'])
        self.assertEqual(checked['kernel_exception'],'ValueError')
        self.assertEqual(checked['kernel_exception_message'],expected['kernel_exception']['message'])

    def test_installed_product_export_is_rejected_before_any_source_read_or_write(self):
        target=ROOT/'scripts/lib/workbook_import_application.py';raw=target.read_bytes()
        receipt,result=self.execute(native=True,args=['--input-xlsx',str(self.fixture.xlsx),'--report-json',str(target)])
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertIsNone(result)
        self.assertEqual(target.read_bytes(),raw)
        _,_,_,events,_,_=read_record(receipt['record_root'])
        self.assertFalse(any(row.get('action')=='workbook-input-read' for row in events))

    def test_oversize_original_source_label_message_is_incomplete_capture_without_false_verdict(self):
        self.fixture.xlsx.write_bytes(original.workbook([(4,{'B':'unknown-'+('x'*66000),'G':'Synthetic text'})]))
        receipt,result=self.execute()
        self.assertEqual(receipt['state'],'incomplete');self.assertEqual(receipt['exit_code'],2)
        self.assertIsNone(receipt['original_exit_code']);self.assertIsNone(result)
        self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_actual_application_CLI_legacy_streams_and_both_inspection_modes(self):
        stdout,stderr=io.StringIO(),io.StringIO()
        args=['generate','--profile',PROFILE,'--source-worktree',str(self.data),'--','--input-xlsx',str(self.fixture.xlsx)]
        with redirect_stdout(stdout),redirect_stderr(stderr):code=run(args,self.instance,self.settings)
        self.assertEqual(code,0);receipt=json.loads(stdout.getvalue())
        for mode in ('inspect','replay'):
            stdout=io.StringIO()
            with redirect_stdout(stdout):code=run([mode,'--record',receipt['record_root']],*([] if mode=='replay' else [self.instance,self.settings]))
            self.assertEqual(code,0);self.assertTrue(json.loads(stdout.getvalue())['retained_declared_replay_consistent'])
        stdout,stderr=io.StringIO(),io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):code=run(['generate','--profile',PROFILE,'--source-worktree',str(self.data),'--format','legacy','--','--input-xlsx',str(self.fixture.xlsx)],self.instance,self.settings)
        expected=self.expected(['--input-xlsx',str(self.fixture.xlsx)])
        self.assertEqual(code,0);self.assertEqual(stdout.getvalue(),expected['stdout']);self.assertEqual(stderr.getvalue(),expected['stderr'])
        self.fixture.xlsx.write_bytes(b'Invalid ZIP')
        stdout,stderr=io.StringIO(),io.StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):
            code=run(['generate','--profile',PROFILE,'--source-worktree',str(self.data),'--format','legacy','--','--input-xlsx',str(self.fixture.xlsx)],self.instance,self.settings)
        self.assertEqual(code,1);self.assertEqual(json.loads(stderr.getvalue())['message'],'File is not a zip file')

    def reseal(self,root,events,retained):
        previous='0'*64
        for index,row in enumerate(events):
            raw=encode({'sequence':index,'previous':previous,'value':row});(root/'events'/f'{index:04}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
        retained['event_count']=len(events);retained['event_tip']=previous;(root/'result.json').write_bytes(encode(retained))

    def test_source_product_authority_request_blob_and_coherently_rehashed_result_tampering(self):
        for attack in ('source','authority','request','blob','result','selection'):
            with self.subTest(attack=attack):
                receipt,_=self.execute();root=Path(receipt['record_root'])
                request,source,value,events,blob,_=read_record(root)
                if attack=='source':
                    source['source_digest']='0'*64;(root/'source.json').write_bytes(encode(source))
                elif attack=='authority':
                    value['official_acceptance']=True;(root/'result.json').write_bytes(encode(value))
                elif attack=='request':
                    request['argv'].append('--forged');(root/'request.json').write_bytes(encode(request))
                elif attack=='blob':
                    ref=next(row['value'] for row in events if row.get('kind')=='returned' and row.get('encoding')=='bytes');p=root/'blobs'/ref['sha256'];p.write_bytes(p.read_bytes()+b' ')
                elif attack=='result':
                    value['result']['kernel_result']['stdout']+='forged';(root/'result.json').write_bytes(encode(value))
                else:
                    next(row for row in events if row.get('kind')=='workbook-selected')['selection']['outputs'][0]['label']='forged'
                    self.reseal(root,events,value)
                with self.assertRaises((ValueError,TypeError,KeyError)):inspect(root)


if __name__=='__main__':unittest.main()
