"""Whole original validator-main structure; runtime/provider composition is separate."""
from pathlib import Path
import ast,copy,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
from lib.providers.lifecycle_ledger_validation_profile import DESCRIPTION,LegacyLifecycleValidatorMessages
FIXTURE=ROOT/'tests/fixtures/v2-operating-verification-original'

class WholeLifecycleValidatorMain(unittest.TestCase):
    def original(self):
        contract=json.loads((FIXTURE/'contract.json').read_bytes());row=contract['files']['scripts/validate_governance_lifecycle_ledger.py'];raw=(FIXTURE/row['fixture']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256']);return ast.parse(raw)
    def test_complete_original_main_flags_calls_imports_outputs_and_order_after_only_declared_ports(self):
        original=next(n for n in self.original().body if isinstance(n,ast.FunctionDef) and n.name=='main')
        tree=ast.parse((ROOT/'scripts/lib/lifecycle_ledger_validation.py').read_bytes());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef));main=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='main'));self.assertEqual(main.args.args.pop(0).arg,'self')
        imports={}
        for node in original.body:
            if isinstance(node,ast.ImportFrom):
                for i,name in enumerate(node.names):imports[name.asname or name.name]=copy.deepcopy(node) if i==0 else None
        attrs={'self.root':'ROOT','self.default_ledger':'DEFAULT_LEDGER','self.context.contracts.require':'require','self.context.store.load_transactions':'load_transactions','self.context.preparation.validate_preparation':'validate_preparation','self.prefix.check_accepted_prefix':'check_accepted_prefix','self.receipts.verify_new_receipts':'verify_new_receipts','self.actions.verify_new_actions':'verify_new_actions','self.context.ledger.validate_current':'validate_current','self.context.ledger.validate_pilot':'validate_pilot','self.context.ledger.validate_exceptions':'validate_exceptions','self.description':'__doc__','self.argument_parser':'argparse.ArgumentParser'}
        formats=[n for n in ast.walk(original) if isinstance(n,ast.JoinedStr) and any(isinstance(v,ast.Constant) and type(v.value) is str and 'against GitHub.' in v.value for v in n.values)]
        self.assertEqual(len(formats),4);messages=dict(zip(('receipts','captures','actions','operating'),formats))
        class Restore(ast.NodeTransformer):
            def visit_Assign(self,node):
                if len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in imports:return imports[node.targets[0].id]
                return self.generic_visit(node)
            def visit_Attribute(self,node):
                name=ast.unparse(node)
                return ast.copy_location(ast.parse(attrs[name],mode='eval').body,node) if name in attrs else self.generic_visit(node)
            def visit_Call(self,node):
                name=ast.unparse(node.func)
                if name.startswith('self.messages.'):
                    key=name.rsplit('.',1)[1];assert key in messages and len(node.args)==1 and not node.keywords
                    old=copy.deepcopy(messages[key]);next(v for v in old.values if isinstance(v,ast.FormattedValue)).value=self.visit(node.args[0]);return old
                if name=='parser.parse_args':assert len(node.args)==1 and ast.unparse(node.args[0])=='self.argv';node.args=[]
                return self.generic_visit(node)
        restored=Restore().visit(main);self.assertEqual(ast.dump(restored,include_attributes=False),ast.dump(original,include_attributes=False))
        source=(ROOT/'scripts/lib/lifecycle_ledger_validation.py').read_text();self.assertNotIn('github',source.lower());self.assertNotIn('lib.providers',source);self.assertNotIn('subprocess',source)
    def test_legacy_provider_description_and_each_rendered_message_match_immutable_original(self):
        original=self.original();self.assertEqual(DESCRIPTION,ast.get_docstring(original));main=next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name=='main')
        formats=[n for n in ast.walk(main) if isinstance(n,ast.JoinedStr) and any(isinstance(v,ast.Constant) and type(v.value) is str and 'against GitHub.' in v.value for v in n.values)]
        for name,node in zip(('receipts','captures','actions','operating'),formats):
            for value in (0,1,23,None):
                expected=''.join(v.value if isinstance(v,ast.Constant) else str(value) for v in node.values);self.assertEqual(getattr(LegacyLifecycleValidatorMessages,name)(value),expected)
