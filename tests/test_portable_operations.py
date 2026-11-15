"""Provider-shaped fixtures and real local Git; no remote mutations or authority."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.portable_intake.operations import SCM,GitWorkspace,dispatch_ci,run_link,branch,require_compatible
from lib.consumer_github import AccessFailure
from test_portable_runtime import context

SHA='a'*40
SOURCE='automation/portable-consumer/'+'b'*24


class FakeAPI:
    def __init__(self,provider='github'):
        self.provider=provider;self.writes=[];self.rows=[]

    def get(self,path):
        if '/git/ref/heads/' in path:return {'object':{'sha':SHA}}
        if '/repository/branches/' in path:return {'commit':{'id':SHA}}
        if '/branches?' in path:return {'values':[{'id':'refs/heads/'+SOURCE,'latestCommit':SHA}]}
        if '/pull-requests?' in path:return {'values':deepcopy(self.rows),'isLastPage':True}
        return {'id':42,'full_name':'group/repo','path_with_namespace':'group/subgroup/repo','project':{'key':'group'},'slug':'repo'}

    def pages(self,path,field=None):return deepcopy(self.rows)

    def native(self,state='open',sha=SHA):
        if self.provider=='github':return {'number':7,'state':'open' if state=='open' else 'closed',
            'merged_at':'2026-11-15T12:00:00Z' if state=='merged' else None,'html_url':'https://scm.example/group/repo/pull/7',
            'head':{'ref':SOURCE,'sha':sha,'repo':{'id':42}},'base':{'ref':'main','repo':{'id':42}}}
        if self.provider=='gitlab':return {'iid':'opaque-mr-key','state':{'open':'opened','closed':'closed','merged':'merged'}[state],
            'web_url':'https://scm.example/group/subgroup/repo/-/merge_requests/7','source_branch':SOURCE,
            'target_branch':'main','sha':sha,'source_project_id':42,'target_project_id':42}
        return {'id':'opaque-pr-key','state':{'open':'OPEN','merged':'MERGED','closed':'DECLINED'}[state],
            'fromRef':{'id':'refs/heads/'+SOURCE,'latestCommit':sha,'repository':{'id':42}},
            'toRef':{'id':'refs/heads/main','repository':{'id':42}},'links':{'self':[{'href':'https://scm.example/projects/group/repos/repo/pull-requests/7'}]}}

    def post(self,path,payload):self.writes.append((path,payload));return self.native()
    def post_form(self,path,payload):self.writes.append((path,{'form':payload}));return self.native()


class OperationsTests(unittest.TestCase):
    def scm(self,provider):
        ci={'github':'github-actions','gitlab':'gitlab-ci','bitbucket-dc':'bamboo'}[provider]
        profile=context(ci)['scm'];api=FakeAPI(provider)
        return SCM(profile,api,api),api

    def test_three_provider_proposals_use_same_reconciliation_contract(self):
        for provider in ('github','gitlab','bitbucket-dc'):
            scm,api=self.scm(provider)
            result=scm.propose(SOURCE,'main',SHA,'Review synthetic evidence','No actual remote proposal')
            self.assertEqual(result['state'],'open');self.assertEqual(result['sha'],SHA)
            self.assertEqual(len(api.writes),1)
            self.assertNotIn('merge',api.writes[0][1])

    def test_closed_and_merged_proposals_are_never_reopened_or_created_again(self):
        for provider in ('github','gitlab','bitbucket-dc'):
            for state in ('closed','merged','open'):
                scm,api=self.scm(provider);api.rows=[api.native(state)]
                self.assertEqual(scm.propose(SOURCE,'main',SHA,'Title','Body')['state'],state)
                self.assertEqual(api.writes,[])

    def test_existing_proposal_wrong_head_requires_reconciliation(self):
        for provider in ('github','gitlab','bitbucket-dc'):
            scm,api=self.scm(provider);api.rows=[api.native('open','c'*40)]
            with self.assertRaisesRegex(ValueError,'identity_conflict'):scm.propose(SOURCE,'main',SHA,'Title','Body')
            self.assertEqual(api.writes,[])

    def test_cross_repository_pr_or_mr_cannot_satisfy_same_branch(self):
        for provider in ('github','gitlab','bitbucket-dc'):
            scm,api=self.scm(provider);row=api.native()
            if provider=='github':row['head']['repo']['id']=43
            elif provider=='gitlab':row['source_project_id']=43
            else:row['fromRef']['repository']['id']=43
            api.rows=[row]
            with self.assertRaisesRegex(ValueError,'cross_repository'):scm.propose(SOURCE,'main',SHA,'Title','Body')
            self.assertEqual(api.writes,[])

    def test_reader_alone_cannot_propose(self):
        scm,api=self.scm('github');scm.writer=None
        with self.assertRaisesRegex(ValueError,'separate_publisher'):scm.propose(SOURCE,'main',SHA,'Title','Body')

    def test_lost_mutation_reply_is_reconciled_without_second_creation(self):
        for provider in ('github','gitlab','bitbucket-dc'):
            scm,api=self.scm(provider)
            def lost_reply(path,payload):
                api.writes.append((path,payload));api.rows=[api.native()]
                raise AccessFailure('mutation_outcome_unknown')
            api.post=lost_reply
            with self.assertRaises(AccessFailure):scm.propose(SOURCE,'main',SHA,'Title','Body')
            self.assertEqual(scm.propose(SOURCE,'main',SHA,'Title','Body')['state'],'open')
            self.assertEqual(len(api.writes),1)

    def test_native_proposal_url_cannot_smuggle_credentials_or_another_instance(self):
        scm,api=self.scm('github')
        for url in ('https://token@scm.example/group/repo/pull/7','https://scm.example/pull/7?secret=hidden','https://other.example/pull/7'):
            row=api.native();row['html_url']=url;api.rows=[row]
            with self.assertRaises(ValueError):scm.propose(SOURCE,'main',SHA,'Title','Body')
        self.assertEqual(api.writes,[])

    def test_explicit_ci_dispatch_and_unsupported_bamboo_variables(self):
        for provider in ('github-actions','gitlab-ci','bamboo'):
            api=FakeAPI()
            profile={'provider':provider,'native_id':'opaque-plan-or-workflow','repository_path':'group/repo','native_branch':'main'}
            dispatch_ci(profile,api,ref='main');self.assertEqual(len(api.writes),1)
            if provider=='bamboo':
                self.assertEqual(api.writes[0][1],{'form':{}})
                with self.assertRaises(ValueError):dispatch_ci(profile,api,ref='different')
                with self.assertRaises(ValueError):dispatch_ci(profile,api,ref='main',inputs={'ignored':'must not be ignored'})

    def test_native_run_links_preserve_instances_subgroups_and_opaque_keys(self):
        for provider in ('github-actions','gitlab-ci','bamboo'):
            ctx=context(provider);link=run_link(ctx)
            self.assertTrue(link.startswith(ctx['ci']['instance']+'/'))
            self.assertIn(ctx['ci']['run_id'],link)
            if provider=='gitlab-ci':self.assertIn('/group/subgroup/repo/-/pipelines/',link)

    def test_git_ref_injection_and_main_publication_ref_rejected(self):
        for value in ('../main','main\nextra','-c core.sshCommand=evil','refs//heads/main','topic.lock','main:other'):
            with self.assertRaises(ValueError):branch(value)
        work=GitWorkspace('/private/tmp/unused-portable-test','https://scm.example/repo.git')
        with self.assertRaises(ValueError):work.push('main',SHA)
        with self.assertRaises(ValueError):GitWorkspace('/private/tmp/unused','https://token@scm.example/repo.git')

    def test_real_git_commit_only_contains_explicit_candidate_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();work=GitWorkspace(root,'https://scm.example/repo.git')
            work.git('init','-q');work.prepared=True  # Owned local fixture, no remote fetch.
            relative='status/portable/v2/candidates/'+'c'*64+'/'+'d'*64+'.json'
            sha=work.commit({relative:json.dumps({'synthetic':True,'official_acceptance':False})},'Synthetic local candidate',at='2026-11-15T12:00:00Z')
            self.assertEqual(len(sha),40)
            self.assertEqual(work.git('diff-tree','--no-commit-id','--name-only','-r','--root','HEAD'),relative)
            with self.assertRaises(ValueError):work.commit({'model/controls/unsafe.json':'{}'},'Forbidden scope',at='2026-11-15T12:00:00Z')
            with self.assertRaises(ValueError):work.commit({},'Empty batch',at='2026-11-15T12:00:00Z')
            with self.assertRaises(ValueError):work.commit({relative:'{}'},'No historical overwrite',at='2026-11-15T12:00:00Z')

    def test_new_vm_closure_detects_config_and_infra_drift(self):
        import shutil
        with tempfile.TemporaryDirectory() as temporary:
            one,two=Path(temporary)/'one',Path(temporary)/'two'
            for root in (one,two):
                for name in ('scripts','schemas','model','policies','architecture','releases','pipeline-baseline','.github/workflows','.agents','docs/governance/source-documents','docs/foundation','config','infra'):
                    (root/name).mkdir(parents=True)
                (root/'config/profile.json').write_text('{}');(root/'infra/deploy.yml').write_text('---\n')
            require_compatible(one,two)
            for relative in ('config/profile.json','infra/deploy.yml'):
                original=(two/relative).read_bytes();(two/relative).write_text('drift')
                with self.assertRaisesRegex(AccessFailure,'application_update_required'):require_compatible(one,two)
                (two/relative).write_bytes(original)

    def test_frozen_commit_is_reproducible_after_losing_a_private_scratch_checkout(self):
        values=[]
        with tempfile.TemporaryDirectory() as temporary:
            for name in ('first','recovered'):
                root=Path(temporary)/name;root.mkdir()
                work=GitWorkspace(root,'https://scm.example/repo.git');work.git('init','--template=','-q');work.prepared=True
                path='status/portable/v2/candidates/'+'a'*64+'/'+'b'*64+'.json'
                values.append(work.commit({path:'{"synthetic":true}\n'},'Frozen candidate batch',at='2026-11-15T12:00:00Z'))
        self.assertEqual(values[0],values[1])

    def test_git_credentials_never_enter_argv_and_ambient_hooks_tracing_are_disabled(self):
        from unittest.mock import patch
        import subprocess
        work=GitWorkspace('/private/tmp/unexecuted-operation','https://scm.example/repo.git',token='synthetic-secret',username='reader')
        with patch.dict('os.environ',{'GIT_TRACE_CURL':'/untrusted/log','GIT_CONFIG_PARAMETERS':'untrusted','GIT_ASKPASS':'/untrusted/helper'}),patch(
                'lib.portable_intake.operations.subprocess.run',return_value=subprocess.CompletedProcess([],0,b'version\n',b'')) as run:
            work.git('version')
        args,kwargs=run.call_args
        self.assertNotIn('synthetic-secret',' '.join(args[0]))
        env=kwargs['env'];self.assertEqual(env['AXIOM_GIT_TOKEN'],'synthetic-secret')
        self.assertEqual(env['GIT_ASKPASS'],'/bin/false');self.assertNotIn('GIT_TRACE_CURL',env)
        self.assertNotIn('GIT_CONFIG_PARAMETERS',env)
        self.assertEqual(env['GIT_CONFIG_VALUE_2'],'false');self.assertEqual(env['GIT_CONFIG_VALUE_3'],'/dev/null')
