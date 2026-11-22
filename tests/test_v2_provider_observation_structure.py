"""Every original function body restored by explicit port rebinding, no slices."""
from pathlib import Path
import ast,copy,hashlib,json,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];FIXTURE=ROOT/'tests/fixtures/v2-provider-observation-original'


class RestoredWholeObservationFunctions(unittest.TestCase):
    def restore(self,node,aliases):
        node=copy.deepcopy(node);node.args.args.pop(0)
        class Restore(ast.NodeTransformer):
            def visit_Attribute(self,n):
                if isinstance(n.value,ast.Name) and n.value.id=='self' and n.attr in aliases:
                    return ast.copy_location(ast.Name(aliases[n.attr],n.ctx),n)
                return self.generic_visit(n)
        return Restore().visit(node)
    def nodes(self,path,classname=None):
        body=ast.parse(path.read_bytes()).body
        if classname:body=next(n for n in body if isinstance(n,ast.ClassDef) and n.name==classname).body
        return {n.name:n for n in body if isinstance(n,ast.FunctionDef)}
    def test_complete_main_and_strict_json_helper_ast_are_retained(self):
        actual=self.nodes(ROOT/'scripts/lib/provider_observation.py','ProviderObservation');old=self.nodes(FIXTURE/'entrypoint.txt');aliases={'argparse':'argparse','path':'Path','native':'os','description':'__doc__','Reader':'Reader','BoundedAudit':'BoundedAudit','check_private_file':'check_private_file','read_json':'read_json','capture_reviews':'capture_reviews','capture_security':'capture_security','atomic_json':'atomic_json','datetime':'datetime'}
        self.assertEqual(ast.dump(self.restore(actual['main'],aliases),include_attributes=False),ast.dump(old['main'],include_attributes=False));old=self.nodes(FIXTURE/'runtime.txt');self.assertEqual(ast.dump(self.restore(actual['read_json'],{'path':'Path'}),include_attributes=False),ast.dump(old['read_json'],include_attributes=False))
    def test_all_six_assurance_function_bodies_include_original_loader_and_security_branches(self):
        old=self.nodes(FIXTURE/'assurance.txt');actual=self.nodes(ROOT/'scripts/lib/providers/provider_observation_assurance.py','LegacyProviderAssurance');aliases={name:name for name in old};aliases.update(root='ROOT',process='subprocess',loader='importlib');self.assertEqual(set(actual)-{'__init__'},set(old))
        for name in old:
            with self.subTest(function=name):self.assertEqual(ast.dump(self.restore(actual[name],aliases),include_attributes=False),ast.dump(old[name],include_attributes=False))
    def test_entire_immutable_source_files_bind_all_function_oracles(self):
        contract=json.loads((FIXTURE/'contract.json').read_bytes());self.assertEqual(contract['v1_reference'],'6b557fefe295b58272d2271326576ca3a3687197')
        for label,row in contract['sources'].items():
            raw=(FIXTURE/(label+'.txt')).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256']);self.assertEqual(subprocess.check_output(['git','show',contract['v1_reference']+':'+row['v1_path']],cwd=ROOT),raw)
    def test_complete_original_Reader_and_BoundedAudit_classes_are_unchanged(self):
        before=ast.parse((FIXTURE/'transport.txt').read_bytes());after=ast.parse((ROOT/'scripts/lib/providers/transports.py').read_bytes())
        for name in ('Reader','BoundedAudit'):
            with self.subTest(classname=name):
                old=next(n for n in before.body if isinstance(n,ast.ClassDef) and n.name==name)
                new=next(n for n in after.body if isinstance(n,ast.ClassDef) and n.name==name)
                self.assertEqual(ast.dump(old,include_attributes=False),ast.dump(new,include_attributes=False))
        sys.path.insert(0,str(ROOT/'scripts'))
        from lib.v2_boundary import violations
        name='scripts/lib/provider_observation_reads.py'
        self.assertEqual(violations(name,(ROOT/name).read_text()),[])
