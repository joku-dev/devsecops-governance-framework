"""All twelve whole original functions and exact provider formatting reconstruct."""
from pathlib import Path
import ast,copy,hashlib,json,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from test_v2_self_security_publication import ORIGINAL
from lib.providers.self_security_publication_profile import LITERALS


class WholeSelfSecurityPublicationStructure(unittest.TestCase):
    def test_all_original_core_function_AST_bodies_are_restored_by_explicit_port_rebinding(self):
        old=ast.parse(ORIGINAL.read_bytes());original={n.name:n for n in old.body if isinstance(n,ast.FunctionDef)};core=ast.parse((ROOT/'scripts/lib/self_security_publication.py').read_bytes());klass=next(n for n in core.body if isinstance(n,ast.ClassDef));profile=ast.parse((ROOT/'scripts/lib/providers/self_security_publication_profile.py').read_bytes());profile_methods={n.name:n for n in ast.walk(profile) if isinstance(n,ast.FunctionDef)}
        class Restore(ast.NodeTransformer):
            def visit_Call(self,n):
                if ast.unparse(n.func)=='self.profile.review_body':return copy.deepcopy(next(n.value for n in original['publish'].body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='body' for t in n.targets)))
                if ast.unparse(n.func)=='self.profile.incomplete_observation':return copy.deepcopy(profile_methods['incomplete_observation'].body[0].value)
                if ast.unparse(n.func)=='self.profile.literal':return ast.Constant(LITERALS[ast.literal_eval(n.args[0])])
                names={'self.profile.run_url':"f'https://github.com/{repository}/actions/runs/{run_id}/attempts/{attempt}'",'self.profile.workflow_endpoint':"f'repos/{repository}/actions/workflows/{workflow}/dispatches'"}
                key=ast.unparse(n.func)
                if key in names:return ast.parse(names[key],mode='eval').body
                if key=='self.profile.pull_endpoint':return ast.parse("f\"repos/{repository}/pulls/{existing_pr['number']}\"" if len(n.args)==2 else "f'repos/{repository}/pulls'",mode='eval').body
                return self.generic_visit(n)
            def visit_BinOp(self,n):
                text=ast.unparse(n)
                if text=="'user.name=' + self.profile.author_name":return ast.Constant('user.name=github-actions[bot]')
                if text=="'user.email=' + self.profile.author_email":return ast.Constant('user.email=41898282+github-actions[bot]@users.noreply.github.com')
                return self.generic_visit(n)
            def visit_Attribute(self,n):
                mapping={'self.root':'ROOT','self.Path':'Path','self.process.run':'subprocess.run','self.environment':'os.environ','self.profile.branch':'BRANCH','self.profile.check_workflows':'CHECK_WORKFLOWS','self.profile.expected_legacy_protection_404':'EXPECTED_LEGACY_PROTECTION_404','self.profile.output_key':"'GITHUB_OUTPUT'",'self.profile.summary_key':"'GITHUB_STEP_SUMMARY'",'self.profile.ref_key':"'GITHUB_REF'",'self.profile.repository_key':"'GITHUB_REPOSITORY'",'self.profile.run_id_key':"'GITHUB_RUN_ID'",'self.profile.attempt_key':"'GITHUB_RUN_ATTEMPT'"};key=ast.unparse(n)
                if key in mapping:return ast.parse(mapping[key],mode='eval').body
                if isinstance(n.value,ast.Name) and n.value.id=='self' and n.attr in original:return ast.Name(id=n.attr,ctx=ast.Load())
                return self.generic_visit(n)
        count=0
        for fn in [n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name!='__init__']:
            count+=1
            with self.subTest(function=fn.name):
                restored=copy.deepcopy(fn);restored.args.args=restored.args.args[1:]
                if fn.name in ('open_refresh_pr','publish'):
                    self.assertEqual(ast.unparse(restored.body.pop(0)),'if api is None:\n    api = self.provider_api')
                    if restored.args.defaults:restored.args.defaults[-1]=ast.Name(id='github_api',ctx=ast.Load())
                    else:restored.args.kw_defaults[-1]=ast.Name(id='github_api',ctx=ast.Load())
                if fn.name=='open_refresh_pr':
                    self.assertEqual(ast.unparse(restored.body.pop(0)),'endpoint = self.profile.open_pr_endpoint(repository)');restored.body[:0]=copy.deepcopy(original[fn.name].body[:2])
                self.assertEqual(ast.dump(Restore().visit(restored)),ast.dump(original[fn.name]))
        self.assertEqual(count,11);self.assertEqual(len(original),12)
        body=profile_methods['review_body'].body[0].value;expected=next(n.value for n in original['publish'].body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='body' for t in n.targets));self.assertEqual(ast.dump(body),ast.dump(expected))
    def test_original_GET_PATCH_POST_helper_keeps_original_json_command_options_and_empty_result(self):
        from types import SimpleNamespace
        from lib.providers.self_security_publication_api import LegacySelfSecurityPublicationAPI
        from lib.providers.self_security_publication_profile import LegacySelfSecurityPublicationProfile
        ns={'__name__':'immutable','__file__':str(ROOT/'scripts/publish_self_security_refresh.py')};exec(compile(ORIGINAL.read_bytes(),'immutable_self_security','exec'),ns)
        for method,payload,raw in [('GET',None,'[]'),('POST',{'title':'Ä'},'{}'),('PATCH',{'body':'x'},'')]:
            calls=[]
            def run(command,**options):calls.append((command,options));return SimpleNamespace(stdout=raw)
            ns['subprocess']=SimpleNamespace(run=run);expected=ns['github_api'](method,'repos/owner/repo/pulls',payload);old_calls=copy.deepcopy(calls);calls.clear();actual=LegacySelfSecurityPublicationAPI(SimpleNamespace(run=run),LegacySelfSecurityPublicationProfile())(method,'repos/owner/repo/pulls',payload);self.assertEqual(actual,expected);self.assertEqual(calls,old_calls)
        contract=json.loads((ORIGINAL.parent/'contract.json').read_bytes());self.assertEqual(hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),contract['sha256'])
