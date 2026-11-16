"""Original declared-selection snapshot wires and private immutable log replay."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib,io,json,shutil,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib import agent_usage,agent_usage_application as app
from lib.portable.contracts import canonical_digest
FIXTURE=ROOT/'tests/fixtures/axiom-v1-parity/agent-usage-cases.json'
AT='2026-11-15T12:30:00Z'

class AgentUsageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=json.loads(FIXTURE.read_text())
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.node=self.root/'node';self.node.mkdir(mode=0o700)
        self.context=app.AgentUsageContext(self.node,{'node_id':'usage-test-node'})
    def tearDown(self):self.temp.cleanup()
    def create(self,case=None):
        c=case or self.fixture['cases'][0]
        return self.context.create(c['usage_log_wire'].encode(),{'kind':'operator','present':True},c['source_log_label'],c['generated_at'],c['latest_count'])
    def test_original_source_fingerprints_remain_unchanged(self):
        self.assertEqual(self.fixture['v1_reference'],'6b557fefe295b58272d2271326576ca3a3687197')
        for name,sha in self.fixture['source_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),sha)
    def test_all_seven_actual_old_cli_cases_match_fourteen_complete_file_wires(self):
        for c in self.fixture['cases']:
            with self.subTest(c['id']):
                assessment,value=self.create(c);data=Path(value['data_directory'])
                for name,raw in c['expected_wires'].items():self.assertEqual((data/app.OUTPUTS[name]).read_bytes(),raw.encode())
                self.assertEqual(self.context.inspect(assessment),value)
                for flag in app.FLAGS:self.assertIs(value[flag],False)
    def test_original_zero_and_negative_count_mean_all_events(self):
        for name in ('zero-keeps-all','negative-clamps-zero-keeps-all'):
            c=next(c for c in self.fixture['cases'] if c['id']==name);_,value=self.create(c)
            snapshot=json.loads((Path(value['data_directory'])/app.OUTPUTS['result.json']).read_text())
            self.assertEqual(len(snapshot['latest_events']),len(c['events']));self.assertEqual(value['latest_count_effective'],0)
            self.assertEqual(value['latest_count_requested'],c['latest_count'])
    def test_offset_and_fraction_clock_remain_raw_original_display_context(self):
        c=next(c for c in self.fixture['cases'] if c['id']=='offset-fraction-clock');_,value=self.create(c)
        snapshot=json.loads((Path(value['data_directory'])/app.OUTPUTS['result.json']).read_text());self.assertEqual(snapshot['generated_at'],c['generated_at'])
        with self.assertRaisesRegex(ValueError,'timezone_required'):self.context.create(b'',{'kind':'operator','present':True},'log','2026-11-15T12:00:00',10)
    def test_idempotent_repeat_and_retained_log_do_not_need_caller_file(self):
        c=self.fixture['cases'][0];path=self.root/'caller.jsonl';path.write_text(c['usage_log_wire']);raw=path.read_bytes()
        first,a=self.context.create(raw,{'kind':'operator','present':True},'caller-selected.jsonl',AT,10);path.unlink()
        second,b=self.context.create(raw,{'kind':'operator','present':True},'caller-selected.jsonl',AT,10)
        self.assertEqual(first,second);self.assertEqual(a,b);self.assertEqual(self.context.inspect(first),a)
    def test_source_log_label_changes_output_identity_without_reading_a_host_path(self):
        first,a=self.create();c=self.fixture['cases'][0]
        second,b=self.context.create(c['usage_log_wire'].encode(),{'kind':'operator','present':True},'/declared/outside/log.jsonl',AT,10)
        self.assertNotEqual(first,second);self.assertEqual(a['input_id'],b['input_id'])
        snapshot=json.loads((Path(b['data_directory'])/app.OUTPUTS['result.json']).read_text());self.assertEqual(snapshot['source_log'],'/declared/outside/log.jsonl')
    def test_default_committed_legacy_log_is_exact_git_data_and_not_private_execution_history(self):
        with redirect_stdout(io.StringIO()) as output:self.assertEqual(app.run(['create','--at',AT],self.node,{'node_id':'usage-test-node'}),0)
        value=json.loads(output.getvalue());self.assertEqual(value['source_origin']['kind'],'committed');self.assertEqual(value['source_log_label'],app.LOG)
        self.assertEqual(value['source_origin']['revision'],value['source_revision']);self.assertFalse(value['agent_execution_verified'])
        raw,_=self.context.input_data(value['input_id']);self.assertEqual(raw,app.git_read(ROOT,'show',value['source_revision']+':'+app.LOG))
    def test_cli_arbitrary_operator_log_missing_log_and_inspection(self):
        path=self.root/'outside.jsonl';c=self.fixture['cases'][0];path.write_text(c['usage_log_wire'])
        args=['create','--usage-log',str(path),'--source-log-label',c['source_log_label'],'--latest-count','0','--at',AT]
        with redirect_stdout(io.StringIO()) as output:self.assertEqual(app.run(args,self.node,{'node_id':'usage-test-node'}),0)
        value=json.loads(output.getvalue());self.assertEqual(value['source_origin'],{'kind':'operator','present':True});path.unlink()
        with redirect_stdout(io.StringIO()) as output:self.assertEqual(app.run(['inspect','--assessment',value['assessment_id']],self.node,{'node_id':'usage-test-node'}),0)
        self.assertEqual(json.loads(output.getvalue())['assessment_id'],value['assessment_id'])
        with redirect_stdout(io.StringIO()) as output:self.assertEqual(app.run(args,self.node,{'node_id':'usage-test-node'}),0)
        missing=json.loads(output.getvalue());self.assertIs(missing['source_origin']['present'],False);snapshot=json.loads((Path(missing['data_directory'])/app.OUTPUTS['result.json']).read_text());self.assertEqual(snapshot['event_count'],0)
    def test_operator_symlink_and_dangling_symlink_are_rejected(self):
        for name,target in [('missing','absent'),('existing','real')]:
            if name=='existing':(self.root/target).write_bytes(b'')
            path=self.root/name;path.symlink_to(self.root/target)
            with self.assertRaisesRegex(ValueError,'unsafe_agent_usage_log'):app.run(['create','--usage-log',str(path),'--at',AT],self.node,{'node_id':'usage-test-node'})
    def test_invalid_jsonl_and_nonobject_events_are_not_successful_reports(self):
        for raw in (b'{bad\n',b'[]\n',b'\xff',b'['*2000):
            with self.assertRaises(ValueError):self.context.create(raw,{'kind':'operator','present':True},'log',AT,10)
        self.assertEqual(list(self.context.assessments.iterdir()),[])
    def test_unsupported_event_metadata_fails_before_assessment_publication(self):
        with self.assertRaisesRegex(ValueError,'invalid_agent_usage_event_metadata'):self.context.create(b'{"selected_agents":[null]}\n',{'kind':'operator','present':True},'log',AT,10)
        self.assertEqual(list(self.context.assessments.iterdir()),[])
    def test_invalid_count_labels_and_input_origin_are_rejected(self):
        for label,count in [('',10),('bad\nlabel',10),('log',True),('log','10')]:
            with self.assertRaises(ValueError):self.context.create(b'',{'kind':'operator','present':True},label,AT,count)
        with self.assertRaisesRegex(ValueError,'input_origin'):self.context.create(b'',{'kind':'native-verified'},'log',AT,10)
    def test_input_bytes_extra_members_and_symlinks_fail(self):
        assessment,value=self.create();root=self.context.inputs/value['input_id'];path=root/'events.jsonl';saved=path.read_bytes();path.write_bytes(b'{}\n')
        with self.assertRaisesRegex(ValueError,'agent_usage_input_changed'):self.context.inspect(assessment)
        path.write_bytes(saved);(root/'extra').mkdir()
        with self.assertRaisesRegex(ValueError,'unexpected_agent_usage_input_members'):self.context.inspect(assessment)
        (root/'extra').rmdir();path.unlink();path.symlink_to(self.root/'absent')
        with self.assertRaises(ValueError):self.context.inspect(assessment)
    def test_output_bytes_and_unexpected_directories_fail_without_repair(self):
        assessment,value=self.create();root=Path(value['data_directory']);path=root/app.OUTPUTS['result.json'];saved=path.read_bytes();path.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'agent_usage_output_changed'):self.context.inspect(assessment)
        path.write_bytes(saved);(root/'extra').mkdir()
        with self.assertRaisesRegex(ValueError,'unexpected_agent_usage_artifact_members'):self.context.inspect(assessment)
    def test_foreign_node_and_changed_runtime_fail(self):
        assessment,_=self.create();foreign=app.AgentUsageContext(self.node,{'node_id':'different-node'})
        with self.assertRaisesRegex(ValueError,'agent_usage_binding_changed'):foreign.inspect(assessment)
        with patch.object(app,'source_digest',return_value='f'*64):
            with self.assertRaisesRegex(ValueError,'agent_usage_product_changed'):self.context.inspect(assessment)
    def test_resealed_claimed_authority_and_effective_count_are_rejected(self):
        assessment,value=self.create();original=json.loads((self.context.assessments/(assessment+'.json')).read_text())
        for flag in app.FLAGS:
            changed={**original,flag:True};identity=canonical_digest(changed);(self.context.assessments/(identity+'.json')).write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError,'invalid_agent_usage_assessment'):self.context.inspect(identity)
        changed={**original,'latest_count_effective':9};identity=canonical_digest(changed);(self.context.assessments/(identity+'.json')).write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError,'agent_usage_count_changed'):self.context.inspect(identity)
    def test_resealed_boolean_byte_length_cannot_replace_integer_length(self):
        c=next(c for c in self.fixture['cases'] if c['id']=='empty');_,value=self.create(c);root=self.context.inputs/value['input_id'];m=json.loads((root/'manifest.json').read_text());self.assertEqual(m['bytes'],1)
        m['bytes']=True;identity=canonical_digest(m);other=self.context.inputs/identity;shutil.copytree(root,other);(other/'manifest.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'invalid_agent_usage_input_length'):self.context.input_data(identity)
    def test_log_event_output_and_disk_limits_leave_no_assessment(self):
        with patch.object(app,'MAX_LOG',1):
            with self.assertRaisesRegex(ValueError,'agent_usage_log_byte_budget'):self.context.create(b'{}\n',{'kind':'operator','present':True},'log',AT,10)
        with patch.object(app,'MAX_EVENTS',1):
            with self.assertRaisesRegex(ValueError,'agent_usage_event_budget'):app.events(b'{}\n{}\n')
        with patch.object(app,'MAX_OUTPUT',1):
            with self.assertRaisesRegex(ValueError,'agent_usage_output_budget'):self.create()
        with patch.object(app,'reserve',side_effect=ValueError('synthetic_reserve')):
            with self.assertRaisesRegex(ValueError,'synthetic_reserve'):self.create()
        self.assertEqual(list(self.context.assessments.iterdir()),[])
    def test_missing_and_empty_source_remain_distinct_without_changing_original_reports(self):
        first,a=self.context.create(b'',{'kind':'operator','present':True},'same-label',AT,10)
        second,b=self.context.create(b'',{'kind':'operator','present':False},'same-label',AT,10)
        self.assertNotEqual(first,second);self.assertNotEqual(a['input_id'],b['input_id']);self.assertEqual(a['files'],b['files'])
        with self.assertRaisesRegex(ValueError,'invalid_agent_usage_input_presence'):self.context.create(b'{}\n',{'kind':'operator','present':False},'log',AT,10)

    def test_generated_files_remain_private(self):
        self.create()
        for root in (self.context.inputs,self.context.artifacts,self.context.assessments):
            for path in root.rglob('*'):
                if path.is_file():self.assertEqual(path.stat().st_mode&0o077,0)

if __name__=='__main__':unittest.main()
