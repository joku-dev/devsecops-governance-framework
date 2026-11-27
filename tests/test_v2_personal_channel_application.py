"""Registered program capture, node/source/authority binding and whole replay."""
from pathlib import Path
from unittest.mock import patch
import copy,hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_personal_channel_programs as original
from test_v2_personal_channel_context import FrozenDatetime
from lib.personal_channel_application import generate,inspect,request_valid,emit_legacy,PROFILE
from lib.personal_channel_ports import read_record,encode,AUTHORITY
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read
from lib.requirement_validation_budget import InputAdmissionError

class PersonalChannelApplication(unittest.TestCase):
    def setUp(self):
        fixture=original.WholePersonalChannelPrograms();fixture.setUp();self.addCleanup(fixture.doCleanups);self.fixture=fixture
        self.source,self.config,self.tools=fixture.fixture();self.instance=self.source.parent/'instance';self.instance.mkdir(mode=0o700)
        self.settings={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
    def generate(self,program='check',native=False,args=None,**options):
        if args is None:args=['--output',str(self.source/'generated/reports/lifecycle-personal-channel/new.json')] if program=='check' else ['--ignored-original-argument']
        with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}),patch('lib.providers.personal_channel_transport.datetime',FrozenDatetime):
            return generate({'source_worktree':str(self.source),'legacy_arguments':list(args),'program':program,
                'transport_profile':'legacy-personal-github-get-v1','provider_executable':str(self.tools/'gh'),'write_selected_files':native,**options},self.instance,self.settings)
    def reseal(self,root,events,value):
        previous='0'*64
        for index,event in enumerate(events):
            raw=encode({'sequence':index,'previous':previous,'value':event});(root/'events'/f'{index:08}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
        value['event_count'],value['event_tip']=len(events),previous;(root/'result.json').write_bytes(encode(value))

    def test_all_three_whole_programs_both_modes_bind_source_outputs_and_no_authority(self):
        for program in ('statement','check','evidence'):
            for native in (False,True):
                with self.subTest(program=program,native=native):
                    before=original.snapshot(self.source);receipt,result=self.generate(program,native)
                    self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0)
                    self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred'])
                    request,source,value,events,blob,closed=read_record(receipt['record_root'])
                    self.assertEqual('parser_context' in request,program=='check');self.assertEqual(request['provider_executable'],str(self.tools/'gh'))
                    inspected=inspect(receipt['record_root'],node=self.settings);self.assertTrue(inspected['retained_declared_replay_consistent'])
                    self.assertEqual(inspected['successful_outputs'],result['successful_outputs'])
                    if native:
                        for name,ref in result['successful_outputs'].items():self.assertEqual(Path(name).read_bytes(),blob(ref))
                    else:self.assertEqual(original.snapshot(self.source),before)
                    original.restore(self.source,before)
                    calls=self.tools/'calls.jsonl'
                    if calls.exists():calls.unlink()

    def test_pure_replay_after_source_and_program_deletion_rejects_foreign_node(self):
        for native in (False,True):
            with self.subTest(native=native):
                receipt,result=self.generate(native=native);self.assertEqual(receipt['state'],'complete',receipt)
                # Keep the second mode's source until it has been captured;
                # restore only the isolated fixture when needed below.
                shutil.rmtree(self.source);shutil.rmtree(self.tools)
                with patch('subprocess.Popen',side_effect=AssertionError('No subprocess')),patch('lib.personal_channel_application.NativeIO',side_effect=AssertionError('No source')),patch('lib.personal_channel_ports.NativePersonalTransport',side_effect=AssertionError('No provider')):
                    checked=inspect(receipt['record_root'])
                self.assertTrue(checked['retained_declared_replay_consistent']);self.assertFalse(checked['native_source_or_exports_repeated'])
                with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'b'*32})
                if not native:
                    self.source,self.config,self.tools=self.fixture.fixture()

    def test_original_errors_are_complete_and_technical_capture_failures_have_no_original_verdict(self):
        receipt,result=self.generate(args=[]);self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],1)
        old=subprocess.run([sys.executable,'-B',str(self.source/'scripts/check_lifecycle_personal_channel.py')],cwd=self.source,capture_output=True,env={**os.environ,'PYTHONPATH':str(self.source/'scripts'),'PYTHONDONTWRITEBYTECODE':'1'})
        error=result['kernel_result']['kernel_exception'];self.assertEqual(old.returncode,1);self.assertTrue(old.stderr.endswith((error['type']+': '+error['message']+'\n').encode()))
        with patch('lib.providers.synthetic_lifecycle_io.NativeIO.read',side_effect=InputAdmissionError('Captured input unavailable')):receipt,result=self.generate()
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
        with patch('lib.personal_channel_application.Record.finish',side_effect=OSError('terminal unavailable')):receipt,result=self.generate()
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(receipt['journal_terminal_written']);self.assertEqual(result['exit_code'],0)

    def test_explicit_profiles_parser_function_arguments_and_schema_metadata_fail_closed(self):
        receipt,_=self.generate('statement');request,*_=read_record(receipt['record_root'])
        changes=[{**request,'schema_version':True},{**request,'transport_profile':'unknown'},{**request,'provider_executable':'bad\0tool'},
                 {**request,'parser_context':{}},{**request,'argv':[True]},{**request,'verify_base_ref':'HEAD'},{**request,'resources':[{'uri':'https://invalid','label':'relative'}]}]
        for value in changes:
            with self.subTest(keys=list(value)):
                with self.assertRaises(ValueError):request_valid(value)
        with patch('lib.personal_channel_application.Record',side_effect=AssertionError('No record')):
            with self.assertRaisesRegex(ValueError,'transport_profile'):self.generate(transport_profile='unknown')

    def test_resealed_output_raw_stream_authority_source_parser_and_orphan_attacks_reject(self):
        for attack in ('stdout','stderr-part','authority','source','parser','extra-blob'):
            with self.subTest(attack=attack):
                receipt,_=self.generate(args=['--help']);root=Path(receipt['record_root']);request,source,value,events,*_=read_record(root)
                if attack=='stdout':value['result']['kernel_result']['stdout']='forged help\n';self.reseal(root,events,value)
                elif attack=='stderr-part':value['result']['kernel_result']['stderr_parts']=[{'text':'forged diagnostic\n'}];self.reseal(root,events,value)
                elif attack=='authority':value['official_acceptance']=0;self.reseal(root,events,value)
                elif attack=='source':source['source_digest']='0'*64;(root/'source.json').write_bytes(encode(source))
                elif attack=='parser':
                    self.assertNotEqual(request['parser_context']['width'],24);request['parser_context']['width']=24;events[1]['request']=request;(root/'request.json').write_bytes(encode(request));self.reseal(root,events,value)
                else:
                    raw=b'orphan';(root/'blobs'/hashlib.sha256(raw).hexdigest()).write_bytes(raw)
                with self.assertRaises(ValueError,msg=attack):inspect(root)

    def test_actual_top_level_cli_replays_closed_record_without_instance_or_selected_sources(self):
        receipt,_=self.generate();self.assertEqual(receipt['state'],'complete',receipt);shutil.rmtree(self.source);shutil.rmtree(self.tools)
        result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py'),'personal-channel','replay','--record',receipt['record_root']],capture_output=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout),inspect(receipt['record_root']));self.assertFalse(result.stderr)

    def test_actual_top_level_generate_legacy_help_and_guarded_inspect_from_fresh_development_node(self):
        from test_portable_runtime import OPA
        node=self.source.parent/'cli-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')]
        environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':'60','LINES':'24'}
        def call(arguments,expected=0):
            result=subprocess.run([*cli,*arguments],capture_output=True,env=environment,timeout=180)
            self.assertEqual(result.returncode,expected,result.stderr[-3000:]);return result
        call(['--instance',str(node),'init','--development','--opa',str(OPA)])
        source_before=original.snapshot(self.source)
        for program in ('statement','evidence','check'):
            args=['--help'] if program=='check' else ['--ignored-original-argv']
            base=['--instance',str(node),'personal-channel','generate','--profile',PROFILE,'--transport-profile','legacy-personal-github-get-v1','--program',program,'--source-worktree',str(self.source)]
            receipt=json.loads(call([*base,'--',*args]).stdout);self.assertEqual(receipt['state'],'complete');self.assertFalse(receipt['official_acceptance'])
            old=subprocess.run([sys.executable,'-B',str(self.source/'scripts'/original.NAMES[program]),*args],cwd=self.source,capture_output=True,env={**environment,'PYTHONPATH':str(self.source/'scripts')},timeout=120)
            expected=original.snapshot(self.source);original.restore(self.source,source_before)
            legacy=call([*base,'--format','legacy','--',*args]);self.assertEqual(legacy.stdout,old.stdout);self.assertEqual(legacy.stderr,old.stderr)
            request,_,result,_,blob,_=read_record(receipt['record_root'])
            files,dirs=map(dict,source_before)
            for name,value in result['result']['private_projected_changes'].items():
                relative=Path(name).relative_to(self.source).as_posix()
                if value['kind']=='file':files[relative]=(blob(value['content']),value['mode'])
                elif value['kind']=='directory':dirs[relative]=value['mode']
                else:self.fail(value)
            self.assertEqual((files,dirs),expected)
            checked=json.loads(call(['--instance',str(node),'personal-channel','inspect','--record',receipt['record_root']]).stdout)
            self.assertTrue(checked['retained_declared_replay_consistent']);self.assertEqual(original.snapshot(self.source),source_before)
        settings=json.loads((node/'instance.json').read_bytes());self.assertTrue(settings['development'])
        self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')

    def test_legacy_output_preserves_ordered_opaque_provider_stderr_bytes(self):
        from contextlib import redirect_stdout,redirect_stderr
        import io
        gh=self.tools/'gh';raw=gh.read_text();position=raw.index('import json,sys')
        gh.write_text(raw[:position]+"import sys\nsys.stderr.buffer.write(b'opaque\\xfferror\\r\\n');sys.stderr.buffer.flush()\n"+raw[position:]);gh.chmod(0o700)
        receipt,result=self.generate();self.assertEqual(receipt['state'],'complete',receipt)
        stdout_raw,stderr_raw=io.BytesIO(),io.BytesIO();stdout=io.TextIOWrapper(stdout_raw,encoding='utf-8');stderr=io.TextIOWrapper(stderr_raw,encoding='utf-8')
        with redirect_stdout(stdout),redirect_stderr(stderr):emit_legacy(result,read_record(receipt['record_root'])[4]);stdout.flush();stderr.flush()
        self.assertEqual(stdout_raw.getvalue(),result['kernel_result']['stdout'].encode());self.assertEqual(stderr_raw.getvalue(),b'opaque\xfferror\r\n'*3)
        stdout.detach();stderr.detach()

if __name__=='__main__':unittest.main(verbosity=2)
