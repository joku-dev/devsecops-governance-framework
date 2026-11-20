"""Whole context and real original CLI: defaults, numeric exits and lazy effects."""
import errno,json,os,shutil,subprocess,sys,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_harmonized_workbook_import as original
from lib.workbook_import_context import execute
from lib.workbook_import_limits import InputAdmissionError


class Ports(original.Memory):
    def read(self,name,label):
        self.calls.append(('read',name,label))
        if name not in self.files:raise FileNotFoundError(errno.ENOENT,'No such file or directory',label)
        return self.files[name]
    def mkdir(self,name,mode,parents,exist_ok,label):self.calls.append(('mkdir',name,mode,parents,exist_ok,label))
    def write_text(self,name,text,encoding,label):
        self.calls.append(('write',name,label))
        if name==self.fail:raise OSError(errno.ENOSPC,'No space left on device',label)
        self.files[name]=text.encode(encoding);return len(text)


class WholeWorkbookContext(unittest.TestCase):
    def setUp(self):
        self.fixture=original.WholeHarmonizedWorkbookImport('test_whole_real_model_all_standards_three_export_bytes_streams_and_candidate_boundaries')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.data=self.fixture.data;self.program=self.data/'scripts/import_harmonized_requirements_workbook.py';self.program.parent.mkdir()
        self.program.write_bytes(original.FROZEN.read_bytes())
    def memory(self,fail=None):return Ports({str(p):p.read_bytes() for p in self.data.rglob('*') if p.is_file()},fail)
    def run_core(self,port,args):
        with patch('subprocess.Popen',side_effect=AssertionError('No native program')),patch.object(Path,'open',side_effect=AssertionError('No observed native file')):
            return execute(str(self.data),str(self.data),args,port,port)
    def actual_cli(self,args):
        result=subprocess.run([sys.executable,'-B',str(self.program),*args],cwd=self.data,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True)
        return result

    def test_actual_original_CLI_success_with_absolute_relative_and_all_default_outputs(self):
        for chosen in (str(self.fixture.xlsx),'source.xlsx'):
            with self.subTest(path=chosen):
                args=['--input-xlsx',chosen];port=self.memory();expected=self.actual_cli(args);value=self.run_core(port,args)
                self.assertEqual(value['exit_code'],expected.returncode);self.assertEqual(value['exit_code'],0)
                self.assertEqual(value['stdout'].encode(),expected.stdout);self.assertEqual(value['stderr'].encode(),expected.stderr)
                self.assertIsNone(value['kernel_exception']);self.assertIsNone(value['original_exit_signal'])
                for name in original.OUT:self.assertEqual(port.files[str(self.data/name)],(self.data/name).read_bytes())
                reads=[name for action,name,*_ in port.calls if action=='read']
                self.assertEqual(reads,[str(self.data/'model/requirements/harmonized-devsecops-requirements.yaml'),str(self.fixture.xlsx),str(self.fixture.xlsx)])

    def test_actual_original_argparse_exit2_and_usage_unchanged(self):
        for args in ([],['--input-xlsx','source.xlsx','--unknown-flag']):
            with self.subTest(args=args):
                port=self.memory();expected=self.actual_cli(args);value=self.run_core(port,args)
                self.assertEqual(value['exit_code'],expected.returncode);self.assertEqual(value['exit_code'],2)
                self.assertEqual(value['stdout'].encode(),expected.stdout);self.assertEqual(value['stderr'].encode(),expected.stderr)
                self.assertEqual(value['original_exit_signal'],{'type':'SystemExit','value':2});self.assertEqual(port.calls,[])

    def test_actual_original_string_exit1_keeps_message_and_no_exports(self):
        self.fixture.xlsx.write_bytes(original.workbook([(4,{'B':'unknown source','G':'text'})]));args=['--input-xlsx','source.xlsx'];port=self.memory()
        expected=self.actual_cli(args);value=self.run_core(port,args)
        self.assertEqual(value['exit_code'],expected.returncode);self.assertEqual(value['exit_code'],1)
        self.assertEqual(value['stdout'].encode(),expected.stdout);self.assertEqual(value['stderr'].encode(),expected.stderr)
        self.assertEqual(value['original_exit_signal']['type'],'SystemExit');self.assertIsInstance(value['original_exit_signal']['value'],str)
        self.assertFalse(any(row[0] in ('mkdir','write') for row in port.calls))

    def test_missing_model_stops_before_any_workbook_read_without_preloading(self):
        model=self.data/'model/requirements/harmonized-devsecops-requirements.yaml';model.unlink();self.fixture.xlsx.write_bytes(b'invalid ZIP')
        args=['--input-xlsx',str(self.fixture.xlsx)];port=self.memory();expected=self.fixture.original(args);value=self.run_core(port,args)
        self.assertEqual({k:value[k] for k in expected},expected)
        self.assertEqual(port.calls,[('read',str(model),str(model))])

    def test_output_then_relative_print_error_is_whole_original_not_suppressed(self):
        for relative in (True,False):
            with self.subTest(relative=relative):
                destination='relative.md' if relative else str(self.data.parent/'external/report.md')
                args=['--input-xlsx',str(self.fixture.xlsx),'--report-md',destination];port=self.memory()
                # Keep the native original cwd equal to the explicit context cwd.
                prior=Path.cwd();os.chdir(self.data)
                try:expected=self.fixture.original(args)
                finally:os.chdir(prior)
                value=self.run_core(port,args);self.assertEqual({k:value[k] for k in expected},expected)
                self.assertEqual(value['kernel_exception']['type'],'ValueError')
                writes=[name for action,name,*_ in port.calls if action=='write'];self.assertEqual(len(writes),3)
                for name in writes:self.assertEqual(port.files[name],Path(name).read_bytes())

    def test_all_three_original_failed_export_positions_preserve_prefix_files(self):
        for index,name in enumerate(original.OUT):
            with self.subTest(position=index):
                args=['--input-xlsx',str(self.fixture.xlsx)];fail=str(self.data/name);port=self.memory(fail)
                expected=self.fixture.original(args,fail);value=self.run_core(port,args)
                self.assertEqual({k:value[k] for k in expected},expected)
                writes=[p for action,p,*_ in port.calls if action=='write'];self.assertEqual(writes,[str(self.data/p) for p in original.OUT[:index+1]])
                for p in writes[:-1]:self.assertEqual(port.files[p],Path(p).read_bytes())

    def test_actual_valid_duplicate_yaml_admission_is_not_original_business_exit(self):
        model=self.data/'model/requirements/harmonized-devsecops-requirements.yaml'
        model.write_bytes(b'same: &admission_same true\n'+b'same: *admission_same\n'*5000+model.read_bytes())
        args=['--input-xlsx',str(self.fixture.xlsx)];port=self.memory();expected=self.actual_cli(args)
        self.assertEqual(expected.returncode,0)
        with self.assertRaises(InputAdmissionError):self.run_core(port,args)
        self.assertEqual(len(port.calls),1)

    def test_archive_admission_propagates_without_original_failed_verdict_or_exports(self):
        args=['--input-xlsx',str(self.fixture.xlsx)];port=self.memory();self.assertEqual(self.actual_cli(args).returncode,0)
        with patch('lib.workbook_import_limits.MAX_MEMBER',1),self.assertRaises(InputAdmissionError):self.run_core(port,args)
        self.assertEqual(len(port.calls),2);self.assertTrue(all(row[0]=='read' for row in port.calls))

    def test_original_universal_newlines_in_valid_and_invalid_model(self):
        model=self.data/'model/requirements/harmonized-devsecops-requirements.yaml';original_raw=model.read_bytes()
        args=['--input-xlsx',str(self.fixture.xlsx)]
        for raw in (original_raw.replace(b'\n',b'\r\n'),b'requirements:\r\n  broken: [\r\n'):
            with self.subTest(valid=raw.startswith(b'schema_version')):
                model.write_bytes(raw);port=self.memory();expected=self.fixture.original(args);value=self.run_core(port,args)
                self.assertEqual({k:value[k] for k in expected},expected)

    def test_no_observed_source_program_execution_and_explicit_path_namespace(self):
        args=['--input-xlsx',str(self.fixture.xlsx)];port=self.memory()
        port.files[str(self.program)]=b'raise AssertionError("Observed code must never execute")'
        value=self.run_core(port,args);self.assertEqual(value['exit_code'],0)
        self.assertNotIn(str(self.program),[name for action,name,*_ in port.calls if action=='read'])
        from lib.workbook_import_context import WorkbookPaths
        first,second=WorkbookPaths(str(self.data),port,port),WorkbookPaths(str(self.data),port,port)
        with self.assertRaisesRegex(ValueError,'foreign_path'):first.path(second.path('x'))


if __name__=='__main__':unittest.main()
