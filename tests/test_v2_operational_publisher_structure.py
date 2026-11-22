"""Every whole original function and platform renderer after named port substitution."""
from pathlib import Path
import ast,copy,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
FIXTURE=ROOT/'tests/fixtures/v2-operational-publisher-original'
def original():
 c=json.loads((FIXTURE/'contract.json').read_bytes());row=c['files']['scripts/publish_operational_update.py'];raw=(FIXTURE/row['fixture']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];return ast.parse(raw)
def functions(file,cls):return {n.name:n for n in next(n for n in ast.parse((ROOT/file).read_bytes()).body if isinstance(n,ast.ClassDef) and n.name==cls).body if isinstance(n,ast.FunctionDef)}
class WholeOperationalPublisherStructure(unittest.TestCase):
 def test_all_five_complete_core_functions_and_all_original_constants_are_preserved(self):
  old=original();old_functions={n.name:n for n in old.body if isinstance(n,ast.FunctionDef)};new=functions('scripts/lib/operational_publication.py','OperationalPublisher');pub=old_functions['publish'];url=next(n.value for n in pub.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='run_url');pr=next(n.value for n in pub.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='pr');body=pr.args[1].values[next(i for i,k in enumerate(pr.args[1].keys) if k.value=='body')];dispatch=next(n for n in ast.walk(pub) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='api' and isinstance(n.args[1],ast.Dict) and len(n.args[1].keys)==1)
  mapping={'self.root':'ROOT','self.Path':'Path','self.git':'git','self.allowed':'allowed','self.selected_paths':'selected_paths','self.publish':'publish','self.process.run':'subprocess.run','self.environment':'os.environ','self.argument_parser':'argparse.ArgumentParser','self.profile.description':'__doc__','self.profile.check_workflows':'CHECK_WORKFLOWS'}
  literals={'output_key':'GITHUB_OUTPUT','summary_key':'GITHUB_STEP_SUMMARY','ref_key':'GITHUB_REF','repository_key':'GITHUB_REPOSITORY','run_id_key':'GITHUB_RUN_ID','attempt_key':'GITHUB_RUN_ATTEMPT','author_name':'github-actions[bot]','author_email':'41898282+github-actions[bot]@users.noreply.github.com'}
  imports={n.names[0].name:n for n in ast.walk(pub) if isinstance(n,ast.ImportFrom)}
  class Restore(ast.NodeTransformer):
   def visit_Assign(self,node):
    t=node.targets[0];key=t.id if isinstance(t,ast.Name) else t.elts[0].id
    return copy.deepcopy(imports[key]) if key in imports else self.generic_visit(node)
   def visit_Attribute(self,node):
    label=ast.unparse(node)
    if label in mapping:return ast.copy_location(ast.parse(mapping[label],mode='eval').body,node)
    if label.startswith('self.profile.') and label.rsplit('.',1)[1] in literals:return ast.copy_location(ast.Constant(value=literals[label.rsplit('.',1)[1]]),node)
    return self.generic_visit(node)
   def visit_BinOp(self,node):
    text=ast.unparse(node)
    values={"'user.name=' + self.profile.author_name":'user.name=github-actions[bot]',"'user.email=' + self.profile.author_email":'user.email=41898282+github-actions[bot]@users.noreply.github.com'}
    return ast.copy_location(ast.Constant(value=values[text]),node) if text in values else self.generic_visit(node)
   def visit_Call(self,node):
    name=ast.unparse(node.func)
    if name=='self.profile.run_url':return copy.deepcopy(url)
    if name=='self.profile.review_body':return copy.deepcopy(body)
    if name=='self.profile.pulls_endpoint':return copy.deepcopy(pr.args[0])
    if name=='self.profile.workflow_endpoint':return copy.deepcopy(dispatch.args[0])
    if name=='parser.parse_args':assert len(node.args)==1 and ast.unparse(node.args[0])=='self.argv';node.args=[]
    return self.generic_visit(node)
  for name in ('git','allowed','selected_paths','publish','main'):
   with self.subTest(name=name):
    node=copy.deepcopy(new[name]);self.assertEqual(node.args.args.pop(0).arg,'self')
    if name=='publish':self.assertEqual(ast.unparse(node.body.pop(0)),'if api is None:\n    api = self.provider_api');node.args.kw_defaults[-1]=ast.Name(id='github_api',ctx=ast.Load())
    self.assertEqual(ast.dump(Restore().visit(node),include_attributes=False),ast.dump(old_functions[name],include_attributes=False))
  source=ast.parse((ROOT/'scripts/lib/operational_publication.py').read_bytes())
  for name in ('LEDGERS','COMMON','SCOPES'):
   a=next(n for n in old.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name);b=next(n for n in source.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id==name);self.assertEqual(ast.dump(a,include_attributes=False),ast.dump(b,include_attributes=False))
  text=(ROOT/'scripts/lib/operational_publication.py').read_text();self.assertNotIn('github',text.lower());self.assertNotIn('GITHUB_',text);self.assertNotIn('subprocess',text);self.assertNotIn('lib.providers',text)
 def test_whole_original_provider_POST_helper_lives_in_the_explicit_adapter(self):
  old=next(n for n in original().body if isinstance(n,ast.FunctionDef) and n.name=='github_api');new=copy.deepcopy(functions('scripts/lib/providers/operational_publication_api.py','LegacyOperationalPublicationAPI')['__call__']);new.name='github_api';self.assertEqual(new.args.args.pop(0).arg,'self');command=next(n for n in ast.walk(old) if isinstance(n,ast.Call) and ast.unparse(n.func)=='subprocess.run').args[0]
  class Restore(ast.NodeTransformer):
   def visit_Call(self,n):
    if ast.unparse(n.func)=='self.process.run':n.func=ast.parse('subprocess.run',mode='eval').body
    elif ast.unparse(n.func)=='self.profile.api_command':return copy.deepcopy(command)
    return self.generic_visit(n)
  self.assertEqual(ast.dump(Restore().visit(new),include_attributes=False),ast.dump(old,include_attributes=False))
 def test_every_platform_renderer_and_binding_matches_original(self):
  from lib.providers.operational_publication_profile import LegacyOperationalPublicationProfile as P
  old=original();self.assertEqual(P.description,ast.get_docstring(old));self.assertEqual(P.check_workflows,ast.literal_eval(next(n.value for n in old.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='CHECK_WORKFLOWS')))
  self.assertEqual(P.api_command('repos/example/project/pulls'),['gh','api','--method','POST','repos/example/project/pulls','--input','-']);self.assertEqual(P.run_url('example/project','44','2'),'https://github.com/example/project/actions/runs/44/attempts/2')
if __name__=='__main__':unittest.main(verbosity=2)
