"""Whole Store over actual recorded SQLite, inert replay and native failure state."""
from pathlib import Path
from unittest.mock import patch
from types import ModuleType
import copy,hashlib,json,os,shutil,sqlite3,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.private_intake_store import Store
from lib.private_intake_sql import SQLite,Paths,Clock,ReplaySQLite
from lib.providers.private_intake_sql import NativeSQLite
from lib.providers.consumer_lifecycle_storage import Record,read_record
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.synthetic_lifecycle_io import ReplayIO
from lib.private_intake_sql_protocol import scalar,RetainedSQLError
from lib.requirement_review_output import RetainedOutputError
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError

class RecordedPrivateStore(unittest.TestCase):
    completed=[]
    def setUp(self):
        mask=os.umask(0o077);self.addCleanup(os.umask,mask);tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.top=Path(tmp.name).resolve();self.root=self.top/'state';self.records=self.top/'records';self.records.mkdir(mode=0o700)
    @staticmethod
    def failed(callback):
        try:callback()
        except Exception as error:return {'type':error.original_type if isinstance(error,RetainedOutputError) else type(error).__name__,'message':error.original_message if isinstance(error,RetainedOutputError) else str(error)}
        raise AssertionError('Expected original operation error')
    def open(self):
        record=Record(self.records,{'profile':'test-whole-store'},{'scope':'private-source-engineering-test','official_acceptance':False});record.append({'kind':'execution-intent'});owner=NativeIO(record,mode='selected-files',cwd=str(self.top),private_state=self.records,product_root=ROOT);backend=NativeSQLite(owner,root=str(self.root),cwd=str(self.top),forbidden_roots=(ROOT,self.records));port=SQLite(backend);paths=Paths(str(self.root),str(self.top),owner,backend);return record,owner,backend,lambda:Store(str(self.root),path_factory=paths.path,sqlite_port=port,clock_port=Clock(backend))
    def capture(self,program):
        record,owner,backend,factory=self.open()
        try:result=program(factory)
        finally:resources=backend.release_resources()
        record.finish('complete',{'exit_code':0,'result':result,'resources':resources},owner.touched);return record,result,resources
    def replay(self,record,program,*,events_override=None,blobs_override=None):
        _,_,retained,events,blob,closed=read_record(record.root)
        # Copy only retained bytes into inert test memory before removing all
        # original data and denying every native database/path/clock effect.
        cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};cache.update(blobs_override or {});seen=set()
        def inert(ref):
            raw=cache[ref['sha256']]
            if hashlib.sha256(raw).hexdigest()!=ref['sha256'] or len(raw)!=ref['bytes']:raise IntegrityError('Controlled retained blob corruption')
            seen.add(ref['sha256']);return raw
        owner=ReplayIO(events if events_override is None else events_override,inert,'selected-files',str(self.top));backend=ReplaySQLite(owner,root=str(self.root),cwd=str(self.top));port=SQLite(backend);paths=Paths(str(self.root),str(self.top),owner,backend)
        with patch('sqlite3.connect',side_effect=AssertionError('No native SQLite during pure reconstruction')),patch('os.open',side_effect=AssertionError('No original file opens')),patch('time.time',side_effect=AssertionError('No new clock samples')):
            result=program(lambda:Store(str(self.root),path_factory=paths.path,sqlite_port=port,clock_port=Clock(backend)));resources=backend.release_resources();owner.finish()
        self.assertEqual({'exit_code':0,'result':result,'resources':resources},retained['result']);self.assertEqual(seen,set(cache));return backend,result
    def workflow(self,factory):
        store=factory();result={'missing':store.get('none','default'),'initial_jobs':store.jobs(),'initial_active':store.active_batch()}
        try:
            store.put('data',{'unicode':'€','numbers':[1,2],'status':None});result['data']=store.get('data');store.discover('example/project',{'id':'10','run_attempt':1,'status':'in_progress'});result['waiting']=store.jobs();store.discover('example/project',{'id':10,'run_attempt':1,'status':'completed'});result['first']=store.claim();store.failure(result['first'],'temporary',True,-1);result['retry']=store.jobs();result['reclaim']=store.claim();store.recover();job=store.jobs('queued')[0];store.update(job,state='verified',snapshot='a'*64,snapshot_path='verified/a.json');store.recover();result['verified']=store.jobs();store.discover('example/project',{'id':10,'run_attempt':2,'status':'completed'});result['new_attempt']=store.jobs();result['no_batch']=store.active_batch();result['invalid_field']=self.failed(lambda:store.update(job,approval=True));result['original_empty_batch_SQL']=self.failed(lambda:store.batch('none'))
        finally:store.close()
        result['after_close']=self.failed(store.jobs);return result
    def test_entire_store_native_record_complete_SQL_engine_and_source_free_replay(self):
        record,result,resources=self.capture(self.workflow);self.assertEqual(resources['original_unclosed_connections'],[]);self.assertEqual(set(p.name for p in self.root.iterdir()),{'queue.sqlite3'});native_bytes=(self.root/'queue.sqlite3').read_bytes();_,_,_,events,blob,_=read_record(record.root);times=[scalar(row['result'],blob) for row in events if row.get('kind')=='private-intake-sql-outcome' and type(row.get('result')) is dict and row['result'].get('kind')=='float'];self.assertEqual(len(times),3)
        original=ModuleType('whole_original_store');exec(compile((ROOT/'tests/fixtures/v2-intake-atomic-json-original/consumer_intake_store.txt').read_bytes(),'whole_immutable_store','exec'),original.__dict__);values=iter(times);original.time=type('ObservedClock',(),{'time':lambda self:next(values)})();other=self.top/'original';expected=self.workflow(lambda:original.Store(other));self.assertEqual(result,expected);self.assertEqual(native_bytes,(other/'queue.sqlite3').read_bytes());self.assertEqual(list(values),[])
        shutil.rmtree(self.root);backend,replayed=self.replay(record,self.workflow);self.assertEqual(replayed,result);row=backend.final_snapshot['files']['queue.sqlite3'];self.assertEqual(blob(row['content']),native_bytes);self.assertFalse(self.root.exists());self.completed.append({'whole_original_methods':12,'real_SQLite_and_native_clock_used':True,'original_whole_outputs_and_database_bytes_equal_under_same_observed_clock_inputs':True,'source_removed_no_new_SQLite_path_or_clock_replay':True,'all_blobs_consumed':True,'producer_authority_transferred':False})
    def test_original_version_two_namespace_refusal_and_leaf_symlink_refusal_are_complete(self):
        for case in ('version-two','symlink'):
            with self.subTest(case=case):
                if self.root.exists() or self.root.is_symlink():
                    if self.root.is_symlink():self.root.unlink()
                    else:shutil.rmtree(self.root)
                if case=='version-two':
                    self.root.mkdir(mode=0o700)
                    with sqlite3.connect(self.root/'queue.sqlite3') as seed:seed.execute('PRAGMA user_version=2')
                    seed.close();before=(self.root/'queue.sqlite3').read_bytes()
                else:
                    other=self.top/'private-target';other.mkdir(mode=0o700);self.root.symlink_to(other,target_is_directory=True)
                program=lambda factory:self.failed(factory);record,result,_=self.capture(program);self.assertEqual(result['type'],'ValueError')
                if case=='version-two':self.assertEqual((self.root/'queue.sqlite3').read_bytes(),before);shutil.rmtree(self.root)
                else:self.assertEqual(list(other.iterdir()),[]);self.root.unlink()
                self.replay(record,program)
    def test_known_original_unclosed_connection_is_explicit_separate_cleanup_not_false_rollback(self):
        def program(factory):
            store=factory();store.put('committed',7);return {'value':store.get('committed')}
        record,result,resources=self.capture(program);self.assertEqual(resources['original_unclosed_connections'],['connection-1']);self.assertEqual(resources['outside_original_connection_cleanup'],['connection-1']);self.assertFalse(record.capture_incomplete);shutil.rmtree(self.root);self.replay(record,program)
    def test_database_aliases_and_public_permissions_are_refused_before_SQLite_opens(self):
        for case in ('symlink','hardlink','public-mode'):
            with self.subTest(case=case):
                self.root.mkdir(mode=0o700);target=self.top/('unchanged-'+case);target.write_bytes(b'not a database');target.chmod(0o600);database=self.root/'queue.sqlite3'
                if case=='symlink':database.symlink_to(target)
                elif case=='hardlink':os.link(target,database)
                else:database.write_bytes(b'not a database');database.chmod(0o644)
                record,owner,backend,factory=self.open()
                with patch('sqlite3.connect',side_effect=AssertionError('Rejected aliases must never reach SQLite')):
                    with self.assertRaises(InputAdmissionError):factory()
                self.assertTrue(record.capture_incomplete);self.assertEqual(target.read_bytes(),b'not a database');backend.release_resources();self.assertIsNone(backend.fd);record.finish('incomplete',None,owner.touched);shutil.rmtree(self.root)
    def test_lost_SQLite_intent_never_starts_connection_and_releases_directory_handle(self):
        append=Record.append;record,owner,backend,factory=self.open()
        def lose(journal,row):
            if row.get('kind')=='private-intake-sql-intent' and row.get('action')=='connect':raise OSError('Controlled intent loss before connect')
            return append(journal,row)
        with patch.object(Record,'append',lose),patch('sqlite3.connect',side_effect=AssertionError('No native call without durable intent')):
            with self.assertRaises(InputAdmissionError):factory()
        self.assertTrue(record.capture_incomplete);self.assertEqual(list(self.root.iterdir()),[]);backend.release_resources();self.assertIsNone(backend.fd);record.finish('incomplete',None,owner.touched)
    def test_lost_commit_completion_keeps_actual_commit_blocks_more_SQL_and_releases_owned_resources(self):
        append=Record.append;phase={'action':None};record,owner,backend,factory=self.open()
        def lose(journal,row):
            if row.get('kind')=='private-intake-sql-intent':phase['action']=row['action']
            if row.get('kind')=='private-intake-sql-outcome' and phase['action']=='exit':raise OSError('Controlled completion loss after native commit')
            return append(journal,row)
        with patch.object(Record,'append',lose):
            store=factory()
            with self.assertRaises(InputAdmissionError):store.put('actually_committed',1)
        self.assertTrue(record.capture_incomplete)
        with patch('sqlite3.connect',side_effect=AssertionError('No extra new SQL')),patch.object(owner,'perform',side_effect=AssertionError('No extra filesystem observations after journal loss')),patch.object(owner,'mkdir',side_effect=AssertionError('No extra filesystem writes after journal loss')):
            with self.assertRaises(InputAdmissionError):factory()
        resources=backend.release_resources();self.assertEqual(resources['original_unclosed_connections'],['connection-1']);record.finish('incomplete',None,owner.touched)
        with sqlite3.connect(self.root/'queue.sqlite3') as check:self.assertEqual(check.execute("SELECT value FROM meta WHERE key='actually_committed'").fetchone(),('1',))
        check.close()
    def test_changed_SQL_request_row_shape_and_final_database_bytes_are_rejected(self):
        program=lambda factory:self.simple(factory);record,_,_=self.capture(program);_,_,_,events,_,_=read_record(record.root);shutil.rmtree(self.root)
        changed=copy.deepcopy(events);row=next(r for r in changed if r.get('kind')=='private-intake-sql-intent' and r.get('action')=='execute');row['arguments']['sql']='ATTACH DATABASE ? AS unsafe'
        with self.assertRaises(IntegrityError):self.replay(record,program,events_override=changed)
        changed=copy.deepcopy(events);row=next(r for r in changed if r.get('kind')=='private-intake-sql-outcome' and type(r.get('result')) is dict and r['result'].get('cursor'));row['result']['names']=[]
        with self.assertRaises(IntegrityError):self.replay(record,program,events_override=changed)
        released=next(row for row in events if row.get('kind')=='private-intake-sql-released')
        _,_,_,_,blob,_=read_record(record.root)
        metadata=json.loads(blob(released['database_snapshot']));ref=metadata['files']['queue.sqlite3']['content'];raw=blob(ref);changed_raw=raw[:-1]+bytes([raw[-1]^1])
        with self.assertRaises(IntegrityError):self.replay(record,program,blobs_override={ref['sha256']:changed_raw})
    def test_original_unique_batch_failure_rolls_back_and_reconstructs_actual_context_exception(self):
        def program(factory):
            store=factory()
            try:
                with store.db:store.db.execute('INSERT INTO batches(id,base,state,manifest) VALUES (?,?,?,?)',('one','head','prepared','{}'))
                def conflict():
                    with store.db:store.db.execute('INSERT INTO batches(id,base,state,manifest) VALUES (?,?,?,?)',('two','head','open','{}'))
                result={'error':self.failed(conflict),'active':store.active_batch()};store.batch('one',state='open',pr=7);result['opened']=store.active_batch();store.batch('one',state='published');result['published']=store.active_batch();return result
            finally:store.close()
        record,result,_=self.capture(program);self.assertEqual(result['error']['type'],'IntegrityError');self.assertEqual(result['active']['id'],'one');self.assertEqual(result['opened']['pr'],7);self.assertIsNone(result['published']);shutil.rmtree(self.root);self.replay(record,program)
        _,_,_,events,_,_=read_record(record.root);changed=copy.deepcopy(events);row=next(row for row in changed if row.get('kind')=='private-intake-sql-outcome' and row.get('error') is not None);row['result']={'invented_success':True}
        with self.assertRaises(IntegrityError):self.replay(record,program,events_override=changed)
    def test_native_scalar_limits_overflow_unicode_and_blob_values_preserve_original_errors(self):
        def program(factory):
            store=factory()
            try:
                result={}
                for label,value in [('overflow',1<<80),('surrogate',chr(0xd800))]:
                    def invalid(value=value):
                        with store.db:store.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',(label,value))
                    result[label]=self.failed(invalid)
                with store.db:
                    store.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('large','x'*(2*1024**2+1)))
                    store.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('binary',bytes([255])))
                result['large']=self.failed(lambda:store.get('large'));result['binary']=self.failed(lambda:store.get('binary'));return result
            finally:store.close()
        record,result,_=self.capture(program);self.assertEqual(result['overflow']['type'],'OverflowError');self.assertEqual(result['surrogate']['type'],'UnicodeEncodeError');self.assertEqual(result['binary']['type'],'UnicodeDecodeError');shutil.rmtree(self.root);self.replay(record,program)
    @staticmethod
    def simple(factory):
        store=factory()
        try:store.put('key','value');return store.get('key')
        finally:store.close()

if __name__=='__main__':unittest.main()
