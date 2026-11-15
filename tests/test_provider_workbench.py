"""Provider-shaped drafts and real private Git packets; no remote publication."""
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.providers.workbench import PacketWorkspace, WorkbenchPublication, REGISTER
from lib.providers.operations import SCM
from lib.provider_errors import AccessFailure
from test_portable_operations import FakeAPI, SOURCE, SHA
from test_portable_runtime import context

DRAFT='b'*32
GCR='docs/governance/change-requests/GCR-WB-'+DRAFT+'.md'
NEW_SOURCE='docs/governance/source-documents/NEW-SRC-001.docx'


class DraftContracts(unittest.TestCase):
    def test_native_clone_identity_rejects_another_same_origin_repository(self):
        for provider,ci,fields in (
                ('github','github-actions',{'clone_url':'https://scm.example/group/repo.git'}),
                ('gitlab','gitlab-ci',{'http_url_to_repo':'https://scm.example/group/subgroup/repo.git'}),
                ('bitbucket-dc','bamboo',{'links':{'clone':[{'href':'https://scm.example/scm/group/repo.git'}]}})):
            api=FakeAPI(provider);scm=SCM(context(ci)['scm'],api,api)
            scm.check_identity();scm.repository.update(fields)
            valid=next(iter(fields.values()))
            if isinstance(valid,dict):valid=valid['clone'][0]['href']
            scm.require_clone_remote(valid)
            with self.assertRaisesRegex(ValueError,'native_clone_repository_mismatch'):
                scm.require_clone_remote('https://scm.example/another/repository.git')

    def test_three_native_providers_get_explicit_draft_proposals(self):
        for provider,ci in [('github','github-actions'),('gitlab','gitlab-ci'),('bitbucket-dc','bamboo')]:
            api=FakeAPI(provider);scm=SCM(context(ci)['scm'],api,api)
            original=api.post
            def post(path,payload):
                row=original(path,payload)
                if provider=='gitlab':row['title']=payload['title']
                else:row['draft']=payload['draft']
                return row
            api.post=post
            result=scm.propose(SOURCE,'main',SHA,'Synthetic draft','Human review only',draft=True)
            self.assertEqual(result['state'],'open')
            payload=api.writes[0][1]
            if provider=='gitlab':self.assertTrue(payload['title'].startswith('Draft: '))
            else:self.assertIs(payload['draft'],True)
            self.assertNotIn('merge',payload)

    def test_missing_native_draft_confirmation_is_held_without_retry(self):
        api=FakeAPI('github');scm=SCM(context()['scm'],api,api)
        with self.assertRaisesRegex(AccessFailure,'native_draft_not_confirmed'):
            scm.propose(SOURCE,'main',SHA,'Synthetic draft','Human review only',draft=True)
        self.assertEqual(len(api.writes),1)


class PacketContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'private';self.root.mkdir()
        p=self.root/REGISTER;p.parent.mkdir(parents=True)
        self.before={'schema_version':'1.0.0','documents':[{'id':'OLD-SRC-001','status':'approved'}]}
        p.write_text(yaml.safe_dump(self.before))
        for args in (['init','-q'],['add','.'],['-c','user.name=Fixture',
                    '-c','user.email=fixture@example.invalid','commit','-qm','Synthetic fixture']):
            subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True)
        self.workspace=PacketWorkspace(self.root,'https://scm.example/group/repo.git')
        self.workspace.prepared=True
        after=deepcopy(self.before)
        after['documents'].append({'id':'NEW-SRC-001','status':'candidate','source_path':NEW_SOURCE})
        self.files={GCR:b'# Synthetic proposal\n',REGISTER:yaml.safe_dump(after).encode(),
                    NEW_SOURCE:b'\x00\xffsynthetic binary source; not a real DOCX'}

    def commit(self,files=None,kind='source_candidate'):
        return self.workspace.commit_packet(self.files if files is None else files,kind,
            at='2026-11-15T12:00:00Z',draft_id=DRAFT)

    def test_real_git_preserves_binary_source_and_only_candidate_packet_paths(self):
        sha=self.commit()
        self.assertEqual(len(sha),40)
        self.assertEqual(self.workspace.git('show',sha+':'+NEW_SOURCE,binary=True),self.files[NEW_SOURCE])
        self.assertEqual(set(self.workspace.git('diff-tree','--no-commit-id','--name-only','-r',sha).splitlines()),set(self.files))

    def test_cannot_modify_an_existing_approved_register_entry(self):
        value=yaml.safe_load(self.files[REGISTER]);value['documents'][0]['status']='candidate'
        self.files[REGISTER]=yaml.safe_dump(value).encode()
        with self.assertRaisesRegex(ValueError,'register_mismatch'):self.commit()

    def test_new_source_must_remain_candidate(self):
        value=yaml.safe_load(self.files[REGISTER]);value['documents'][-1]['status']='approved'
        self.files[REGISTER]=yaml.safe_dump(value).encode()
        with self.assertRaisesRegex(ValueError,'register_mismatch'):self.commit()

    def test_packet_cannot_publish_executable_or_baseline_paths(self):
        for name in ('scripts/evil.py','releases/l1/changed.json','../escape','/absolute'):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError,'scope_violation'):
                    self.commit({**self.files,name:b'bad'})

    def test_change_proposal_cannot_overwrite_another_request(self):
        files={**self.files,'docs/governance/change-requests/GCR-2026-001.md':b'changed'}
        with self.assertRaisesRegex(ValueError,'identity_mismatch'):self.commit(files)

    def test_registered_source_review_cannot_rewrite_bytes(self):
        source=self.root/NEW_SOURCE;source.parent.mkdir(parents=True);source.write_bytes(b'original')
        with self.assertRaisesRegex(ValueError,'cannot_rewrite_source'):
            self.commit({GCR:b'proposal',NEW_SOURCE:b'changed'},'source_review')

    def test_registered_source_review_retains_exact_original_bytes(self):
        source=self.root/NEW_SOURCE;source.parent.mkdir(parents=True);source.write_bytes(b'original')
        self.workspace.git('add','--',NEW_SOURCE)
        self.workspace.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                           'commit','-qm','Original source fixture')
        sha=self.commit({GCR:b'proposal',NEW_SOURCE:b'original'},'source_review')
        self.assertEqual(self.workspace.git('show',sha+':'+NEW_SOURCE,binary=True),b'original')

    def test_packet_branch_cannot_target_default_branch(self):
        with self.assertRaisesRegex(ValueError,'proposal_branch_required'):
            self.workspace.push_packet('main','a'*40)


class PublicationContracts(unittest.TestCase):
    def profile(self):
        return {'schema_version':2,'scm':context()['scm'],'api_url':'https://scm.example',
            'remote':'https://scm.example/group/repo.git','target':'main','git_username':'fixture',
            **{name:'/private/fixture/'+name for name in ('reader_credential','publisher_credential',
               'git_reader_credential','git_publisher_credential')}}

    def test_api_or_git_credentials_cannot_cross_declared_instance(self):
        for field in ('api_url','remote'):
            profile=self.profile();profile[field]='https://evil.example/group/repo'
            with self.assertRaises(ValueError):WorkbenchPublication(profile)

    def test_implicit_or_extra_profile_configuration_is_rejected(self):
        for profile in ({},{**self.profile(),'fallback_cli':'gh'}):
            with self.assertRaisesRegex(ValueError,'invalid_workbench_publication_profile'):
                WorkbenchPublication(profile)

    def test_private_profile_rejects_ambiguous_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'profile.json'
            path.write_text('{"schema_version":2,"schema_version":1}')
            path.chmod(0o600)
            with self.assertRaisesRegex(ValueError,'duplicate_json_key'):
                WorkbenchPublication.from_file(path)

    def test_dirty_source_checkout_is_rejected_before_network_or_credential_reads(self):
        adapter=WorkbenchPublication(self.profile())
        with patch.object(adapter,'token',side_effect=AssertionError('must not read credentials')):
            with self.assertRaisesRegex(ValueError,'clean tracked'):
                adapter.publish(root=Path('/fixture'),destination=Path('/fixture/private'),draft_id=DRAFT,
                    context={'commit':SHA},files={},kind='source_candidate',at='2026-11-15T12:00:00Z',
                    local_run=lambda *args:' M source.py')

    def test_changed_remote_base_stops_before_workspace_or_write(self):
        adapter=WorkbenchPublication(self.profile());scm=Mock()
        scm.branch_sha.return_value='f'*40
        with patch.object(adapter,'token',return_value='synthetic-token'),patch(
                'lib.providers.workbench.SCM',return_value=scm),patch(
                'lib.providers.workbench.PacketWorkspace',side_effect=AssertionError('must not stage')):
            with self.assertRaisesRegex(ValueError,'Remote default branch differs'):
                adapter.publish(root=Path('/fixture'),destination=Path('/fixture/private'),draft_id=DRAFT,
                    context={'commit':SHA},files={},kind='source_candidate',at='2026-11-15T12:00:00Z',
                    local_run=lambda *args:'')
