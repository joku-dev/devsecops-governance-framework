"""Synthetic native responses and real files/OPA; no live provider acceptance."""
from copy import deepcopy
import base64
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.consumer_intake_store import Store as LegacyStore, atomic_json, file_digest
from lib.portable.contracts import canonical_digest, execution_key
from lib.portable.runtime import baseline, evaluate, prepare_evidence, source_digest
from lib.portable_intake.bundle import export_bundle, unpack, verify_bundle
from lib.portable_intake.store import Store, migrate_legacy
from lib.portable_intake.transport import Reader, capture
from test_portable_runtime import context, OPA, SHA
import governance_runtime
import intake_portable_evidence

AT='2026-11-15T12:10:00Z'
CONFIG=b'on:\n  push:\n    branches: [trunk]\njobs:\n  portable:\n    name: approved synthetic pinned pipeline fixture\n'


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        self.checkout=self.root/'application';self.checkout.mkdir()
        self.assessment=self.root/'assessment';self.assessment.mkdir()
        self.bundle=self.root/'bundle'
        self.ctx=context();self.ctx['synthetic']=False
        self.ctx['ci']['instance']=self.ctx['scm']['instance']
        self.policy={'schema_version':'2.0.0','scm':self.ctx['scm'],'ci':self.ctx['ci'],
                     'baseline_id':baseline()[1]['id'],'baseline_digest':baseline()[1]['digest'],
                     'runtime_source_digest':source_digest(),'max_age_seconds':86400,'future_skew_seconds':0,
                     'max_severity':'high','producer_config_sha256':hashlib.sha256(CONFIG).hexdigest(),
                     'transport':{'instance':self.ctx['ci']['instance'],'api_url':'https://scm.example',
                         'workflow_path':'.github/workflows/portable.yml','job_name':'portable',
                         'logical_job_id':self.ctx['ci']['job_id'],'upload_step_name':'Upload bundle',
                         'artifact_name':'axiom-portable-pipeline-l1','configuration_path':'.gitlab-ci.yml'}}
        (self.checkout/'artifact.bin').write_bytes(b'synthetic application bytes')
        artifact=file_digest(self.checkout/'artifact.bin')
        atomic_json(self.checkout/'sbom.json',{'bomFormat':'CycloneDX','specVersion':'1.5','components':[],
             'metadata':{'component':{'type':'application','name':'unit-fixture','hashes':[{'alg':'SHA-256','content':artifact}]}}})
        atomic_json(self.checkout/'scan.json',{'scanner':'synthetic-unit-scanner','max_severity':'none',
                                            'findings':[],'artifact_sha256':artifact})
        self.rebuild()

    def rebuild(self):
        payload,subjects=prepare_evidence(self.ctx,self.checkout,'artifact.bin','sbom.json','scan.json')
        self.result=evaluate(self.ctx,payload,subjects,opa=OPA,at='2026-11-15T12:00:00Z')
        for name,value in [('context.json',self.ctx),('result.json',self.result),('evaluation-input.json',payload)]:
            atomic_json(self.assessment/name,value)
        if self.bundle.exists():
            import shutil
            shutil.rmtree(self.bundle)
        export_bundle(self.assessment,self.checkout,self.bundle)

    def verify(self,**kwargs):
        return verify_bundle(self.bundle,self.policy,opa=OPA,at=kwargs.pop('at',AT),**kwargs)

    def rewrite(self,filename,mutate):
        value=json.loads((self.bundle/filename).read_text());mutate(value)
        atomic_json(self.bundle/filename,value)
        if filename!='bundle.json':
            manifest=json.loads((self.bundle/'bundle.json').read_text())
            row=next(row for row in manifest['files'] if row['path']==filename)
            row.update(sha256=file_digest(self.bundle/filename),size=(self.bundle/filename).stat().st_size)
            atomic_json(self.bundle/'bundle.json',manifest)

    def test_local_integrity_does_not_claim_native_provenance(self):
        receipt=self.verify()
        self.assertEqual(receipt['trust'],'integrity_verified')
        self.assertEqual(receipt['decision'],'pass')
        self.assertFalse(receipt['candidate_eligible'])
        self.assertFalse(receipt['official_acceptance'])
        self.assertIsNone(receipt['blocks_merge'])

    def envelope(self):
        payload=json.loads((self.bundle/'evaluation-input.json').read_text())
        self.rewrite('evaluation-input.json',lambda value:(value.clear(),value.update(
            payload=payload,subjects=deepcopy(self.result['subjects']))))

    def test_runtime_cli_bundle_and_verifier_preserve_the_same_input_bytes(self):
        # Only native API acquisition is synthetic. Run the actual CLI, files,
        # pinned OPA, exporter, ZIP unpacking and common verifier end to end.
        profile=self.root/'profile.json';atomic_json(profile,{})
        assessment=self.root/'cli-assessment';bundle=self.root/'cli-bundle'
        ctx=deepcopy(self.ctx);ctx['synthetic']=True
        for command in (['init','-q'],['add','.'],['-c','user.name=Fixture',
                        '-c','user.email=fixture@example.invalid','commit','-qm','Synthetic CLI fixture']):
            subprocess.run(['git','-C',str(self.checkout),*command],check=True,capture_output=True)
        revision=subprocess.check_output(['git','-C',str(self.checkout),'rev-parse','HEAD'],text=True).strip()
        ctx['revision'].update(tested=revision,source=revision)
        with patch.object(governance_runtime,'collect_context',return_value=ctx):
            code=governance_runtime.main(['run','--ci','github-actions','--profile',str(profile),
                '--checkout',str(self.checkout),'--artifact','artifact.bin','--sbom','sbom.json',
                '--scan','scan.json','--output-directory',str(assessment),'--opa',str(OPA),
                '--mode','report-only','--at','2026-11-15T12:00:00Z'])
        self.assertEqual(code,0,(assessment/'diagnostics.json').read_text())
        self.assertEqual(intake_portable_evidence.main(['bundle','--assessment',str(assessment),
            '--checkout',str(self.checkout),'--destination',str(bundle)]),0)
        self.assertEqual((assessment/'evaluation-input.json').read_bytes(),
                         (bundle/'evaluation-input.json').read_bytes())
        unpacked=unpack(bundle.with_suffix('.zip'),self.root/'cli-unpacked')
        receipt=verify_bundle(unpacked,self.policy,opa=OPA,at=AT)
        self.assertEqual(receipt['execution'],'complete')
        self.assertEqual(receipt['trust'],'integrity_verified')
        self.assertFalse(receipt['candidate_eligible'])

    def test_cli_envelope_and_retained_flat_payload_have_identical_receipts_except_digest(self):
        flat=self.verify();self.envelope();enveloped=self.verify()
        self.assertNotEqual(flat.pop('bundle_digest'),enveloped.pop('bundle_digest'))
        self.assertEqual(flat,enveloped)

    def test_resigned_envelope_cannot_replace_subject_bindings(self):
        self.envelope()
        for change in (lambda value:value['subjects'].reverse(),
                       lambda value:value['subjects'][0].update(sha256='0'*64),
                       lambda value:value.pop('subjects'),
                       lambda value:value.update(untrusted=True),
                       lambda value:value.update(payload=[])):
            original=(self.bundle/'evaluation-input.json').read_bytes()
            self.rewrite('evaluation-input.json',change)
            with self.assertRaisesRegex(ValueError,'evaluation_input_subject_binding_mismatch'):
                self.verify()
            (self.bundle/'evaluation-input.json').write_bytes(original)
            self.rewrite('evaluation-input.json',lambda value:None)

    def test_resigned_envelope_payload_is_still_derived_from_actual_files(self):
        self.envelope()
        self.rewrite('evaluation-input.json',lambda value:value['payload']['repository'].update(
            direct_push_allowed=True))
        with self.assertRaisesRegex(ValueError,'does_not_match_files'):self.verify()

    def test_non_object_input_is_rejected(self):
        (self.bundle/'evaluation-input.json').write_text('[]')
        manifest=json.loads((self.bundle/'bundle.json').read_text())
        row=next(row for row in manifest['files'] if row['role']=='input')
        row.update(sha256=file_digest(self.bundle/'evaluation-input.json'),size=2)
        atomic_json(self.bundle/'bundle.json',manifest)
        with self.assertRaisesRegex(ValueError,'invalid_evaluation_input'):self.verify()

    def test_declared_provenance_cannot_be_added_to_manifest(self):
        self.rewrite('bundle.json',lambda m:m.update(native_verified=True))
        with self.assertRaises(ValueError):self.verify()

    def test_tampered_member_rejected_before_assessment(self):
        (self.bundle/'subjects/artifact/artifact.bin').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError,'digest_mismatch'):self.verify()

    def test_resigned_forged_verdict_fails_real_opa_recomputation(self):
        self.rewrite('result.json',lambda r:r.update(decision='fail'))
        with self.assertRaisesRegex(ValueError,'recomputation'):self.verify()

    def test_resigned_forged_scan_facts_fail_file_derivation(self):
        self.rewrite('evaluation-input.json',lambda r:r['repository'].update(direct_push_allowed=True))
        with self.assertRaisesRegex(ValueError,'does_not_match_files'):self.verify()

    def test_wrong_policy_revision_or_baseline_cannot_pass(self):
        for name in ('baseline_digest','runtime_source_digest'):
            old=self.policy[name];self.policy[name]='0'*64
            with self.assertRaises(ValueError):self.verify()
            self.policy[name]=old

    def test_provider_instance_namespace_is_enforced(self):
        self.policy['scm']=deepcopy(self.policy['scm']);self.policy['scm']['instance']='https://other.example'
        with self.assertRaisesRegex(ValueError,'binding'):self.verify()

    def test_duplicate_and_conflicting_replay_are_explicit(self):
        first=self.verify();key=first['execution_key']
        self.assertEqual(self.verify(history={key:first['bundle_digest']})['replay'],'duplicate')
        receipt=self.verify(history={key:'0'*64})
        self.assertEqual(receipt['replay'],'conflict');self.assertFalse(receipt['candidate_eligible'])

    def test_explicit_clock_rejects_stale_future_and_naive_time(self):
        self.assertEqual(self.verify(at='2026-11-17T12:10:00Z')['freshness'],'stale_or_future')
        self.assertEqual(self.verify(at='2026-11-15T11:59:00Z')['freshness'],'stale_or_future')
        with self.assertRaises(ValueError):self.verify(at='2026-11-15T12:10:00')

    def test_private_policy_cannot_extend_central_governance_freshness_limit(self):
        self.policy['max_age_seconds']=86401
        with self.assertRaisesRegex(ValueError,'unsupported_verification_policy'):self.verify()

    def test_future_clock_tolerance_cannot_relax_the_central_policy(self):
        self.policy['future_skew_seconds']=1
        with self.assertRaises(ValueError):self.verify()

    def test_ambiguous_or_unmanifested_members_rejected(self):
        (self.bundle/'unlisted.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'file_set'):self.verify()
        (self.bundle/'unlisted.json').unlink()
        self.rewrite('bundle.json',lambda m:m['files'].append(deepcopy(m['files'][0])))
        with self.assertRaises(ValueError):self.verify()

    def test_paths_symlinks_and_duplicate_json_keys_rejected(self):
        target=self.bundle/'subjects/artifact/artifact.bin';target.unlink();target.symlink_to(self.checkout/'artifact.bin')
        with self.assertRaises(ValueError):self.verify()
        target.unlink();target.write_bytes((self.checkout/'artifact.bin').read_bytes())
        (self.bundle/'bundle.json').write_text('{"schema_version":"2.0.0","schema_version":"2.0.0"}')
        with self.assertRaisesRegex(ValueError,'duplicate_json'):self.verify()

    def test_safe_archive_and_export_freshness(self):
        with self.assertRaises(FileExistsError):export_bundle(self.assessment,self.checkout,self.bundle)
        for member in ('../escape','/absolute','a/../../escape'):
            archive=self.root/'bad.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr(member,'bad')
            with tempfile.TemporaryDirectory(dir=self.root) as d:
                with self.assertRaises(ValueError):unpack(archive,Path(d)/'out')

    def native(self,provider='github-actions',*,unsafe_archive=False):
        if provider!=self.ctx['ci']['provider']:
            self.ctx=context(provider);self.ctx['synthetic']=False;self.ctx['ci']['instance']=self.ctx['scm']['instance']
            self.policy['scm']=self.ctx['scm'];self.policy['ci']=self.ctx['ci']
            self.policy['transport']['instance']=self.ctx['ci']['instance']
            self.rebuild()
        archive=self.root/'native.zip'
        with zipfile.ZipFile(archive,'w') as z:
            for path in self.bundle.rglob('*'):
                if path.is_file():z.write(path,str(path.relative_to(self.bundle)))
            if unsafe_archive:z.writestr('../escape','unsafe synthetic archive member')
        blob=archive.read_bytes()
        ctx=self.ctx;route='/repos/'+ctx['scm']['path']
        job={'id':987,'name':'portable','status':'completed','started_at':'2026-11-15T11:59:00Z',
             'completed_at':'2026-11-15T12:05:00Z','steps':[{'name':'Upload bundle','conclusion':'success'}]}
        artifact={'id':123,'name':'axiom-portable-pipeline-l1','expired':False,'created_at':'2026-11-15T12:01:00Z',
             'workflow_run':{'id':42,'repository_id':42,'head_sha':SHA},'digest':'sha256:'+hashlib.sha256(blob).hexdigest()}
        responses={route:{'id':42,'full_name':ctx['scm']['path'],'default_branch':'trunk'},
             route+'/branches/trunk':{'name':'trunk','protected':True},
             route+'/branches/trunk/protection':{'enforce_admins':{'enabled':True},'required_pull_request_reviews':{
                 'required_approving_review_count':1,'bypass_pull_request_allowances':{'users':[],'teams':[],'apps':[]}}},
             route+'/actions/runs/42/attempts/1':{'id':42,'run_attempt':1,'status':'completed','repository':{'id':42},
                 'path':'.github/workflows/portable.yml','head_sha':SHA,'event':'push','head_branch':'trunk'},
             route+'/contents/.github/workflows/portable.yml?ref='+SHA:{'content':base64.b64encode(CONFIG).decode()}}
        if provider=='gitlab-ci':
            responses={'/projects/42':{'id':42,'path_with_namespace':ctx['scm']['path'],'default_branch':'trunk'},
                '/projects/42/repository/branches/trunk':{'name':'trunk','protected':True},
                '/projects/42/protected_branches?per_page=100&page=1':[{'id':1,'name':'trunk','push_access_levels':[{'access_level':0}]}],
                '/projects/42/approval_rules?per_page=100&page=1':[{'rule_type':'regular','approvals_required':1,'protected_branches':[]}],
                '/projects/42/pipelines/42':{'id':42,'project_id':42,'sha':SHA,'status':'failed','source':'push','ref':'trunk'},
                '/projects/42/jobs/job-42':{'id':'job-42','pipeline':{'id':42,'project_id':42,'sha':SHA},'commit':{'id':SHA},'name':'portable','status':'failed',
                                         'tag':False,
                                         'started_at':'2026-11-15T11:59:00Z','finished_at':'2026-11-15T12:05:00Z'},
                '/projects/42/repository/files/.gitlab-ci.yml?ref='+SHA:{'content':base64.b64encode(CONFIG).decode()}}
        if provider=='bamboo':
            responses={'/rest/api/latest/result/PROJ-PLAN-42.json?expand=artifacts':{
                'key':'PROJ-PLAN-42','lifeCycleState':'Finished','vcsRevisionKey':SHA,
                'artifacts':{'artifact':[{'name':'axiom-portable-pipeline-l1','link':{'href':'https://scm.example/artifact.zip'}}]}}}
        class FakeReader:
            base='https://scm.example'
            def get(inner,path):return deepcopy(responses[path])
            def pages(inner,path,field):return deepcopy([job] if field=='jobs' else [artifact])
            def download(inner,path,destination):Path(destination).write_bytes(blob)
        return FakeReader(),responses,job,artifact

    def test_native_github_and_gitlab_use_same_verifier_and_preserve_negative_result(self):
        scan=json.loads((self.checkout/'scan.json').read_text())
        scan.update(max_severity='critical',findings=[{'id':'synthetic-critical','severity':'critical'}])
        atomic_json(self.checkout/'scan.json',scan);self.rebuild()
        for provider in ('github-actions','gitlab-ci'):
            reader,_,_,_=self.native(provider)
            observation,_=capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)
            receipt=self.verify(observation=observation)
            self.assertEqual(receipt['trust'],'provenance_verified')
            self.assertTrue(receipt['candidate_eligible'])
            self.assertEqual(receipt['decision'],'fail')
            self.assertEqual(receipt['producer']['ci']['provider'],provider)

    def mr_native(self,mode):
        self.ctx=context('gitlab-ci');self.ctx['synthetic']=False
        self.ctx['ci']['instance']=self.ctx['scm']['instance'];self.ctx['ci']['event']='pull_request'
        self.ctx['revision'].update(mode=mode,branch='feature',source=SHA if mode=='source-head' else 'b'*40,
                                    target=None if mode=='source-head' else 'c'*40)
        self.ctx['change_request']={'kind':'merge_request','id':'5','source_repository':'42','target_repository':'42',
                                   'source_branch':'feature','target_branch':'trunk'}
        self.policy['scm']=self.ctx['scm'];self.policy['ci']=self.ctx['ci'];self.policy['transport']['instance']=self.ctx['ci']['instance']
        self.rebuild();reader,responses,_,_=self.native('gitlab-ci')
        responses['/projects/42/pipelines/42'].update(source='merge_request_event',ref='refs/merge-requests/5/'+('head' if mode=='source-head' else 'merge'))
        responses['/projects/42/merge_requests/5']={'iid':5,'source_project_id':42,'target_project_id':42,
            'source_branch':'feature','target_branch':'trunk','sha':self.ctx['revision']['source']}
        responses['/projects/42/merge_requests/5/pipelines?per_page=100&page=1']=[{'id':42,'sha':SHA}]
        responses['/projects/42/repository/commits/'+SHA]={'id':SHA,'parent_ids':['b'*40,'c'*40]}
        return reader,responses

    def test_gitlab_source_head_and_merge_parent_bindings_use_native_metadata(self):
        for mode in ('source-head','merge-result'):
            reader,_=self.mr_native(mode)
            observation,_=capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)
            self.assertTrue(observation.attempt_bound)
            self.assertEqual(self.verify(observation=observation)['trust'],'provenance_verified')

    def test_native_mr_observation_cannot_be_relabelled_as_mainline(self):
        _,native_responses=self.mr_native('merge-result');requested=deepcopy(self.ctx)
        self.ctx['ci']['event']='push';self.ctx['change_request']=None
        self.ctx['revision'].update(mode='branch',branch='trunk',source=SHA,target=None)
        self.rebuild();reader,responses,_,_=self.native('gitlab-ci');responses.update(native_responses)
        observation,_=capture(requested,self.policy,reader,self.root/'download.zip',at=AT)
        self.assertTrue(observation.attempt_bound)  # Genuine MR proof, different declared bundle context.
        receipt=self.verify(observation=observation)
        self.assertEqual(receipt['trust'],'integrity_verified');self.assertFalse(receipt['candidate_eligible'])

    def test_wrong_mr_pipeline_or_merge_parent_prevents_native_promotion(self):
        for field in ('pipeline','parents'):
            reader,responses=self.mr_native('merge-result')
            if field=='pipeline':responses['/projects/42/merge_requests/5/pipelines?per_page=100&page=1']=[{'id':99,'sha':SHA}]
            else:responses['/projects/42/repository/commits/'+SHA]['parent_ids']=['b'*40,'d'*40]
            observation,_=capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)
            self.assertEqual(self.verify(observation=observation)['trust'],'integrity_verified')

    def test_branch_source_revision_cannot_be_fabricated(self):
        self.ctx['revision']['source']='b'*40;self.rebuild();reader,_,_,_=self.native()
        observation,_=capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)
        self.assertEqual(self.verify(observation=observation)['trust'],'integrity_verified')

    def test_github_push_with_ambiguous_tag_branch_trigger_cannot_promote(self):
        reader,responses,_,_=self.native()
        broad=b'on: [push]\njobs: {}\n'
        responses['/repos/group/repo/contents/.github/workflows/portable.yml?ref='+SHA]['content']=base64.b64encode(broad).decode()
        self.policy['producer_config_sha256']=hashlib.sha256(broad).hexdigest()
        observation,_=capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)
        self.assertEqual(self.verify(observation=observation)['trust'],'integrity_verified')

    def test_gitlab_tag_cannot_supply_branch_provenance(self):
        reader,responses,_,_=self.native('gitlab-ci');responses['/projects/42/jobs/job-42']['tag']=True
        observation,_=capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)
        self.assertEqual(self.verify(observation=observation)['trust'],'integrity_verified')

    def test_native_commit_config_attempt_and_artifact_mismatches_do_not_promote(self):
        reader,responses,_,artifact=self.native()
        responses['/repos/group/repo/actions/runs/42/attempts/1']['head_sha']='b'*40
        with self.assertRaisesRegex(ValueError,'artifact_binding'):capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)
        reader,_,_,_=self.native();self.policy['producer_config_sha256']='0'*64
        observation,_=capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)
        self.assertEqual(self.verify(observation=observation)['trust'],'integrity_verified')

    def test_native_collection_rejects_unapproved_repository_before_any_request(self):
        reader,_,_,_=self.native()
        requested=deepcopy(self.ctx);requested['scm']['native_id']='different-repository'
        with self.assertRaisesRegex(ValueError,'outside_intake_policy'):
            capture(requested,self.policy,reader,self.root/'download.zip',at=AT)

    def test_native_github_pr_head_is_not_treated_as_verified_merge_provenance(self):
        self.ctx['ci']['event']='pull_request';self.ctx['revision']['mode']='source-head'
        self.ctx['change_request']={'kind':'pull_request','id':'5','source_repository':'42','target_repository':'42',
            'source_branch':'trunk','target_branch':'main'}
        self.rebuild();reader,responses,_,_=self.native()
        responses['/repos/group/repo/actions/runs/42/attempts/1']['event']='pull_request'
        observation,_=capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)
        self.assertEqual(self.verify(observation=observation)['trust'],'integrity_verified')

    def test_native_archive_digest_tampering_is_rejected(self):
        reader,_,_,artifact=self.native();artifact['digest']='sha256:'+'0'*64
        with self.assertRaisesRegex(ValueError,'archive_digest'):
            capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)

    def test_consumer_cannot_forge_protection_facts_even_with_genuine_native_run(self):
        reader,responses,_,_=self.native()
        responses['/repos/group/repo/branches/trunk']['protected']=False
        observation,_=capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)
        receipt=self.verify(observation=observation)
        self.assertEqual(receipt['trust'],'integrity_verified');self.assertFalse(receipt['candidate_eligible'])

    def test_synthetic_native_fixture_cannot_earn_provenance(self):
        self.ctx['synthetic']=True;self.rebuild();reader,_,_,_=self.native()
        observation,_=capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)
        self.assertEqual(self.verify(observation=observation)['trust'],'integrity_verified')

    def test_native_observation_is_bound_to_the_exact_downloaded_manifest(self):
        reader,_,_,_=self.native();observation,_=capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)
        self.rewrite('bundle.json',lambda manifest:manifest['files'].reverse())
        receipt=self.verify(observation=observation)
        self.assertEqual(receipt['trust'],'integrity_verified');self.assertFalse(receipt['candidate_eligible'])

    def test_native_completion_time_cannot_be_renewed_by_editing_result_time(self):
        from dataclasses import replace
        reader,_,_,_=self.native();observation,_=capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)
        observation=replace(observation,started_at='2026-11-01T11:59:00Z',completed_at='2026-11-01T12:05:00Z')
        self.assertEqual(self.verify(observation=observation)['trust'],'integrity_verified')

    def test_bamboo_transport_collects_bytes_but_reports_unresolved_spec_closure(self):
        reader,_,_,_=self.native('bamboo')
        observation,_=capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)
        self.assertEqual(self.verify(observation=observation)['trust'],'integrity_verified')

    def test_persistent_replay_is_atomic_and_never_reclassifies_history(self):
        reader,_,_,_=self.native();observation,_=capture(self.ctx,self.policy,reader,self.root/'download.zip',at=AT)
        receipt=self.verify(observation=observation)
        store=Store(self.root/'state');self.addCleanup(store.close)
        self.assertTrue(store.record(receipt)[1])
        original,inserted=store.record({**receipt,'trust':'unverified','candidate_eligible':False})
        self.assertFalse(inserted);self.assertEqual(original,receipt)
        with self.assertRaisesRegex(ValueError,'conflict'):store.record({**receipt,'bundle_digest':'0'*64})

    def test_local_cli_records_replay_and_keeps_mac_vm_roots_separate(self):
        import contextlib,io,importlib.util
        from unittest.mock import patch
        spec=importlib.util.spec_from_file_location('portable_intake_cli',ROOT/'scripts/intake_portable_evidence.py')
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        policy=self.root/'policy.json';atomic_json(policy,self.policy)
        arguments=['verify-local','--bundle',str(self.bundle),'--policy',str(policy),'--opa',str(OPA),'--at',AT]
        values=[]
        for name in ('mac','mac','vm'):
            output=io.StringIO()
            with contextlib.redirect_stdout(output),patch.object(cli,'require_storage'):
                self.assertEqual(cli.main([*arguments,'--root',str(self.root/name)]),0)
            values.append(json.loads(output.getvalue()))
        self.assertEqual([v['processing_replay'] for v in values],['new','duplicate','new'])
        self.assertTrue(values[0]['recorded']);self.assertFalse(values[1]['recorded'])
        self.assertEqual(values[0]['receipt']['trust'],'integrity_verified')

    def test_failed_native_verification_preserves_raw_archive_and_redacted_diagnostics(self):
        import importlib.util
        from unittest.mock import patch
        self.rewrite('result.json',lambda value:value.update(decision='fail'))
        reader,_,_,_=self.native()
        spec=importlib.util.spec_from_file_location('portable_failed_intake_cli',ROOT/'scripts/intake_portable_evidence.py')
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        policy=self.root/'policy.json';atomic_json(policy,self.policy)
        ctx=self.root/'requested-context.json';atomic_json(ctx,self.ctx)
        state=self.root/'native-state'
        with patch.object(cli,'Reader',return_value=reader),patch.object(cli,'require_storage'):
            with self.assertRaisesRegex(ValueError,'recomputation'):
                cli.main(['collect','--root',str(state),'--policy',str(policy),'--context',str(ctx),'--opa',str(OPA),'--at',AT])
        failures=list((state/'raw/failures').iterdir())
        self.assertEqual(len(failures),1)
        self.assertTrue((failures[0]/'artifact.zip').is_file())
        self.assertEqual(json.loads((failures[0]/'diagnostics.json').read_text())['diagnostics'],['bundle_verification_failed'])

    def test_failed_native_zip_extraction_also_preserves_original_bytes(self):
        import importlib.util
        from unittest.mock import patch
        reader,_,_,_=self.native(unsafe_archive=True)
        spec=importlib.util.spec_from_file_location('portable_bad_zip_cli',ROOT/'scripts/intake_portable_evidence.py')
        cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
        policy=self.root/'policy.json';atomic_json(policy,self.policy)
        ctx=self.root/'requested-context.json';atomic_json(ctx,self.ctx)
        state=self.root/'bad-zip-state'
        with patch.object(cli,'Reader',return_value=reader),patch.object(cli,'require_storage'):
            with self.assertRaisesRegex(ValueError,'Unsafe ZIP'):
                cli.main(['collect','--root',str(state),'--policy',str(policy),'--context',str(ctx),'--opa',str(OPA),'--at',AT])
        failure=next((state/'raw/failures').iterdir())
        self.assertTrue((failure/'artifact.zip').is_file())
        self.assertFalse((state/'escape').exists())

    def test_recorded_receipt_cannot_finish_another_queued_execution(self):
        store=Store(self.root/'state');self.addCleanup(store.close)
        other=deepcopy(self.ctx);other['ci']['job_id']='different-native-job'
        key=store.discover(other,at=1)
        with self.assertRaisesRegex(ValueError,'queue_receipt'):store.finish(key,self.verify())


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()

    def test_opaque_provider_and_instance_queue_keys_restart_and_bounded_retry(self):
        store=Store(self.root/'state')
        keys=[]
        for provider in ('github-actions','gitlab-ci','bamboo'):
            for instance in ('https://one.example','https://two.example'):
                ctx=context(provider);ctx['scm']['instance']=instance;ctx['ci']['instance']=instance
                keys.append(store.discover(ctx,at=100))
        self.assertEqual(len(set(keys)),6)
        job=store.claim(at=100);store.close();store=Store(self.root/'state');self.addCleanup(store.close)
        store.recover();self.assertEqual(store.counts(),{'queued':6})
        for count in range(4):store.fail(job['key'],'rate_limited',at=100,retryable=True,delay=60)
        self.assertEqual(store.counts(),{'held':1,'queued':5})

    def legacy(self):
        root=self.root/'legacy';store=LegacyStore(root)
        run={'id':42,'run_attempt':1,'status':'completed'}
        store.discover('group/repo',run)
        snapshot=b'{"historical":true,"trust":"unverified"}\n'
        (root/'raw').mkdir();(root/'raw/artifact.zip').write_bytes(b'historical artifact bytes')
        (root/'verified').mkdir();(root/'verified/snapshot.json').write_bytes(snapshot)
        store.put('http:/repos/group/repo/actions',{'etag':'fixed','data':[run]})
        store.put('poll_watermark','2026-11-14T12:00:00Z')
        with store.db:
            store.db.execute('INSERT INTO batches(id,base,state,manifest,commit_sha,pr,url) VALUES (?,?,?,?,?,?,?)',
                ('original-batch','a'*40,'open','[]','b'*40,123,'https://github.com/group/repo/pull/123'))
        store.close()
        mapping={'schema_version':2,'repositories':{'group/repo':{'scm':context()['scm'],
            'ci_provider':'github-actions','ci_instance':'https://ci.example','legacy_scope':'workflow-aggregate'}}}
        return root,mapping,snapshot

    def test_legacy_state_version_and_migration_preserve_all_bytes_and_remote_mapping(self):
        root,mapping,snapshot=self.legacy()
        original=sqlite3.connect(root/'queue.sqlite3')
        try:
            self.assertEqual(original.execute('PRAGMA user_version').fetchone()[0],1)
        finally:
            original.close()
        destination=migrate_legacy(root,mapping,self.root/'candidate')
        new=Store(destination);self.addCleanup(new.close)
        self.assertEqual(new.db.execute('PRAGMA user_version').fetchone()[0],2)
        self.assertEqual((destination/'verified/snapshot.json').read_bytes(),snapshot)
        self.assertEqual(new.db.execute('SELECT id,pr,url FROM batches').fetchone()[:],
                         ('original-batch',123,'https://github.com/group/repo/pull/123'))
        kinds=dict(new.db.execute('SELECT kind,count(*) FROM legacy_mapping GROUP BY kind'))
        self.assertEqual(kinds,{'job':1,'meta':2,'batches':1,'file':2})
        with self.assertRaises(ValueError):LegacyStore(destination)
        old=LegacyStore(root);self.assertEqual(len(old.jobs()),1);old.close()

    def test_ambiguous_and_partial_migration_stop_without_changing_source(self):
        root,mapping,_=self.legacy();mapping['repositories']={'other/repo':mapping['repositories']['group/repo']}
        with self.assertRaises(ValueError):migrate_legacy(root,mapping,self.root/'bad')
        self.assertFalse((self.root/'bad').exists())
        root_mapping={'schema_version':2,'repositories':{'group/repo':{'scm':context()['scm'],
            'ci_provider':'github-actions','ci_instance':'https://ci.example','legacy_scope':'workflow-aggregate'}}}
        def crash(stage):raise RuntimeError(stage)
        with self.assertRaises(RuntimeError):migrate_legacy(root,root_mapping,self.root/'partial',fault=crash)
        with self.assertRaises(ValueError):Store(self.root/'partial')
        old=LegacyStore(root);self.assertEqual(len(old.jobs()),1);old.close()
        migrate_legacy(root,root_mapping,self.root/'retry')

    def test_unknown_future_schema_is_rejected(self):
        root=self.root/'state';store=Store(root);store.db.execute('PRAGMA user_version=99');store.close()
        with self.assertRaises(ValueError):Store(root)

    def test_v2_backup_restore_preserves_migration_lineage_and_detects_tampering(self):
        from lib.portable_intake.store import backup_v2
        from lib.consumer_intake_store import verify_backup
        import shutil
        root,mapping,snapshot=self.legacy()
        candidate=migrate_legacy(root,mapping,self.root/'candidate')
        store=Store(candidate);backup_v2(store,self.root/'backup');store.close()
        verify_backup(self.root/'backup')
        shutil.copytree(self.root/'backup',self.root/'restored');(self.root/'restored/manifest.json').unlink()
        restored=Store(self.root/'restored');self.addCleanup(restored.close)
        self.assertEqual((self.root/'restored/verified/snapshot.json').read_bytes(),snapshot)
        self.assertEqual(restored.db.execute('SELECT count(*) FROM legacy_mapping').fetchone()[0],6)
        (self.root/'backup/migration.json').write_text('{}')
        with self.assertRaises(ValueError):verify_backup(self.root/'backup')

    def test_failure_after_database_step_still_requires_complete_migration_marker(self):
        root,mapping,_=self.legacy()
        def crash(stage):
            if stage=='database_migrated':raise RuntimeError('injected crash')
        with self.assertRaises(RuntimeError):migrate_legacy(root,mapping,self.root/'partial',fault=crash)
        with self.assertRaisesRegex(ValueError,'incomplete_state_migration'):Store(self.root/'partial')

    def test_legacy_restore_keeps_original_database_and_later_evidence_separate(self):
        from lib.portable_intake.store import backup_v2,restore_legacy
        root,mapping,snapshot=self.legacy()
        candidate=migrate_legacy(root,mapping,self.root/'candidate')
        (candidate/'raw/later-evidence.bin').write_bytes(b'later v2 evidence must remain available')
        store=Store(candidate);backup_v2(store,self.root/'backup');store.close()
        restored=restore_legacy(self.root/'backup',self.root/'legacy-restored')
        old=LegacyStore(restored);self.addCleanup(old.close)
        self.assertEqual(len(old.jobs()),1)
        self.assertEqual((restored/'verified/snapshot.json').read_bytes(),snapshot)
        self.assertFalse((restored/'raw/later-evidence.bin').exists())
        self.assertTrue((self.root/'backup/raw/later-evidence.bin').exists())

    def test_reader_budget_rejects_before_network_and_redacts_endpoint_errors(self):
        reader=Reader('https://api.example',budget=0)
        from lib.consumer_github import AccessFailure
        with self.assertRaises(AccessFailure):reader.get('/runs')
        with self.assertRaises(ValueError):Reader('http://api.example')

    def test_full_archive_copy_budget_is_reserved_before_acquisition(self):
        from unittest.mock import patch
        from lib.portable_intake.bundle import require_storage
        from lib.consumer_github import AccessFailure
        import shutil
        usage=shutil.disk_usage(self.root)
        with patch('lib.portable_intake.bundle.shutil.disk_usage',return_value=usage._replace(free=9*1024**3)):
            with self.assertRaisesRegex(AccessFailure,'storage_budget'):require_storage(self.root,{})
        with patch('lib.portable_intake.bundle.shutil.disk_usage',return_value=usage._replace(free=11*1024**3)):
            require_storage(self.root,{})
