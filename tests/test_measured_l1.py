"""Measured evidence cannot turn declarations, missing approvals or tampering into PASS."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import yaml
from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.measured_l1 import FILES, SERVICES, normalize, validate_snapshot, store_snapshot, load_snapshots, binding
from lib.measured_security import REPOSITORY, WORKFLOW
from lib.viewer_app import project


class MeasuredL1Tests(unittest.TestCase):
    def setUp(self):
        self.run = {'id': 42, 'run_attempt': 1, 'repository': {'full_name': REPOSITORY, 'id': 9},
            'head_branch': 'main', 'event': 'push', 'status': 'completed', 'conclusion': 'success',
            'path': WORKFLOW, 'head_sha': 'a'*40, 'created_at': '2026-09-16T10:00:00Z', 'updated_at': '2026-09-16T10:01:00Z'}
        self.context = {'repository': REPOSITORY, 'commit': 'a'*40, 'run_id': '42', 'attempt': '1', 'event': 'push'}
        def artifact(name, number):
            return {'id': number, 'name': name, 'expired': False, 'workflow_run': {'id': 42, 'head_sha': 'a'*40, 'head_branch': 'main', 'repository_id': 9}}
        self.report_artifact = artifact('l1-control-coverage', 1)
        self.trace = {'requirements': [{'id': 'REQ-1', 'test_class_prefix': 'test.', 'requirement': 'Example'}]}
        self.images = {s: 'sha256:'+hashlib.sha256(s.encode()).hexdigest() for s in SERVICES}
        self.report = {'context': self.context, 'reference_baseline': 'l1-baseline-v1.1.3', 'report_type': 'l1-measured-evidence-coverage',
            'evidence_errors': {}, 'enforcement': 'report-only', 'official_compliance_result': False, 'production_approval': False,
            'controls': [{'control_id': f'DSCB-L1-REQ-{i:03}', 'coverage': 'measured'} for i in range(1,17)],
            'test_summary': {'pass': 2}, 'static_analysis': {'bandit': 1, 'ruff': 1}, 'vulnerability_severities': {'HIGH': 5},
            'images': {s: {'image_id': self.images[s]} for s in SERVICES}}
        self.bundles = {}
        for number,(name,required) in enumerate(FILES.items(),2):
            values = {f: {} for f in required}
            if name == 'source':
                values.update({'bandit.json': {'results': [{}], 'errors': []}, 'ruff.json': [{}]})
            if name == 'platform':
                values = {f: {'http_status': 403} for f in required}
                values['commit.json'] = {'http_status': 200, 'data': {'sha': 'a'*40, 'author': {'id': 1}}}
                values['run.json'] = {'http_status': 200, 'data': {'id': 42, 'head_sha': 'a'*40}}
            if name == 'runtime':
                values['deployment.json'] = {'commit': 'a'*40, 'run_id': '42', 'containers': [
                    {'image_id': self.images[s], 'environment': 'ephemeral-ci'} for s in ('query-api','neo4j')]}
            if name.startswith('image-'):
                service = name[6:]; identity = self.images[service]
                values.update({'subject.json': {'service': service, 'commit': 'a'*40, 'image_id': identity,
                        'archive_sha256': 'b'*64, 'python_base': 'python@sha256:'+'c'*64},
                    'image-metadata.json': {'Id': identity},
                    'sbom.cyclonedx.json': {'bomFormat': 'CycloneDX', 'components': [{}], 'metadata': {'component': {
                        'type': 'container', 'properties': [{'name': 'aquasecurity:trivy:ImageID', 'value': identity}]}}},
                    'vulnerabilities.json': {'Metadata': {'ImageID': identity}, 'Results': [{'Vulnerabilities': [
                        {'VulnerabilityID': 'CVE-2026-1234', 'Severity': 'HIGH', 'PkgName': 'test', 'InstalledVersion': '1'}]}]}})
            raw = {}
            for f in required:
                if f.endswith('.execution.json'): values[f] = {'exit_code': 0}
                raw[f] = (b'<testsuites><testsuite><testcase classname="test.example" name="works"/></testsuite></testsuites>' if f == 'junit.xml'
                          else b'Tool 1.0\n' if f.endswith('.log') else json.dumps(values[f]).encode())
            self.bundles[name] = (raw, artifact('l1-'+name, number)); self.seal(name)

    def seal(self,name):
        raw = self.bundles[name][0]
        raw['manifest.json'] = json.dumps({'context': self.context, 'files': {n: {'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)} for n,b in raw.items() if n != 'manifest.json'}}).encode()

    def change(self,name,filename,value):
        self.bundles[name][0][filename] = value if isinstance(value,bytes) else json.dumps(value).encode()
        self.seal(name)

    def normalized(self):
        return normalize(self.run,json.dumps(self.report).encode(),self.report_artifact,self.bundles,json.dumps(self.trace).encode())

    def test_measured_rules_preserve_approval_gaps_despite_optimistic_producer(self):
        item=self.normalized()
        self.assertEqual({'measured':5,'partial':6,'findings':2,'gap':3},item['summary'])
        self.assertEqual({'DSCB-L1-REQ-'+f'{n:03}' for n in (3,13,14)}, {r['control_id'] for r in item['controls'] if r['assessment']=='gap'})
        model=yaml.safe_load((ROOT/'model/controls/dscb-l1.yaml').read_text())
        self.assertEqual({r['id'] for r in model['requirements']},{r['control_id'] for r in item['controls']})
        self.assertFalse(item['production_approval']);self.assertFalse(item['official_compliance_result'])

    def test_authenticated_api_access_alone_is_not_branch_or_deployment_approval(self):
        for name in ('protection.json','rules.json','environments.json'):
            self.change('platform',name,{'http_status':200,'data':{}})
        item=self.normalized()
        self.assertEqual('partial',item['controls'][2]['assessment'])
        self.assertEqual(['gap','gap'],[item['controls'][n]['assessment'] for n in (12,13)])

    def test_edited_raw_bytes_are_rejected(self):
        self.bundles['source'][0]['junit.xml'] += b' '
        with self.assertRaisesRegex(ValueError,'hash/size'): self.normalized()

    def test_other_attempt_or_commit_cannot_reuse_old_manifest(self):
        for key,value in [('attempt','2'),('commit','f'*40),('repository','other/repo'),('event','pull_request')]:
            with self.subTest(key=key):
                original=self.bundles['runtime'][0]['manifest.json'];manifest=json.loads(original);manifest['context'][key]=value
                self.bundles['runtime'][0]['manifest.json']=json.dumps(manifest).encode()
                with self.assertRaisesRegex(ValueError,'context'):self.normalized()
                self.bundles['runtime'][0]['manifest.json']=original

    def test_foreign_run_artifact_rejected(self):
        self.report_artifact['workflow_run']['id']=43
        with self.assertRaisesRegex(ValueError,'binding'):self.normalized()

    def test_pr_manual_failed_or_other_workflow_cannot_be_official_measurement(self):
        for field,value in [('event','pull_request'),('event','workflow_dispatch'),('conclusion','failure'),('path','other.yml'),('head_branch','feature')]:
            with self.subTest(field=field):
                old=self.run[field];self.run[field]=value
                with self.assertRaises(ValueError):self.normalized()
                self.run[field]=old

    def test_sast_counts_recomputed_and_execution_failure_stays_gap(self):
        self.report['static_analysis']['bandit']=0
        with self.assertRaisesRegex(ValueError,'SAST counts'):self.normalized()
        self.report['static_analysis']['bandit']=1
        self.change('source','bandit.execution.json',{'exit_code':2})
        self.assertEqual('gap',self.normalized()['controls'][3]['assessment'])

    def test_tool_completion_with_no_findings_does_not_claim_review(self):
        self.change('source','bandit.json',{'results':[],'errors':[]});self.change('source','ruff.json',[])
        self.report['static_analysis']={'bandit':0,'ruff':0}
        self.assertEqual('partial',self.normalized()['controls'][3]['assessment'])

    def test_junit_counts_and_traceability_are_recomputed(self):
        self.report['test_summary']['pass']=999
        with self.assertRaisesRegex(ValueError,'JUnit'):self.normalized()
        self.report['test_summary']['pass']=2;self.trace['requirements'][0]['test_class_prefix']='nonexistent.'
        self.assertEqual('gap',self.normalized()['controls'][0]['assessment'])

    def test_empty_or_entity_bearing_junit_is_not_evidence(self):
        for value in [b'<testsuites/>',b'<!DOCTYPE x><testsuites/>',
                      '<!DOCTYPE testsuites [<!ENTITY word "substituted">]><testsuites><testcase name="&word;"/></testsuites>'.encode('utf-16')]:
            self.change('source','junit.xml',value)
            with self.assertRaises(ValueError):self.normalized()

    def test_scan_and_runtime_image_mismatch_rejected_even_when_resealed(self):
        value=json.loads(self.bundles['runtime'][0]['deployment.json']);value['containers'][0]['image_id']='sha256:'+'f'*64
        self.change('runtime','deployment.json',value)
        with self.assertRaisesRegex(ValueError,'Runtime images'):self.normalized()

    def test_sbom_bound_to_other_image_rejected(self):
        value=json.loads(self.bundles['image-query-api'][0]['sbom.cyclonedx.json'])
        value['metadata']['component']['properties'][0]['value']='sha256:'+'f'*64
        self.change('image-query-api','sbom.cyclonedx.json',value)
        with self.assertRaisesRegex(ValueError,'SBOM'):self.normalized()

    def test_snapshot_state_binding_and_missing_refs_are_validated(self):
        item=self.normalized()
        for key in ('official_compliance_result','production_approval','risk_acceptance'):
            with self.assertRaises(ValidationError):validate_snapshot({**item,key:True})
        changed=deepcopy(item);changed['controls'][12]['assessment']='measured'
        with self.assertRaisesRegex(ValueError,'observations'):validate_snapshot(changed)
        changed=deepcopy(item);changed['run']['attempt']=2
        with self.assertRaisesRegex(ValueError,'binding'):validate_snapshot(changed)
        changed=deepcopy(item);del changed['sources']['source/bandit.json'];changed['evidence_binding']=binding(changed)
        with self.assertRaisesRegex(ValueError,'sources'):validate_snapshot(changed)

    def test_duplicate_producer_control_rejected(self):
        self.report['controls'][0]=self.report['controls'][1]
        with self.assertRaisesRegex(ValueError,'duplicate'):self.normalized()

    def test_storage_is_append_only_and_idempotent(self):
        item=self.normalized()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=store_snapshot(root,item);self.assertEqual(path,store_snapshot(root,item))
            changed=deepcopy(item);changed['sources']['source/tests.execution.json']['sha256']='f'*64;changed['evidence_binding']=binding(changed)
            with self.assertRaisesRegex(ValueError,'Conflicting'):store_snapshot(root,changed)
            self.assertEqual([item],load_snapshots(root))

    def test_snapshot_filename_cannot_disguise_another_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=store_snapshot(root,self.normalized());path.rename(path.with_name('run-43-attempt-1.json'))
            with self.assertRaisesRegex(ValueError,'path/identity'):load_snapshots(root)

    def test_viewer_preserves_baseline_and_selects_measurements_by_source_time_attempt(self):
        first=self.normalized();later=deepcopy(first);later['run']['id']='43';later['run']['created_at']='2026-09-16T11:00:00Z'
        first['run']['created_at']='2026-09-16T12:00:00+02:00'
        official={'status':'pass','commit_id':'a'*40,'trust':{'replay':'fail'}}
        index={'repositories':[{'repository_id':REPOSITORY,'latest_result':official}]}
        data=project(index,{'repositories':[]},[],[later,first]);row=data['repositories'][0]
        self.assertEqual(official,row['devsecops']);self.assertEqual(later,row['l1_assessment'])
        self.assertEqual('fail',row['devsecops']['trust']['replay'])
        self.assertIsNone(project(index,{'repositories':[]},[])['repositories'][0]['l1_assessment'])
