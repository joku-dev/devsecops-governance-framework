"""Whole original synthetic packets and POSIX demo sequences; prototype only."""
from pathlib import Path
from contextlib import redirect_stdout,redirect_stderr
import argparse,ast,base64,copy,errno,hashlib,io,json,os,shutil,subprocess,sys,tempfile,unittest
from unittest.mock import patch
from contextlib import nullcontext,contextmanager
import fcntl
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.synthetic_ledger_context import compose,PROGRAMS
from lib.repository_schemas import RepositorySchemas
from lib.v2_boundary import violations
from test_v2_synthetic_lifecycle_reports import materialize_original_sources
CONTRACT=json.loads((ROOT/'tests/fixtures/v2-synthetic-ledger-original/contract.json').read_bytes())


def original_sources(data):
 materialize_original_sources(data)
 for name,row in CONTRACT['sources'].items():
  raw=(ROOT/row['fixture']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];target=data/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)


def snapshot(root):
 files={p.relative_to(root).as_posix():(p.read_bytes(),p.stat().st_mode&0o777) for p in root.rglob('*') if p.is_file()}
 dirs={p.relative_to(root).as_posix():p.stat().st_mode&0o777 for p in root.rglob('*') if p.is_dir()}
 return files,dirs


@contextmanager
def selected_cwd(root):
 previous=Path.cwd()
 try:
  os.chdir(root);yield
 finally:os.chdir(previous)

def pending_snapshot(root):
 """Normalize only the one observed random pending name; preserve all bytes,
 modes, link counts and complete inode-equivalence groups inside this tree."""
 files,dirs=snapshot(root);pending=[n for n in files if Path(n).name.startswith('.pending-')]
 if len(pending)!=1:raise AssertionError('Exactly one original temporary publication must remain')
 name=pending[0];canonical=str(Path(name).parent/('.pending-'+hashlib.sha256(files[name][0]).hexdigest()))
 names={n:canonical if n==name else n for n in files};assert len(set(names.values()))==len(files)
 groups={};links={}
 for name in files:
  info=(root/name).stat();groups.setdefault((info.st_dev,info.st_ino),[]).append(names[name]);links[names[name]]=info.st_nlink
 aliases=[]
 for names_in_group in groups.values():
  if len(names_in_group)>1:
   assert len(names_in_group)==2 and all(links[n]==2 for n in names_in_group)
   aliases.append(sorted(names_in_group))
 return ({names[n]:v for n,v in files.items()},dirs,links,sorted(aliases))

def restore(root,value):
 files,dirs=value
 for p in sorted(root.rglob('*'),key=lambda p:len(p.parts),reverse=True):
  relative=p.relative_to(root).as_posix()
  if p.is_dir():
   if relative not in dirs:p.rmdir()
  elif relative not in files:p.unlink()
 for name,(raw,mode) in files.items():
  p=root/name
  # Keep unchanged read-only source preimages intact. Only disposable data
  # actually changed by the reference run needs restoration.
  if not p.exists() or p.read_bytes()!=raw:
   if p.exists():p.chmod(p.stat().st_mode&0o777|0o600)
   p.write_bytes(raw)
  if p.stat().st_mode&0o777!=mode:p.chmod(mode)
 for name,mode in dirs.items():(root/name).chmod(mode)


