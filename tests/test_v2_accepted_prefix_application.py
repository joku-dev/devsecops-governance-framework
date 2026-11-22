"""Registered read-only prefix records, complete helper comparisons and closed replay."""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_accepted_prefix as fixture
from test_v2_accepted_prefix_recording import ORACLE
from test_v2_personal_channel_programs import snapshot
from lib.accepted_prefix_application import generate,inspect,request_valid,PROFILE
from lib.accepted_prefix_ports import Record,read_record,encode
from lib.providers.accepted_prefix_metadata import NativeGitInputs
from lib.providers.personal_channel_process import NativeReadProcess
from lib.requirement_validation_budget import InputAdmissionError
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read

class AcceptedPrefixApplication(unittest.TestCase):
    def setUp(self):
        case=fixture.WholeAcceptedPrefix();case.setUp();self.addCleanup(case.doCleanups);self.reference=case
        self.source,self.base=case.selected('normal');self.instance=self.source.parent/'prefix-check-instance';self.instance.mkdir(mode=0o700)
        self.settings={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
    def generate(self,**extra):return generate({'source_worktree':str(self.source),'base_ref':self.base,'transport_profile':'legacy-accepted-prefix-git-v1',**extra},self.instance,self.settings)
    def reseal(self,root,events,value):
        previous='0'*64
        for i,event in enumerate(events):
            raw=encode({'sequence':i,'previous':previous,'value':event});(root/'events'/f'{i:08}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
        value['event_count'],value['event_tip']=len(events),previous;(root/'result.json').write_bytes(encode(value))
    def test_entire_original_helper_return_source_bytes_modes_and_no_writes_or_authority(self):
        before=snapshot(self.source);env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(self.source/'scripts'),'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null'}
        old=subprocess.run([sys.executable,'-B','-c',ORACLE,str(self.source),self.base],cwd=self.source,env=env,capture_output=True,timeout=180);self.assertEqual(old.returncode,0,old.stderr)
        receipt,result=self.generate();self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_return_value'],json.loads(old.stdout)['return_value']);self.assertEqual(snapshot(self.source),before)
        self.assertFalse(receipt['source_export_requested']);self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['structural_ledger_validation_included']);self.assertEqual(receipt['verification_scope'],'whole_original_accepted_prefix_helper')
        checked=inspect(receipt['record_root'],node=self.settings);self.assertTrue(checked['retained_declared_replay_consistent']);self.assertEqual(checked['successful_writes'],[]);self.assertEqual(checked['successful_outputs'],{})
        self.assertEqual(result['kernel_result']['stdout'],'');self.assertEqual(result['kernel_result']['kernel_exception'],json.loads(old.stdout)['exception'])
    def test_selected_source_and_Git_removed_pure_replay_foreign_node_is_rejected(self):
        receipt,_=self.generate();self.assertEqual(receipt['state'],'complete',receipt);shutil.rmtree(self.source)
        with patch('lib.accepted_prefix_ports.NativeIO',side_effect=AssertionError('No native owner')),patch('subprocess.Popen',side_effect=AssertionError('No native Git')),patch.object(NativeGitInputs,'read',side_effect=AssertionError('No source/index')):
            checked=inspect(receipt['record_root']);self.assertTrue(checked['retained_declared_replay_consistent']);self.assertFalse(checked['native_source_or_exports_repeated'])
            with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'b'*32})
    def test_strict_readonly_request_has_no_provider_command_writer_resource_or_authority_options(self):
        receipt,_=self.generate();request,*_=read_record(receipt['record_root'])
        for bad in ({**request,'schema_version':True},{**request,'base_ref':True},{**request,'profile':'other'},{**request,'transport_profile':'other'},{**request,'base_ref':'bad\0base'},{**request,'resources':[{'uri':'x','label':'y'}]},{**request,'export_mode':'selected-files'},{**request,'provider_executable':'gh'},{**request,'argv':[]},{**request,'official_acceptance':True}):
            with self.assertRaises(ValueError):request_valid(bad)
        for base in ('','not-an-immutable-sha','0'*40):request_valid({**request,'base_ref':base})
    def test_resealed_count_authority_base_source_auxiliary_and_orphan_records_fail_closed(self):
        for attack in ('count','authority','base','source','auxiliary','orphan'):
            with self.subTest(attack=attack):
                receipt,_=self.generate();self.assertEqual(receipt['state'],'complete',receipt);root=Path(receipt['record_root']);request,source,value,events,blob,_=read_record(root)
                if attack=='count':value['result']['kernel_result']['return_value']=999;self.reseal(root,events,value)
                elif attack=='authority':value['official_acceptance']=0;self.reseal(root,events,value)
                elif attack=='base':request['base_ref']='different';events[1]['request']=request;(root/'request.json').write_bytes(encode(request));self.reseal(root,events,value)
                elif attack=='source':source['source_digest']='0'*64;(root/'source.json').write_bytes(encode(source))
                elif attack=='auxiliary':
                    i=next(i for i,e in enumerate(events) if e.get('kind')=='intent' and e.get('action')=='accepted-prefix-hash-auxiliary-create');row=events[i+1];wire=json.loads(blob(row['value']));wire['OS_isolation_attested']=True;raw=encode(wire);sha=hashlib.sha256(raw).hexdigest();(root/'blobs'/sha).write_bytes(raw);row['value']={'sha256':sha,'bytes':len(raw)};self.reseal(root,events,value)
                else:raw=b'orphan';(root/'blobs'/hashlib.sha256(raw).hexdigest()).write_bytes(raw)
                with self.assertRaises(ValueError,msg=attack):inspect(root)
    def test_original_invalid_and_missing_base_remain_complete_original_diagnostics(self):
        for base,expected in (('','ContractError'),('0'*40,'ContractError'),('f'*40,'CalledProcessError')):
            with self.subTest(base=base):
                receipt,result=self.generate(base_ref=base);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],1);self.assertIsNone(receipt['original_return_value']);self.assertEqual(result['kernel_result']['kernel_exception']['type'],expected);self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
    def test_unobserved_source_input_is_incomplete_without_fabricated_original_count_or_exit(self):
        with patch.object(NativeGitInputs,'read',side_effect=InputAdmissionError('Unobserved source input')):receipt,_=self.generate()
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertIsNone(receipt['original_return_value']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
    def test_lost_completion_after_actual_hash_leaves_quarantined_scope_without_retry_or_original_verdict(self):
        append=Record.append;run=NativeReadProcess.run;hash_calls=[];blocked=False;before=snapshot(self.source)
        def process(process,args,*rest,**kwargs):
            value=run(process,args,*rest,**kwargs)
            if 'hash-object' in args:hash_calls.append(args)
            return value
        def lost(record,row):
            nonlocal blocked
            if hash_calls and row.get('kind')=='returned':blocked=True
            if blocked:raise OSError('Explicit lost hash completion')
            return append(record,row)
        with patch.object(Record,'append',lost),patch.object(NativeReadProcess,'run',process):receipt,_=self.generate()
        self.assertEqual(len(hash_calls),1);self.assertTrue(blocked);self.assertEqual(receipt['state'],'incomplete');self.assertFalse(receipt['journal_terminal_written']);self.assertIsNone(receipt['original_exit_code']);self.assertIsNone(receipt['original_return_value']);self.assertEqual(snapshot(self.source),before)
        scopes=list((self.instance/'state/accepted-prefix-hash').iterdir());self.assertEqual(len(scopes),1);self.assertTrue((scopes[0]/'HEAD').is_file())
    def test_actual_top_level_generate_inspect_and_source_free_replay_on_paused_node(self):
        from test_portable_runtime import OPA
        node=self.source.parent/'actual-prefix-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')]
        def call(args):
            p=subprocess.run([*cli,*args],capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=180);self.assertEqual(p.returncode,0,p.stderr[-4000:]);return p
        call(['--instance',str(node),'init','--development','--opa',str(OPA)])
        receipt=json.loads(call(['--instance',str(node),'accepted-prefix','generate','--profile',PROFILE,'--transport-profile','legacy-accepted-prefix-git-v1','--source-worktree',str(self.source),'--base-ref',self.base]).stdout);self.assertEqual(receipt['state'],'complete');self.assertGreater(receipt['original_return_value'],0)
        checked=json.loads(call(['--instance',str(node),'accepted-prefix','inspect','--record',receipt['record_root']]).stdout);shutil.rmtree(self.source)
        pure=json.loads(call(['accepted-prefix','replay','--record',receipt['record_root']]).stdout);self.assertEqual(pure,checked);self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')
