"""Whole frozen V1 context/evidence/gate wires and private retained-byte operations."""
import argparse
import base64
from copy import deepcopy
import hashlib
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib import pipeline_application as application, pipeline_evidence as core
from lib.provider_ports import declared_pipeline_environment, DECLARED_PIPELINE_PROFILES
from lib.portable.contracts import canonical_digest
FIXTURE=ROOT/'tests/fixtures/axiom-v1-parity/context-pipeline-cases.json'
AT='2026-11-15T12:00:00.123456+00:00'

def metadata(case):
    p=argparse.ArgumentParser();p.add_argument('--platform');p.add_argument('--output');p.add_argument('--gate-output');p.add_argument('--platform-context-file',default='')
    for key,value in application.DEFAULTS.items():p.add_argument('--'+key.replace('_','-'),**({'action':'store_true'} if isinstance(value,bool) else {'default':value}))
    args=vars(p.parse_args(case['arguments']));return {k:args[k] for k in application.DEFAULTS}


class PurePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=json.loads(FIXTURE.read_text())
    def test_original_source_fingerprints_are_unchanged(self):
        self.assertEqual(self.fixture['v1_reference'],'6b557fefe295b58272d2271326576ca3a3687197')
        for name,sha in self.fixture['source_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),sha)
    def test_all_four_original_profiles_and_sixteen_context_wires(self):
        self.assertEqual(set(DECLARED_PIPELINE_PROFILES),{c['platform'] for c in self.fixture['cases']})
        for c in self.fixture['cases']:
            with self.subTest(c['id']):self.assertEqual(application.wire(declared_pipeline_environment(c['platform'],c['environment'])['context']).decode(),c['expected_wires']['context-output.json'])
    def test_only_explicit_finite_environment_fields_and_profiles_are_accepted(self):
        for env in ({'GITHUB_TOKEN':'not-a-token'},{'BUILD_NUMBER':None},{'BUILD_NUMBER':'x'*4097}):
            with self.assertRaisesRegex(ValueError,'invalid_declared_pipeline_environment'):declared_pipeline_environment('jenkins',env)
        with self.assertRaisesRegex(ValueError,'unsupported_declared_pipeline_profile'):declared_pipeline_environment('unlisted',{})
    def test_original_boolean_severity_and_run_purpose_rules(self):
        for value in ('1','true',' yes ','Y','on',True):self.assertTrue(core.as_bool(value))
        for value in ('','false','none',None,0):self.assertFalse(core.as_bool(value))
        self.assertEqual(core.run_purpose('push',True,'main'),('release',True))
        self.assertEqual(core.run_purpose('manual_build',True,'main'),('diagnostic',False))
        self.assertEqual(core.run_purpose('pull_request',False,'main'),('pull_request_validation',False))
        self.assertEqual(core.run_purpose('push',True,'trunk'),('branch_validation',False))
    def test_malformed_scan_uses_original_fallback_but_valid_non_object_is_invalid(self):
        self.assertEqual(application.scan_severity(b'bad','CRITICAL'),'CRITICAL')
        self.assertEqual(application.scan_severity(b'{}','CRITICAL'),'critical')
        self.assertEqual(application.scan_severity(b'{"max_severity":"NONE"}','critical'),'none')
        with self.assertRaisesRegex(ValueError,'scan_shape'):application.scan_severity(b'[]','none')


class PipelineOperationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=json.loads(FIXTURE.read_text())
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.root=Path(self.temporary.name).resolve();self.node=self.root/'node';self.node.mkdir(mode=0o700)
        self.app=application.PipelineContext(self.node,{'node_id':'pipeline-test-node'})
        self.case=deepcopy(self.fixture['cases'][0])
    def tearDown(self):self.temporary.cleanup()
    def capture(self,c=None,kind='all',at=AT):
        c=c or self.case;root=self.root/c['id'];root.mkdir(mode=0o700,exist_ok=True)
        params=metadata(c);sources={}
        for slot,key in [('artifact','artifact_path'),('sbom','sbom_path'),('scan','vulnerability_scan_path'),('signature','signature_path')]:
            if params[key] in c['input_files']:
                path=root/slot;path.write_bytes(base64.b64decode(c['input_files'][params[key]]));sources[slot]=path
        return self.app.create(kind,c['platform'],c['environment'],params,c['context_override'],sources,at)
    def test_all_original_48_context_evidence_gate_json_files_match_without_normalization(self):
        for c in self.fixture['cases']:
            with self.subTest(c['id']):
                _,v=self.capture(c);root=Path(v['data_directory'])
                for key,name in [('context','context-output.json'),('evidence','evidence.json'),('gate','gate.json')]:self.assertEqual((root/application.OUTPUTS[key]).read_bytes(),c['expected_wires'][name].encode())
                self.assertFalse(v['pipeline_execution_verified']);self.assertFalse(v['waiver_approval_verified']);self.assertFalse(v['official_acceptance'])
    def test_repeat_is_idempotent_and_each_kind_has_only_its_original_outputs(self):
        first,a=self.capture();second,b=self.capture();self.assertEqual(first,second);self.assertEqual(a,b)
        _,context=self.capture(kind='context');self.assertEqual(set(context['files']),{application.OUTPUTS['context']})
        _,pipeline=self.capture(kind='pipeline');self.assertEqual(set(pipeline['files']),{application.OUTPUTS['evidence'],application.OUTPUTS['gate']})
    def test_retained_raw_inputs_replay_after_caller_files_are_removed(self):
        assessment,v=self.capture()
        for path in (self.root/self.case['id']).iterdir():path.unlink()
        self.assertEqual(self.app.inspect(assessment),v)
    def test_input_byte_mutation_and_extra_member_fail_before_replay(self):
        assessment,v=self.capture();data=self.app.inputs/v['input_id']/'data';path=data/'artifact';saved=path.read_bytes();path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'input_bytes_changed'):self.app.inspect(assessment)
        path.write_bytes(saved);extra=data/'unused';extra.mkdir()
        with self.assertRaisesRegex(ValueError,'unexpected_declared_pipeline_input_members'):self.app.inspect(assessment)
    def test_input_symlinks_and_unexpected_output_directories_are_rejected(self):
        assessment,v=self.capture();root=Path(v['data_directory']);(root/'extra').mkdir()
        with self.assertRaisesRegex(ValueError,'unexpected_declared_pipeline_artifact_members'):self.app.inspect(assessment)
        (root/'extra').rmdir();path=self.root/'linked';path.symlink_to(self.root/self.case['id']/'artifact')
        with self.assertRaisesRegex(ValueError,'unsafe_declared_pipeline_source'):self.app.capture(self.case['platform'],{},metadata(self.case),None,{'artifact':path})
    def test_output_bytes_and_forged_files_manifest_fail(self):
        assessment,v=self.capture();path=Path(v['data_directory'])/application.OUTPUTS['gate'];path.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'declared_pipeline_output_changed'):self.app.inspect(assessment)
    def test_foreign_node_and_changed_product_are_rejected(self):
        assessment,_=self.capture();foreign=application.PipelineContext(self.node,{'node_id':'other'})
        with self.assertRaisesRegex(ValueError,'binding_changed'):foreign.inspect(assessment)
        with patch.object(application,'source_digest',return_value='f'*64):
            with self.assertRaisesRegex(ValueError,'product_changed'):self.app.inspect(assessment)
    def test_explicit_offset_clock_is_normalized_like_original_utc_isoformat(self):
        _,v=self.capture(at='2026-11-15T13:00:00.123456+01:00');root=Path(v['data_directory'])
        self.assertEqual((root/application.OUTPUTS['evidence']).read_text(),self.case['expected_wires']['evidence.json'])
        with self.assertRaisesRegex(ValueError,'timezone_required'):self.capture(at='2026-11-15T12:00:00')
    def test_invalid_metadata_and_unused_signature_are_rejected(self):
        for value in ({'unknown':True},{'artifact_path':''},{'release_candidate':'true'},{'artifact_path':'a\nb'}):
            with self.assertRaisesRegex(ValueError,'parameters'):application.parameters(value)
        with self.assertRaisesRegex(ValueError,'signature_label_required'):self.app.capture(self.case['platform'],{},{},None,{'signature':self.root/'absent'})
    def test_byte_limits_and_disk_reserve_fail_without_assessment_publication(self):
        c=self.case
        with patch.dict(application.LIMITS,artifact=1):
            with self.assertRaisesRegex(ValueError,'invalid_ci_bundle_file'):self.capture()
        with patch.object(application,'reserve',side_effect=ValueError('synthetic_reserve')):
            with self.assertRaisesRegex(ValueError,'synthetic_reserve'):self.capture()
        self.assertEqual(list(self.app.assessments.iterdir()),[])
    def test_schema_cannot_claim_operating_or_signature_authority(self):
        _,v=self.capture();value={k:x for k,x in v.items() if k not in ('assessment_id','data_directory','declared_gate_status')}
        for flag in application.FLAGS:
            changed={**value,flag:True}
            with self.assertRaisesRegex(ValueError,'invalid_declared_pipeline_assessment'):self.app.validate(changed)
    def test_missing_sources_produce_original_finding_data_without_blocking(self):
        c=next(c for c in self.fixture['cases'] if c['id']=='github-actions-missing');_,v=self.capture(c)
        self.assertEqual(v['declared_gate_status'],'fail');self.assertEqual(v['mode'],'report-only')
        evidence=json.loads((Path(v['data_directory'])/application.OUTPUTS['evidence']).read_text());self.assertEqual(evidence['pipeline']['status'],'success')
        self.assertFalse(v['pipeline_execution_verified']);self.assertFalse(v['official_acceptance'])
    def test_retained_files_have_private_permissions(self):
        _,v=self.capture()
        for root in (self.app.inputs,self.app.assessments,self.app.artifacts):
            for path in root.rglob('*'):
                if path.is_file():self.assertEqual(path.stat().st_mode&0o077,0)

    def test_cli_findings_remain_data_unless_local_exit_is_explicit(self):
        environment=self.root/'environment.json';environment.write_text('{}')
        arguments=['create','--kind','all','--profile','jenkins','--environment',str(environment),'--at',AT]
        with redirect_stdout(io.StringIO()) as captured:
            self.assertEqual(application.run(arguments,self.node,{'node_id':'pipeline-test-node'}),0)
        first=json.loads(captured.getvalue());self.assertEqual(first['declared_gate_status'],'fail')
        with redirect_stdout(io.StringIO()) as captured:
            self.assertEqual(application.run([*arguments,'--fail-on-findings'],self.node,{'node_id':'pipeline-test-node'}),1)
        self.assertEqual(json.loads(captured.getvalue())['assessment_id'],first['assessment_id'])
        with redirect_stdout(io.StringIO()) as captured:
            self.assertEqual(application.run(['inspect','--assessment',first['assessment_id']],self.node,{'node_id':'pipeline-test-node'}),0)
        self.assertFalse(json.loads(captured.getvalue())['pipeline_execution_verified'])

    def test_resealed_authority_and_manifest_shape_cannot_be_accepted(self):
        assessment,value=self.capture();record=self.app.assessments/(assessment+'.json')
        raw=json.loads(record.read_text());raw['signature_verified']=True;changed=canonical_digest(raw)
        (self.app.assessments/(changed+'.json')).write_text(json.dumps(raw))
        with self.assertRaisesRegex(ValueError,'invalid_declared_pipeline_assessment'):self.app.inspect(changed)

if __name__=='__main__':unittest.main()