class WholeSyntheticLedgerCore(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()/'data';self.root.mkdir()
  for name in ('model','schemas','docs/examples','tests/fixtures/governance-lifecycle'):
   shutil.copytree(ROOT/name,self.root/name,ignore=shutil.ignore_patterns('__pycache__','.DS_Store'))
  original_sources(self.root)
 def context(self,args):
  schemas=RepositorySchemas(self.root,identifier_bases=('https://joku-dev.github.io/devsecops-governance-framework/schemas/',))
  return compose(self.root,validator_class=schemas,path_factory=Path,argument_parser=argparse.ArgumentParser,argv=list(args),native=os,locking=fcntl,temporary=tempfile)
 def compare(self,name,args,code=0,fault=None):
  command=[sys.executable,'-B',str(self.root/'scripts'/PROGRAMS[name][0]),*args]
  if fault:
   target,nth=fault
   driver='''import errno,runpy,sys,importlib
from unittest.mock import patch
path=sys.argv[1];sys.argv=sys.argv[1:]
target=TARGET;nth=NTH;module,name=target.rsplit('.',1);original=getattr(importlib.import_module(module),name);calls=[]
def inject(*args,**kwargs):
 calls.append(1)
 if len(calls)==nth:raise OSError(errno.EIO,'injected '+target+'-'+str(nth))
 return original(*args,**kwargs)
with patch(target,side_effect=inject):runpy.run_path(path,run_name='__main__')
'''.replace('TARGET',repr(target)).replace('NTH',str(nth))
   command=[sys.executable,'-B','-c',driver,str(self.root/'scripts'/PROGRAMS[name][0]),*args]
  old=subprocess.run(command,cwd=self.root,capture_output=True,timeout=90,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(self.root/'scripts')})
  self.assertEqual(old.returncode,code,old.stderr[-2500:]);expected=pending_snapshot(self.root) if fault and fault[0]=='os.unlink' else snapshot(self.root);restore(self.root,self.before)
  ctx,programs=self.context(args);out,err=io.StringIO(),io.StringIO();error=None;actual=0
  injection=nullcontext()
  if fault:
   target,nth=fault;module,attribute=target.rsplit('.',1);native=getattr(__import__(module),attribute);calls=[]
   def inject(*args,**kwargs):
    calls.append(1)
    if len(calls)==nth:raise OSError(errno.EIO,'injected '+target+'-'+str(nth))
    return native(*args,**kwargs)
   injection=patch(target,side_effect=inject)
  with selected_cwd(self.root),injection,redirect_stdout(out),redirect_stderr(err):
   try:programs[name].main()
   except SystemExit as e:actual=0 if e.code is None else e.code
   except Exception as e:actual=1;error=e
  self.last_error=error
  self.assertEqual(actual,old.returncode,(name,error));self.assertEqual(out.getvalue().encode(),old.stdout)
  if error is None:self.assertEqual(err.getvalue().encode(),old.stderr)
  else:self.assertTrue(old.stderr.decode().endswith(type(error).__name__+': '+str(error)+'\n'))
  self.assertEqual(pending_snapshot(self.root) if fault and fault[0]=='os.unlink' else snapshot(self.root),expected);return ctx,programs
 def demo(self,name):
  ledger=self.root/'new-ledger';output=self.root/'exports/index.json';args=['--ledger',str(ledger),'--output',str(output)]
  if name in ('closure','exception'):args+=['--report',str(self.root/'exports/report.md')]
  self.before=snapshot(self.root);self.compare(name,args)
  # The original default rerun guard must leave accepted history intact.
  self.before=snapshot(self.root);self.compare(name,args,1)
 def test_complete_synthetic_demo_all_history_bytes_modes_stdout_and_nonempty_guard(self):self.demo('synthetic')
 def test_complete_action_demo_all_history_bytes_modes_stdout_and_nonempty_guard(self):self.demo('action')
 def test_complete_closure_demo_all_history_bytes_modes_stdout_and_nonempty_guard(self):self.demo('closure')
 def test_complete_exception_demo_all_history_bytes_modes_stdout_and_nonempty_guard(self):self.demo('exception')
 def test_all_six_original_help_and_unknown_parser_streams(self):
  for name in PROGRAMS:
   for args,code in ((['--help'],0),(['--unknown'],2)):
    with self.subTest(program=name,args=args):self.before=snapshot(self.root);self.compare(name,args,code)
 def selected_transaction(self,scenario,kind):
  paths=sorted((ROOT/'governance/lifecycle'/scenario/'transactions').glob('*.json'))
  for index,path in enumerate(paths):
   row=json.loads(path.read_bytes());record=row.get('record') or row.get('observation')
   if record and record['record_type']==kind:return paths,index,row,record
  self.fail('Missing original transaction '+kind)
 def record_arguments(self,scenario,kind,suffix):
  paths,index,row,record=self.selected_transaction(scenario,kind);ledger=self.root/('ledger-'+suffix);transactions=ledger/'transactions';transactions.mkdir(parents=True)
  for path in paths[:index]:(transactions/path.name).write_bytes(path.read_bytes())
  source=self.root/('inputs-'+suffix);source.mkdir();record_file=source/'record.json';record_file.write_bytes(json.dumps(record).encode())
  for uri,encoded in row['resources'].items():
   self.assertTrue(uri.startswith('fixture://'));filename=uri[len('fixture://'):];self.assertEqual(Path(filename).name,filename);(source/filename).write_bytes(base64.b64decode(encoded,validate=True))
  return ['--synthetic','--ledger',str(ledger),'--record',str(record_file),'--resources',str(source),'--expected-revision',str(row['expected_revision'])],ledger,record_file,record,source
 def test_complete_original_synthetic_observation_intake_and_duplicate_and_stale_revision(self):
  paths,index,row,record=self.selected_transaction('synthetic-closure','observation');self.assertEqual(index,0)
  ledger=self.root/'intake-observations';inputs=self.root/'observation-inputs';inputs.mkdir()
  report=base64.b64decode(row['resources'][record['body']['snapshot_ref']['uri']],validate=True)
  (inputs/'report.json').write_bytes(report)
  (inputs/'context.json').write_bytes(json.dumps(record['body']['source_context']).encode())
  (inputs/'trust.json').write_bytes(json.dumps(record['body']['trust']).encode())
  args=['--synthetic','--ledger',str(ledger),'--report',str(inputs/'report.json'),'--context',str(inputs/'context.json'),'--trust',str(inputs/'trust.json'),'--recorded-at',record['recorded_at'],'--policy-version',record['body']['policy_version'],'--expected-revision','0']
  self.before=snapshot(self.root);ctx,_=self.compare('observation',args)
  self.assertEqual(len(ctx.store.load_transactions(ledger)),1)
  self.before=snapshot(self.root);self.compare('observation',args)
  # A new delivery with the old expected revision must not append a transaction.
  source=json.loads((inputs/'context.json').read_bytes());source['run_id']='another-original-intake-delivery';(inputs/'context.json').write_bytes(json.dumps(source).encode())
  trust=json.loads((inputs/'trust.json').read_bytes());trust['capture']['source']['run_id']=source['run_id'];(inputs/'trust.json').write_bytes(json.dumps(trust).encode())
  self.before=snapshot(self.root);self.compare('observation',args,1)
  self.assertEqual(str(self.last_error),'Stale expected finding revision')
  self.assertEqual(len(ctx.store.load_transactions(ledger)),1)
 def test_complete_original_decision_remediation_closure_and_exception_intake_and_duplicate(self):
  for kind,scenario in (('decision','synthetic-closure'),('remediation','synthetic-closure'),('closure','synthetic-closure'),('exception','synthetic-exceptions')):
   with self.subTest(kind=kind):
    args,ledger,_,record,_=self.record_arguments(scenario,kind,kind);self.before=snapshot(self.root);ctx,_=self.compare('record',args)
    self.assertEqual(ctx.store.load_transactions(ledger)[-1]['record'],record)
    self.before=snapshot(self.root);self.compare('record',args)
 def test_original_intake_live_URI_traversal_and_symlink_guards_leave_ledger_unchanged(self):
  for attack in ('live','traversal','symlink'):
   with self.subTest(attack=attack):
    args,ledger,path,record,resources=self.record_arguments('synthetic-closure','decision','guard-'+attack)
    ref=record['approval']['proof_ref']
    if attack=='live':ref['uri']='https://example.invalid/not-a-fixture'
    elif attack=='traversal':ref['uri']='fixture://../escape.json'
    else:
     target=resources/ref['uri'][len('fixture://'):];raw=target.read_bytes();target.unlink();other=resources/'other-resource.json';other.write_bytes(raw);target.symlink_to(other)
    path.write_bytes(json.dumps(record).encode());self.before=snapshot(self.root);self.compare('record',args,1)
    self.assertEqual(str(self.last_error),{'live':'Live resources are not supported','traversal':'Fixture resources must have flat filenames','symlink':'Fixture resource cannot be a symlink'}[attack])
    if attack=='symlink':self.assertTrue(target.is_symlink())
 def publication_error(self,target,nth,*,published):
  ledger=self.root/'failing-ledger';args=['--ledger',str(ledger),'--output',str(self.root/'output.json')]
  self.before=snapshot(self.root);ctx,_=self.compare('synthetic',args,1,fault=(target,nth))
  self.assertFalse((self.root/'output.json').exists());transactions=list((ledger/'transactions').glob('*.json')) if (ledger/'transactions').exists() else []
  self.assertEqual(len(transactions),int(published));self.assertFalse(list(ledger.rglob('.pending-*')))
  if published:self.assertEqual(len(ctx.store.load_transactions(ledger)),1)
 def test_whole_original_file_fsync_failure_leaves_no_published_transaction(self):self.publication_error('os.fsync',1,published=False)
 def test_whole_original_directory_fsync_failure_retains_already_published_transaction(self):self.publication_error('os.fsync',2,published=True)
 def test_whole_original_link_failure_keeps_empty_ledger_and_cleans_temporary(self):self.publication_error('os.link',1,published=False)
 def test_whole_original_writer_lock_error_keeps_lock_file_and_no_transaction(self):self.publication_error('fcntl.flock',1,published=False)
 def test_complete_original_relative_unicode_ledger_and_output_paths(self):
  self.before=snapshot(self.root);self.compare('closure',['--ledger','ledger-Ä','--output','exports-Ä/index.json','--report','exports-Ä/report.md'])
 def test_whole_original_unlink_failure_retains_publication_and_temporary_alias_and_duplicate_retry(self):
  ledger=self.root/'unlink-failure';args=['--ledger',str(ledger),'--output',str(self.root/'not-written.json')]
  self.before=snapshot(self.root);ctx,_=self.compare('synthetic',args,1,fault=('os.unlink',1))
  pending=list((ledger/'transactions').glob('.pending-*'));published=list((ledger/'transactions').glob('*.json'))
  self.assertEqual(len(pending),1);self.assertEqual(len(published),1);self.assertEqual(pending[0].stat().st_ino,published[0].stat().st_ino);self.assertEqual(published[0].stat().st_nlink,2)
  history=ctx.store.load_transactions(ledger);self.assertEqual(len(history),1);tx=history[0]
  resources={uri:base64.b64decode(raw,validate=True) for uri,raw in tx['resources'].items()}
  profile=json.loads((self.root/'model/governance/lifecycle/synthetic-grs002-profile.json').read_bytes());before=pending_snapshot(self.root)
  result=ctx.store.append_observation(ledger,tx['observation'],resources,profile,expected_revision=0)
  self.assertEqual(result,{'outcome':'duplicate','transaction_ref':None});self.assertEqual(pending_snapshot(self.root),before)
 def test_all24_original_function_AST_bodies_after_only_explicit_root_context_and_effect_ports(self):
  classes={}
  for filename in ('synthetic_ledger_packets.py','synthetic_ledger_store.py','synthetic_ledger_programs.py'):
   classes.update({n.name:n for n in ast.parse((ROOT/'scripts/lib'/filename).read_bytes()).body if isinstance(n,ast.ClassDef)})
  sources={
   'scripts/lib/governance_lifecycle/synthetic.py':('SyntheticObservations',None),
   'scripts/lib/governance_lifecycle/synthetic_actions.py':('SyntheticActions',None),
   'scripts/lib/governance_lifecycle/synthetic_exceptions.py':('SyntheticExceptions',None),
   'scripts/lib/governance_lifecycle/store.py':('SyntheticLedgerStore',None),
   'scripts/run_governance_lifecycle_synthetic_demo.py':('SyntheticHistoryDemo','DEMO_AS_OF'),
   'scripts/run_governance_lifecycle_action_demo.py':('SyntheticActionDemo','ACTION_AS_OF'),
   'scripts/run_governance_lifecycle_closure_demo.py':('SyntheticClosureDemo','PILOT_AS_OF'),
   'scripts/run_governance_lifecycle_exception_demo.py':('SyntheticExceptionDemo','EXCEPTION_AS_OF'),
   'scripts/intake_governance_lifecycle_observation.py':('SyntheticObservationIntake',None),
   'scripts/intake_governance_lifecycle_action.py':('SyntheticActionIntake',None)}
  mapping={'self.path_factory':'Path','self.native':'os','self.locking':'fcntl','self.temporary':'tempfile','self.default_profile':'DEFAULT_PROFILE','self.description':'__doc__',
   'self.argument_parser':'argparse.ArgumentParser',
   'self.context.demo_synthetic.run_demo':'run_demo','self.context.report_pilot.generate':'generate','self.context.report_exceptions.generate':'generate','self.context.synthetic.synthetic_packet':'synthetic_packet','self.context.synthetic_actions.resource':'resource'}
  for component,names in {'adapter':('json_bytes','strict_json','adapt_grs002'),'contracts':('require','approval_target','record_ref','versioned_ref'),'kernel':('project','prepare_transaction','replay','transaction_name','transaction_ref'),'decisions':('progress_statement','prepare_action_transaction'),'closure':('prepare_closure_transaction',),'exceptions':('prepare_exception_transaction','exception_profile'),'store':('load_transactions','append_observation','append_action','append_closure','append_exception'),'synthetic_actions':('decision_packet','remediation_packet','closure_packet'),'synthetic_exceptions':('exception_packet',)}.items():
   for name in names:mapping['self.context.'+component+'.'+name]=name
  total=0
  for source,(cls,constant) in sources.items():
   raw=(ROOT/CONTRACT['sources'][source]['fixture']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),CONTRACT['sources'][source]['sha256']);original=ast.parse(raw)
   old={n.name:n for n in original.body if isinstance(n,ast.FunctionDef)};new={n.name:n for n in classes[cls].body if isinstance(n,ast.FunctionDef) and n.name!='__init__'};self.assertEqual(set(old),set(new));total+=len(old)
   fields={**mapping,**{'self.'+name:name for name in old},'self.root':'ROOT'}
   if constant:fields['self.as_of']=constant
   if cls=='SyntheticActionDemo':fields['self.root']='Path(__file__).resolve().parents[1]'
   class Restore(ast.NodeTransformer):
    def visit_Attribute(self,node):
     value=ast.unparse(node)
     if value in fields:return ast.copy_location(ast.parse(fields[value],mode='eval').body,node)
     return self.generic_visit(node)
    def visit_Call(self,node):
     if isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='parser' and node.func.attr=='parse_args':
      self_outer.assertEqual([ast.unparse(x) for x in node.args],['self.argv']);node.args=[]
     return self.generic_visit(node)
   self_outer=self
   for name,expected in old.items():
    with self.subTest(source=source,function=name):
     actual=copy.deepcopy(new[name]);self.assertEqual(actual.args.args.pop(0).arg,'self');actual=Restore().visit(actual)
     if cls=='SyntheticLedgerStore' and isinstance(expected.body[0],ast.ImportFrom):actual.body.insert(0,copy.deepcopy(expected.body[0]))
     self.assertEqual(ast.dump(actual,include_attributes=False),ast.dump(expected,include_attributes=False))
  self.assertEqual(total,24)
 def test_new_core_has_no_provider_or_legacy_imports(self):
  for name in ('synthetic_ledger_packets.py','synthetic_ledger_store.py','synthetic_ledger_programs.py','synthetic_ledger_context.py'):
   p=ROOT/'scripts/lib'/name;self.assertEqual(violations(str(p.relative_to(ROOT)),p.read_text()),[])

 def test_whole_source_compatibility_is_excluded_from_active_package_and_fingerprint(self):
  from lib.v2_source import selected_paths
  from lib.portable import runtime
  names={'synthetic':'run_governance_lifecycle_synthetic_demo.py',
   'action':'run_governance_lifecycle_action_demo.py','closure':'run_governance_lifecycle_closure_demo.py',
   'exception':'run_governance_lifecycle_exception_demo.py','observation':'intake_governance_lifecycle_observation.py',
   'record':'intake_governance_lifecycle_action.py'}
  excluded=set()
  for key,name in names.items():
   source='scripts/'+name;legacy='scripts/lib/providers/legacy_synthetic_ledger_'+key+'.py'
   entry=CONTRACT['sources'][source]
   self.assertEqual((ROOT/legacy).read_bytes(),(ROOT/entry['fixture']).read_bytes())
   self.assertIn('legacy_synthetic_ledger_'+key,(ROOT/source).read_text())
   excluded.update((source,legacy))
  self.assertFalse(excluded&set(selected_paths(ROOT)))
  observed=[];original=runtime.file_digest
  def digest(path):
   observed.append(str(path.relative_to(ROOT)))
   return original(path)
  with patch.object(runtime,'file_digest',side_effect=digest):runtime.source_digest()
  self.assertFalse(excluded&set(observed))


if __name__=='__main__':unittest.main()
