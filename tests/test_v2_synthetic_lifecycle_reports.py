"""Whole immutable original five generator bodies, complete render bytes and parsers."""
from contextlib import redirect_stdout,redirect_stderr
from pathlib import Path,PurePosixPath
from types import SimpleNamespace
import argparse,ast,copy,hashlib,io,json,os,shutil,subprocess,sys,tempfile,unittest

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
from lib import synthetic_lifecycle_reports as core
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.v2_boundary import violations
from jsonschema import Draft202012Validator

REFERENCES={
 'index':('generate_governance_lifecycle_index.py','SyntheticIndex','59b3571afeac364764ee23d40399f388b940b2cc3f0d0a8c87751a366f0f22af'),
 'pilot':('generate_governance_lifecycle_pilot.py','SyntheticPilot','db8f9541db65aafc3544b8182bebfdc5b295ed8134c03b0d43be02d13cae6079'),
 'exceptions':('generate_governance_lifecycle_exceptions.py','SyntheticExceptions','2821f676ebb2482cca2feab0c5109b51d5b0298c16d3c7906783a736753204df'),
 'overview':('generate_governance_lifecycle_overview.py','SyntheticOverview','0fd464a7a05a74ec6de8393d4323651b58d2ced8d03742f09b3dae046d569c38'),
 'viewer':('generate_governance_lifecycle_viewer.py','SyntheticViewer','98763089ef2c2328670695da339573346af746d92697a08ffa26cc4b8c886d65'),
}
PORTS={'require':('contracts','require'),'project':('kernel','project'),'load_transactions':('store','load_transactions'),'strict_json':('adapter','strict_json'),'json_bytes':('adapter','json_bytes'),'record_ref':('contracts','record_ref'),'schema_validator':('contracts','schema_validator'),'timestamp':('contracts','timestamp'),'transaction_ref':('kernel','transaction_ref')}

def frozen(name):
 filename,cls,sha=REFERENCES[name];p=ROOT/'tests/fixtures/v2-repository-validation'/('history-'+filename+'.txt');raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==sha;return p,raw

