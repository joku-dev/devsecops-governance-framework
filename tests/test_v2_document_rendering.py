"""Whole immutable original document rendering, exact exports and explicit ports."""
from pathlib import Path,PurePosixPath
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
from types import SimpleNamespace
import argparse,ast,copy,errno,hashlib,importlib,importlib.machinery,importlib.util,io,json,os,sys,tempfile,unittest,yaml
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
FROZEN=ROOT/'tests/fixtures/v2-document-rendering-original/render_governance_documents.py.txt'
assert hashlib.sha256(FROZEN.read_bytes()).hexdigest()=='e98b4768f231788de391537237e1c43b35958731ce320bec461677c8b97f3df7'
_loader=importlib.machinery.SourceFileLoader('whole_original_document_renderer',str(FROZEN))
original=importlib.util.module_from_spec(importlib.util.spec_from_loader(_loader.name,_loader));_loader.exec_module(original)
from lib.document_rendering import GovernanceDocumentRenderer
from lib.v2_boundary import violations
core=SimpleNamespace(GovernanceDocumentRenderer=GovernanceDocumentRenderer)
class Memory:
 def __init__(self,files):self.files=dict(files);self.events=[]
 def path(self,value):return Logical(self,PurePosixPath(str(value)))
 def read(self,path,label):
  self.events.append(('read',label))
  if path not in self.files:raise FileNotFoundError(errno.ENOENT,os.strerror(errno.ENOENT),label)
  return self.files[path]
 def mkdir(self,path,mode,parents,exist_ok,label):
  assert (mode,parents,exist_ok)==(0o777,True,True);self.events.append(('mkdir',label))
 def write_text(self,path,value,encoding,label):
  assert encoding=='utf-8';self.events.append(('write',label));self.files[path]=value.encode(encoding);return len(value)
class Logical:
 def __init__(self,m,p):self.m,self.p=m,p
 def __truediv__(self,value):
  try:return Logical(self.m,self.p/value)
  except TypeError as error:raise TypeError(str(error).replace("'PurePosixPath' and","'PosixPath' and",1)) from None
 def __str__(self):return str(self.p)
 @property
 def parent(self):return Logical(self.m,self.p.parent)
 def relative_to(self,value):return self.p.relative_to(PurePosixPath(str(value)))
 def read_text(self,encoding=None):
  self.m.events.append(('read',str(self)))
  if str(self) not in self.m.files:raise FileNotFoundError(errno.ENOENT,os.strerror(errno.ENOENT),str(self))
  return self.m.files[str(self)].decode(encoding or 'utf-8').replace('\r\n','\n').replace('\r','\n')
 def open(self,mode,encoding=None):
  assert mode=='r';return io.StringIO(self.read_text(encoding))
 def mkdir(self,parents=False,exist_ok=False):assert parents and exist_ok;self.m.events.append(('mkdir',str(self)))
 def write_text(self,text,encoding=None):
  assert encoding=='utf-8';self.m.events.append(('write',str(self)));self.m.files[str(self)]=text.encode(encoding);return len(text)
def capture(callback):
 out,err=io.StringIO(),io.StringIO()
 with redirect_stdout(out),redirect_stderr(err):
  try:code,error=callback(),None
  except SystemExit as failure:code,error=failure.code if isinstance(failure.code,int) else 1,{'type':'SystemExit','message':str(failure.code)}
  except Exception as failure:code,error=1,{'type':type(failure).__name__,'message':str(failure)}
 return {'exit':code,'error':error,'stdout':out.getvalue(),'stderr':err.getvalue()}

