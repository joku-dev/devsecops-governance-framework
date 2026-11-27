"""Whole immutable original and all seven method ASTs; isolated prototype only."""
from pathlib import Path
from contextlib import redirect_stdout,redirect_stderr
import argparse,ast,copy,hashlib,io,json,os,shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'tests/fixtures/v2-documentation-reconciliation-original'
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.documentation_reconciliation import DocumentationReconciliation,ORIGINAL_DESCRIPTION
CONTRACT=json.loads((B/'contract.json').read_bytes());FILENAME='reconcile_documentation_after_merge.py'

class GitPort:
 def __init__(self,root):self.root=root;self.calls=[]
 def run(self,command,**options):
  assert command[0]=='git' and options=={'cwd':self.root,'check':True,'capture_output':True,'text':True}
  assert command[1:4]==['diff','--name-only','--diff-filter=ACDMR'] and len(command)==5 or command==['git','ls-files','*.md']
  self.calls.append(list(command));return subprocess.run(command,**options,timeout=20)

def snapshot(root):
 return ({p.relative_to(root).as_posix():(p.read_bytes(),p.stat().st_mode&0o777) for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts},
         {p.relative_to(root).as_posix():p.stat().st_mode&0o777 for p in root.rglob('*') if p.is_dir() and '.git' not in p.relative_to(root).parts})
def restore(root,value):
 files,dirs=value
 for p in sorted(root.rglob('*'),key=lambda p:len(p.parts),reverse=True):
  name=p.relative_to(root).as_posix()
  if '.git' in p.relative_to(root).parts:continue
  if p.is_dir():
   if name not in dirs:p.rmdir()
  elif name not in files:p.unlink()
 for name,(raw,mode) in files.items():
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
  if not p.exists() or p.read_bytes()!=raw:p.write_bytes(raw)
  p.chmod(mode)
 for name,mode in dirs.items():(root/name).chmod(mode)

