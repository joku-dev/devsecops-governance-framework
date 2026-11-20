"""Actual source-bound requests retain formatter input without selected IO."""
from pathlib import Path
from unittest.mock import patch
import copy,json,os,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_synthetic_ledger_application as reference
from lib.synthetic_ledger_application import inspect,request_valid
from lib.synthetic_ledger_ports import read_record,encode

class LedgerParserContext(unittest.TestCase):
    setUp=reference.WholeLedgerApplication.setUp
    generate=reference.WholeLedgerApplication.generate
    reseal=reference.WholeLedgerApplication.reseal

    def test_all_six_help_parser_requests_retain_native_context_and_replay_after_width_change(self):
        for program in ('synthetic','action','closure','exception','observation','record'):
            for args,code in ((['--help'],0),(['--unknown'],2)):
                with self.subTest(program=program,args=args):
                    with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}):
                        receipt,result=self.generate(program,args=args,source_worktree='/missing-selected-source')
                    self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],code)
                    request,source,retained,events,blob,closed=read_record(receipt['record_root'])
                    self.assertEqual(request['parser_context']['width'],58);self.assertEqual(len(events),3)
                    self.assertIsNone(result['ledger_binding']);self.assertFalse(result['successful_outputs'])
                    with patch.dict(os.environ,{'COLUMNS':'180'}),patch('shutil.get_terminal_size',side_effect=AssertionError('No terminal in replay')),patch('lib.synthetic_ledger_application.capture_parser_context',side_effect=AssertionError('No native context in replay')),patch('lib.synthetic_ledger_application.NativeIO',side_effect=AssertionError('No selected source in replay')):
                        self.assertEqual(inspect(receipt['record_root'])['original_exit_code'],code)

    def test_missing_or_malformed_parser_context_is_not_a_native_default_fallback(self):
        receipt,_=self.generate(args=['--help']);request,*_=read_record(receipt['record_root'])
        absent={k:v for k,v in request.items() if k!='parser_context'}
        for value in (absent,{**request,'parser_context':None},{**request,'parser_context':{**request['parser_context'],'width':True}}):
            with self.assertRaises(ValueError):request_valid(value)

    def test_resealed_wrong_formatter_context_and_final_stream_fail_whole_result_comparison(self):
        for attack in ('profile','width','stdout'):
            with patch.dict(os.environ,{'COLUMNS':'80'}):receipt,result=self.generate('closure',args=['--help'])
            root=Path(receipt['record_root']);request,source,value,events,*_=read_record(root)
            if attack=='stdout':value['result']['kernel_result']['stdout']='forged original stdout\n'
            else:
                if attack=='width':request['parser_context']['width']=38
                else:
                    old=request['parser_context']['version'][1];minor=13 if old in (11,12) else 12
                    request['parser_context'].update(version=[3,minor,3],profile=f'cpython-3.{minor}-argparse-v1')
                events[1]['request']=request;(root/'request.json').write_bytes(encode(request))
            self.reseal(root,events,value)
            with self.assertRaisesRegex(ValueError,'whole_result_changed'):inspect(root)

    def test_native_unknown_profile_failure_creates_no_selected_source_or_original_verdict(self):
        with patch('lib.synthetic_ledger_application.capture_parser_context',side_effect=ValueError('native profile unavailable')),patch('lib.synthetic_ledger_application.NativeIO',side_effect=AssertionError('No selected source')):
            with self.assertRaisesRegex(ValueError,'native profile unavailable'):self.generate(args=['--help'])
        self.assertFalse((self.instance/'state/synthetic-ledger/records').exists())

if __name__=='__main__':unittest.main(verbosity=2)
