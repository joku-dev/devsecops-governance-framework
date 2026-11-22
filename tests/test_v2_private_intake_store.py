"""Whole immutable Store class, real SQLite effects and complete native outcomes.

Clock values are explicit deterministic test inputs, not native measurements.
The entire original module is the oracle; no successful-path function slice.
"""
from pathlib import Path
from types import ModuleType
import ast,copy,hashlib,json,os,sqlite3,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.private_intake_store import Store
RAW=(ROOT/'tests/fixtures/v2-intake-atomic-json-original/consumer_intake_store.txt').read_bytes()
REFERENCE='6b557fefe295b58272d2271326576ca3a3687197'

class Clock:
    def __init__(self):self.value=1000.25;self.calls=[]
    def time(self):self.calls.append(self.value);return self.value

class SQLite:
    Row=sqlite3.Row
    def __init__(self):self.statements=[];self.connections=[]
    def connect(self,*args,**kwargs):
        value=sqlite3.connect(*args,**kwargs);value.set_trace_callback(self.statements.append);self.connections.append(value);return value

class WholePrivateStore(unittest.TestCase):
    completed=[]
    def setUp(self):
        mask=os.umask(0o077);self.addCleanup(os.umask,mask);temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.top=Path(temp.name).resolve()
    def original(self):
        module=ModuleType('whole_immutable_intake_store');module.__file__=str(ROOT/'tests/fixtures/v2-intake-atomic-json-original/consumer_intake_store.txt');exec(compile(RAW,module.__file__,'exec'),module.__dict__);return module
    def factories(self):
        original=self.original()
        for label in ('original','ported'):
            clock=Clock();database=SQLite();path=self.top/label
            if label=='original':original.time=clock;original.sqlite3=database;factory=lambda root:original.Store(root)
            else:factory=lambda root:Store(root,path_factory=Path,sqlite_port=database,clock_port=clock)
            yield label,path,factory,database,clock
    @staticmethod
    def error(callback):
        try:callback()
        except Exception as error:return {'type':type(error).__name__,'message':str(error),'sqlite_errorcode':getattr(error,'sqlite_errorcode',None),'sqlite_errorname':getattr(error,'sqlite_errorname',None)}
        raise AssertionError('Expected whole original error')
    @staticmethod
    def dump(store):
        return {'version':store.db.execute('PRAGMA user_version').fetchone()[0],
            'schema':[tuple(row) for row in store.db.execute("SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name")],
            'meta':[tuple(row) for row in store.db.execute('SELECT * FROM meta ORDER BY key')],
            'jobs':store.jobs(),'batches':[tuple(row) for row in store.db.execute('SELECT * FROM batches ORDER BY id')]}
    def test_entire_immutable_source_and_all_twelve_original_method_bodies_are_retained(self):
        self.assertEqual(hashlib.sha256(RAW).hexdigest(),'d8ecb4902f86bb82b61570aafbe22c117bb0e9246b5c3b616429d1561c9b82d5');self.assertEqual(RAW,subprocess.check_output(['git','show',REFERENCE+':scripts/lib/consumer_intake_store.py'],cwd=ROOT))
        original=next(n for n in ast.parse(RAW).body if isinstance(n,ast.ClassDef) and n.name=='Store');model=next(n for n in ast.parse((ROOT/'scripts/lib/private_intake_store.py').read_bytes()).body if isinstance(n,ast.ClassDef) and n.name=='Store');model=copy.deepcopy(model);init=next(n for n in model.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
        self.assertEqual([n.arg for n in init.args.kwonlyargs],['path_factory','sqlite_port','clock_port']);self.assertEqual(ast.dump(init.body[0],include_attributes=False),ast.dump(ast.parse('self.paths, self.sqlite, self.clock = path_factory, sqlite_port, clock_port').body[0],include_attributes=False));init.body.pop(0);init.args.kwonlyargs=[];init.args.kw_defaults=[]
        class Restore(ast.NodeTransformer):
            def visit_Attribute(self,node):
                if isinstance(node.value,ast.Name) and node.value.id=='self' and node.attr in ('paths','sqlite','clock'):return ast.copy_location(ast.Name({'paths':'Path','sqlite':'sqlite3','clock':'time'}[node.attr],node.ctx),node)
                return self.generic_visit(node)
        self.assertEqual(ast.dump(Restore().visit(model),include_attributes=False),ast.dump(original,include_attributes=False));self.assertEqual(len([n for n in original.body if isinstance(n,ast.FunctionDef)]),12)
    def test_whole_store_metadata_attempts_claim_recovery_retries_batches_sql_and_database_bytes_equal(self):
        outcomes=[];traces=[];files=[]
        for label,path,factory,database,clock in self.factories():
            store=factory(path);self.addCleanup(store.close);result={'missing':store.get('absent',{'default':True}),'empty_jobs':store.jobs(),'empty_active':store.active_batch()};store.put('accepted',{'label':'€','steps':[True,None,1]});result['accepted']=store.get('accepted');store.put('accepted',{'replacement':2});result['replacement']=store.get('accepted')
            run={'id':'10','run_attempt':'1','status':'in_progress'};store.discover('example/project',run);result['waiting']=store.jobs('waiting');store.discover('example/project',{**run,'status':'completed'});result['queued']=store.jobs('queued');store.discover('example/project',{**run,'run_attempt':2,'status':'completed'});result['superseded']=store.jobs();result['first_claim']=store.claim();store.discover('example/project',{**run,'run_attempt':2,'status':'completed','updated':'retained-payload'});result['working_payload_refresh']=store.jobs();result['retry_steps']=[]
            for step in range(4):
                job=next(row for row in store.jobs() if row['attempt']==2);store.failure(job,'temporary-read-error',True,7);result['retry_steps'].append(store.jobs());result['not_yet_eligible']=store.claim()
                if step<3:clock.value+=10000;result['retry_steps'].append(store.claim())
            store.discover('example/project',{'id':20,'run_attempt':1,'status':'completed'});result['second_claim']=store.claim();store.recover();result['recovered']=store.jobs();job=next(row for row in store.jobs() if row['run_id']==20);store.update(job,state='verified',snapshot='a'*64,snapshot_path='verified/result.json',error=None);store.recover();result['verified_history']=store.jobs();store.discover('example/project',{'id':20,'run_attempt':2,'status':'in_progress'});result['retained_verified_attempt']=store.jobs()
            with store.db:store.db.execute('INSERT INTO batches(id,base,state,manifest) VALUES (?,?,?,?)',('first','b'*40,'prepared',json.dumps({'snapshot':'a'*64})))
            result['prepared_batch']=store.active_batch();store.batch('first',state='open',commit_sha='c'*40,pr=7,url='https://example.invalid/review/7');result['opened_batch']=store.active_batch();store.batch('first',state='published');result['no_active_batch']=store.active_batch();result['whole_database']=self.dump(store);store.close();store.close();result['clock_observations']=clock.calls;result['after_close']=self.error(store.jobs);outcomes.append(result);traces.append(database.statements);files.append((path/'queue.sqlite3').read_bytes());self.assertEqual(set(p.name for p in path.iterdir()),{'queue.sqlite3'})
        self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(traces[0],traces[1]);self.assertEqual(files[0],files[1]);self.assertEqual(outcomes[0]['first_claim']['state'],'queued');self.assertEqual(outcomes[0]['working_payload_refresh'][-1]['state'],'working');self.assertEqual(outcomes[0]['retry_steps'][-1][-1]['state'],'held');self.completed.append({'all_12_methods_whole_native_outcomes_SQL_and_database_bytes_equal':True,'sqlite_version':sqlite3.sqlite_version,'clock_is_explicit_test_input_not_native_measurement':True})
    def test_invalid_updates_original_sql_errors_and_rollback_context_are_preserved(self):
        outcomes=[];traces=[]
        for label,path,factory,database,clock in self.factories():
            store=factory(path);self.addCleanup(store.close);store.discover('example/project',{'id':1,'run_attempt':1,'status':'completed'});job=store.jobs()[0];result={'empty_update':self.error(lambda:store.update(job)),'unknown_update':self.error(lambda:store.update(job,authority=True)),'bad_batch_field':self.error(lambda:store.batch('x',authority=True)),'original_empty_batch_SQL':self.error(lambda:store.batch('x')),'bad_discover':self.error(lambda:store.discover('example/project',{'id':'not-an-integer','run_attempt':1,'status':'completed'}))}
            with store.db:store.db.execute('INSERT INTO batches(id,base,state,manifest) VALUES (?,?,?,?)',('one','head','prepared','{}'))
            def conflict():
                with store.db:store.db.execute('INSERT INTO batches(id,base,state,manifest) VALUES (?,?,?,?)',('two','head','open','{}'))
            result['unique_active_batch']=self.error(conflict);result['active_after_rollback']=store.active_batch();result['whole_database']=self.dump(store);store.close();outcomes.append(result);traces.append(database.statements)
        self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(traces[0],traces[1]);self.assertEqual(outcomes[0]['unique_active_batch']['type'],'IntegrityError');self.assertEqual(outcomes[0]['original_empty_batch_SQL']['type'],'OperationalError');self.assertIn('ROLLBACK',traces[0])
    def test_existing_v2_namespace_is_closed_and_refused_without_schema_or_data_rewrite(self):
        outcomes=[]
        for label,path,factory,database,clock in self.factories():
            path.mkdir(mode=0o700)
            with sqlite3.connect(path/'queue.sqlite3') as seed:seed.execute('PRAGMA user_version=2');seed.execute('CREATE TABLE keep(value)');seed.execute("INSERT INTO keep VALUES ('immutable older namespace')")
            seed.close();before=(path/'queue.sqlite3').read_bytes();result=self.error(lambda:factory(path));self.assertEqual(result['type'],'ValueError');self.assertEqual(result['message'],'Consumer state requires a compatible versioned operator');self.assertEqual(database.statements,['PRAGMA user_version']);self.assertEqual(before,(path/'queue.sqlite3').read_bytes());self.assertEqual(self.error(lambda:database.connections[0].execute('SELECT 1'))['type'],'ProgrammingError');outcomes.append(result)
        self.assertEqual(outcomes[0],outcomes[1])
    def test_symlink_root_is_original_refusal_before_any_sqlite_connection(self):
        outcomes=[]
        for label,path,factory,database,clock in self.factories():
            target=self.top/(label+'-target');target.mkdir(mode=0o700);path.symlink_to(target,target_is_directory=True);outcomes.append(self.error(lambda:factory(path)));self.assertEqual(database.connections,[]);self.assertEqual(list(target.iterdir()),[])
        self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(outcomes[0]['message'],'Operations root must not be a symlink')
    def test_malformed_metadata_blob_and_nonserializable_inputs_keep_original_python_errors(self):
        outcomes=[];traces=[]
        for label,path,factory,database,clock in self.factories():
            store=factory(path);self.addCleanup(store.close)
            with store.db:store.db.execute('INSERT INTO meta VALUES (?,?)',('broken','invalid JSON'));store.db.execute('INSERT INTO meta VALUES (?,?)',('binary',b'\xff'))
            result={'malformed_json':self.error(lambda:store.get('broken')),'binary_decode':self.error(lambda:store.get('binary')),'input_JSON_type':self.error(lambda:store.put('unsupported',object())),'missing_job_field':self.error(lambda:store.failure({},'bad-input'))};store.close();outcomes.append(result);traces.append(database.statements)
        self.assertEqual(outcomes[0],outcomes[1]);self.assertEqual(traces[0],traces[1]);self.assertEqual(outcomes[0]['binary_decode']['type'],'UnicodeDecodeError')

if __name__=='__main__':unittest.main()
