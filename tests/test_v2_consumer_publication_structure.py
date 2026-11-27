"""Reconstruct every original function AST through explicit composition ports only."""
from pathlib import Path
import ast,copy,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from test_v2_consumer_publication import ORIGINAL


class WholeConsumerPublicationStructure(unittest.TestCase):
    def test_all_five_whole_kernel_functions_and_provider_POST_helper_reconstruct_original_AST(self):
        original=ast.parse(ORIGINAL.read_bytes());functions={v.name:v for v in original.body if isinstance(v,ast.FunctionDef)}
        body_dict=next(n for n in ast.walk(functions['publish']) if isinstance(n,ast.Dict) and any(isinstance(k,ast.Constant) and k.value=='body' for k in n.keys));body=body_dict.values[[k.value for k in body_dict.keys].index('body')]
        class Restore(ast.NodeTransformer):
            def visit_Call(self,node):
                # Replace only the declared provider-formatting/data ports.
                names={'run_url':"f'https://github.com/{repository}/actions/runs/{run_id}/attempts/{attempt}'",'pulls_endpoint':"f'repos/{repository}/pulls'",'workflow_endpoint':"f'repos/{repository}/actions/workflows/{workflow}/dispatches'"}
                if isinstance(node.func,ast.Attribute) and ast.unparse(node.func.value)=='self.profile':
                    if node.func.attr=='review_body':return copy.deepcopy(body)
                    if node.func.attr in names:return ast.parse(names[node.func.attr],mode='eval').body
                node=self.generic_visit(node)
                if isinstance(node.func,ast.Attribute) and node.func.attr=='parse_args':node.args=[]
                return node
            def visit_BinOp(self,node):
                if ast.unparse(node)=="'user.name=' + self.profile.author_name":return ast.Constant('user.name=github-actions[bot]')
                if ast.unparse(node)=="'user.email=' + self.profile.author_email":return ast.Constant('user.email=41898282+github-actions[bot]@users.noreply.github.com')
                return self.generic_visit(node)
            def visit_Attribute(self,node):
                mapping={'self.Path':'Path','self.root':'ROOT','self.process.run':'subprocess.run','self.environment':'os.environ','self.argument_parser':'argparse.ArgumentParser','self.profile.check_workflows':'CHECK_WORKFLOWS','self.profile.description':'__doc__','self.profile.output_key':"'GITHUB_OUTPUT'",'self.profile.summary_key':"'GITHUB_STEP_SUMMARY'",'self.profile.ref_key':"'GITHUB_REF'",'self.profile.repository_key':"'GITHUB_REPOSITORY'",'self.profile.run_id_key':"'GITHUB_RUN_ID'",'self.profile.attempt_key':"'GITHUB_RUN_ATTEMPT'",'self.gates.validate_publication':'validate_publication'}
                key=ast.unparse(node)
                if key in mapping:return ast.parse(mapping[key],mode='eval').body
                if isinstance(node.value,ast.Name) and node.value.id=='self' and node.attr in functions:return ast.Name(id=node.attr,ctx=ast.Load())
                return self.generic_visit(node)
        core=ast.parse((ROOT/'scripts/lib/consumer_publication.py').read_bytes());klass=next(n for n in core.body if isinstance(n,ast.ClassDef))
        for method in [n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name!='__init__']:
            with self.subTest(function=method.name):
                restored=Restore().visit(copy.deepcopy(method));restored.args.args=restored.args.args[1:]
                if restored.name=='publish':
                    self.assertEqual(ast.unparse(restored.body[0]),'if api is None:\n    api = self.provider_api');restored.body.pop(0);restored.args.kw_defaults[-1]=ast.Name(id='github_api',ctx=ast.Load());position=next(i for i,n in enumerate(restored.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='validate_publication');restored.body.insert(position,ast.ImportFrom(module='lib.governance_lifecycle.consumer_acceptance',names=[ast.alias(name='validate_publication')],level=0))
                self.assertEqual(ast.dump(restored,include_attributes=False),ast.dump(functions[method.name],include_attributes=False))
        api=ast.parse((ROOT/'scripts/lib/providers/operational_publication_api.py').read_bytes());call=copy.deepcopy(next(n for n in ast.walk(api) if isinstance(n,ast.FunctionDef) and n.name=='__call__'));call.name='github_api';call.args.args=call.args.args[1:]
        class RestoreAPI(ast.NodeTransformer):
            def visit_Call(self,node):
                if ast.unparse(node.func)=='self.profile.api_command':return copy.deepcopy(functions['github_api'].body[0].value.args[0])
                return self.generic_visit(node)
            def visit_Attribute(self,node):
                if ast.unparse(node)=='self.process.run':return ast.parse('subprocess.run',mode='eval').body
                return self.generic_visit(node)
        self.assertEqual(ast.dump(RestoreAPI().visit(call),include_attributes=False),ast.dump(functions['github_api'],include_attributes=False))
    def test_provider_review_body_and_exact_four_workflows_remain_original(self):
        original=ast.parse(ORIGINAL.read_bytes());profile=ast.parse((ROOT/'scripts/lib/providers/consumer_publication_profile.py').read_bytes());body_dict=next(n for n in ast.walk(original) if isinstance(n,ast.Dict) and any(isinstance(k,ast.Constant) and k.value=='body' for k in n.keys));expected=body_dict.values[[k.value for k in body_dict.keys].index('body')];actual=next(n for n in ast.walk(profile) if isinstance(n,ast.FunctionDef) and n.name=='review_body').body[0].value;self.assertEqual(ast.dump(actual),ast.dump(expected));before=next(n.value for n in original.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CHECK_WORKFLOWS' for t in n.targets));after=next(n.value for n in ast.walk(profile) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='check_workflows' for t in n.targets));self.assertEqual(ast.literal_eval(after),ast.literal_eval(before))
