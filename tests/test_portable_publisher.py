"""Native fixtures exercise the publisher state machine; no remote writes."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import test_portable_controller as controller_fixtures
from test_portable_controller import NOW
from lib.consumer_github import AccessFailure
from lib.consumer_intake_store import atomic_json
from lib.portable_intake.controller import collect_task,profile_key,RawBudget
from lib.portable_intake.operations import GitWorkspace
from lib.portable_intake.publisher import (active_batch,candidate,canonical_text,freeze,local_candidate,
    observe_committed,path_for,publish,reconcile,reject_legacy_activity,route_owned,shadow_match,update_batch)
from test_portable_runtime import OPA

NODE='a'*32
SHA='b'*40


class PublisherTests(unittest.TestCase):
    def setUp(self):
        f=controller_fixtures.ControllerTests('runTest');f.setUp();self.addCleanup(f.doCleanups)
        self.f=f;self.queue=f.queue;self.profile=f.profile;self.root=f.root
        pool,*_=f.native();task,self.key=f.task()
        collect_task(self.queue,task,self.profile,pool,RawBudget(f.store.root),opa=OPA,at=NOW)
        self.task=dict(self.queue.db.execute('SELECT * FROM native_tasks').fetchone())
        self.document,self.receipt=local_candidate(self.queue,self.task)
        self.committed=self.root/'committed';self.committed.mkdir()
        (self.committed/'config').mkdir()
        atomic_json(self.committed/'config/consumer-intake-routing.json',{'schema_version':1,'default_owner':'github-actions',
            'routes':[{'repository':self.document['scm']['path'],'domain':'devsecops','owner':'vm'}]})
        self.routing={'schema_version':1,'default_owner':'ci','routes':[{
            'profile_digest':profile_key(self.profile),'owner':'vm','node_id':NODE,'domain':'devsecops','scope':'pipeline-l1'}]}

    def ready(self):
        self.queue.put('shadow_started:'+self.task['profile'],NOW-90000)
        self.queue.put('shadow_match:'+self.task['profile'],{'at':NOW-100,'task_key':'prior-independent-fixture',
            'verifier_source_digest':self.document['verifier_source_digest']})

    def frozen(self):
        self.ready()
        return freeze(self.queue,[self.profile],self.routing,NODE,base=SHA,target='main',at=NOW,committed_root=self.committed)

    def test_owner_and_node_are_explicit_and_default_is_ci(self):
        self.assertTrue(route_owned(self.routing,self.profile,NODE))
        self.assertFalse(route_owned(self.routing,self.profile,'b'*32))
        self.assertFalse(route_owned({'schema_version':1,'default_owner':'ci','routes':[]},self.profile,NODE))
        self.assertIsNone(freeze(self.queue,[self.profile],self.routing,NODE,base=SHA,target='main',at=NOW,committed_root=self.committed))

    def test_shadow_requires_full_window_new_mainline_and_exact_committed_content(self):
        path=self.committed/path_for(self.document);atomic_json(path,self.document)
        self.queue.put('shadow_started:'+self.task['profile'],NOW-100)
        self.assertFalse(shadow_match(self.queue,self.task,self.document,self.committed,at=NOW))
        self.queue.put('shadow_started:'+self.task['profile'],NOW-90000)
        self.assertTrue(shadow_match(self.queue,self.task,self.document,self.committed,at=NOW))
        altered=deepcopy(self.document);altered['decision']='fail'
        self.assertFalse(shadow_match(self.queue,self.task,altered,self.committed,at=NOW))
        for field,value in [('synthetic',True),('event','pull_request'),('trust','integrity_verified')]:
            altered=deepcopy(self.document);altered[field]=value;atomic_json(path,altered)
            self.assertFalse(shadow_match(self.queue,self.task,altered,self.committed,at=NOW))

    def test_shadow_never_publishes_same_committed_candidate(self):
        self.ready();atomic_json(self.committed/path_for(self.document),self.document)
        self.assertEqual(observe_committed(self.queue,self.committed,at=NOW),1)
        self.assertIsNone(freeze(self.queue,[self.profile],self.routing,NODE,base=SHA,target='main',at=NOW,committed_root=self.committed))

    def test_feature_push_or_unknown_native_default_branch_cannot_fulfil_mainline_shadow(self):
        from lib.portable_intake.controller import Queue
        from lib.portable_intake.store import Store
        for default in ('different-default',None):
            pool,_,responses,_,_=self.f.native()
            responses['/repos/'+self.profile['policy']['scm']['path']]['default_branch']=default
            store=Store(self.root/('native-'+str(default)))
            try:
                queue=Queue(store);queue.discover(self.profile,self.f.locator,at=NOW);task=queue.claim(at=NOW)
                receipt=collect_task(queue,task,self.profile,pool,RawBudget(store.root),opa=OPA,at=NOW)
                self.assertTrue(receipt['candidate_eligible'])  # legitimate branch-scoped evidence
                task=dict(queue.db.execute('SELECT * FROM native_tasks').fetchone())
                document,_=local_candidate(queue,task);atomic_json(self.committed/path_for(document),document)
                queue.put('shadow_started:'+task['profile'],NOW-90000)
                self.assertFalse(queue.get('native_context:'+task['key'])['mainline_proven'])
                self.assertFalse(shadow_match(queue,task,document,self.committed,at=NOW))
            finally:store.close()

    def test_changed_private_native_capture_cannot_assert_default_branch_proof(self):
        self.ready();atomic_json(self.committed/path_for(self.document),self.document)
        path=self.f.store.root/self.task['raw_path']/'native-capture.json'
        metadata=json.loads(path.read_text());metadata['observation']['native_default_branch']='forged-default'
        atomic_json(path,metadata)
        self.assertFalse(shadow_match(self.queue,self.task,self.document,self.committed,at=NOW))

    def test_candidate_whitelist_preserves_native_ids_without_private_scan_data(self):
        text=canonical_text(self.document)
        self.assertEqual(self.document['ci']['job_id'],'987')
        self.assertEqual(self.document['producer_execution_key'],self.receipt['execution_key'])
        self.assertFalse(self.document['official_acceptance']);self.assertIsNone(self.document['blocks_merge'])
        for forbidden in ('native_reference','token','responses','artifact.bin','scanner','raw_path'):
            self.assertNotIn(forbidden,text)

    def test_frozen_base_files_and_batch_are_immutable_across_restart(self):
        batch=self.frozen();self.assertIsNotNone(batch)
        next_batch=freeze(self.queue,[self.profile],self.routing,NODE,base='c'*40,target='different',at=NOW+1,committed_root=self.committed)
        self.assertEqual(batch,next_batch)
        manifest=json.loads(batch['manifest']);self.assertEqual(len(manifest['tasks']),1)
        self.assertEqual(manifest['files'][path_for(self.document)],canonical_text(self.document))

    def test_one_batch_freezes_at_most_twenty_five_distinct_tasks(self):
        self.ready()
        # Queue/state stress fixture; gate/receipt/file parity is covered above with real OPA.
        for n in range(30):
            key=f'{n:064x}'
            with self.queue.db:self.queue.db.execute(
                'INSERT INTO native_tasks(key,profile,locator,state,discovered,receipt_key,raw_path) VALUES (?,?,?,?,?,?,?)',
                (key,self.task['profile'],self.task['locator'],'verified',NOW-100,'fixture-receipt-'+str(n),self.task['raw_path']))
        def distinct(queue,task):
            document=deepcopy(self.document);document['native_execution_key']=task['key']
            return document,self.receipt
        with patch('lib.portable_intake.publisher.local_candidate',side_effect=distinct):
            batch=freeze(self.queue,[self.profile],self.routing,NODE,base=SHA,target='main',at=NOW,committed_root=self.committed)
        manifest=json.loads(batch['manifest']);self.assertEqual(len(manifest['tasks']),25)
        self.assertEqual(len(set(manifest['files'])),25)
        self.assertEqual(self.queue.db.execute("SELECT count(*) FROM native_tasks WHERE state='verified'").fetchone()[0],6)

    def test_expired_receipt_cannot_renew_at_proposal_time(self):
        self.ready()
        result=freeze(self.queue,[self.profile],self.routing,NODE,base=SHA,target='main',at=NOW+86401,committed_root=self.committed)
        self.assertIsNone(result)
        self.assertEqual(self.queue.db.execute('SELECT state FROM native_tasks').fetchone()[0],'held')

    def test_old_verifier_receipt_is_retained_but_not_automatically_promoted_after_update(self):
        self.ready()
        with patch('lib.portable_intake.publisher.verifier_digest',return_value='0'*64):
            self.assertIsNone(freeze(self.queue,[self.profile],self.routing,NODE,base=SHA,target='main',at=NOW,committed_root=self.committed))
        row=self.queue.db.execute('SELECT state,error FROM native_tasks').fetchone()
        self.assertEqual(tuple(row),('held','proposal_verifier_update_required'))
        self.assertEqual(json.loads(self.queue.db.execute('SELECT receipt FROM receipts').fetchone()[0]),self.receipt)

    def test_modified_raw_result_is_detected_before_freeze(self):
        self.ready();path=self.f.store.root/self.task['raw_path']/'bundle/result.json'
        payload=json.loads(path.read_text());payload['generated_at']='2026-11-16T12:00:00Z';atomic_json(path,payload)
        with self.assertRaisesRegex(ValueError,'bytes_changed'):self.frozen()

    def test_existing_legacy_batch_holds_new_publisher(self):
        with self.queue.db:
            self.queue.db.execute('CREATE TABLE batches(id TEXT,state TEXT)')
            self.queue.db.execute("INSERT INTO batches VALUES ('original-id','open')")
        self.ready()
        with self.assertRaisesRegex(AccessFailure,'legacy_publication'):
            freeze(self.queue,[self.profile],self.routing,NODE,base=SHA,target='main',at=NOW,committed_root=self.committed)

    def test_terminal_native_changes_are_not_reopened(self):
        batch=self.frozen();update_batch(self.queue,batch['id'],commit_sha=SHA)
        class SCM:
            def changes(inner,source,target):return [{'id':'opaque-MR','sha':SHA,'state':'closed','url':'https://scm.example/mr/opaque'}]
        self.assertTrue(reconcile(self.queue,active_batch(self.queue),SCM()))
        self.assertIsNone(active_batch(self.queue))
        self.assertEqual(self.queue.db.execute('SELECT state FROM native_tasks').fetchone()[0],'not_accepted')
        self.assertEqual(self.queue.db.execute('SELECT change_id FROM portable_batches').fetchone()[0],'opaque-MR')

    def test_lost_reply_reconciles_existing_open_change_without_writing(self):
        batch=self.frozen();update_batch(self.queue,batch['id'],commit_sha=SHA)
        class SCM:
            def changes(inner,source,target):return [{'id':'native-7','sha':SHA,'state':'open','url':'https://scm.example/mr/7'}]
        result=publish(self.queue,[],{},NODE,SCM(),installed=ROOT,workspace_factory=None,base=SHA,target='main',at=NOW)
        self.assertEqual(result['state'],'open');self.assertEqual(result['change_id'],'native-7')

    def test_complete_real_git_proposal_and_lost_reply_recovery_reuse_frozen_commit(self):
        import shutil
        from lib.portable_intake.publisher import active_batch
        self.ready();initial=GitWorkspace(self.committed,'https://scm.example/central.git')
        initial.git('init','--template=','-q');initial.git('add','config')
        initial.git('-c','user.name=Fixture','-c','user.email=fixture@localhost','-c','commit.gpgsign=false',
                    'commit','-qm','Initial local fixture',stamp='2026-11-15T10:00:00Z')
        base=initial.git('rev-parse','HEAD');pushes=[];rows=[];proposals=[]
        class OwnedWorkspace(GitWorkspace):
            def prepare(inner,revision):
                shutil.copytree(self.committed,inner.root)
                inner.git('checkout','--detach','-q',revision);inner.prepared=True
            def push(inner,source,sha):
                pushes.append((source,sha))
                changed=inner.git('diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines()
                self.assertEqual(changed,[path_for(self.document)])
        class SCM:
            profile={'provider':'gitlab'}
            def changes(inner,source=None,target=None,*,prefixes=None):
                return [r for r in rows if (source is None or r['source']==source) and (target is None or r['target']==target)
                        and (prefixes is None or r['source'].startswith(prefixes))]
            def propose(inner,source,target,sha,title,body):
                proposals.append((source,sha));rows.append({'id':'opaque-MR','source':source,'target':target,
                    'sha':sha,'state':'open','url':'https://scm.example/group/central/-/merge_requests/7'})
                raise AccessFailure('mutation_outcome_unknown')
        scm=SCM();factory=lambda path:OwnedWorkspace(path,'https://scm.example/central.git')
        arguments=dict(installed=self.committed,workspace_factory=factory,base=base,target='main',at=NOW)
        with self.assertRaisesRegex(AccessFailure,'outcome_unknown'):
            publish(self.queue,[self.profile],self.routing,NODE,scm,**arguments)
        frozen=active_batch(self.queue);self.assertEqual(frozen['state'],'prepared')
        self.assertEqual(frozen['commit_sha'],pushes[0][1])
        recovered=publish(self.queue,[self.profile],self.routing,NODE,scm,**arguments)
        self.assertEqual(recovered['state'],'open');self.assertEqual(recovered['change_id'],'opaque-MR')
        self.assertEqual(len(pushes),1);self.assertEqual(len(proposals),1)

    def test_merged_proposal_waits_for_exact_current_committed_bytes(self):
        batch=self.frozen();update_batch(self.queue,batch['id'],commit_sha=SHA,state='accepted_pending_sync')
        class Workspace:
            root=self.committed
            def prepare(inner,base):self.assertEqual(base,SHA)
        with patch('lib.portable_intake.publisher.require_compatible'):
            with self.assertRaisesRegex(AccessFailure,'accepted_sync_required'):
                publish(self.queue,[],{},NODE,None,installed=ROOT,workspace_factory=lambda p:Workspace(),base=SHA,target='main',at=NOW)
            path=self.committed/path_for(self.document);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(canonical_text(self.document))
            self.assertIsNone(publish(self.queue,[],{},NODE,None,installed=ROOT,workspace_factory=lambda p:Workspace(),base=SHA,target='main',at=NOW))
        self.assertEqual(self.queue.db.execute('SELECT state FROM native_tasks').fetchone()[0],'reviewed_candidate')
        self.assertEqual(self.queue.db.execute('SELECT state FROM portable_batches').fetchone()[0],'reviewed')

    def test_git_reader_and_publisher_credentials_are_separate(self):
        import subprocess
        work=GitWorkspace('/private/tmp/not-executed','https://scm.example/repo.git',token='synthetic-reader',publisher_token='synthetic-writer')
        with patch('lib.portable_intake.operations.subprocess.run',return_value=subprocess.CompletedProcess([],0,b'ok',b'')) as run:
            work.git('fetch','origin',SHA);self.assertEqual(run.call_args.kwargs['env']['AXIOM_GIT_TOKEN'],'synthetic-reader')
            work.git('push','origin','ref',publishing=True);self.assertEqual(run.call_args.kwargs['env']['AXIOM_GIT_TOKEN'],'synthetic-writer')
            self.assertNotIn('synthetic-writer',' '.join(run.call_args.args[0]))
