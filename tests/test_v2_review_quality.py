"""Original offline packet/score wires, explicit trace inputs and private replay."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib,io,json,shutil,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib import review_quality as core,review_quality_application as app
from lib.portable.contracts import canonical_digest
FIXTURE=ROOT/'tests/fixtures/axiom-v1-parity/review-quality-cases.json';AT='2026-11-15T12:00:00Z'

def descriptor(raw):return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}

class ReviewQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads(FIXTURE.read_text());cls.real_program=staticmethod(app.program_data);cls.program=app.program_data()
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.root=Path(self.temporary.name).resolve();self.node=self.root/'node';self.node.mkdir(mode=0o700)
        self.mock=patch.object(app,'program_data',side_effect=lambda:deepcopy(self.program));self.mock.start();self.addCleanup(self.mock.stop)
        self.context=app.ReviewQualityContext(self.node,{'node_id':'quality-test-node'})
    def tearDown(self):self.temporary.cleanup()
    def create(self,kind='prepare',dataset=None,bundle=None,traces=None,origin='operator'):
        return self.context.create(kind,json.dumps(dataset or self.fixture['dataset']).encode(),json.dumps(bundle).encode() if bundle is not None else None,{k:v.encode() for k,v in (traces or {}).items()},origin,AT)
    def measured(self):return deepcopy(next(c for c in self.fixture['cases'] if c['id']=='supplied-unverified-measurements'))
    def test_original_source_fingerprints_and_exact_program_role_skill_bytes(self):
        for name,sha in self.fixture['source_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),sha)
        program=self.real_program();self.assertEqual(program['program_id'],self.program['program_id']);self.assertEqual(json.loads(program['default']),self.fixture['dataset'])
        for role_id,sha in program['role_sha'].items():self.assertEqual(hashlib.sha256((ROOT/'.agents/roles'/(role_id+'.yaml')).read_bytes()).hexdigest(),sha)
    def test_default_and_operator_prepare_match_all_26_original_whole_file_hashes(self):
        for dataset,expected in [(self.fixture['dataset'],self.fixture['prepared_file_hashes']),(self.fixture['operator_dataset']['dataset'],self.fixture['operator_dataset']['prepared_file_hashes'])]:
            identity,value=self.create(dataset=dataset);root=Path(value['data_directory']);self.assertEqual({p.name:descriptor(p.read_bytes()) for p in root.iterdir()},expected)
            self.assertEqual(self.context.inspect(identity),value)
            for flag in app.FLAGS:self.assertIs(value[flag],False)
    def test_all_nine_default_original_grade_success_and_error_cases_match(self):
        for case in self.fixture['cases']:
            with self.subTest(case['id']):
                if case['original_exit']:
                    with self.assertRaises(ValueError) as error:self.create('grade',bundle=case['response_bundle'],traces=case['traces'])
                    self.assertEqual('error: '+str(error.exception)+'\n',case['expected_error'])
                else:
                    identity,value=self.create('grade',bundle=case['response_bundle'],traces=case['traces']);raw=(Path(value['data_directory'])/'evaluation-grade.json').read_bytes();self.assertEqual(descriptor(raw),case['expected_grade']);self.assertEqual(self.context.inspect(identity),value)
    def test_explicit_operator_dataset_grade_preserves_complete_original_writer(self):
        case=self.fixture['operator_dataset'];_,value=self.create('grade',dataset=case['dataset'],bundle=case['response_bundle']);self.assertEqual(descriptor((Path(value['data_directory'])/'evaluation-grade.json').read_bytes()),case['expected_grade'])
    def test_invalid_synthetic_and_unknown_role_datasets_preserve_original_failures(self):
        for case in self.fixture['invalid_datasets']:
            with self.assertRaises(ValueError) as error:self.create(dataset=case['dataset'])
            self.assertEqual('error: '+str(error.exception)+'\n',case['expected_error'])
        self.assertEqual(list(self.context.assessments.iterdir()),[])
    def test_supplied_trace_metrics_remain_unauthenticated_and_no_model_is_invoked(self):
        c=self.measured();_,value=self.create('grade',bundle=c['response_bundle'],traces=c['traces']);report=json.loads((Path(value['data_directory'])/'evaluation-grade.json').read_text())
        self.assertEqual(report['measurement_case_count'],10);self.assertFalse(report['provider_invoked']);self.assertFalse(report['independent_human_approval'])
        for row in report['cases']:self.assertEqual(row['measurements']['assurance'],'supplied_runtime_trace_not_authenticated')
        self.assertFalse(value['trace_authenticity_verified']);self.assertFalse(value['model_execution_verified'])
    def test_complete_coverage_is_schema_coverage_not_correctness_or_approval(self):
        c=next(c for c in self.fixture['cases'] if c['id']=='wrong-classification');_,value=self.create('grade',bundle=c['response_bundle']);report=json.loads((Path(value['data_directory'])/'evaluation-grade.json').read_text())
        self.assertTrue(report['complete_coverage']);self.assertLess(report['classification_accuracy'],1);self.assertFalse(value['independent_human_approval'])
    def test_trace_file_from_response_never_reads_an_unattached_host_path(self):
        c=self.measured();record=c['response_bundle']['records'][0];old_label=record['trace_file'];host=self.root/'unattached.json';host.write_text(c['traces'][old_label]);record['trace_file']=str(host)
        original=app.safe_bytes
        def guarded(path,*args,**kwargs):
            self.assertNotEqual(Path(path).resolve(),host);return original(path,*args,**kwargs)
        with patch.object(app,'safe_bytes',side_effect=guarded):
            with self.assertRaisesRegex(ValueError,'not a supplied retained input'):self.create('grade',bundle=c['response_bundle'],traces=c['traces'])
        c['traces'][str(host)]=c['traces'].pop(old_label);_,value=self.create('grade',bundle=c['response_bundle'],traces=c['traces']);self.assertEqual(descriptor((Path(value['data_directory'])/'evaluation-grade.json').read_bytes()),c['expected_grade'])
    def test_bad_trace_hash_and_invalid_elapsed_usage_model_fields_are_rejected(self):
        c=self.measured();c['response_bundle']['records'][0]['trace_sha256']='f'*64
        with self.assertRaisesRegex(ValueError,'trace digest mismatch'):self.create('grade',bundle=c['response_bundle'],traces=c['traces'])
        for field,value in [('elapsed_seconds',float('inf')),('elapsed_seconds',-1),('elapsed_seconds',True),('usage',{'input_tokens':True,'cached_input_tokens':0,'output_tokens':0}),('observed_model','invalid model')]:
            c=self.measured();r=c['response_bundle']['records'][0];trace=json.loads(c['traces'][r['trace_file']]);trace[field]=value;raw=json.dumps(trace,indent=2)+'\n';c['traces'][r['trace_file']]=raw;r['trace_sha256']=hashlib.sha256(raw.encode()).hexdigest()
            with self.assertRaises(ValueError):self.create('grade',bundle=c['response_bundle'],traces=c['traces'])
    def test_nonfinite_aggregate_is_rejected_instead_of_serializing_infinity(self):
        c=self.measured()
        for record in c['response_bundle']['records']:
            trace=json.loads(c['traces'][record['trace_file']]);trace['elapsed_seconds']=1e308;raw=json.dumps(trace,indent=2)+'\n';c['traces'][record['trace_file']]=raw;record['trace_sha256']=hashlib.sha256(raw.encode()).hexdigest()
        with self.assertRaisesRegex(ValueError,'nonfinite_result_input_number'):self.create('grade',bundle=c['response_bundle'],traces=c['traces'])
        self.assertEqual(list(self.context.assessments.iterdir()),[])

    def test_deep_trace_json_is_a_controlled_invalid_operation(self):
        c=self.measured();record=c['response_bundle']['records'][0];raw='['*2000+'0'+']'*2000
        c['traces'][record['trace_file']]=raw;record['trace_sha256']=hashlib.sha256(raw.encode()).hexdigest()
        # The parser's configured recursion limit can also allow parsing far
        # enough to reject the array shape; either is a controlled invalid input.
        with self.assertRaises(ValueError):
            self.create('grade',bundle=c['response_bundle'],traces=c['traces'])
        self.assertEqual(list(self.context.assessments.iterdir()),[])
    def test_idempotent_repeat_and_caller_removal_keep_full_replay(self):
        case=self.fixture['operator_dataset'];first,a=self.create('grade',dataset=case['dataset'],bundle=case['response_bundle']);second,b=self.create('grade',dataset=case['dataset'],bundle=case['response_bundle']);self.assertEqual(first,second);self.assertEqual(a,b)
    def test_cli_prepare_and_grade_operator_files_replay_after_files_are_removed(self):
        c=self.fixture['operator_dataset'];dataset=self.root/'dataset.json';dataset.write_text(json.dumps(c['dataset']));responses=self.root/'responses.json';responses.write_text(json.dumps(c['response_bundle']))
        with redirect_stdout(io.StringIO()) as out:self.assertEqual(app.run(['prepare','--dataset',str(dataset),'--at',AT],self.node,{'node_id':'quality-test-node'}),0)
        prepared=json.loads(out.getvalue());self.assertEqual(prepared['dataset_origin'],'operator')
        with redirect_stdout(io.StringIO()) as out:self.assertEqual(app.run(['grade','--dataset',str(dataset),'--responses',str(responses),'--at',AT],self.node,{'node_id':'quality-test-node'}),0)
        value=json.loads(out.getvalue());dataset.unlink();responses.unlink()
        with redirect_stdout(io.StringIO()) as out:self.assertEqual(app.run(['inspect','--assessment',value['assessment_id']],self.node,{'node_id':'quality-test-node'}),0)
        self.assertEqual(json.loads(out.getvalue())['files'],value['files'])
    def test_default_committed_dataset_and_operator_origin_are_separate(self):
        with redirect_stdout(io.StringIO()) as out:self.assertEqual(app.run(['prepare','--at',AT],self.node,{'node_id':'quality-test-node'}),0)
        default=json.loads(out.getvalue());self.assertEqual(default['dataset_origin'],'committed');_,operator=self.create();self.assertNotEqual(default['input_id'],operator['input_id']);self.assertEqual(default['files'],operator['files'])
        with self.assertRaisesRegex(ValueError,'committed_dataset_changed'):self.create(dataset=self.fixture['operator_dataset']['dataset'],origin='committed')

    def test_cli_explicit_trace_attachments_keep_original_score_after_caller_removal(self):
        c=self.measured();responses=self.root/'measured-responses.json';responses.write_text(json.dumps(c['response_bundle']))
        arguments=['grade','--responses',str(responses),'--at',AT];paths=[]
        for index,(name,text) in enumerate(c['traces'].items()):
            path=self.root/('trace-'+str(index)+'.json');path.write_text(text);paths.append(path)
            arguments.extend(['--trace',name,str(path)])
        with redirect_stdout(io.StringIO()) as output:self.assertEqual(app.run(arguments,self.node,{'node_id':'quality-test-node'}),0)
        value=json.loads(output.getvalue());self.assertEqual(descriptor((Path(value['data_directory'])/'evaluation-grade.json').read_bytes()),c['expected_grade'])
        responses.unlink()
        for path in paths:path.unlink()
        self.assertEqual(self.context.inspect(value['assessment_id'])['files'],value['files'])
    def test_input_byte_changes_extra_members_and_boolean_lengths_fail(self):
        identity,value=self.create();root=self.context.inputs/value['input_id'];path=root/'data/dataset.json';raw=path.read_bytes();path.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'input_bytes_changed'):self.context.inspect(identity)
        path.write_bytes(raw);(root/'data/extra').mkdir()
        with self.assertRaisesRegex(ValueError,'input_members'):self.context.inspect(identity)
        (root/'data/extra').rmdir();manifest=json.loads((root/'manifest.json').read_text());manifest['files']['dataset.json']['bytes']=True;new=canonical_digest(manifest);target=self.context.inputs/new;shutil.copytree(root,target);(target/'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'input_length'):self.context.input_data(new)
    def test_output_changes_extra_directories_and_symlinks_fail(self):
        identity,value=self.create();root=Path(value['data_directory']);path=root/'evaluation-manifest.json';raw=path.read_bytes();path.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'output_changed'):self.context.inspect(identity)
        path.write_bytes(raw);(root/'extra').mkdir()
        with self.assertRaisesRegex(ValueError,'output_members'):self.context.inspect(identity)
        (root/'extra').rmdir();path.unlink();path.symlink_to(self.root/'absent')
        with self.assertRaises(ValueError):self.context.inspect(identity)
    def test_foreign_node_runtime_program_and_forged_authority_are_rejected(self):
        identity,value=self.create();other=app.ReviewQualityContext(self.node,{'node_id':'different-node'})
        with self.assertRaisesRegex(ValueError,'binding_changed'):other.inspect(identity)
        with patch.object(app,'source_digest',return_value='f'*64):
            with self.assertRaisesRegex(ValueError,'program_changed'):self.context.inspect(identity)
        original=json.loads((self.context.assessments/(identity+'.json')).read_text())
        for flag in app.FLAGS:
            changed={**original,flag:True};new=canonical_digest(changed);(self.context.assessments/(new+'.json')).write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'invalid_review_quality_assessment'):self.context.inspect(new)
    def test_prepare_forbids_responses_and_grade_requires_them(self):
        with self.assertRaisesRegex(ValueError,'unexpected_review_prepare_input'):self.create(bundle={})
        with self.assertRaisesRegex(ValueError,'review_responses_required'):self.create('grade')
        with self.assertRaisesRegex(ValueError,'unsupported_review_quality_operation'):self.create('execute-model')
        self.assertEqual(list(self.context.assessments.iterdir()),[])
    def test_case_count_path_length_trace_label_and_trace_size_limits(self):
        with patch.object(app,'MAX_CASES',1):
            with self.assertRaisesRegex(ValueError,'case_budget'):self.create()
        data=deepcopy(self.fixture['operator_dataset']['dataset']);data['cases'][0]['id']='x'*244
        with self.assertRaisesRegex(ValueError,'case_budget'):self.create(dataset=data)
        with self.assertRaisesRegex(ValueError,'invalid_review_trace_label'):self.create('grade',bundle={},traces={'bad\nlabel':'{}'})
        with patch.object(app,'MAX_TRACE',1):
            with self.assertRaisesRegex(ValueError,'review_trace_byte_budget'):self.create('grade',bundle={},traces={'label':'{}'})
    def test_output_budget_is_enforced_during_construction_and_disk_reserve_before_publication(self):
        with patch.object(app,'MAX_OUTPUT_TOTAL',1):
            with self.assertRaisesRegex(ValueError,'review_quality_output_budget'):self.create()
        with patch.object(app,'reserve',side_effect=ValueError('synthetic_reserve')):
            with self.assertRaisesRegex(ValueError,'synthetic_reserve'):self.create()
        self.assertEqual(list(self.context.assessments.iterdir()),[])
    def test_private_files_and_missing_naive_clock(self):
        self.create()
        for directory in (self.context.inputs,self.context.artifacts,self.context.assessments):
            for path in directory.rglob('*'):
                if path.is_file():self.assertEqual(path.stat().st_mode&0o077,0)
        with self.assertRaisesRegex(ValueError,'timezone_required'):self.context.create('prepare',self.program['default'],None,{},'committed','2026-11-15T12:00:00')

if __name__=='__main__':unittest.main()
