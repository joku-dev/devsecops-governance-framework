"""Negative admission and content-binding tests for the complete five-image profile."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from lib.container_typed_evidence import PROFILE, SERVICES, NAMES, SBOM_NAMES, verify_bundle, verify_docker_archive
from lib.evidence_trust import load_freshness_policy, promote_effective_level, verify_trust_capture
from intake_ha_container_trust import bind_artifact, extract_selected, prior_for_evidence_type
from generate_typed_evidence_results_index import project_result
from jsonschema import Draft202012Validator


def image_tar(path, corrupt_layer=False):
    layer = b'layer bytes'
    config = json.dumps({'config': {'Labels': {'org.opencontainers.image.revision': 'a'*40}}, 'rootfs': {'diff_ids': ['sha256:'+hashlib.sha256(layer).hexdigest()]}}).encode()
    digest = hashlib.sha256(config).hexdigest()
    files = {'config.json': config, 'layer.tar': layer if not corrupt_layer else b'wrong',
             'manifest.json': json.dumps([{'Config':'config.json', 'Layers':['layer.tar']}]).encode()}
    with tarfile.open(path, 'w') as tar:
        for name, content in files.items():
            info=tarfile.TarInfo(name);info.size=len(content);tar.addfile(info,io.BytesIO(content))
    return 'sha256:'+digest


class ContainerTypedTests(unittest.TestCase):
    def bundle(self, root):
        run={'id':123,'repository':{'id':9,'full_name':'joku-dev/ha-CPsWMS'},'head_sha':'a'*40,
             'head_branch':'main','event':'push','status':'completed','conclusion':'success',
             'path':'.github/workflows/l1-measured-evidence.yml','name':'L1 Measured Evidence',
             'run_attempt':1,'html_url':'https://github.com/joku-dev/ha-CPsWMS/actions/runs/123',
             'created_at':'2026-09-17T10:00:00Z','updated_at':'2026-09-17T10:05:00Z',
             'referenced_workflows':[{'path':'joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-l1-v1.1.3.yml@l1-baseline-v1.1.3',
                                      'ref':'refs/tags/l1-baseline-v1.1.3','sha':'b'*40}]}
        context={'repository':run['repository']['full_name'],'commit':run['head_sha'],'run_id':'123','attempt':'1','event':'push'}
        report={'context':context,'report_type':'l1-measured-evidence-coverage','evidence_errors':{},
                'reference_baseline':'l1-baseline-v1.1.3',
                'official_compliance_result':False,'enforcement':'report-only','production_approval':False,
                'images':{},'vulnerability_severities':{},'test_summary':{'pass':57}}
        declaration={'profile':PROFILE,'enforcement':'report-only','context':context,'images':{}}
        bundles,paths={},{}
        for n,service in enumerate(SERVICES):
            path=root/service;path.mkdir();paths[service]=path
            image_id=image_tar(path/'image.tar');archive_hash=hashlib.sha256((path/'image.tar').read_bytes()).hexdigest()
            values={'subject.json':{'service':service,'commit':run['head_sha'],'image_id':image_id,'archive_sha256':archive_hash},
                    'sbom.cyclonedx.json':{'bomFormat':'CycloneDX','specVersion':'1.6',
                        'metadata':{'component':{'type':'container','properties':[{'name':'aquasecurity:trivy:ImageID','value':image_id}]}},
                        'components':[{'type':'library','name':'package-a','version':'1.0'}]},
                    'sbom.execution.json':{'exit_code':0,'execution_ok':True,'command':['trivy','image','--image-src','docker','--format','cyclonedx','--output','sbom.cyclonedx.json',image_id]},
                    'vulnerabilities.json':{'Metadata':{'ImageID':image_id},'Results':[{'Target':'os','Vulnerabilities':[]}]},
                    'vulnerabilities.execution.json':{'exit_code':0,'execution_ok':True,'command':['trivy','image','--image-src','docker',image_id]},
                    'archive.execution.json':{'exit_code':0,'execution_ok':True},
                    'trivy-version.execution.json':{'exit_code':0,'execution_ok':True}}
            for name,value in values.items():(path/name).write_text(json.dumps(value))
            (path/'trivy-version.log').write_text('Version: 0.70.0\n')
            manifest={'context':{**context,'observed_at':'2026-09-17T10:02:00Z'},'files':{
                name:{'sha256':hashlib.sha256((path/name).read_bytes()).hexdigest(),'bytes':(path/name).stat().st_size} for name in NAMES}}
            (path/'manifest.json').write_text(json.dumps(manifest))
            artifact={'id':n+1,'name':'l1-image-'+service,'expired':False,'size_in_bytes':100,
                      'verified_zip_sha256':'f'*64,'workflow_run':{'id':123,'head_sha':run['head_sha'],'head_branch':'main','repository_id':9}}
            bundles[service]=({name:(path/name).read_bytes() for name in ('manifest.json','subject.json','vulnerabilities.json','vulnerabilities.execution.json')},artifact)
            report['images'][service]={'image_id':image_id}
            declaration['images'][service]={'artifact_name':artifact['name'],'image_id':image_id,
                'archive_sha256':archive_hash,
                'sbom_sha256':manifest['files']['sbom.cyclonedx.json']['sha256'],'sbom_component_count':1}
        coverage_artifact={'id':99,'name':'l1-control-coverage','verified_zip_sha256':'c'*64}
        return run,report,declaration,bundles,paths,coverage_artifact

    def verify(self, args, baseline_run=None):
        return verify_bundle(*args[:5], verified_at='2026-09-17T10:06:00Z',
                             coverage_artifact=args[5], baseline_run=baseline_run)

    def test_all_five_images_verified_and_projected(self):
        with tempfile.TemporaryDirectory() as temp:
            args=self.bundle(Path(temp)); trusts=self.verify(args)
        self.assertEqual({'vulnerability_scan','sbom'},set(trusts))
        for trust in trusts.values():
            self.assertEqual('integrity_verified',trust['effective_level'])
            self.assertEqual(5,len(trust['capture']['observations']['container_images']))
            self.assertEqual(35,len(trust['capture']['subjects']))
            self.assertFalse(trust['capture']['observations']['independent_attestation'])
            Draft202012Validator(json.loads((ROOT/'schemas/evidence-trust-record.schema.json').read_text())).validate(trust)
            checks={check['id']:check['result'] for check in trust['checks']}
            self.assertEqual('pass',checks['baseline_ref_resolved'])
            self.assertEqual('pass',checks['custody_recorded'])
            self.assertEqual(6,len(trust['capture']['custody_record']['raw_artifacts']))
        vulnerability=project_result({'evidence_type':'vulnerability_scan','trust':trusts['vulnerability_scan']},ROOT/'status/fake.json')
        sbom=project_result({'evidence_type':'sbom','trust':trusts['sbom']},ROOT/'status/fake.json')
        self.assertEqual(5,len(vulnerability['container_images']))
        self.assertEqual(5,len(sbom['container_images']))
        self.assertEqual(5,sbom['component_count'])
        self.assertEqual('CycloneDX',sbom['format']['name'])
        freshness=next(c for c in trusts['sbom']['checks'] if c['id']=='freshness_evaluated')
        self.assertEqual('pass',freshness['result'])

    def test_complete_checks_advance_only_after_replay_evaluation(self):
        from lib.result_ledger import apply_replay_assessment
        with tempfile.TemporaryDirectory() as temp:
            trusts=self.verify(self.bundle(Path(temp)))
        for trust in trusts.values():
            self.assertEqual('integrity_verified',trust['effective_level'])
            assessed=apply_replay_assessment(trust,[])
            assessed['effective_level']=promote_effective_level(assessed['effective_level'],assessed['checks'])
            self.assertEqual('provenance_verified',assessed['effective_level'])

    def test_baseline_and_custody_tampering_do_not_advance_level(self):
        from lib.result_ledger import apply_replay_assessment
        with tempfile.TemporaryDirectory() as temp:
            args=self.bundle(Path(temp))
            args[0]['referenced_workflows']=[]
            trusts=self.verify(args)
        for trust in trusts.values():
            checks={check['id']:check['result'] for check in trust['checks']}
            self.assertEqual('fail',checks['baseline_ref_resolved'])
            assessed=apply_replay_assessment(trust,[])
            self.assertEqual('integrity_verified',assessed['effective_level'])

    def test_same_commit_successful_mainline_baseline_run_can_bind_evidence(self):
        from lib.result_ledger import apply_replay_assessment
        with tempfile.TemporaryDirectory() as temp:
            args=self.bundle(Path(temp))
            producer=args[0]
            workflow_refs=deepcopy(producer['referenced_workflows'])
            producer['referenced_workflows']=[]
            baseline_run={
                'id':456,'run_attempt':1,'path':'.github/workflows/devsecops-baseline.yml',
                'event':'push','head_branch':'main','head_sha':producer['head_sha'],
                'status':'completed','conclusion':'success','head_repository':{'id':9},
                'html_url':'https://github.com/joku-dev/ha-CPsWMS/actions/runs/456',
                'referenced_workflows':workflow_refs,
            }
            trusts=self.verify(args,baseline_run=baseline_run)
        for trust in trusts.values():
            baseline=trust['capture']['observations']['baseline_resolution']
            checks={check['id']:check['result'] for check in trust['checks']}
            self.assertEqual('456',baseline['baseline_run']['run_id'])
            self.assertEqual('pass',checks['baseline_ref_resolved'])
            baseline_check=next(check for check in trust['checks'] if check['id']=='baseline_ref_resolved')
            self.assertIn('baseline_run.head_sha',baseline_check['evidence_refs'])
            assessed=apply_replay_assessment(trust,[])
            assessed['effective_level']=promote_effective_level(assessed['effective_level'],assessed['checks'])
            self.assertEqual('provenance_verified',assessed['effective_level'])

    def test_paired_baseline_requires_same_commit_successful_mainline_run(self):
        with tempfile.TemporaryDirectory() as temp:
            args=self.bundle(Path(temp))
            producer=args[0]
            refs=deepcopy(producer['referenced_workflows'])
            producer['referenced_workflows']=[]
            invalid_runs=[
                {'id':1,'path':'.github/workflows/devsecops-baseline.yml','event':'push','head_branch':'main',
                 'head_sha':'f'*40,'status':'completed','conclusion':'success','head_repository':{'id':9},'referenced_workflows':refs},
                {'id':2,'path':'.github/workflows/devsecops-baseline.yml','event':'workflow_dispatch','head_branch':'main',
                 'head_sha':producer['head_sha'],'status':'completed','conclusion':'success','head_repository':{'id':9},'referenced_workflows':refs},
                {'id':3,'path':'.github/workflows/devsecops-baseline.yml','event':'push','head_branch':'main',
                 'head_sha':producer['head_sha'],'status':'completed','conclusion':'failure','head_repository':{'id':9},'referenced_workflows':refs},
                {'id':4,'path':'.github/workflows/devsecops-baseline.yml','event':'push','head_branch':'main',
                 'head_sha':producer['head_sha'],'status':'completed','conclusion':'success','head_repository':{'id':10},'referenced_workflows':refs},
            ]
            for baseline_run in invalid_runs:
                trusts=self.verify(args,baseline_run=baseline_run)
                for trust in trusts.values():
                    checks={check['id']:check['result'] for check in trust['checks']}
                    self.assertEqual('fail',checks['baseline_ref_resolved'])

    def test_normalized_custody_digest_is_recomputed(self):
        from lib.result_ledger import apply_replay_assessment
        with tempfile.TemporaryDirectory() as temp:
            args=self.bundle(Path(temp));trust=self.verify(args)['sbom']
            tampered=deepcopy(trust['capture']['custody_record'])
            tampered['normalized_digest']='0'*64
            subject_paths={service.replace('-', '_')+'_'+name.replace('.', '_').replace('-', '_'):
                           args[4][service]/name for service in SERVICES for name in SBOM_NAMES}
            checked=verify_trust_capture(trust,repository_id='joku-dev/ha-CPsWMS',commit_id='a'*40,
                run_id='123',artifact_name='l1-control-coverage',subject_paths=subject_paths,
                verified_at='2026-09-17T10:06:00Z',
                freshness_policy=load_freshness_policy(ROOT/'model/evidence/evidence-freshness-policies.yaml','freshness-sbom-subject-bound'),
                produced_at='2026-09-17T10:02:00Z',freshness_subject_bound=True,
                baseline={'ref':'refs/tags/l1-baseline-v1.1.3','sha':'b'*40},baseline_ref='l1-baseline-v1.1.3',
                custody_record=tampered)
        checks={check['id']:check['result'] for check in checked['checks']}
        self.assertEqual('fail',checks['custody_recorded'])
        self.assertEqual('integrity_verified',apply_replay_assessment(checked,[])['effective_level'])

    def test_tampered_archive_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            args=self.bundle(Path(temp)); (args[4][SERVICES[0]]/'image.tar').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'digest mismatch'): self.verify(args)

    def test_tampered_or_wrongly_bound_sbom_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            args=self.bundle(Path(temp)); path=args[4][SERVICES[0]]/'sbom.cyclonedx.json'
            sbom=json.loads(path.read_text());sbom['metadata']['component']['properties'][0]['value']='sha256:'+'0'*64
            path.write_text(json.dumps(sbom))
            manifest=json.loads((args[4][SERVICES[0]]/'manifest.json').read_text())
            manifest['files']['sbom.cyclonedx.json']={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size}
            (args[4][SERVICES[0]]/'manifest.json').write_text(json.dumps(manifest))
            args[3][SERVICES[0]][0]['manifest.json']=json.dumps(manifest).encode()
            args[2]['images'][SERVICES[0]]['sbom_sha256']=manifest['files']['sbom.cyclonedx.json']['sha256']
            with self.assertRaisesRegex(ValueError,'SBOM format, contents or image binding'): self.verify(args)

    def test_archive_config_and_layer_must_match(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'image.tar'; identity=image_tar(path)
            with self.assertRaisesRegex(ValueError,'config'):verify_docker_archive(path,'sha256:'+'0'*64)
            image_tar(path,corrupt_layer=True)
            with self.assertRaisesRegex(ValueError,'layer'):verify_docker_archive(path,identity)

    def test_missing_image_or_wrong_declaration_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            args=self.bundle(Path(temp));args[2]['images'].pop(SERVICES[0])
            with self.assertRaisesRegex(ValueError,'Incomplete'):self.verify(args)

    def test_wrong_attempt_in_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            args=self.bundle(Path(temp));raw=args[3][SERVICES[0]][0]
            manifest=json.loads(raw['manifest.json']);manifest['context']['attempt']='2';raw['manifest.json']=json.dumps(manifest).encode()
            with self.assertRaisesRegex(ValueError,'context'):self.verify(args)

    def test_manual_and_pr_runs_not_official(self):
        with tempfile.TemporaryDirectory() as temp:
            args=self.bundle(Path(temp))
            for event in ('pull_request','workflow_dispatch'):
                args[0]['event']=event
                with self.assertRaisesRegex(ValueError,'main push'):self.verify(args)

    def test_artifact_authoritative_binding_and_duplicates(self):
        with tempfile.TemporaryDirectory() as temp:
            args=self.bundle(Path(temp));a=args[3][SERVICES[0]][1]
            with self.assertRaisesRegex(ValueError,'exactly one'):bind_artifact([a,a],a['name'],args[0])
            a=deepcopy(a);a['workflow_run']['head_sha']='wrong'
            with self.assertRaisesRegex(ValueError,'binding'):bind_artifact([a],a['name'],args[0])

    def test_expired_freshness_does_not_become_new_when_rehashed(self):
        with tempfile.TemporaryDirectory() as temp:
            args=self.bundle(Path(temp));trust=verify_bundle(*args[:5],verified_at='2026-09-19T10:06:00Z',
                coverage_artifact=args[5])['vulnerability_scan']
        check=next(c for c in trust['checks'] if c['id']=='freshness_evaluated')
        self.assertEqual('fail',check['result'])

    def test_zip_selection_does_not_extract_untrusted_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);archive=root/'x.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr('../escape','bad');z.writestr('subject.json','{}')
            extract_selected(archive,root/'out',['subject.json'])
            self.assertFalse((root/'escape').exists())
            self.assertEqual('{}',(root/'out/subject.json').read_text())

    def test_replay_history_is_scoped_by_evidence_type(self):
        snapshots=[{'trust':{'capture':{'evidence_type':'vulnerability_scan'}}},
                   {'trust':{'capture':{'evidence_type':'sbom'}}}]
        self.assertEqual([snapshots[1]],prior_for_evidence_type(snapshots,'sbom'))

if __name__=='__main__':unittest.main()
