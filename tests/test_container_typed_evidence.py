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
from lib.container_typed_evidence import PROFILE, SERVICES, NAMES, verify_bundle, verify_docker_archive
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
             'created_at':'2026-09-17T10:00:00Z','updated_at':'2026-09-17T10:05:00Z'}
        context={'repository':run['repository']['full_name'],'commit':run['head_sha'],'run_id':'123','attempt':'1','event':'push'}
        report={'context':context,'report_type':'l1-measured-evidence-coverage','evidence_errors':{},
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
        return run,report,declaration,bundles,paths

    def verify(self, args):
        return verify_bundle(*args, verified_at='2026-09-17T10:06:00Z')

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
        vulnerability=project_result({'evidence_type':'vulnerability_scan','trust':trusts['vulnerability_scan']},ROOT/'status/fake.json')
        sbom=project_result({'evidence_type':'sbom','trust':trusts['sbom']},ROOT/'status/fake.json')
        self.assertEqual(5,len(vulnerability['container_images']))
        self.assertEqual(5,len(sbom['container_images']))
        self.assertEqual(5,sbom['component_count'])
        self.assertEqual('CycloneDX',sbom['format']['name'])
        freshness=next(c for c in trusts['sbom']['checks'] if c['id']=='freshness_evaluated')
        self.assertEqual('pass',freshness['result'])

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
            args=self.bundle(Path(temp));trust=verify_bundle(*args,verified_at='2026-09-19T10:06:00Z')['vulnerability_scan']
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