class WholeGovernanceDocumentRendering(unittest.TestCase):
    def compare_case(self,name,tool=None,args=(),missing=None,*,use_context=False):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / 'data'
            root.mkdir(mode=448)
            docs = [{'id': 'P1', 'type': 'policy', 'title': 'Policy <&> Unicode ä', 'status': 'draft', 'repository_path': 'docs/policy.md', 'purpose': 'existing declared purpose'}, {'id': 'D1', 'type': 'directive', 'title': 'Directive', 'status': 'candidate', 'repository_path': 'docs/directive.md'}, {'id': 'S1', 'type': 'source', 'title': 'Ignored source', 'status': 'candidate', 'repository_path': 'missing-source.md'}]
            profile = {'document_number': 'SYNTHETIC', 'prepared_by': 'Declared preparation', 'approved_by': 'Declared approval label only', 'endorsed_by': '', 'authorized_by': 'Declared authorization label only', 'area_of_application': 'synthetic fixture', 'version': '0.1', 'revision_description': 'synthetic fixture', 'revision_date': '2026-11-20', 'entry_into_force': 'No authority transferred'}
            profiles = {key: dict(profile) for key in ('P1', 'D1')}
            if missing=='source-none':docs[0]['repository_path']=None
            if missing=='source-int':docs[0]['repository_path']=7
            if missing=='id-none':docs[0]['id']=None;profiles[None]=dict(profile)
            if missing=='title-int':docs[0]['title']=7
            if missing == 'profile':
                del profiles['D1']
            files = {'model/documents/governance-documents.yaml': yaml.safe_dump({'documents': docs}).encode(), 'model/documents/governance-document-rendering.yaml': yaml.safe_dump({'render_profiles': profiles}).encode(), 'docs/policy.md': b'# Heading\r\n\r\n- one & <two>\r\n- **three**\r\n\r\n## Next\r\n`paragraph` & end\r\n', 'docs/directive.md': '### Three\n\nText ä\n- trailing list'.encode()}
            if missing == 'alias-budget':files['model/documents/governance-documents.yaml']=('documents: []\nanchor: &x true\nunused: ['+','.join(['*x']*5000)+']\n').encode()
            if missing == 'recursive-alias':files['model/documents/governance-documents.yaml']=b'documents: []\nunused: &cycle [*cycle]\n'
            if missing == 'malformed-catalog':files['model/documents/governance-documents.yaml']=b'documents: [broken'
            if missing == 'invalid-utf8':files['model/documents/governance-documents.yaml']=b'documents: [\xff'
            if missing == 'source':
                del files['docs/directive.md']
            for path, raw in files.items():
                p = root / path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(raw)
            memory = Memory({str(root / path): raw for path, raw in files.items()})
            tool_calls = {'original': [], 'prototype': []}
            docx = b'controlled-optional-tool-result-not-real-DOCX'

            def tool_run(which, arguments, **kwargs):
                assert kwargs == {'capture_output': True, 'text': True, 'check': False}
                tool_calls[which].append(arguments)
                if tool == 0:
                    if which == 'original':
                        Path(arguments[3]).write_bytes(docx)
                    else:
                        memory.files[arguments[3]] = docx
                return SimpleNamespace(returncode=tool, stdout='controlled stdout', stderr='controlled stderr')
            finder = lambda name: None if tool is None else '/explicit-controlled/pandoc'
            with patch.multiple(original, ROOT=root, CATALOG_PATH=root / 'model/documents/governance-documents.yaml', RENDERING_PATH=root / 'model/documents/governance-document-rendering.yaml', OUT_DIR=root / 'generated/documents'), patch.object(original.shutil, 'which', finder), patch.object(original.subprocess, 'run', lambda a, **k: tool_run('original', a, **k)), patch.object(sys, 'argv', ['render_governance_documents.py', *args]):
                expected = capture(original.main)
            engine = core.GovernanceDocumentRenderer(memory.path(root), path_factory=memory.path, yaml_load=yaml.safe_load, which=finder, run_process=lambda a, **k: tool_run('prototype', a, **k), argument_parser=lambda: argparse.ArgumentParser(prog='render_governance_documents.py'), argv=args)
            with patch('subprocess.Popen', side_effect=AssertionError('No native process in prototype')), patch.object(Path, 'open', side_effect=AssertionError('No native file in prototype')):
                if use_context:
                    from lib.document_rendering_context import execute
                    value=execute(str(root),list(args),memory,memory,SimpleNamespace(which=finder,run=lambda a,**k:tool_run('prototype',a,**k)))
                    signal=value['original_exit_signal']
                    actual={'exit':value['exit_code'],'error':value['kernel_exception'] if signal is None else {'type':'SystemExit','message':str(signal['value'])},'stdout':value['stdout'],'stderr':value['stderr']}
                else:actual = capture(engine.main)
            assert actual == expected, (name, actual, expected)
            actual_files = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            assert memory.files == actual_files, name
            assert tool_calls['original'] == tool_calls['prototype'], name
            outputs = {str(Path(path).relative_to(root)): {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} for path, raw in actual_files.items() if '/generated/documents/' in path}
            return {'name': name, 'whole_exit_streams_and_exception_equal': True, 'all_files_byte_equal': True, 'ordered_original_tool_calls_equal': True, 'original_exit': expected['exit'], 'output_files': outputs}

    def test_whole_all_documents_without_optional_tool(self):self.compare_case('all-no-tool')
    def test_whole_all_documents_with_controlled_optional_success(self):self.compare_case('all-controlled-success',0)
    def test_whole_nonzero_optional_tool_keeps_original_skip_message(self):self.compare_case('all-controlled-nonzero',7)
    def test_whole_repeated_selection_retains_original_order(self):self.compare_case('selected-directive',args=['--document-id','D1','--document-id','D1'])
    def test_whole_unknown_selection_is_original_empty_success(self):self.compare_case('unknown-selection',args=['--document-id','UNKNOWN'])
    def test_whole_missing_later_profile_keeps_prior_outputs(self):self.compare_case('missing-second-profile',missing='profile')
    def test_whole_missing_later_source_keeps_prior_outputs(self):self.compare_case('missing-second-source',missing='source')

    def test_original_nonstrings_keep_native_path_type_error_and_partial_exports(self):
        for kind in ('source-none','source-int','id-none','title-int'):
            with self.subTest(kind=kind):self.compare_case(kind,missing=kind)

    def test_all_original_markdown_branches_and_raw_html_escape(self):
        engine=GovernanceDocumentRenderer(PurePosixPath('/unused'),path_factory=None,yaml_load=None,which=None,run_process=None,argument_parser=None,argv=[])
        values=['','# One\n\n## Two\n### Three\nParagraph `code` **bold** & <tag>','- first\n- second\n\ntext','- first\n# Heading','- first\n## Heading','- first\n### Heading','- trailing','| A | B |\n| -- | -- |\n| ä | <&> |']
        for value in values:
            with self.subTest(markdown=value):self.assertEqual(engine.markdown_to_html(value),original.markdown_to_html(value))

    def test_whole_original_method_AST_after_only_explicit_ports(self):
        old={n.name:n for n in ast.parse(FROZEN.read_bytes()).body if isinstance(n,ast.FunctionDef)}
        cls=next(n for n in ast.parse((ROOT/'scripts/lib/document_rendering.py').read_bytes()).body if isinstance(n,ast.ClassDef))
        new={n.name:n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name!='__init__'}
        self.assertEqual(set(old),set(new));self.assertEqual(len(old),9)
        self.assertEqual(violations('scripts/lib/document_rendering.py',(ROOT/'scripts/lib/document_rendering.py').read_text()),[])
        names=set(old);fields={'root':'ROOT','catalog_path':'CATALOG_PATH','rendering_path':'RENDERING_PATH','out_dir':'OUT_DIR','path_factory':'Path'}
        ports={'yaml_load':('yaml','safe_load'),'which':('shutil','which'),'run_process':('subprocess','run'),'argument_parser':('argparse','ArgumentParser')}
        class Restore(ast.NodeTransformer):
            def visit_Attribute(self,n):
                if isinstance(n.value,ast.Name) and n.value.id=='self':
                    if n.attr in fields:return ast.copy_location(ast.Name(fields[n.attr],n.ctx),n)
                    if n.attr in names:return ast.copy_location(ast.Name(n.attr,n.ctx),n)
                    if n.attr in ports:
                        module,field=ports[n.attr];return ast.copy_location(ast.Attribute(ast.Name(module,ast.Load()),field,n.ctx),n)
                return self.generic_visit(n)
            def visit_Call(self,n):
                if isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='parser' and n.func.attr=='parse_args':
                    assert len(n.args)==1 and ast.unparse(n.args[0])=='self.argv';n.args=[]
                return self.generic_visit(n)
        for name,node in old.items():
            with self.subTest(method=name):
                changed=copy.deepcopy(new[name]);self.assertEqual(changed.args.args.pop(0).arg,'self');changed=Restore().visit(changed)
                self.assertEqual(ast.dump(changed,include_attributes=False),ast.dump(node,include_attributes=False))

    def test_source_only_compatibility_facade_aliases_whole_original_adapter(self):
        raw=(ROOT/'scripts/lib/providers/legacy_document_rendering.py').read_bytes()
        self.assertEqual(raw.replace(b'ROOT = Path(__file__).resolve().parents[3]',b'ROOT = Path(__file__).resolve().parents[1]'),FROZEN.read_bytes())
        facade=importlib.import_module('render_governance_documents');adapter=importlib.import_module('lib.providers.legacy_document_rendering')
        self.assertIs(facade,adapter);self.assertEqual(facade.ROOT,ROOT)

if __name__=='__main__':unittest.main()
