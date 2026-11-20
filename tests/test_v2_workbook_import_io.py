"""Actual selected workbook reads/writes and complete no-native reconstruction."""
import errno,hashlib,json,os,shutil,sys,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_harmonized_workbook_import as original
from lib.providers.workbook_import_io import Data,Output,Selection
from lib.providers.sbom_export_storage import Record,read_record,encode
from lib.workbook_import_context import execute
from lib.workbook_import_io import ReplayIO
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError


class WholeWorkbookNativeIO(unittest.TestCase):
    def setUp(self):
        self.fixture=original.WholeHarmonizedWorkbookImport('test_whole_real_model_all_standards_three_export_bytes_streams_and_candidate_boundaries')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups);self.data=self.fixture.data
        self.state=self.data.parent/'private-state';self.state.mkdir(mode=0o700)
    def record(self,*,args=None,native=False):
        args=['--input-xlsx',str(self.fixture.xlsx)] if args is None else args
        mode='selected-files' if native else 'private-candidate'
        request={'source_label':str(self.data),'cwd_label':str(self.data),'argv':args,'export_mode':mode}
        record=Record(self.state,request,{'scope':'unintegrated whole original IO unit evidence, no product binding'})
        record.append({'kind':'execution-intent','request':request})
        data=Data(record);output=Output(record,mode);selected=Selection(record,str(self.data),data,output,self.state)
        result=error=None
        try:
            kernel=execute(str(self.data),str(self.data),args,data,output,selection=selected)
            result={'exit_code':kernel['exit_code'],'kernel_result':kernel,'successful_outputs':output.files,'successful_writes':output.writes}
        except Exception as failure:error=failure
        state='incomplete' if error is not None or record.capture_incomplete else 'complete'
        record.finish(state,result,output.touched,error)
        return record,result,error
    def replay(self,record):
        request,source,retained,events,blob,closed=read_record(record.root)
        self.assertEqual(retained['state'],'complete')
        port=ReplayIO(events,blob,request['export_mode'],request['cwd_label'])
        with patch('subprocess.Popen',side_effect=AssertionError('No child program in reconstruction')), \
                patch('lib.providers.workbook_import_io.Data.read',side_effect=AssertionError('No selected source in reconstruction')), \
                patch('lib.providers.workbook_import_io.Output.write_text',side_effect=AssertionError('No output in reconstruction')):
            kernel=execute(request['source_label'],request['cwd_label'],request['argv'],port,port,selection=port.select)
        port.finish()
        result={'exit_code':kernel['exit_code'],'kernel_result':kernel,'successful_outputs':port.files,'successful_writes':port.writes}
        self.assertEqual(encode(result),encode(retained['result']));self.assertEqual(port.touched,retained['touched_files']);self.assertTrue(closed())
        self.assertEqual(events[-1],{'kind':'terminal','state':'complete','exit_code':kernel['exit_code']})
        return kernel,port
    def main_expected(self,args):
        expected=self.fixture.original(args)
        return {**expected,'original_exit_signal':None}

    def test_whole_private_projection_three_original_outputs_and_original_streams(self):
        args=['--input-xlsx',str(self.fixture.xlsx)];before={str(p):p.read_bytes() for p in self.data.rglob('*') if p.is_file()}
        record,result,error=self.record(args=args)
        self.assertIsNone(error);self.assertEqual({str(p):p.read_bytes() for p in self.data.rglob('*') if p.is_file()},before)
        expected=self.main_expected(args);self.assertEqual(result['kernel_result'],expected)
        _,_,retained,_,blob,_=read_record(record.root)
        self.assertEqual({name:blob(ref) for name,ref in result['successful_outputs'].items()},{str(self.data/name):(self.data/name).read_bytes() for name in original.OUT})
        self.assertEqual(retained['touched_files'],{});self.assertEqual(len(result['successful_writes']),3)
        self.replay(record)

    def test_whole_actual_native_exports_keep_all_original_bytes_streams_and_existing_modes(self):
        args=['--input-xlsx',str(self.fixture.xlsx)];expected=self.main_expected(args)
        modes={str(self.data/name):(self.data/name).stat().st_mode&0o777 for name in original.OUT}
        for name in original.OUT:(self.data/name).write_bytes(b'old output')
        record,result,error=self.record(args=args,native=True)
        self.assertIsNone(error);self.assertEqual(result['kernel_result'],expected)
        _,_,value,_,blob,_=read_record(record.root)
        self.assertEqual({name:blob(ref) for name,ref in result['successful_outputs'].items()},{str(self.data/name):(self.data/name).read_bytes() for name in original.OUT})
        for name,mode in modes.items():self.assertEqual(Path(name).stat().st_mode&0o777,mode)
        self.assertTrue(set(modes)<=set(value['touched_files']));self.replay(record)

    def test_custom_outside_root_original_after_write_error_retains_all_three_files(self):
        external=self.data.parent/'custom';args=['--input-xlsx',str(self.fixture.xlsx),'--mapping-output',str(external/'map.yaml'),'--report-json',str(external/'report.json'),'--report-md',str(external/'report.md')]
        expected=self.main_expected(args);record,result,error=self.record(args=args,native=True)
        self.assertIsNone(error);self.assertEqual(result['kernel_result'],expected);self.assertEqual(result['exit_code'],1)
        self.assertEqual(len(result['successful_writes']),3)
        self.assertEqual(result['kernel_result']['kernel_exception']['type'],'ValueError');self.replay(record)

    def test_relative_paths_and_repeated_custom_output_preserve_original_all_write_events(self):
        args=['--input-xlsx','source.xlsx','--mapping-output','all.txt','--report-json','all.txt','--report-md','all.txt']
        prior=Path.cwd();os.chdir(self.data)
        try:expected=self.main_expected(args)
        finally:os.chdir(prior)
        record,result,error=self.record(args=args,native=True)
        self.assertIsNone(error);self.assertEqual(result['kernel_result'],expected)
        self.assertEqual(len(result['successful_writes']),3);self.assertEqual(len(result['successful_outputs']),1)
        self.assertEqual({r['path'] for r in result['successful_writes']},{str(self.data/'all.txt')});self.replay(record)

    def test_actual_first_and_second_and_third_file_directory_errors_preserve_original_prefix(self):
        for index,name in enumerate(original.OUT):
            with self.subTest(index=index):
                target=self.data/name;target.parent.mkdir(parents=True,exist_ok=True)
                if target.is_file():target.unlink()
                target.mkdir()
                args=['--input-xlsx',str(self.fixture.xlsx)];expected=self.main_expected(args)
                record,result,error=self.record(args=args,native=True)
                self.assertIsNone(error);self.assertEqual(result['kernel_result'],expected)
                self.assertEqual(len(result['successful_writes']),index);self.replay(record);target.rmdir()

    def test_actual_parent_file_mkdir_error_prevents_every_export(self):
        (self.data/'generated').write_bytes(b'parent is a file')
        args=['--input-xlsx',str(self.fixture.xlsx)];expected=self.main_expected(args)
        record,result,error=self.record(args=args,native=True)
        self.assertIsNone(error);self.assertEqual(result['kernel_result'],expected)
        self.assertEqual(result['successful_writes'],[]);self.replay(record)

    def test_actual_controlled_seven_byte_write_failure_and_reconstruction(self):
        args=['--input-xlsx',str(self.fixture.xlsx)];name=str(self.data/original.OUT[0]);old=Path.write_text
        def original_write(path,text,*a,**kw):
            if str(path)==name:
                with path.open('w',encoding='utf-8') as stream:stream.write(text[:7]);stream.flush()
                raise OSError(errno.ENOSPC,'No space left on device')
            return old(path,text,*a,**kw)
        with patch.object(Path,'write_text',original_write):expected=self.main_expected(args)
        calls=[]
        def native_write(port,fd,view):
            calls.append(len(view))
            if len(calls)==1:return os.write(fd,view[:7])
            raise OSError(errno.ENOSPC,'No space left on device')
        with patch.object(Output,'write_chunk',native_write):record,result,error=self.record(args=args,native=True)
        self.assertIsNone(error);self.assertEqual(result['kernel_result'],expected);self.assertEqual(Path(name).read_bytes(),b'schema_')
        self.replay(record)

    def test_selected_source_deletion_does_not_repeat_source_or_output_in_reconstruction(self):
        record,result,error=self.record(native=True);self.assertIsNone(error)
        shutil.rmtree(self.data);self.replay(record)

    def test_lazy_missing_model_error_has_no_workbook_read_or_output(self):
        (self.data/'model/requirements/harmonized-devsecops-requirements.yaml').unlink()
        args=['--input-xlsx',str(self.fixture.xlsx)];expected=self.main_expected(args)
        record,result,error=self.record(args=args);self.assertIsNone(error);self.assertEqual(result['kernel_result'],expected)
        events=read_record(record.root)[3]
        self.assertEqual(len([row for row in events if row.get('action')=='workbook-input-read']),1);self.replay(record)

    def test_original_numeric2_and_help0_and_string1_are_complete_recorded_program_outcomes(self):
        for args,code in (([],2),(['--help'],0),(['--input-xlsx','source.xlsx','--unknown'],2)):
            with self.subTest(args=args):
                record,result,error=self.record(args=args);self.assertIsNone(error);self.assertEqual(result['exit_code'],code);self.replay(record)
        self.fixture.xlsx.write_bytes(original.workbook([(4,{'B':'unknown label','G':'text'})]))
        record,result,error=self.record();self.assertIsNone(error);self.assertEqual(result['exit_code'],1)
        self.assertIsInstance(result['kernel_result']['original_exit_signal']['value'],str);self.replay(record)

    def test_additional_alias_private_state_and_YAML_admission_are_incomplete_without_verdict(self):
        model=self.data/'model/requirements/harmonized-devsecops-requirements.yaml';raw=model.read_bytes()
        original_model=self.data.parent/'model.yaml';original_model.write_bytes(raw);model.unlink();model.symlink_to(original_model)
        record,result,error=self.record();self.assertIsInstance(error,InputAdmissionError);self.assertIsNone(result)
        self.assertEqual(read_record(record.root)[2]['state'],'incomplete')
        model.unlink();model.write_bytes(b'same: &admission true\n'+b'same: *admission\n'*5000+raw)
        record,result,error=self.record();self.assertIsInstance(error,InputAdmissionError);self.assertIsNone(result)
        self.assertEqual(read_record(record.root)[2]['state'],'incomplete')
        model.write_bytes(raw);record,result,error=self.record(args=['--input-xlsx',str(self.state/'forbidden.xlsx')])
        self.assertIsInstance(error,InputAdmissionError);self.assertIsNone(result)

    def test_actual_input_disappearance_between_original_reads_is_incomplete_capture(self):
        read=Data.read
        def disappear(port,path,label):
            raw=read(port,path,label)
            if path==str(self.fixture.xlsx) and Path(path).exists():Path(path).unlink()
            return raw
        with patch.object(Data,'read',disappear):record,result,error=self.record()
        self.assertIsInstance(error,InputAdmissionError);self.assertIsNone(result)
        self.assertEqual(read_record(record.root)[2]['state'],'incomplete')

    def test_actual_output_parent_disappearance_after_mkdir_is_incomplete_capture(self):
        mkdir=Output.mkdir
        def disappear(port,path,mode,parents,exist_ok,label):
            value=mkdir(port,path,mode,parents,exist_ok,label)
            if port.mkdir_position==3:shutil.rmtree(self.data/'model/traceability')
            return value
        with patch.object(Output,'mkdir',disappear):record,result,error=self.record(native=True)
        self.assertIsInstance(error,InputAdmissionError);self.assertIsNone(result)
        self.assertEqual(read_record(record.root)[2]['state'],'incomplete')

    def test_private_raw_capture_failure_does_not_become_original_disk_error(self):
        with patch.object(Record,'blob',side_effect=OSError(errno.ENOSPC,'Controlled private capture failure')):
            record,result,error=self.record()
        self.assertIsInstance(error,InputAdmissionError);self.assertIsNone(result)
        self.assertEqual(read_record(record.root)[2]['state'],'incomplete')

    def test_private_observer_failure_after_actual_write_never_claims_original_success(self):
        append=Record.append
        def fail_after_write(record,value):
            if value.get('kind')=='workbook-write-after':raise OSError(errno.ENOSPC,'Controlled private observer failure')
            return append(record,value)
        with patch.object(Record,'append',fail_after_write):record,result,error=self.record(native=True)
        self.assertIsInstance(error,InputAdmissionError);self.assertIsNone(result)
        self.assertTrue((self.data/original.OUT[0]).is_file())
        self.assertEqual(read_record(record.root)[2]['state'],'incomplete')

    def reseal(self,record,events,retained):
        previous='0'*64
        for index,row in enumerate(events):
            raw=encode({'sequence':index,'previous':previous,'value':row});(record.root/'events'/f'{index:04}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
        retained['event_tip']=previous;retained['event_count']=len(events);(record.root/'result.json').write_bytes(encode(retained))

    def test_coherently_rehashed_input_label_output_progress_and_unused_event_are_rejected(self):
        for attack in ('input-label','write-progress','extra-event'):
            with self.subTest(attack=attack):
                record,result,error=self.record(native=True);self.assertIsNone(error)
                _,_,retained,events,_,_=read_record(record.root)
                if attack=='input-label':next(row for row in events if row.get('action')=='workbook-input-read')['arguments']['label']='forged'
                elif attack=='write-progress':next(row for row in events if row.get('kind')=='workbook-write-after')['progress']['written_bytes']+=1
                else:events.insert(-1,{'kind':'unused'})
                self.reseal(record,events,retained)
                with self.assertRaises((ValueError,AssertionError)):self.replay(record)


if __name__=='__main__':unittest.main()
