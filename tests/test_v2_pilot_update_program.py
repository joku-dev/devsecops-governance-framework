"""Complete immutable original runner and operating-write bodies after declared ports."""
from pathlib import Path
import ast,copy,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
FIXTURE=ROOT/'tests/fixtures/v2-pilot-update-original'
NAMES={'self.root':'ROOT','self.Path':'Path','self.context.contracts.require':'require','self.context.adapter.strict_json':'strict_json','self.context.admission.VALIDATION_LEDGER':'VALIDATION_LEDGER','self.context.actions.ACTION_LEDGER':'ACTION_LEDGER','self.receipts.append_capture':'append_capture','self.context.admission.load_operating':'load_operating','self.context.store.load_transactions':'load_transactions','self.operating.capture':'capture','self.operating.verify_provider':'verify_provider','self.fresh.collect_preflight':'collect_preflight','self.actions.collect_action':'collect_action','self.actions.append_action_snapshot':'append_action_snapshot','self.operating.generate':'generate','self.temporary.TemporaryDirectory':'tempfile.TemporaryDirectory','self.git.run':'subprocess.run'}
OPERATING={'self.Path':'Path','self.root':'ROOT','self.context.operating.captures':'captures','self.collector.collect':'collect','self.context.contracts.require':'require','self.context.operating.CAPTURES':'CAPTURES','self.context.adapter.json_bytes':'json_bytes','self.context.operating.projection':'projection','self.context.operating.INDEX':'INDEX','self.context.operating.REPORT':'REPORT','self.context.operating.STATEMENT_PATH':'STATEMENT_PATH','self.context.operating.render':'render','self.context.operating.statement_template':'statement_template','self.context.operating.request':'request','self.context.personal.statement_body':'statement_body'}
def original(filename):
 c=json.loads((FIXTURE/'contract.json').read_bytes());row=next(v for k,v in c['files'].items() if k.endswith('/'+filename));raw=(FIXTURE/row['fixture']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];return ast.parse(raw)
def cls(filename,name):return next(n for n in ast.parse((ROOT/'scripts/lib'/filename).read_bytes()).body if isinstance(n,ast.ClassDef) and n.name==name)
def function(tree,name):return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
class Restore(ast.NodeTransformer):
 def __init__(self,names,runner=False):self.names,self.runner=names,runner
 def visit_Attribute(self,n):
  name=ast.unparse(n)
  if self.runner and name=='self.capture_method':return ast.copy_location(ast.Constant(value='github_api_get_via_gh'),n)
  return ast.copy_location(ast.parse(self.names[name],mode='eval').body,n) if name in self.names else self.generic_visit(n)
 def visit_Call(self,n):
  if self.runner and ast.unparse(n.func)=='self.clock':return ast.parse("datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')",mode='eval').body
  return self.generic_visit(n)
 def visit_Expr(self,n):
  checked=self.runner and isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='self.git.run';result=self.generic_visit(n)
  return [ast.parse('import subprocess').body[0],result] if checked else result
 def visit_Assign(self,n):
  text=ast.unparse(n)
  if self.runner:
   if text=='generate_receipts = self.receipt_reports.main':return ast.parse('from generate_lifecycle_pilot_validation import main as generate_receipts').body[0]
   if text=='project_actions, INDEX, REPORT, render = (self.context.actions.project_actions, self.action_reports.INDEX, self.action_reports.REPORT, self.action_reports.render)':return ast.parse('from generate_lifecycle_pilot_actions import project_actions, INDEX, REPORT, render').body[0]
   if text=='json_bytes = self.context.adapter.json_bytes':return ast.parse('from lib.governance_lifecycle.adapter import json_bytes').body[0]
  elif text=='statement_body = self.context.personal.statement_body':return ast.parse('from .personal_probe import statement_body').body[0]
  return self.generic_visit(n)
class PilotUpdateWholeOriginalAST(unittest.TestCase):
 def test_complete_original_run_body_all_operations_imports_time_store_generators_and_order(self):
  old=function(original('run_lifecycle_pilot_update.py'),'run');new=copy.deepcopy(function(cls('pilot_update_program.py','PilotUpdateProgram'),'run'));self.assertEqual(new.args.args.pop(0).arg,'self');self.assertEqual(ast.dump(Restore(NAMES,True).visit(new),include_attributes=False),ast.dump(old,include_attributes=False))
 def test_complete_original_operating_capture_and_generate_bodies_include_exclusive_creation(self):
  old=original('operating_acceptance.py');new=cls('operating_capture.py','OperatingCapture')
  for name in ('capture','generate'):
   with self.subTest(name=name):
    node=copy.deepcopy(function(new,name));self.assertEqual(node.args.args.pop(0).arg,'self');self.assertEqual(ast.unparse(node.args.defaults[0]),'_OMITTED');node.args.defaults=[ast.Name(id='ROOT',ctx=ast.Load())];self.assertEqual(ast.unparse(node.body.pop(0)),'if repo is _OMITTED:\n    repo = self.root');self.assertEqual(ast.dump(Restore(OPERATING).visit(node),include_attributes=False),ast.dump(function(old,name),include_attributes=False))
 def test_complete_original_executable_parser_and_calls_keep_every_option_and_choice(self):
  old=next(n for n in original('run_lifecycle_pilot_update.py').body if isinstance(n,ast.If)).body;new=copy.deepcopy(function(cls('pilot_update_program.py','PilotUpdateProgram'),'main').body)
  class Main(ast.NodeTransformer):
   def visit_Attribute(self,n):
    mapping={'self.description':'__doc__','self.run':'run','self.argument_parser':'argparse.ArgumentParser'};return ast.parse(mapping[ast.unparse(n)],mode='eval').body if ast.unparse(n) in mapping else self.generic_visit(n)
   def visit_Call(self,n):
    if isinstance(n.func,ast.Attribute) and n.func.attr=='parse_args':self_case.assertEqual(len(n.args),1);self_case.assertEqual(ast.unparse(n.args[0]),'self.argv');n.args=[]
    return self.generic_visit(n)
  self_case=self;new=[Main().visit(n) for n in new];self.assertEqual([ast.dump(n,include_attributes=False) for n in new],[ast.dump(n,include_attributes=False) for n in old])
if __name__=='__main__':unittest.main(verbosity=2)
