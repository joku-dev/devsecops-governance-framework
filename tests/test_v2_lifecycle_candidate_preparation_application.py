"""Whole source-bound candidate applications and private immutable replay receipts."""
from pathlib import Path
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
import hashlib,io,json,os,shutil,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_lifecycle_candidate_preparation_core as original
from lib.lifecycle_candidate_preparation_application import generate,inspect,run,request_valid,PROFILE
from lib.lifecycle_candidate_preparation_ports import read_record,encode
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read
from lib.requirement_validation_budget import InputAdmissionError

class CandidateApplication(unittest.TestCase):
    def setUp(self):
        self.reference=original.WholeCandidatePreparation('test_both_complete_programs_preserve_all_example_bytes_and_diagnostic_authority_both_modes');self.reference.setUp();self.addCleanup(self.reference.doCleanups)
        self.instance=self.reference.parent/'instance';self.instance.mkdir(mode=0o700)
        self.settings={'node_id':'e'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}

    def generate(self,program='devsecops',native=False,args=None,**extra):
        root,normal=self.reference.fixture(program)
        return generate({'program':program,'source_worktree':str(root),'legacy_arguments':normal if args is None else args,'write_selected_files':native,**extra},self.instance,self.settings),root

    def reseal(self,root,events,value):
        previous='0'*64
        for index,event in enumerate(events):
            raw=encode({'sequence':index,'previous':previous,'value':event});(root/'events'/f'{index:08}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
        value['event_count'],value['event_tip']=len(events),previous;(root/'result.json').write_bytes(encode(value))

    def test_both_registered_programs_private_and_native_keep_complete_original_candidate_bytes(self):
        for program in original.PROGRAMS:
            for native in (False,True):
                (receipt,result),data=self.generate(program,native=native)
                self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0)
                self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred'])
                expected=(data/'docs/examples/lifecycle-candidates'/f'{program}-candidates.json').read_bytes();output=data/'generated/reports/lifecycle-candidates/result.json'
                if native:self.assertEqual(output.read_bytes(),expected)
                else:self.assertFalse(output.exists());self.assertTrue(result['private_projected_changes'])
                self.assertTrue(inspect(receipt['record_root'],node=self.settings)['retained_declared_replay_consistent'])
                self.assertEqual(result['kernel_result']['stdout'],f"Prepared {len(json.loads(expected)['candidates'])} unverified {'control' if program=='devsecops' else 'gate'} candidates; {'no lifecycle intake or state change.' if program=='devsecops' else 'no marker inference or lifecycle intake.'}\n")

    def test_help_parser_and_empty_retain_context_without_any_selected_data_or_outputs(self):
        for program in original.PROGRAMS:
            for args,code in ((['--help'],0),(['--unknown'],2),([],2)):
                with patch.dict(os.environ,{'COLUMNS':'60'}),(patch('lib.providers.synthetic_lifecycle_io.NativeIO.read',side_effect=AssertionError('No selected source'))):
                    (receipt,result),data=self.generate(program,args=args,source_worktree='/no-selected-candidate-data')
                self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],code);self.assertFalse(result['successful_outputs'])
                request,source,value,events,*_=read_record(receipt['record_root']);self.assertEqual(len(events),3);self.assertEqual(request['parser_context']['width'],58)
                with patch.dict(os.environ,{'COLUMNS':'180'}),patch('shutil.get_terminal_size',side_effect=AssertionError('No consumer terminal')),patch('lib.lifecycle_candidate_preparation_application.capture_parser_context',side_effect=AssertionError('No native context')):
                    self.assertEqual(inspect(receipt['record_root'])['original_exit_code'],code)

    def test_native_source_deleted_replay_is_inert_and_foreign_node_is_rejected(self):
        (receipt,result),data=self.generate('architecture',native=True);self.assertEqual(receipt['state'],'complete',receipt);shutil.rmtree(data)
        with patch('subprocess.Popen',side_effect=AssertionError('No programs')),patch('lib.lifecycle_candidate_preparation_application.NativeIO',side_effect=AssertionError('No selected reads')),patch('lib.providers.synthetic_lifecycle_output.NativeOutput.mkdir_one',side_effect=AssertionError('No mkdir')),patch('lib.providers.synthetic_lifecycle_output.NativeOutput.write_chunk',side_effect=AssertionError('No outputs')):
            value=inspect(receipt['record_root'])
        self.assertEqual(value['successful_outputs'],result['successful_outputs']);self.assertFalse(value['native_source_or_exports_repeated'])
        with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'f'*32})

    def test_original_guard_error_is_complete_but_capture_failure_has_no_original_verdict(self):
        root,args=self.reference.fixture('devsecops');args[5]=args[1]
        receipt,result=generate({'program':'devsecops','source_worktree':str(root),'legacy_arguments':args},self.instance,self.settings)
        self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],1);self.assertEqual(result['kernel_result']['kernel_exception']['type'],'ContractError')
        with patch('lib.providers.synthetic_lifecycle_io.NativeIO.read',side_effect=InputAdmissionError('injected observation unavailable')):
            (receipt,result),_=self.generate()
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_resealed_source_authority_width_stream_and_extra_blob_attacks_fail_closed(self):
        for attack in ('source','authority','width','stdout','extra-blob'):
            with patch.dict(os.environ,{'COLUMNS':'80'}):(receipt,_),_=self.generate(args=['--help'])
            root=Path(receipt['record_root']);request,source,value,events,*_=read_record(root)
            if attack=='source':source['source_digest']='0'*64;(root/'source.json').write_bytes(encode(source))
            elif attack=='authority':value['official_acceptance']=0;self.reseal(root,events,value)
            elif attack=='width':request['parser_context']['width']=38;events[1]['request']=request;(root/'request.json').write_bytes(encode(request));self.reseal(root,events,value)
            elif attack=='stdout':value['result']['kernel_result']['stdout']='forged\n';self.reseal(root,events,value)
            else:raw=b'extra unreferenced raw data';(root/'blobs'/hashlib.sha256(raw).hexdigest()).write_bytes(raw)
            with self.assertRaises(ValueError,msg=attack):inspect(root)

    def test_native_partial_original_write_error_marks_possible_partial_effects_both_programs(self):
        import errno
        from lib.providers.synthetic_lifecycle_output import NativeOutput
        for program in original.PROGRAMS:
            data,args=self.reference.fixture(program);calls=[]
            def partial(port,fd,view):
                calls.append(len(view))
                if len(calls)==1:return os.write(fd,view[:7])
                raise OSError(errno.ENOSPC,'No space left on device')
            with patch.object(NativeOutput,'write_chunk',partial):
                receipt,result=generate({'program':program,'source_worktree':str(data),'legacy_arguments':args,'write_selected_files':True},self.instance,self.settings)
            self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],1);self.assertTrue(receipt['source_effects_may_be_partial'])
            target=Path(args[5]);self.assertEqual(len(target.read_bytes()),7);self.assertEqual(result['kernel_result']['kernel_exception']['type'],'OSError')
            self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent']);self.assertIn(str(target),receipt['source_output_paths_observed'])

    def test_request_context_types_original_cli_and_terminal_storage_boundaries(self):
        (receipt,_),data=self.generate(args=['--help']);request,*_=read_record(receipt['record_root'])
        for bad in ({**request,'schema_version':True},{k:v for k,v in request.items() if k!='parser_context'},{**request,'parser_context':None},{**request,'program':'unknown'}):
            with self.assertRaises(ValueError):request_valid(bad)
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):code=run(['generate','--profile',PROFILE,'--program','devsecops','--source-worktree',str(data),'--','--unknown'],self.instance,self.settings)
        self.assertEqual(code,2);self.assertEqual(json.loads(out.getvalue())['state'],'complete')
        with patch('lib.lifecycle_candidate_preparation_application.Record.finish',side_effect=OSError('terminal storage failed')):
            (receipt,result),_=self.generate(args=['--help'])
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(receipt['journal_terminal_written']);self.assertEqual(result['exit_code'],0)

if __name__=='__main__':unittest.main(verbosity=2)
