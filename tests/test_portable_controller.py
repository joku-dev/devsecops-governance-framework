"""Persistent queue and real bundle/OPA parity using native HTTP fixtures, no live adoption."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.consumer_github import AccessFailure
from lib.consumer_intake_store import atomic_json
from lib.portable.contracts import execution_key
from lib.portable_intake.controller import (Queue,ReaderPool,RawBudget,collect_task,discover_page,
    instant,poll,profile_key,task_key,validate_profiles,work)
from lib.portable_intake.store import Store,backup_v2
import test_portable_intake as fixtures
from test_portable_intake import AT
from test_portable_runtime import OPA
from lib.portable_intake.bundle import timestamp

NOW=timestamp(AT).timestamp()


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.store=Store(self.root/'private');self.addCleanup(self.store.close)
        self.queue=Queue(self.store)
        self.fixture=fixtures.BundleTests('runTest');self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.profile={'id':'fixture','policy':deepcopy(self.fixture.policy),'reader_credential':'reader-fixture',
            'scm_reader_credential':'reader-fixture','discovery':{'lookback_seconds':86400,'plan_key':None}}
        self.locator={'run_id':'42','job_id':'987','attempt':1}

    def native(self):
        reader,responses,job,artifact=self.fixture.native()
        job['id']=987
        class Pool:
            calls=0
            def reader(inner,*args):return reader
        return Pool(),reader,responses,job,artifact

    def task(self):
        key=self.queue.discover(self.profile,self.locator,at=NOW)
        return self.queue.claim(at=NOW),key

    def test_default_registry_has_no_live_consumers_or_authority(self):
        self.assertEqual(validate_profiles(json.loads((ROOT/'config/portable-consumer-profiles.json').read_text())),[])
        self.assertFalse(self.queue.summary(at=NOW)['publisher_active'])

    def test_native_namespaces_and_reruns_are_distinct(self):
        first=task_key(self.profile['policy'],self.locator)
        for area,name,value in [('ci','instance','https://other.example'),('scm','native_id','different-native')]:
            policy=deepcopy(self.profile['policy']);policy[area][name]=value
            self.assertNotEqual(first,task_key(policy,self.locator))
        for name,value in [('attempt',2),('job_id','988'),('run_id','other-run')]:
            self.assertNotEqual(first,task_key(self.profile['policy'],{**self.locator,name:value}))

    def test_queue_restart_dedup_and_exact_profile_binding(self):
        task,key=self.task();self.assertEqual(task['key'],key)
        self.assertIsNone(self.queue.claim(at=NOW))
        self.queue.recover();self.assertEqual(self.queue.claim(at=NOW)['key'],key)
        self.assertEqual(self.queue.discover(self.profile,self.locator,at=NOW),key)
        changed=deepcopy(self.profile);changed['policy']['max_severity']='low'
        with self.assertRaisesRegex(ValueError,'profile_conflict'):self.queue.discover(changed,self.locator,at=NOW)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM native_tasks').fetchone()[0],1)

    def test_retry_budget_and_deferrals_are_persistent(self):
        task,key=self.task()
        for _ in range(5):self.queue.fail(key,'rate_limited',at=NOW,retryable=True,defer=True,delay=120)
        row=self.store.db.execute('SELECT * FROM native_tasks WHERE key=?',(key,)).fetchone()
        self.assertEqual((row['retries'],row['state'],row['next_at']),(0,'queued',NOW+120))
        self.assertIsNone(self.queue.claim(at=NOW+119))
        for _ in range(4):self.queue.fail(key,'provider_read_failed',at=NOW,retryable=True)
        row=self.store.db.execute('SELECT retries,state FROM native_tasks WHERE key=?',(key,)).fetchone()
        self.assertEqual(tuple(row),(4,'held'))

    def test_profile_rejects_cross_issuer_credentials_and_free_env(self):
        validate_profiles({'schema_version':1,'profiles':[self.profile]})
        for mutate in [lambda p:p['policy']['transport'].update(api_url='https://evil.example/api'),
                       lambda p:p.update(reader_credential='publisher-main'),
                       lambda p:p['policy']['transport'].update(bundle_prefix='../../private'),
                       lambda p:p['policy']['transport'].update(token_env='ARBITRARY_TOKEN')]:
            profile=deepcopy(self.profile);mutate(profile)
            with self.assertRaises(ValueError):validate_profiles({'schema_version':1,'profiles':[profile]})

    def test_complete_native_job_uses_same_opa_and_immutable_producer_receipt(self):
        pool,reader,_,_,_=self.native();task,key=self.task()
        receipt=collect_task(self.queue,task,self.profile,pool,RawBudget(self.store.root),opa=OPA,at=NOW)
        self.assertEqual(receipt['producer'],self.fixture.ctx)
        self.assertEqual(receipt['decision'],self.fixture.result['decision'])
        self.assertEqual(receipt['execution_key'],execution_key(self.fixture.ctx))
        self.assertTrue(receipt['candidate_eligible']);self.assertFalse(receipt['official_acceptance'])
        row=self.store.db.execute('SELECT * FROM native_tasks WHERE key=?',(key,)).fetchone()
        self.assertEqual(row['state'],'verified')
        native=json.loads((self.store.root/row['raw_path']/'native-capture.json').read_text())
        self.assertEqual(native['observation']['native_job_id'],'987')
        self.assertTrue((self.store.root/row['raw_path']/'native-artifact.zip').is_file())
        before=self.store.history();self.queue.recover();self.assertIsNone(self.queue.claim(at=NOW))
        self.assertEqual(before,self.store.history())

    def test_changed_native_job_never_records_receipt_and_keeps_failed_capture(self):
        pool,reader,_,job,_=self.native();task,key=self.task()
        job['id']=988
        with self.assertRaises(ValueError):collect_task(self.queue,task,self.profile,pool,RawBudget(self.store.root),opa=OPA,at=NOW)
        self.assertEqual(self.store.history(),{})
        self.assertTrue(list((self.store.root/'raw/native'/key).glob('*/native-capture.json')))

    def test_two_physical_jobs_cannot_alias_one_producer_receipt(self):
        pool,_,_,job,_=self.native();task,key=self.task()
        receipt=collect_task(self.queue,task,self.profile,pool,RawBudget(self.store.root),opa=OPA,at=NOW)
        self.queue.discover(self.profile,{**self.locator,'job_id':'988'},at=NOW)
        other=self.queue.claim(at=NOW);job['id']=988
        with self.assertRaisesRegex(ValueError,'alias_conflict'):
            collect_task(self.queue,other,self.profile,pool,RawBudget(self.store.root),opa=OPA,at=NOW)
        self.assertEqual(self.store.history(),{receipt['execution_key']:receipt['bundle_digest']})

    def test_worker_recovers_and_holds_stale_profile(self):
        task,key=self.task()
        result=work(self.queue,[],type('Pool',(),{'calls':0})(),opa=OPA,at=NOW)
        self.assertEqual(result['counts'],{'held':1})
        self.assertEqual(self.store.db.execute('SELECT error FROM native_tasks').fetchone()[0],'profile_changed_requires_review')

    def test_worker_rate_limit_defers_without_consuming_retries(self):
        self.task()
        with patch('lib.portable_intake.controller.collect_task',side_effect=AccessFailure('rate_limited',True,120)):
            result=work(self.queue,[self.profile],type('Pool',(),{'calls':3})(),opa=OPA,at=NOW)
        self.assertEqual(result['counts'],{'queued':1})
        self.assertEqual(tuple(self.store.db.execute('SELECT retries,next_at FROM native_tasks').fetchone()),(0,NOW+120))

    def test_reader_budget_shared_per_subject_and_throttle_survives_restart(self):
        credentials=self.root/'credentials';credentials.mkdir()
        for name in ('reader-fixture','reader-other'):
            (credentials/name).write_text('synthetic-private-token');(credentials/name).chmod(0o600)
        class Fake:
            def __init__(inner,base,token,budget):inner.base,inner.calls,inner.budget=base,0,budget
            def get(inner,path):
                inner.calls+=1
                raise AccessFailure('rate_limited',True,120)
        pool=ReaderPool(self.queue,credentials,at=NOW,factory=Fake)
        one=pool.reader(self.profile['policy']['transport'],'reader-fixture')
        two=pool.reader(self.profile['policy']['transport'],'reader-fixture')
        self.assertIs(one.reader,two.reader)
        with self.assertRaises(AccessFailure):one.get('/native')
        with self.assertRaises(AccessFailure):two.get('/native')
        self.assertEqual(pool.calls,1)
        restarted=ReaderPool(self.queue,credentials,at=NOW+60,factory=Fake)
        with self.assertRaises(AccessFailure):restarted.reader(self.profile['policy']['transport'],'reader-fixture')
        self.assertEqual(restarted.calls,0)
        self.assertIsNot(one.reader,pool.reader(self.profile['policy']['transport'],'reader-other').reader)

    def test_poll_cursor_fairness_and_overlapping_windows_deduplicate(self):
        profiles=[]
        for n in range(30):
            p=deepcopy(self.profile);p['id']='repo-'+str(n);p['policy']['scm']['native_id']=str(n);profiles.append(p)
        class Pool:
            calls=0
            def reader(inner,*a):return None
        with patch('lib.portable_intake.controller.discover_page',return_value=([self.locator],False)):
            self.assertEqual(poll(self.queue,profiles,Pool(),at=NOW)['profiles'],25)
            poll(self.queue,profiles,Pool(),at=NOW+60)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM native_tasks').fetchone()[0],30)
        self.assertEqual(self.queue.get('profile_cursor'),20)

    def test_legacy_backup_includes_native_queue_without_new_database(self):
        task,key=self.task();backup=self.root/'backup';backup_v2(self.store,backup)
        connection=sqlite3.connect(backup/'queue.sqlite3')
        try:self.assertEqual(connection.execute('SELECT key FROM native_tasks').fetchone()[0],key)
        finally:connection.close()
        self.assertEqual(len(list(self.store.root.glob('*.sqlite3'))),1)

    def test_native_discovery_includes_failed_github_attempts(self):
        profile=self.profile
        class Fake:
            def get(inner,path):
                self.assertIn('created=',path)
                self.assertIn('/workflows/portable.yml/runs?',path)
                return {'total_count':1,'workflow_runs':[{'id':42,'run_attempt':2,'status':'completed','conclusion':'failure'}]}
            def pages(inner,path,field):
                self.assertIn('/attempts/2/jobs',path)
                return [{'id':987,'name':'portable','status':'completed'}]
        locators,more=discover_page(profile,Fake(),page=1,start=NOW-3600,end=NOW)
        self.assertEqual(locators,[{**self.locator,'attempt':2}]);self.assertFalse(more)

    def test_bamboo_discovery_uses_completed_result_key_and_all_states(self):
        profile=deepcopy(self.profile);profile['policy']['ci']['provider']='bamboo';profile['discovery']['plan_key']='PROJ-PLAN'
        class Fake:
            def get(inner,path):
                self.assertIn('includeAllStates=true',path)
                return {'results':{'result':[{'key':'PROJ-PLAN-42','lifeCycleState':'Finished','buildCompletedTime':AT,'state':'Failed'}]}}
        locators,more=discover_page(profile,Fake(),page=1,start=NOW-3600,end=NOW)
        self.assertEqual(locators,[{'run_id':'PROJ-PLAN-42','job_id':'PROJ-PLAN-42','attempt':1}]);self.assertFalse(more)

    def test_native_bamboo_queue_alias_cannot_contradict_result_identity(self):
        from lib.portable_intake.transport import bamboo_result_key
        self.assertEqual(bamboo_result_key({'key':'PROJ-PLAN-42'}),'PROJ-PLAN-42')
        with self.assertRaises(ValueError):bamboo_result_key({'key':'PROJ-PLAN-42','buildResultKey':'OTHER-PLAN-99'})

    def test_hourly_budget_survives_pool_restart_and_does_not_consume_retries(self):
        credentials=self.root/'credentials';credentials.mkdir()
        atomic_json(credentials/'unused',{})
        (credentials/'reader-fixture').write_text('synthetic-token');(credentials/'reader-fixture').chmod(0o600)
        class Fake:
            def __init__(inner,base,token,budget):inner.base,inner.calls,inner.budget=base,0,budget
            def get(inner,path):inner.calls+=1;return {'ok':True}
        pool=ReaderPool(self.queue,credentials,at=NOW,factory=Fake)
        governed=pool.reader(self.profile['policy']['transport'],'reader-fixture')
        self.queue.put('quota:'+governed.realm,{'window':int(NOW//3600),'used':3000})
        with self.assertRaisesRegex(AccessFailure,'realm_budget_exhausted'):governed.get('/native')
        self.assertEqual(pool.calls,0)
        restarted=ReaderPool(self.queue,credentials,at=NOW+1,factory=Fake)
        with self.assertRaisesRegex(AccessFailure,'realm_budget_exhausted'):
            restarted.reader(self.profile['policy']['transport'],'reader-fixture').get('/native')
        later=ReaderPool(self.queue,credentials,at=NOW+3600,factory=Fake)
        self.assertEqual(later.reader(self.profile['policy']['transport'],'reader-fixture').get('/native'),{'ok':True})

    def test_conditional_cache_is_bounded_and_scoped_by_credential_realm(self):
        from lib.portable_intake.controller import ScopedCache
        first=ScopedCache(self.queue,'one',NOW);second=ScopedCache(self.queue,'two',NOW)
        first.put('/native',{'etag':'fixture-etag','body':{'native':'data'}})
        self.assertIsNone(second.get('/native'));self.assertEqual(first.get('/native')['etag'],'fixture-etag')
        for n in range(520):first.put('/native/'+str(n),{'etag':str(n),'body':{}})
        self.assertEqual(self.queue.db.execute('SELECT count(*) FROM portable_http_cache').fetchone()[0],512)
        first.put('/large',{'etag':'large','body':'x'*(256*1024)})
        self.assertIsNone(first.get('/large'))

    def test_native_cli_exports_identical_candidate_and_replay_does_not_replace_it(self):
        import contextlib,io
        import intake_portable_evidence as cli
        from lib.portable_intake.publisher import candidate,path_for
        pool,reader,_,_,_=self.native()
        context_path=self.root/'context.json';policy_path=self.root/'policy.json'
        atomic_json(context_path,self.fixture.ctx);atomic_json(policy_path,self.profile['policy'])
        directory=self.root/'proposal';operations=self.root/'cli-private'
        arguments=['collect','--root',str(operations),'--context',str(context_path),'--policy',str(policy_path),
            '--opa',str(OPA),'--at',AT,'--candidate-directory',str(directory)]
        with patch.object(cli,'Reader',return_value=reader),patch.object(cli,'require_storage'),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(arguments),0)
            files=list(directory.rglob('*.json'));self.assertEqual(len(files),1)
            first=files[0].read_bytes()
            self.assertEqual(cli.main(arguments),0)
            self.assertEqual(files[0].read_bytes(),first)
        document=json.loads(first);self.assertEqual(document['ci']['job_id'],'987')
        self.assertFalse(document['official_acceptance']);self.assertEqual(document['trust'],'provenance_verified')
        standalone=Store(operations)
        try:saved=json.loads(standalone.db.execute('SELECT receipt FROM receipts').fetchone()[0])
        finally:standalone.close()
        task,_=self.task()
        vm_receipt=collect_task(self.queue,task,self.profile,pool,RawBudget(self.store.root),opa=OPA,at=NOW)
        self.assertEqual(vm_receipt,saved)  # same files/policy/time/replay history, separate state roots
        self.assertEqual(candidate(vm_receipt,self.locator,self.fixture.result['generated_at']),document)

    def test_etag_304_uses_only_same_private_realm_cache(self):
        from email.message import Message
        from urllib.error import HTTPError
        from lib.portable_intake.controller import ScopedCache
        from lib.portable_intake.transport import Reader
        cache=ScopedCache(self.queue,'realm-one',NOW);cache.put('/native',{'etag':'"fixture"','body':{'native_id':'42'}})
        reader=Reader('https://scm.example');reader.cache=cache
        class Opener:
            def open(inner,request,timeout):
                self.assertEqual(request.get_header('If-none-match'),'"fixture"')
                raise HTTPError(request.full_url,304,'not modified',Message(),None)
        with patch('lib.portable_intake.transport.build_opener',return_value=Opener()):
            self.assertEqual(reader.get('/native'),{'native_id':'42'})
        self.assertEqual(reader.calls,1)

    def test_native_audit_limit_preserves_preceding_responses(self):
        from lib.portable_intake.transport import BoundedAudit
        audit=BoundedAudit();audit.append({'first':'preserved'})
        with self.assertRaisesRegex(ValueError,'audit_budget'):audit.append({'oversized':'x'*(8*1024**2)})
        self.assertEqual(audit,[{'first':'preserved'}])

    def test_gitlab_discovery_retains_retried_native_jobs(self):
        profile=deepcopy(self.profile);profile['policy']['ci']['provider']='gitlab-ci'
        class Fake:
            def get(inner,path):return [{'id':'pipeline-opaque','status':'failed'}]
            def pages(inner,path,field=None):
                self.assertIn('include_retried=true',path)
                return [{'id':'old-job','name':'portable','status':'failed'},{'id':'new-job','name':'portable','status':'success'}]
        locators,_=discover_page(profile,Fake(),page=1,start=NOW-3600,end=NOW)
        self.assertEqual([r['job_id'] for r in locators],['old-job','new-job'])


if __name__=='__main__':unittest.main()