class WholeOriginal(unittest.TestCase):
 def setUp(self):
  previous=os.umask(0o077);self.addCleanup(os.umask,previous)
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.parent=Path(self.temp.name).resolve();self.serial=0
 def fixture(self,fmt='sha1',functional=True):
  self.serial+=1;root=self.parent/('data-'+str(self.serial));root.mkdir(mode=0o700)
  for name,raw in {'scripts/'+FILENAME:(B/'original.py.txt').read_bytes(),'README.md':b'# Original README\n','docs/operations/guides/repository-function-catalog.md':b'# Original catalog\n','docs/operations/guides/repository-technical-function-inventory.md':b'# Original inventory\n','links.md':b'[exists](README.md)\n[missing](docs/missing.md)\n[external](https://example.invalid/unused)\n[root](/README.md)\n','unreadable.md':b'\xff'}.items():
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.STDOUT).decode().strip()
  git('init','--object-format='+fmt,'--initial-branch=fixture')
  def commit(message):
   git('add','--force','.');git('-c','commit.gpgsign=false','-c','user.name=AXIOM isolated test','-c','user.email=fixture@invalid.example','commit','--quiet','-m',message);return git('rev-parse','HEAD')
  base=commit('base')
  p=root/('model/example.json' if functional else 'README.md');p.parent.mkdir(parents=True,exist_ok=True);p.write_text('new model\n' if functional else '# Only documentation changed\n')
  merge=commit('change');return root,['--base',base,'--merge',merge,'--pr','42','--title','Title <b>with</b> `quotes` and Ünicode','--body','## Summary\n- Preserve [text](https://example.invalid) and `code`.\n- Second item.\n## Checks\nnot a summary\n','--docs-build-status','caller-declared status; not executed by the reconciler']
 def compare(self,root,args,expected=0):
  before=snapshot(root);old=subprocess.run([sys.executable,'-B',str(root/'scripts'/FILENAME),*args],cwd=self.parent,capture_output=True,timeout=30,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  self.assertEqual(old.returncode,expected,old.stderr[-2500:]);after=snapshot(root);restore(root,before)
  process=GitPort(root);parser=lambda **options:argparse.ArgumentParser(prog=FILENAME,**options)
  kernel=DocumentationReconciliation(root,process=process,path_factory=Path,argument_parser=parser,argv=args);out,err=io.StringIO(),io.StringIO();error=None;code=0
  with redirect_stdout(out),redirect_stderr(err):
   try:code=kernel.main()
   except SystemExit as failure:code=0 if failure.code is None else failure.code
   except Exception as failure:code=1;error=failure
  self.assertEqual(code,old.returncode,(error,old.stderr[-2500:]));self.assertEqual(out.getvalue().encode(),old.stdout)
  if error is None:self.assertEqual(err.getvalue().encode(),old.stderr)
  else:self.assertTrue(old.stderr.decode().endswith(type(error).__name__+': '+str(error)+'\n'),(type(error).__name__,str(error),old.stderr[-2500:]))
  self.assertEqual(snapshot(root),after);return kernel,process,error
 def test_all_seven_original_function_AST_bodies_after_only_explicit_context_and_ports(self):
  raw=(B/'original.py.txt').read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),CONTRACT['original_sha256']);old={n.name:n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)}
  cls=next(n for n in ast.parse((ROOT/'scripts/lib/documentation_reconciliation.py').read_bytes()).body if isinstance(n,ast.ClassDef));new={n.name:n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name!='__init__'};self.assertEqual(set(old),set(new));self.assertEqual(len(old),7)
  fields={'self.root':'ROOT','self.readme':'README','self.catalog':'CATALOG','self.inventory':'INVENTORY','self.audit':'AUDIT','self.functional_roots':'FUNCTIONAL_ROOTS','self.markdown_link':'MARKDOWN_LINK','self.path_factory':'Path','self.description':'__doc__','self.process.run':'subprocess.run','self.argument_parser':'argparse.ArgumentParser',**{'self.'+name:name for name in old}}
  outer=self
  class Restore(ast.NodeTransformer):
   def visit_Attribute(self,node):
    value=ast.unparse(node)
    if value in fields:return ast.copy_location(ast.parse(fields[value],mode='eval').body,node)
    return self.generic_visit(node)
   def visit_Call(self,node):
    if ast.unparse(node.func)=='parser.parse_args':outer.assertEqual([ast.unparse(x) for x in node.args],['self.argv']);node.args=[]
    return self.generic_visit(node)
  for name,expected in old.items():
   with self.subTest(function=name):
    actual=copy.deepcopy(new[name]);self.assertEqual(actual.args.args.pop(0).arg,'self');actual=Restore().visit(actual);self.assertEqual(ast.dump(actual,include_attributes=False),ast.dump(expected,include_attributes=False))
 def test_whole_functional_cli_both_git_formats_full_four_exports_and_append_output(self):
  for fmt in ('sha1','sha256'):
   with self.subTest(fmt=fmt):
    root,args=self.fixture(fmt);output=root/'caller-output';output.write_bytes(b'existing unterminated value')
    self.compare(root,[*args,'--github-output',str(output)])
    self.assertEqual(output.read_bytes(),b'existing unterminated valuerequired=true\n')
    self.assertTrue((root/'generated/reports/documentation-refresh-audit.md').exists())
 def test_whole_nonfunctional_cli_both_formats_writes_only_false_append(self):
  for fmt in ('sha1','sha256'):
   root,args=self.fixture(fmt,functional=False);output=root/'caller-output';self.compare(root,[*args,'--github-output',str(output)]);self.assertEqual(output.read_bytes(),b'required=false\n');self.assertFalse((root/'generated').exists())
 def test_all_original_help_and_parser_streams_need_no_git(self):
  for args,code in ((['--help'],0),(['--unknown'],2)):
   root,_=self.fixture();_,process,_=self.compare(root,args,code);self.assertEqual(process.calls,[])
 def test_original_body_file_unicode_and_invalid_utf8_and_directory_error(self):
  for case in ('unicode','invalid','directory'):
   root,args=self.fixture();path=root/'body-Ü.txt'
   if case=='directory':path.mkdir()
   else:path.write_bytes('## Summary\n- 日本語 and Ünicode\n'.encode() if case=='unicode' else b'\xff')
   self.compare(root,[*args,'--body-file',str(path)],0 if case=='unicode' else 1)
 def test_original_missing_catalog_retains_already_written_readme(self):
  root,args=self.fixture();(root/'docs/operations/guides/repository-function-catalog.md').unlink();_,process,error=self.compare(root,args,1);self.assertEqual(type(error).__name__,'FileNotFoundError');self.assertIn('DOCS_REFRESH_LATEST',(root/'README.md').read_text());self.assertEqual(len(process.calls),1)
 def test_original_replacement_backslash_error_is_not_silently_sanitized(self):
  root,args=self.fixture();(root/'README.md').write_text('# README\n<!-- DOCS_REFRESH_LATEST:start -->\nold\n<!-- DOCS_REFRESH_LATEST:end -->\n');self.compare(root,[*args,'--body','## Summary\n- literal backslash \\q\n'],1)
 def test_original_bad_git_reference_fails_without_writing_outputs(self):
  root,args=self.fixture();self.compare(root,[*args,'--base','missing-reference'],1)

if __name__=='__main__':unittest.main(verbosity=2)
