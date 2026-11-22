"""Whole immutable original precondition and the exact additional read-only request."""
from pathlib import Path
import ast,copy,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
from lib.providers.operating_publication_validation_protocol import LegacyPublicationValidationProtocol
from lib.requirement_validation_budget import InputAdmissionError
FIXTURE=ROOT/'tests/fixtures/v2-publication-validation-original'
class PublicationValidationStructure(unittest.TestCase):
 def test_entire_original_validate_publication_AST_with_only_explicit_context_and_IO_ports(self):
  contract=json.loads((FIXTURE/'contract.json').read_bytes());row=contract['files']['scripts/lib/governance_lifecycle/operating_acceptance.py'];raw=(FIXTURE/row['fixture']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),row['source_sha256']);old=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='validate_publication');tree=ast.parse((ROOT/'scripts/lib/operating_publication_validation.py').read_bytes());new=copy.deepcopy(next(n for n in next(n for n in tree.body if isinstance(n,ast.ClassDef)).body if isinstance(n,ast.FunctionDef) and n.name=='validate_publication'));self.assertEqual(new.args.args.pop(0).arg,'self')
  imports={}
  for n in ast.walk(old):
   if isinstance(n,ast.ImportFrom):imports[n.names[0].asname or n.names[0].name]=n
  mapping={'self.Path':'Path','self.context.operating.validate':'validate','self.operating.verify_new_captures':'verify_new_captures','self.operating.verify_provider':'verify_provider','self.git.check_output':'subprocess.check_output','self.context.contracts.require':'require'}
  class Restore(ast.NodeTransformer):
   def visit_Assign(self,node):
    target=node.targets[0];key=target.id if isinstance(target,ast.Name) else target.elts[0].id
    if key in imports:return copy.deepcopy(imports[key])
    return self.generic_visit(node)
   def visit_Attribute(self,node):
    name=ast.unparse(node);return ast.copy_location(ast.parse(mapping[name],mode='eval').body,node) if name in mapping else self.generic_visit(node)
  self.assertEqual(ast.dump(Restore().visit(new),include_attributes=False),ast.dump(old,include_attributes=False));source=(ROOT/'scripts/lib/operating_publication_validation.py').read_text();self.assertNotIn('subprocess',source);self.assertNotIn('github',source.lower());self.assertNotIn('lib.providers',source)
 def test_protocol_admits_only_original_two_ledger_order_and_checked_text_request(self):
  profile=LegacyPublicationValidationProtocol();cmd=['git','ls-tree','-r','--name-only','abc','--','governance/lifecycle/live-validation','governance/lifecycle/pilot-actions'];args={'command':cmd,'cwd':'/explicit/source','text':True};spec=profile.request('git-tree',args,'/explicit/source','/explicit/source');self.assertEqual(spec['original_arguments'],cmd);self.assertEqual(spec['source_root'],'/explicit/source')
  for bad in ({**args,'text':1},{**args,'cwd':'/foreign'}, {**args,'command':cmd[:-1]},{**args,'command':[*cmd[:6],*reversed(cmd[6:])]},{**args,'command':[*cmd[:4],'-c',*cmd[5:]]},{**args,'command':['git','push','origin','HEAD:main']},{**args,'command':[*cmd,'extra']}, {**args,'shell':True}):
   with self.subTest(bad=bad):
    with self.assertRaises(InputAdmissionError):profile.request('git-tree',bad,'/explicit/source','/explicit/source')
  for kind in ('get','post','git-run','git-checked-run'):
   with self.assertRaises(InputAdmissionError):profile.request(kind,args,'/explicit/source','/explicit/source')
if __name__=='__main__':unittest.main(verbosity=2)
