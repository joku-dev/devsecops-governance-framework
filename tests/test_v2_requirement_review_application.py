"""Actual fixed source exports, private candidates and whole retained replay."""
from contextlib import redirect_stdout
import errno,hashlib,io,json,os,shutil,sys,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_requirement_review_generation as original
from lib.requirement_review_application import generate,inspect,run,PROFILE
from lib.requirement_review_output import OUTPUTS
from lib.requirement_review_ports import read_record,encode,Output
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read


class WholeRequirementReviewApplication(unittest.TestCase):
    def setUp(self):
        self.fixture=original.WholeRequirementReviewGeneration('test_complete_migration_real867_proposals_all_artifacts_json_markdown_and_streams')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.data=self.fixture.data;self.instance=self.data.parent/'instance';self.instance.mkdir(mode=0o700)
        self.settings={'node_id':'b'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),
                       'runtime_source_digest':source_digest()}

    def execute(self,kind,*,native=False):
        return generate({'kind':kind,'source_worktree':str(self.data),'write_source_reports':native},self.instance,self.settings)

    def files(self):
        return {p.relative_to(self.data).as_posix():p.read_bytes() for p in self.data.rglob('*') if p.is_file()}

    def retained_files(self,receipt):
        request,source,value,events,blob,closed=read_record(receipt['record_root'])
        return {name:blob(ref) for name,ref in value['result']['output_files'].items()}

    def test_whole_private_candidates_both_original_files_and_streams_without_source_writes(self):
        for kind in OUTPUTS:
            with self.subTest(kind=kind):
                before=self.files();receipt,result=self.execute(kind)
                self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['exit_code'],0)
                self.assertEqual(receipt['export_mode'],'private-candidate');self.assertFalse(receipt['source_export_requested'])
                self.assertEqual(receipt['source_paths_touched'],[]);self.assertEqual(self.files(),before)
                expected=self.fixture.original(kind)
                self.assertEqual(result['kernel_result'],expected)
                self.assertEqual(self.retained_files(receipt),{n:(self.data/n).read_bytes() for n in OUTPUTS[kind]})
                checked=inspect(receipt['record_root'])
                self.assertTrue(checked['retained_declared_replay_consistent']);self.assertFalse(checked['native_source_or_exports_repeated'])

    def test_actual_native_outputs_equal_whole_original_and_keep_existing_modes(self):
        for kind in OUTPUTS:
            with self.subTest(kind=kind):
                oracle=self.data.parent/('oracle-'+kind);shutil.copytree(self.data,oracle)
                before=self.files();modes={n:(self.data/n).stat().st_mode&0o777 for n in OUTPUTS[kind] if (self.data/n).exists()}
                receipt,result=self.execute(kind,native=True)
                self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['exit_code'],0)
                self.assertTrue(receipt['source_export_requested'])
                selected=self.fixture.data;self.fixture.data=oracle
                try:expected=self.fixture.original(kind)
                finally:self.fixture.data=selected
                self.assertEqual(result['kernel_result'],expected)
                self.assertEqual(self.retained_files(receipt),{n:(oracle/n).read_bytes() for n in OUTPUTS[kind]})
                after=self.files();self.assertEqual({n:raw for n,raw in after.items() if n not in OUTPUTS[kind]},
                                                   {n:raw for n,raw in before.items() if n not in OUTPUTS[kind]})
                for n,mode in modes.items():self.assertEqual((self.data/n).stat().st_mode&0o777,mode)
                self.assertTrue(set(OUTPUTS[kind])<=set(receipt['source_paths_touched']))
                self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_real_first_and_second_output_directory_errors_keep_original_partial_files(self):
        for kind in OUTPUTS:
            for position in (0,1):
                with self.subTest(kind=kind,position=position):
                    target=self.data/OUTPUTS[kind][position]
                    if target.is_file():target.unlink()
                    target.mkdir(parents=True)
                    expected=self.fixture.original(kind)
                    receipt,result=self.execute(kind,native=True)
                    self.assertEqual(result['kernel_result'],expected)
                    self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['exit_code'],1)
                    self.assertEqual(expected['kernel_exception']['type'],'IsADirectoryError')
                    self.assertEqual(set(self.retained_files(receipt)),set(OUTPUTS[kind][:position]))
                    self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
                    target.rmdir()

    def test_real_unicode_failure_truncates_original_first_file_before_encoding(self):
        case=sorted((self.data/'model/requirements/lifecycle-cases').glob('*.json'))[0]
        value=json.loads(case.read_bytes());value['source']['source_id']='unpaired-\ud800';case.write_text(json.dumps(value))
        expected=self.fixture.original('implemented-migration')
        self.assertEqual(expected['kernel_exception']['type'],'UnicodeEncodeError')
        receipt,result=self.execute('implemented-migration',native=True)
        self.assertEqual(result['kernel_result'],expected)
        self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['exit_code'],1)
        target=self.data/OUTPUTS['implemented-migration'][0];self.assertEqual(target.read_bytes(),b'')
        retained=read_record(receipt['record_root'])[2]
        self.assertIn(OUTPUTS['implemented-migration'][0],retained['touched_files'])
        self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_controlled_actual_short_write_error_retains_original_prefix_and_error_wire(self):
        kind='implemented-migration';name=OUTPUTS[kind][0];write=Path.write_text
        def old_failure(path,text,*args,**kwargs):
            if path==self.data/name:
                with path.open('w',encoding='utf-8') as stream:stream.write(text[:7]);stream.flush()
                raise OSError(errno.ENOSPC,'No space left on device')
            return write(path,text,*args,**kwargs)
        with patch.object(Path,'write_text',old_failure):expected=self.fixture.original(kind)
        calls=[]
        def fail_after_prefix(port,fd,view):
            calls.append(len(view))
            if len(calls)==1:return os.write(fd,view[:7])
            raise OSError(errno.ENOSPC,'No space left on device')
        with patch.object(Output,'write_chunk',fail_after_prefix):receipt,result=self.execute(kind,native=True)
        self.assertEqual(result['kernel_result'],expected)
        self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['exit_code'],1)
        self.assertEqual((self.data/name).read_bytes(),b'{\n  "sc')
        self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_replay_after_source_deletion_without_native_or_output_and_foreign_node_rejected(self):
        receipt,_=self.execute('pra-platform',native=True)
        shutil.rmtree(self.data)
        with patch('subprocess.Popen',side_effect=AssertionError('No native execution in replay')), \
             patch('lib.requirement_review_application.Source',side_effect=AssertionError('No source in replay')), \
             patch('lib.requirement_review_application.Output',side_effect=AssertionError('No output in replay')):
            self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
        with self.assertRaisesRegex(ValueError,'foreign_node'):
            inspect(receipt['record_root'],node={**self.settings,'node_id':'a'*32})

    def test_private_cli_legacy_inspection_and_standalone_replay(self):
        stdout=io.StringIO()
        with redirect_stdout(stdout):code=run(['generate','--kind','pra-platform','--profile',PROFILE,'--source-worktree',str(self.data)],self.instance,self.settings)
        self.assertEqual(code,0);receipt=json.loads(stdout.getvalue())
        for mode in ('inspect','replay'):
            stdout=io.StringIO()
            with redirect_stdout(stdout):
                code=run([mode,'--record',receipt['record_root']],*([] if mode=='replay' else [self.instance,self.settings]))
            self.assertEqual(code,0);self.assertTrue(json.loads(stdout.getvalue())['retained_declared_replay_consistent'])

    def test_empty_candidates_keep_original_min_error_and_retained_producer_diagnostic(self):
        path=self.data/'generated/reports/implemented-requirement-migration.json'
        value=json.loads(path.read_bytes())
        for row in value['requirement_candidates']:row['mapping_candidates']=[]
        path.write_text(json.dumps(value))
        expected=self.fixture.original('pra-platform')
        receipt,result=self.execute('pra-platform')
        self.assertEqual(result['kernel_result'],expected)
        self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['exit_code'],1)
        self.assertEqual(result['output_files'],{})
        self.assertEqual(inspect(receipt['record_root'])['kernel_exception'],'ValueError')

    def test_original_render_failure_after_json_write_preserves_whole_first_file(self):
        path=self.data/'generated/reports/implemented-requirement-migration.json'
        value=json.loads(path.read_bytes())
        for row in value['requirement_candidates']:
            if row['source_id']=='PRA-STD-REQ-001':
                for candidate in row['mapping_candidates']:candidate['similarity']='not-numeric'
        path.write_text(json.dumps(value))
        expected=self.fixture.original('pra-platform')
        receipt,result=self.execute('pra-platform',native=True)
        self.assertEqual(result['kernel_result'],expected)
        self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['exit_code'],1)
        self.assertEqual(set(result['output_files']),{OUTPUTS['pra-platform'][0]})
        self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_admission_of_output_alias_and_source_state_overlap_is_not_original_verdict(self):
        target=self.data/OUTPUTS['implemented-migration'][0];raw=target.read_bytes();target.unlink()
        other=self.data.parent/'outside.json';other.write_bytes(raw);target.symlink_to(other)
        receipt,result=self.execute('implemented-migration',native=True)
        self.assertEqual(receipt['state'],'incomplete');self.assertEqual(receipt['exit_code'],2)
        self.assertIsNone(receipt['original_exit_code']);self.assertEqual(other.read_bytes(),raw)
        self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
        with self.assertRaisesRegex(ValueError,'source_state_overlap'):
            generate({'kind':'implemented-migration','source_worktree':str(self.data.parent)},self.instance,self.settings)

    def reseal(self,root,events,retained,*,replacement=None):
        if replacement is not None:
            old,raw=replacement;ref={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
            path=root/'blobs'/ref['sha256'];path.write_bytes(raw);path.chmod(0o600)
            for row in events:
                if row.get('kind')=='source-trace' and row['trace']==old:row['trace']=ref
                if row.get('kind')=='returned' and row['value']==old:row['value']=ref
            (root/'blobs'/old['sha256']).unlink()
        previous='0'*64
        for index,value in enumerate(events):
            raw=encode({'sequence':index,'previous':previous,'value':value})
            (root/'events'/f'{index:04}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
        retained['event_tip']=previous;retained['event_count']=len(events)
        (root/'result.json').write_bytes(encode(retained))

    def test_coherently_rehashed_output_progress_and_result_and_own_decoder_failure_rejected(self):
        for attack in ('progress','result','returned-json'):
            with self.subTest(attack=attack):
                receipt,_=self.execute('pra-platform',native=True);root=Path(receipt['record_root'])
                _,_,value,events,blob,_=read_record(root)
                if attack=='progress':
                    row=next(row for row in events if row.get('kind')=='review-output-after')
                    row['progress']['written_bytes']+=1
                    self.reseal(root,events,value)
                elif attack=='result':
                    value['result']['kernel_result']['stdout']+='forged'
                    (root/'result.json').write_bytes(encode(value))
                else:
                    row=next(row for row in events if row.get('kind')=='returned')
                    self.reseal(root,events,value,replacement=(row['value'],b'{not JSON'))
                with self.assertRaises((ValueError,KeyError,TypeError)):inspect(root)

    def test_source_blob_authority_request_and_product_binding_tampering_rejected(self):
        for attack in ('blob','authority','request','product'):
            with self.subTest(attack=attack):
                receipt,_=self.execute('pra-platform');root=Path(receipt['record_root'])
                if attack=='blob':
                    _,_,_,events,_,_=read_record(root);ref=events[-2]['trace'];path=root/'blobs'/ref['sha256'];path.write_bytes(path.read_bytes()+b' ')
                else:
                    name={'authority':'result.json','request':'request.json','product':'source.json'}[attack]
                    path=root/name;value=json.loads(path.read_bytes())
                    if attack=='authority':value['official_acceptance']=True
                    elif attack=='request':value['export_mode']='unknown-export'
                    else:value['source_digest']='0'*64
                    path.write_bytes(encode(value))
                with self.assertRaises((ValueError,KeyError,TypeError)):inspect(root)


if __name__=='__main__':unittest.main()
