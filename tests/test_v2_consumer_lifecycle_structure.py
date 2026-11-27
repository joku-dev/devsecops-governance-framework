"""Whole immutable original function bodies after only declared ports and default binding."""
from pathlib import Path
import ast,copy,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
FIXTURE=ROOT/'tests/fixtures/v2-consumer-lifecycle-original'
from lib.providers.consumer_lifecycle_profile import LITERALS
# Explicit dependency routes, independently restored to the original imports.
COMMON={'Path':'self.Path','ROOT':'self.root','strict_json':'self.context.adapter.strict_json','json_bytes':'self.context.adapter.json_bytes','require':'self.context.contracts.require','timestamp':'self.context.contracts.timestamp','canonical_digest':'self.context.contracts.canonical_digest','finding_id':'self.context.contracts.finding_id','FORMAT_CHECKER':'self.context.contracts.format_checker','transaction_ref':'self.context.kernel.transaction_ref','revision_ref':'self.context.preparation.revision_ref','load_operating':'self.context.consumer_contracts.load_operating','load_model':'self.context.consumer_contracts.load_model','validate_preparation':'self.context.consumer_contracts.validate_preparation','schema_validator':'self.context.consumer_contracts.schema_validator','load_transactions':'self.context.store.load_transactions','publish_transaction':'self.context.store.publish_transaction','writer_lock':'self.context.store.writer_lock','assess_bound_comments':'self.context.provider.assess_bound_comments','collect_bound':'self.context.provider.collect_bound','replay_bound_snapshot':'self.context.provider.replay_bound_snapshot','comment_identity':'self.context.provider.comment_identity','statement_body':'self.context.personal.statement_body','VALIDATION_LEDGER':'self.context.consumer_admission.VALIDATION_LEDGER','ACTION_LEDGER':'self.context.consumer_actions.ACTION_LEDGER','MODEL':'self.context.consumer_contracts.MODEL','replay_receipts':'self.context.consumer_admission.replay_receipts','append_capture':'self.context.consumer_admission.append_capture','collect_preflight':'self.context.consumer_evidence.collect_preflight','replay_capture':'self.context.consumer_evidence.replay_capture','collect_action':'self.context.consumer_actions.collect_action','append_action_snapshot':'self.context.consumer_actions.append_action_snapshot','project_actions':'self.context.consumer_actions.project_actions','capture':'self.context.consumer_acceptance.capture','verify_provider':'self.context.consumer_acceptance.verify_provider','generate':'self.context.consumer_acceptance.generate','validate':'self.context.consumer_acceptance.validate','validate_publication':'self.context.consumer_acceptance.validate_publication','check_prefix':'self.context.consumer_acceptance.check_prefix','manifest':'self.context.consumer_acceptance.manifest','REQUEST_PATH':'self.context.consumer_acceptance.REQUEST_PATH','verify_new_receipts':'self.context.consumer_admission.verify_new_receipts','verify_new_actions':'self.context.consumer_actions.verify_new_actions','Draft202012Validator':'self.validator_class','github_get':'self.default_fetch','adapt_architecture':'self.architecture.adapt_architecture','positive_id':'self.positive_id','sha':'self.sha','__doc__':'self.description'}
CALLS={'self.process.run':'subprocess.run','self.process.check_output':'subprocess.check_output','self.temporary.TemporaryDirectory':'tempfile.TemporaryDirectory','self.argument_parser':'argparse.ArgumentParser','self.environment_factory':'os.environ.copy'}
CLASSES={'contracts':('consumer_lifecycle_contracts.py','ConsumerContracts'),'admission':('consumer_lifecycle_admission.py','ConsumerAdmission'),'actions':('consumer_lifecycle_actions.py','ConsumerActions'),'acceptance':('consumer_lifecycle_acceptance.py','ConsumerAcceptance'),'evidence':('providers/consumer_lifecycle_evidence.py','LegacyConsumerEvidence'),'runner':('consumer_lifecycle_program.py','ConsumerLifecycleProgram')}
def methods(file,cls):return {n.name:n for n in next(n for n in ast.parse((ROOT/'scripts/lib'/file).read_bytes()).body if isinstance(n,ast.ClassDef) and n.name==cls).body if isinstance(n,ast.FunctionDef)}
def dump(node):return ast.dump(node,include_attributes=False)
class WholeConsumerStructure(unittest.TestCase):
 def test_all_53_original_functions_and_whole_executable_footer_are_preserved(self):
  manifest=json.loads((FIXTURE/'contract.json').read_bytes());count=0
  for key,(file,cls) in CLASSES.items():
   path='scripts/run_consumer_lifecycle.py' if key=='runner' else 'scripts/lib/governance_lifecycle/consumer_'+key+'.py';row=manifest['files'][path];raw=(FIXTURE/row['fixture']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256']);tree=ast.parse(raw);old={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
   mapping={**COMMON,**{name:'self.'+name for name in old}}
   for item in tree.body:
    if isinstance(item,ast.Assign):
     for target in item.targets:
      if isinstance(target,ast.Name) and target.id not in ('ROOT','sha'):mapping[target.id]='self.'+target.id
   if key=='evidence':mapping['github_get']='self.default_fetch'
   new=methods(file,cls)
   for name,original in old.items():
    target=new.get(name);actual_mapping=mapping
    if key=='acceptance' and name in ('verify_required_guard','render','statement_template'):target=methods('providers/consumer_lifecycle_profile.py','LegacyConsumerProfile')[name];actual_mapping=COMMON
    elif key=='evidence' and name=='github_get':target=methods('providers/consumer_lifecycle_profile.py','LegacyConsumerReader')[name];actual_mapping={}
    with self.subTest(module=key,function=name):
     self.assertIsNotNone(target);self.assertEqual(dump(self.restore(target,original,actual_mapping)),dump(original))
    count+=1
   if key=='runner':
    footer=next(n for n in tree.body if isinstance(n,ast.If));target=copy.deepcopy(new['main'])
    # Let the executing interpreter supply its complete FunctionDef fields
    # (including Python 3.12+ type_params), then retain the whole old footer.
    original=ast.parse('def main():\n pass\n').body[0];original.body=footer.body
    self.assertEqual(dump(self.restore(target,original,mapping)),dump(original));count+=1
  self.assertEqual(count,54)
 def restore(self,actual,original,mapping):
  node=copy.deepcopy(actual);self.assertEqual(node.args.args.pop(0).arg,'self');reverse={v:k for k,v in mapping.items()}
  while node.body and isinstance(node.body[0],ast.If) and '_OMITTED' in ast.unparse(node.body[0].test) or node.body and isinstance(node.body[0],ast.If) and '_DEFAULT_FETCH' in ast.unparse(node.body[0].test):node.body.pop(0)
  for values in (node.args.defaults,node.args.kw_defaults):
   for i,value in enumerate(values):
    if isinstance(value,ast.Name) and value.id in ('_OMITTED','_DEFAULT_FETCH'):values[i]=ast.Name(id='ROOT' if value.id=='_OMITTED' else 'github_get',ctx=ast.Load())
  class Restore(ast.NodeTransformer):
   def visit_Call(self,item):
    label=ast.unparse(item.func)
    if label=='self.clock':return ast.parse("datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')",mode='eval').body
    if label=='self.profile.literal':return ast.Constant(LITERALS[item.args[0].value])
    if label in CALLS:item.func=ast.parse(CALLS[label],mode='eval').body
    if label=='parser.parse_args' and len(item.args)==1 and ast.unparse(item.args[0])=='self.argv':item.args=[]
    return self.generic_visit(item)
   def visit_Attribute(self,item):
    label=ast.unparse(item)
    if label=='self.profile.capture_method':return ast.Constant('github_api_get_via_gh')
    if label in reverse:return ast.Name(id=reverse[label],ctx=ast.Load())
    return self.generic_visit(item)
  node=Restore().visit(node)
  # Original function-local imports are dependency declarations. Restore them
  # at their original statement offsets, preserving every actual executable AST.
  def imports(new,old):
   for index,statement in enumerate(old):
    if isinstance(statement,ast.ImportFrom):new.insert(index,copy.deepcopy(statement));continue
    counterpart=new[index]
    for field in ('body','orelse','finalbody'):
     if hasattr(statement,field) and hasattr(counterpart,field):imports(getattr(counterpart,field),getattr(statement,field))
    if isinstance(statement,ast.Try):
     for actual_handler,old_handler in zip(counterpart.handlers,statement.handlers):imports(actual_handler.body,old_handler.body)
  imports(node.body,original.body)
  return node
 def test_core_has_no_provider_literals_imports_or_selected_source_execution(self):
  from lib.v2_boundary import violations
  for file,cls in CLASSES.values():
   if not file.startswith('providers/'):
    text=(ROOT/'scripts/lib'/file).read_text();self.assertEqual(violations('scripts/lib/'+file,text),[])
