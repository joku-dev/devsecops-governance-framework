"""Actual whole original parser streams, retained producer inputs and tamper guards."""
from pathlib import Path
from unittest.mock import patch
import argparse,hashlib,json,os,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_documentation_reconciliation_application as reference
from lib.documentation_reconciliation_application import inspect,request_valid
from lib.documentation_reconciliation_ports import read_record,encode

class DocumentationParserContext(unittest.TestCase):
    setUp=reference.DocumentationApplication.setUp
    generate=reference.DocumentationApplication.generate

    def test_complete_original_help_unknown_and_empty_streams_at_three_widths_both_modes_and_inert_replay(self):
        for columns in (40,80,120):
            for native in (False,True):
                for args,code in ((['--help'],0),(['--unknown'],2),([],2)):
                    with self.subTest(columns=columns,native=native,args=args),patch.dict(os.environ,{'COLUMNS':str(columns),'LINES':'24'}):
                        old=subprocess.run([sys.executable,'-B',str(self.data/'scripts/reconcile_documentation_after_merge.py'),*args],cwd=self.data,capture_output=True,timeout=30,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
                        self.assertEqual(old.returncode,code)
                        with patch('lib.documentation_reconciliation_application.NativeGit.context',side_effect=AssertionError('No selected Git in parser exit')):
                            receipt,result=self.generate(native=native,args=args,source_worktree='/no-selected-documentation-parser-source')
                        self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],code)
                        self.assertEqual(result['kernel_result']['stdout'].encode(),old.stdout);self.assertEqual(result['kernel_result']['stderr'].encode(),old.stderr)
                        request,_,_,events,_,closed=read_record(receipt['record_root']);self.assertEqual(request['parser_context']['width'],columns-2);self.assertEqual(len(events),3);self.assertTrue(closed())
                        with patch.dict(os.environ,{'COLUMNS':'180'}),patch('shutil.get_terminal_size',side_effect=AssertionError('No consumer terminal')),patch.object(argparse,'_',side_effect=AssertionError('No consumer gettext')),patch.object(argparse,'ngettext',side_effect=AssertionError('No consumer plural')),patch('lib.documentation_reconciliation_application.capture_parser_context',side_effect=AssertionError('No native parser discovery')),patch('lib.documentation_reconciliation_application.NativeIO',side_effect=AssertionError('No selected files')),patch('subprocess.Popen',side_effect=AssertionError('No program during replay')):
                            value=inspect(receipt['record_root'])
                        self.assertEqual(value['original_exit_code'],code);self.assertTrue(value['retained_declared_replay_consistent'])

    def test_missing_malformed_or_cross_profile_context_never_falls_back_to_native_parser(self):
        receipt,_=self.generate(args=['--help']);request,*_=read_record(receipt['record_root'])
        for bad in ({k:v for k,v in request.items() if k!='parser_context'},{**request,'parser_context':None},{**request,'parser_context':{**request['parser_context'],'width':True}},{**request,'parser_context':{**request['parser_context'],'profile':'unknown'}}):
            with self.assertRaises(ValueError):request_valid(bad)

    def test_resealed_width_and_final_stream_changes_fail_complete_result_reconstruction(self):
        for attack in ('width','stdout'):
            with patch.dict(os.environ,{'COLUMNS':'80'}):receipt,_=self.generate(args=['--help'])
            root=Path(receipt['record_root']);request,_,value,events,*_=read_record(root)
            if attack=='width':
                request['parser_context']['width']=38;events[1]['request']=request;(root/'request.json').write_bytes(encode(request))
            else:value['result']['kernel_result']['stdout']='forged help stream\n'
            previous='0'*64
            for index,event in enumerate(events):
                raw=encode({'sequence':index,'previous':previous,'value':event});(root/'events'/f'{index:08}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
            value['event_count'],value['event_tip']=len(events),previous;(root/'result.json').write_bytes(encode(value))
            with self.assertRaisesRegex(ValueError,'whole_result_changed'):inspect(root)

    def test_unsupported_native_context_fails_before_records_or_selected_file_observation(self):
        with patch('lib.documentation_reconciliation_application.capture_parser_context',side_effect=ValueError('native parser unavailable')),patch('lib.documentation_reconciliation_application.NativeIO',side_effect=AssertionError('No selected file observation')):
            with self.assertRaisesRegex(ValueError,'native parser unavailable'):self.generate(args=['--help'])
        self.assertFalse((self.instance/'state/documentation-reconciliation/records').exists())

if __name__=='__main__':unittest.main(verbosity=2)
