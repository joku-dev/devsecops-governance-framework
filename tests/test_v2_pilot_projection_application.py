"""Source-bound diagnostic report capture; authority, complete errors and inert replay."""
from pathlib import Path
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
import copy,hashlib,io,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_pilot_projections as original
from lib.pilot_projection_application import generate,inspect,run,request_valid,PROFILE
from lib.pilot_projection_ports import read_record,encode,AUTHORITY
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read
from lib.requirement_validation_budget import InputAdmissionError

class PilotProjectionApplication(unittest.TestCase):
    def setUp(self):
        self.reference=original.WholePilotProjection('test_complete_both_original_programs_history_reports_and_ignored_argv_both_modes');self.reference.setUp();self.addCleanup(self.reference.doCleanups)
        self.source=self.reference.source;self.instance=self.reference.parent/'instance';self.instance.mkdir(mode=0o700)
        self.settings={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}

    def generate(self,program='actions',native=False,args=(),**kwargs):
        return generate({'source_worktree':str(self.source),'legacy_arguments':list(args),'program':program,'capture_profile':'legacy-lifecycle-capture-v1','write_selected_files':native,**kwargs},self.instance,self.settings)

    def reseal(self,root,events,value):
        previous='0'*64
        for index,event in enumerate(events):
            raw=encode({'sequence':index,'previous':previous,'value':event});(root/'events'/f'{index:08}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
        value['event_count'],value['event_tip']=len(events),previous;(root/'result.json').write_bytes(encode(value))

    def test_both_programs_both_modes_keep_exact_original_indices_reports_and_streams(self):
        for program in original.PROGRAMS:
            for native in (False,True):
                name='status/governance-lifecycle-'+('pilot-actions' if program=='actions' else 'live-validation')+'.json';report='generated/reports/governance-lifecycle-'+('pilot-actions' if program=='actions' else 'live-validation')+'.md';before=original.file_oracle.snapshot(self.source);reference=self.reference.original(program,['--help','ignored']);self.assertEqual(reference.returncode,0,reference.stderr);expected={n:(self.source/n).read_bytes() for n in (name,report)};after=original.file_oracle.snapshot(self.source);original.file_oracle.restore(self.source,before)
                receipt,result=self.generate(program,native,args=['--help','ignored']);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0);self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred']);self.assertEqual(result['kernel_result']['stdout'].encode(),reference.stdout);self.assertEqual(result['kernel_result']['stderr'].encode(),reference.stderr)
                request,source,retained,events,blob,closed=read_record(receipt['record_root'])
                self.assertNotIn('parser_context',request);self.assertEqual(request['capture_profile'],'legacy-lifecycle-capture-v1')
                for n in (name,report):self.assertEqual(blob(result['successful_outputs'][str(self.source/n)]),expected[n])
                self.assertEqual(original.file_oracle.snapshot(self.source),after if native else before)
                self.assertTrue(inspect(receipt['record_root'],node=self.settings)['retained_declared_replay_consistent'])

    def test_deleted_source_replay_uses_no_native_program_source_or_output_and_rejects_foreign_node(self):
        receipt,result=self.generate('validation',native=True);self.assertEqual(receipt['state'],'complete',receipt);shutil.rmtree(self.source)
        with patch('subprocess.Popen',side_effect=AssertionError('No program')),patch('lib.pilot_projection_application.NativeIO',side_effect=AssertionError('No selected source')),patch('lib.providers.synthetic_lifecycle_output.NativeOutput.write_chunk',side_effect=AssertionError('No native writes')):
            checked=inspect(receipt['record_root'])
        self.assertTrue(checked['retained_declared_replay_consistent']);self.assertFalse(checked['native_source_or_exports_repeated']);self.assertEqual(checked['successful_outputs'],result['successful_outputs'])
        with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'b'*32})

    def test_explicit_capture_profile_and_strict_metadata_fail_before_record_creation(self):
        receipt,_=self.generate();request,*_=read_record(receipt['record_root'])
        for altered in ({**request,'schema_version':True},{**request,'capture_profile':None},{**request,'capture_profile':'unknown'},{k:v for k,v in request.items() if k!='capture_profile'},{**request,'program':'unknown'},{**request,'argv':[True]}):
            with self.assertRaises(ValueError):request_valid(altered)
        with patch('lib.pilot_projection_application.Record',side_effect=AssertionError('No record')):
            with self.assertRaisesRegex(ValueError,'capture_profile'):self.generate(capture_profile='unknown')

    def test_original_error_is_complete_but_capture_and_terminal_failures_confer_no_original_verdict(self):
        p=self.source/'model/governance/lifecycle/live-operating/00000001.json';raw=p.read_bytes();value=json.loads(raw);value['revision']=999;p.write_text(json.dumps(value))
        receipt,result=self.generate();self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],1);self.assertIsNotNone(result['kernel_result']['kernel_exception']);p.write_bytes(raw)
        with patch('lib.providers.synthetic_lifecycle_io.NativeIO.read',side_effect=InputAdmissionError('Unavailable captured input')):receipt,result=self.generate()
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
        with patch('lib.pilot_projection_application.Record.finish',side_effect=OSError('terminal unavailable')):receipt,result=self.generate()
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(receipt['journal_terminal_written']);self.assertEqual(result['exit_code'],0)

    def test_native_original_report_error_reports_possible_partial_effects_and_retains_index_write(self):
        name='status/governance-lifecycle-pilot-actions.json';(self.source/name).write_bytes(b'old invalid index');shutil.rmtree(self.source/'generated/reports')
        receipt,result=self.generate(native=True);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],1);self.assertTrue(receipt['source_effects_may_be_partial']);self.assertIn(str(self.source/name),result['successful_outputs']);self.assertNotEqual((self.source/name).read_bytes(),b'old invalid index');self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_resealed_request_result_authority_source_and_orphan_blob_attacks_fail_closed(self):
        for attack in ('capture','stdout','authority','source','extra-blob'):
            receipt,_=self.generate();root=Path(receipt['record_root']);request,source,value,events,*_=read_record(root)
            if attack=='capture':request['capture_profile']='unknown';events[1]['request']=request;(root/'request.json').write_bytes(encode(request));self.reseal(root,events,value)
            elif attack=='stdout':value['result']['kernel_result']['stdout']='forged output\n';self.reseal(root,events,value)
            elif attack=='authority':value['official_acceptance']=0;self.reseal(root,events,value)
            elif attack=='source':source['source_digest']='0'*64;(root/'source.json').write_bytes(encode(source))
            else:raw=b'orphan unreferenced data';(root/'blobs'/hashlib.sha256(raw).hexdigest()).write_bytes(raw)
            with self.assertRaises(ValueError,msg=attack):inspect(root)

    def test_actual_top_level_cli_replays_closed_record_without_instance_or_selected_source(self):
        receipt,_=self.generate('actions');self.assertEqual(receipt['state'],'complete',receipt);shutil.rmtree(self.source)
        process=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py'),'pilot-projections','replay','--record',receipt['record_root']],capture_output=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        self.assertEqual(process.returncode,0,process.stderr);self.assertEqual(json.loads(process.stdout),inspect(receipt['record_root']));self.assertFalse(process.stderr)

    def test_application_command_requires_capture_profile_and_preserves_legacy_ignored_arguments(self):
        out,err=io.StringIO(),io.StringIO();reference=self.reference.original('actions',['--help'])
        with redirect_stdout(out),redirect_stderr(err):code=run(['generate','--capture-profile','legacy-lifecycle-capture-v1','--profile',PROFILE,'--program','actions','--source-worktree',str(self.source),'--format','legacy','--','--help'],self.instance,self.settings)
        self.assertEqual(code,reference.returncode);self.assertEqual(out.getvalue().encode(),reference.stdout);self.assertEqual(err.getvalue().encode(),reference.stderr)
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:run(['generate','--profile',PROFILE,'--program','actions','--source-worktree',str(self.source)],self.instance,self.settings)
        self.assertEqual(caught.exception.code,2)

if __name__=='__main__':unittest.main(verbosity=2)