def materialize_original_sources(root):
 """Whole immutable V1 modules in an isolated oracle, with no Git history."""
 for directory in ('scripts/lib','scripts/lib/governance_lifecycle'):
  p=root/directory;p.mkdir(parents=True,exist_ok=True);(p/'__init__.py').write_bytes(b'')
 fixture=ROOT/'tests/fixtures/v2-repository-validation';contract=json.loads((fixture/'contract.json').read_bytes())
 for row in contract['lifecycle_helpers'].values():
  raw=(fixture/row['fixture']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['source_sha256'];(root/row['source_path']).write_bytes(raw)
 fixture=ROOT/'tests/fixtures/v2-intake-records';row=json.loads((fixture/'contract.json').read_bytes())['sources']['scripts/lib/result_ledger.py'];raw=(fixture/row['file']).read_bytes()
 assert hashlib.sha256(raw).hexdigest()=='b16ec64a034326e92fb44dea365903f3bf8b7309c00dd6d6d1d01dbe4c099f1c';(root/'scripts/lib/result_ledger.py').write_bytes(raw)
 for name,(filename,_,_) in REFERENCES.items():(root/'scripts'/filename).write_bytes(frozen(name)[1])

def original_value(name,method,value):
 # Execute the complete original module and complete original dependencies in
 # their own process. The V2 test process never imports the old lifecycle lib.
 with tempfile.TemporaryDirectory() as temporary:
  root=Path(temporary).resolve();materialize_original_sources(root)
  if method=='render_viewer':
   shutil.copytree(ROOT/'schemas',root/'schemas');(root/'scripts/templates').mkdir();(root/'scripts/templates/governance-lifecycle-viewer.html').write_bytes((ROOT/'scripts/templates/governance-lifecycle-viewer.html').read_bytes())
  code='import importlib,json,sys; module=importlib.import_module(sys.argv[1]); print(json.dumps(getattr(module,sys.argv[2])(json.load(sys.stdin))))'
  result=subprocess.run([sys.executable,'-B','-c',code,REFERENCES[name][0].removesuffix('.py'),method],cwd=root,input=json.dumps(value,ensure_ascii=True).encode(),capture_output=True,timeout=60,env={**os.environ,'PYTHONPATH':str(root/'scripts'),'PYTHONDONTWRITEBYTECODE':'1'})
  assert result.returncode==0,result.stderr.decode()[-2000:];return json.loads(result.stdout)

def original(name):return SimpleNamespace(**{method:(lambda value,m=method:original_value(name,m,value)) for method in ('render_report','render_viewer','safe_json')})

def generator(name,root,context,args=(),overview=None):
 filename,cls,_=REFERENCES[name]
 return getattr(core,cls)(root,context,path_factory=type(root),argument_parser=lambda **kw:argparse.ArgumentParser(prog=filename,**kw),argv=list(args),overview=overview)


class WholeSyntheticLifecycleGenerators(unittest.TestCase):
 def test_all19_original_function_bodies_after_only_explicit_ports_and_root_defaults(self):
  parsed=ast.parse((ROOT/'scripts/lib/synthetic_lifecycle_reports.py').read_bytes());classes={n.name:n for n in parsed.body if isinstance(n,ast.ClassDef)};total=0
  for name,(filename,cls,_) in REFERENCES.items():
   tree=ast.parse(frozen(name)[1]);old={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)};new={n.name:n for n in classes[cls].body if isinstance(n,ast.FunctionDef) and n.name!='__init__'}
   self.assertEqual(set(old),set(new));names=set(old);total+=len(old)
   constants={t.id for n in tree.body if isinstance(n,ast.Assign) for t in n.targets if isinstance(t,ast.Name)}|{'DEFAULT_PROFILE'}
   fields={'root':'ROOT','path_factory':'Path','description':'__doc__',**{k:k for k in names|constants}}
   class Restore(ast.NodeTransformer):
    def visit_Attribute(self,node):
     if isinstance(node.value,ast.Name) and node.value.id=='self':
      if node.attr in fields:return ast.copy_location(ast.Name(fields[node.attr],node.ctx),node)
      if node.attr=='argument_parser':return ast.copy_location(ast.Attribute(ast.Name('argparse',ast.Load()),'ArgumentParser',node.ctx),node)
     if isinstance(node.value,ast.Attribute):
      value=node.value
      if isinstance(value.value,ast.Name) and value.value.id=='self' and value.attr=='overview' and node.attr=='validate_overview':return ast.copy_location(ast.Name('validate_overview',node.ctx),node)
      if isinstance(value.value,ast.Attribute) and isinstance(value.value.value,ast.Name) and value.value.value.id=='self' and value.value.attr=='context':
       for key,(component,method) in PORTS.items():
        if value.attr==component and node.attr==method:return ast.copy_location(ast.Name(key,node.ctx),node)
     return self.generic_visit(node)
    def visit_Call(self,node):
     if isinstance(node.func,ast.Attribute) and isinstance(node.func.value,ast.Name) and node.func.value.id=='parser' and node.func.attr=='parse_args':
      assert len(node.args)==1 and ast.unparse(node.args[0])=='self.argv';node.args=[]
     return self.generic_visit(node)
   for method,expected in old.items():
    with self.subTest(source=filename,method=method):
     actual=copy.deepcopy(new[method]);self.assertEqual(actual.args.args.pop(0).arg,'self')
     for index,value in enumerate(actual.args.defaults):
      if isinstance(value,ast.Name) and value.id=='_OMITTED':
       argument=actual.args.args[len(actual.args.args)-len(actual.args.defaults)+index].arg
       guard=actual.body.pop(0);self.assertEqual(ast.unparse(guard),'if '+argument+' is _OMITTED:\n    '+argument+' = self.root');actual.args.defaults[index]=ast.Name('ROOT',ast.Load())
     actual=Restore().visit(actual);self.assertEqual(ast.dump(actual,include_attributes=False),ast.dump(expected,include_attributes=False))
  self.assertEqual(total,19);self.assertEqual(violations('scripts/lib/synthetic_lifecycle_reports.py',(ROOT/'scripts/lib/synthetic_lifecycle_reports.py').read_text()),[])
 def test_construction_retains_original_defaults_without_selected_data_access(self):
  root=PurePosixPath('/explicit/data');context=object()
  for name in REFERENCES:generator(name,root,context)
  item=generator('index',root,context);self.assertEqual(item.DEFAULT_LEDGER,root/'governance/lifecycle/synthetic');self.assertEqual(item.DEFAULT_INDEX,root/'status/governance-lifecycle-synthetic-index.json')
  self.assertEqual(generator('pilot',root,context).DEFAULT_PROFILE,item.DEFAULT_PROFILE)
  self.assertEqual(generator('exceptions',root,context).DEFAULT_PROFILE,item.DEFAULT_PROFILE)
 def test_help_and_parser_two_keep_whole_actual_original_streams_without_data_access(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);oracle=Path(temporary.name).resolve();materialize_original_sources(oracle)
  for name,(filename,_,_) in REFERENCES.items():
   for args,expected in ((['--help'],0),(['--unknown-argument'],2)):
    with self.subTest(generator=name,args=args):
     self.assertEqual((oracle/'scripts'/filename).read_bytes(),frozen(name)[1])
     p=subprocess.run([sys.executable,str(oracle/'scripts'/filename),*args],cwd=oracle,capture_output=True,timeout=30,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
     item=generator(name,PurePosixPath('/missing/selected/data'),object(),args);out,err=io.StringIO(),io.StringIO()
     with redirect_stdout(out),redirect_stderr(err),self.assertRaises(SystemExit) as caught:item.main()
     self.assertEqual(caught.exception.code,expected);self.assertEqual(p.returncode,expected);self.assertEqual(out.getvalue().encode(),p.stdout);self.assertEqual(err.getvalue().encode(),p.stderr)
 def test_all_complete_current_synthetic_report_and_CSP_viewer_bytes_equal_original(self):
  context=RepositoryLifecycle(ROOT,validator_class=Draft202012Validator,path_factory=Path)
  overview=generator('overview',ROOT,context)
  for name,path in (('pilot','status/governance-lifecycle-closure-index.json'),('exceptions','status/governance-lifecycle-exception-index.json'),('overview','status/governance-lifecycle-overview.json')):
   with self.subTest(generator=name):
    value=json.loads((ROOT/path).read_bytes());self.assertEqual(generator(name,ROOT,context).render_report(value),original(name).render_report(value))
  value=json.loads((ROOT/'status/governance-lifecycle-overview.json').read_bytes())
  self.assertEqual(generator('viewer',ROOT,context,overview=overview).render_viewer(value),original('viewer').render_viewer(value))
 def test_whole_original_JSON_values_unicode_and_script_termination_escape(self):
  item=generator('viewer',PurePosixPath('/explicit/data'),object());value={'nested':['</script><script>bad</script>','&<>\u2028\u2029','quotes"\\'], 'true':True,'null':None,'number':3.5}
  rendered=item.safe_json(value);self.assertEqual(rendered,original('viewer').safe_json(value));self.assertEqual(json.loads(rendered),value);self.assertNotIn('</script>',rendered);self.assertNotIn('\u2028',rendered);self.assertNotIn('\u2029',rendered)


if __name__=='__main__':unittest.main()
