"""Explicit producer parse contexts in all prior whole-program capture APIs."""
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
import argparse,hashlib,json,os,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib import synthetic_lifecycle_application as lifecycle
from lib import workbook_import_application as workbook
from lib import document_rendering_application as renderer
from lib import synthetic_ledger_application as ledger
from lib import lifecycle_candidate_preparation_application as candidates
from lib.synthetic_lifecycle_context import GENERATORS
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read

class ProducerParserContext(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve();self.instance=self.root/'instance';self.instance.mkdir(mode=0o700)
        self.settings={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}

    def capture(self,api,*,generator='pilot',argv=('--help',),native=False):
        options={'source_worktree':'/no-selected-producer-parser-source','legacy_arguments':list(argv),'write_selected_reports':native}
        if api is lifecycle:options['generator']=generator
        if api is renderer:options['tool_path']='/no-pandoc-for-parser'
        return api.generate(options,self.instance,self.settings)

    def forbidden_replay(self,api,root):
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ,{'COLUMNS':'180','LINES':'24'}))
            for name in ('shutil.get_terminal_size','argparse._','argparse.ngettext','subprocess.Popen',
                'lib.providers.synthetic_lifecycle_io.NativeIO.read','lib.providers.workbook_import_io.Data.read',
                'lib.providers.document_rendering_io.Data.read','lib.providers.document_rendering_tools.Tools.which',
                'lib.providers.document_rendering_tools.Tools.run','lib.providers.synthetic_lifecycle_output.NativeOutput.mkdir_one',
                'lib.providers.synthetic_lifecycle_output.NativeOutput.write_chunk'):
                stack.enter_context(patch(name,side_effect=AssertionError('No consumer/native observer in pure replay')))
            stack.enter_context(patch.object(api,'capture_parser_context',side_effect=AssertionError('No producer observation in replay')))
            return api.inspect(root)

    def test_all_five_reporting_parsers_reconstruct_whole_help_unknown_streams_both_modes_without_host_defaults(self):
        for generator in GENERATORS:
            for native in (False,True):
                for argv,code in ((['--help'],0),(['--unknown'],2)):
                    with self.subTest(generator=generator,native=native,argv=argv),patch.dict(os.environ,{'COLUMNS':'60'}):
                        receipt,result=self.capture(lifecycle,generator=generator,argv=argv,native=native)
                    self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],code)
                    request,_,_,events,_,closed=lifecycle.read_record(receipt['record_root']);self.assertEqual(len(events),3);self.assertTrue(closed());self.assertEqual(request['parser_context']['width'],58)
                    self.assertFalse(result['successful_outputs']);self.assertEqual(self.forbidden_replay(lifecycle,receipt['record_root'])['original_exit_code'],code)

    def test_workbook_and_renderer_parser_exits_reconstruct_without_selected_data_tools_or_terminal(self):
        for api in (workbook,renderer):
            for native in (False,True):
                for argv,code in ((['--help'],0),(['--unknown'],2)):
                    with self.subTest(api=api.__name__,native=native,argv=argv),patch.dict(os.environ,{'COLUMNS':'60'}):receipt,result=self.capture(api,argv=argv,native=native)
                    self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],code)
                    request,_,_,events,_,closed=api.read_record(receipt['record_root']);self.assertEqual(len(events),3);self.assertTrue(closed());self.assertEqual(request['parser_context']['width'],58)
                    self.assertFalse(result['successful_outputs']);self.assertEqual(self.forbidden_replay(api,receipt['record_root'])['original_exit_code'],code)

    def test_execution_admission_requires_typed_context_and_metadata_bridge_cannot_execute(self):
        for api in (lifecycle,workbook,renderer):
            receipt,_=self.capture(api);request=api.read_record(receipt['record_root'])[0];self.assertEqual(api.request_valid(request),request)
            for bad in ({k:v for k,v in request.items() if k!='parser_context'},{**request,'parser_context':None},{**request,'parser_context':{**request['parser_context'],'width':True}},{**request,'parser_context':{**request['parser_context'],'profile':'unknown'}}):
                with self.assertRaises(ValueError):api.request_valid(bad)
            if api is lifecycle:
                fields={k:v for k,v in request.items() if k!='parser_context'};self.assertEqual(lifecycle.request_fields_valid(fields),fields)
                with self.assertRaises(ValueError):lifecycle.request_valid(fields)

    def test_resealed_width_and_final_stream_mutations_fail_whole_result_not_normalization(self):
        for api in (lifecycle,workbook,renderer):
            for attack in ('width','stdout'):
                with patch.dict(os.environ,{'COLUMNS':'80'}):receipt,_=self.capture(api)
                root=Path(receipt['record_root']);request,source,value,events,*_=api.read_record(root)
                if attack=='width':request['parser_context']['width']=38;events[1]['request']=request;(root/'request.json').write_bytes(api.encode(request))
                else:value['result']['kernel_result']['stdout']='forged final stdout\n'
                previous='0'*64
                files=sorted((root/'events').glob('*.json'));self.assertEqual(len(files),len(events))
                for index,(event,file) in enumerate(zip(events,files)):
                    raw=api.encode({'sequence':index,'previous':previous,'value':event});file.write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
                value['event_count'],value['event_tip']=len(events),previous;(root/'result.json').write_bytes(api.encode(value))
                with self.assertRaisesRegex(ValueError,'whole_result_changed'):api.inspect(root)

    def test_unsupported_native_parser_fails_before_records_or_selected_observers(self):
        for api in (lifecycle,workbook,renderer):
            with patch.object(api,'capture_parser_context',side_effect=ValueError('native parser not admitted')):
                with self.assertRaisesRegex(ValueError,'native parser not admitted'):self.capture(api)
        self.assertFalse((self.instance/'state').exists())

    def test_ledger_and_candidate_metadata_bridges_keep_their_required_parser_execution_context(self):
        for api,selector in ((ledger,{'program':'synthetic'}),(candidates,{'program':'devsecops'})):
            receipt,result=api.generate({'source_worktree':'/no-selected-bridge-source','legacy_arguments':['--help'],**selector},self.instance,self.settings)
            self.assertEqual(receipt['state'],'complete',receipt);request=api.read_record(receipt['record_root'])[0]
            self.assertIn('parser_context',request)
            with self.assertRaises(ValueError):api.request_valid({k:v for k,v in request.items() if k!='parser_context'})
            self.assertTrue(api.inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_exact_older_reporting_width_regression_is_closed_under_explicit_producer_profile(self):
        with patch.dict(os.environ,{'COLUMNS':'80'}):receipt,_=self.capture(lifecycle)
        for columns in ('80','40','80'):
            with patch.dict(os.environ,{'COLUMNS':columns}),patch('shutil.get_terminal_size',side_effect=AssertionError('No terminal')):
                self.assertTrue(lifecycle.inspect(receipt['record_root'])['retained_declared_replay_consistent'])

if __name__=='__main__':unittest.main(verbosity=2)
