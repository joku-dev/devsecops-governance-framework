"""Whole unchanged original review methods, streams, files and partial writes."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from importlib.machinery import SourceFileLoader
import ast
import errno
import hashlib
import importlib.util
import io
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.requirement_review_context import execute, ReviewOutputPath
from lib.requirement_migration_generation import ImplementedRequirementMigration
from lib.requirement_platform_generation import PRARequirementPlatformReview
from lib.providers.repository_data_io import RepositoryDataIO
from lib.providers.requirement_review_profile import LEGACY_MIGRATION_INVENTORY
from lib.v2_boundary import violations

SPECS = {
    'implemented-migration': ('generate_implemented_requirement_migration',
        'e80f6d2a371da8fad3c726bfeb4290cb88d2001708db97c42800a0d2d9eca81d',
        {'ROOT':'root','CASES':'cases','OUT_JSON':'out_json','OUT_MD':'out_md'},
        'requirement_migration_generation.py', 'ImplementedRequirementMigration'),
    'pra-platform': ('generate_pra_requirement_platform_review',
        '5160bb924bd38c8411a91f32b5d50299ae489f74776da4989ae1ac024b800a79',
        {'ROOT':'root','CASE':'case','CANDIDATES':'candidates','CAPABILITIES':'capabilities',
         'ALLOCATIONS':'allocations','ARTIFACT_REGISTER':'artifact_register','SOURCE':'source','OUT':'out'},
        'requirement_platform_generation.py', 'PRARequirementPlatformReview'),
}
OUTPUTS = {
    'implemented-migration': ('generated/reports/implemented-requirement-migration.json',
                             'generated/reports/implemented-requirement-migration.md'),
    'pra-platform': ('docs/governance/review-packets/PRA-2026-001/review.json',
                     'docs/governance/review-packets/PRA-2026-001/review.md'),
}
ORIGINALS = {}
for kind,(stem,pin,*_) in SPECS.items():
    path=ROOT/'tests/fixtures/v2-requirement-review-original'/(stem+'.py.txt')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==pin
    loader=SourceFileLoader('immutable_original_'+stem,str(path))
    module=importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name,loader))
    loader.exec_module(module)
    ORIGINALS[kind]=module


class MemoryOutput:
    def __init__(self,label,fail=None):
        self.label,self.fail,self.files,self.calls=label,fail,{},[]
    def mkdir(self,name,mode,parents,exist_ok):
        self.calls.append(('mkdir',name,mode,parents,exist_ok))
    def write_text(self,name,text,encoding):
        self.write(name,text.encode(encoding))
        return len(text)
    def write(self,name,raw):
        self.calls.append(('write',name))
        if name==self.fail:
            raise OSError(errno.ENOSPC,'No space left on device',str(self.label/name))
        self.files[name]=raw


class WholeRequirementReviewGeneration(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.data=Path(temporary.name).resolve()/'data';self.data.mkdir(mode=0o700)
        for name in ['model','architecture','policies','schemas','.github/workflows',
                     'releases','docs/governance/source-documents']:
            target=self.data/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copytree(ROOT/name,target)
        target=self.data/'generated/reports';target.mkdir(parents=True)
        shutil.copyfile(ROOT/'generated/reports/implemented-requirement-migration.json',
                        target/'implemented-requirement-migration.json')

    def original(self,kind,fail=None):
        module=ORIGINALS[kind]
        constants={key:self.data/str(getattr(module,key).relative_to(module.ROOT))
                   for key in SPECS[kind][2] if key!='ROOT'}
        stdout,stderr=io.StringIO(),io.StringIO()
        write=Path.write_text
        def controlled(path,data,*args,**kwargs):
            if fail is not None and path==self.data/fail:
                raise OSError(errno.ENOSPC,'No space left on device',str(path))
            return write(path,data,*args,**kwargs)
        with patch.multiple(module,ROOT=self.data,**constants),patch.object(Path,'write_text',controlled), \
                redirect_stdout(stdout),redirect_stderr(stderr):
            try:code,error=module.main(),None
            except Exception as failure:
                code,error=1,{'type':type(failure).__name__,'message':str(failure)}
        return {'exit_code':code,'stdout':stdout.getvalue(),'stderr':stderr.getvalue(),'kernel_exception':error}

    def compare(self,kind,fail=None):
        # Preserve any prior outputs, so a failed first write cannot invent one.
        before={name:(self.data/name).read_bytes() if (self.data/name).is_file() else None
                for name in OUTPUTS[kind]}
        expected=self.original(kind,fail)
        expected_files={name:(self.data/name).read_bytes() for name in OUTPUTS[kind]
                        if (self.data/name).is_file() and (self.data/name).read_bytes()!=before[name]}
        sink=MemoryOutput(self.data,fail)
        actual=execute(kind,str(self.data),RepositoryDataIO(self.data),sink,
                       inventory_roots=LEGACY_MIGRATION_INVENTORY if kind=='implemented-migration' else None)
        self.assertEqual(actual,expected)
        # A successful identical overwrite is still an original export effect.
        expected_names=[row[1] for row in sink.calls if row[0]=='write' and row[1]!=fail]
        self.assertEqual(sink.files,{name:(self.data/name).read_bytes() for name in expected_names})
        self.assertTrue(set(expected_files)<=set(sink.files))
        return actual,sink

    def test_complete_migration_real867_proposals_all_artifacts_json_markdown_and_streams(self):
        value,sink=self.compare('implemented-migration')
        self.assertEqual(value['exit_code'],0)
        report=json.loads(sink.files[OUTPUTS['implemented-migration'][0]])
        self.assertEqual(report['summary']['source_requirements'],867)
        self.assertEqual(report['summary']['artifact_records'],564)
        self.assertEqual(report['summary']['confirmed_register_entries'],19)
        self.assertEqual(report['status'],'review_required')
        self.assertEqual([row[0] for row in sink.calls],['write','write'])

    def test_complete_platform_real56_proposals_decisions_models_json_markdown_and_streams(self):
        value,sink=self.compare('pra-platform')
        self.assertEqual(value['exit_code'],0)
        report=json.loads(sink.files[OUTPUTS['pra-platform'][0]])
        self.assertEqual(report['summary']['requirements'],56)
        self.assertTrue(report['decision_rules']['separate_human_decisions_required'])
        self.assertFalse(report['decision_rules']['activation_or_runtime_change_authorized'])
        self.assertEqual(sink.calls[0],('mkdir','docs/governance/review-packets/PRA-2026-001',0o777,True,True))

    def test_every_form_classifier_branch_and_original_priority(self):
        engine=PRARequirementPlatformReview(PurePosixPath('/data'),PurePosixPath('/output'))
        statements=['Systems MUST:','Implement the following logical architecture layers now',
            'Implement the following mandatory capabilities','May be deployed for projects',
            'Shall be responsible for operations','Shall be verified through testing',
            'Shall be applied together with related rules','Platform stack capability requirements',
            'Control baseline level | Meaning','Control baseline requirement | Meaning',
            'They MUST retain evidence','It MUST work','Systems shall retain evidence',
            'Systems must record owners','Systems may include other tools','Descriptive model row',
            ' \tSystems\nMUST retain evidence\r\n']
        for value in statements:
            with self.subTest(statement=value):
                self.assertEqual(engine.classify_form(value),ORIGINALS['pra-platform'].classify_form(value))

    def test_all_original_candidate_lineage_threshold_rounding_ties_and_top8(self):
        root=PurePosixPath('/data')
        engine=ImplementedRequirementMigration(root,root,())
        proposal={'case_id':'case','proposal_id':'proposal','source_id':'ARCH-EA-REQ-001',
                  'source_requirement_id':'source-row','statement':'Systems MUST retain evidence','decision':None}
        artifacts=[{'source_basis':'ARCH-SDD-REQ-001','type':'architecture','comparison_text':proposal['statement'],
                    'path':'architecture/'+str(n)+'.yaml','artifact_id':str(n),'sha256':'a'*64} for n in range(12)]
        artifacts += [{'source_basis':'other','type':'controls','comparison_text':'different','path':'model/other.yaml','artifact_id':None,'sha256':'b'*64}]
        for source in ['ARCH-EA-REQ-001','ARCH-PA-REQ-001','ARCH-SA-REQ-001','ARCH-TPL-REQ-001','ARCH-SDD-REQ-001','other']:
            with self.subTest(source=source):
                current={**proposal,'source_id':source}
                self.assertEqual(engine.candidate_rows([current],artifacts),ORIGINALS['implemented-migration'].candidate_rows([current],artifacts))
        rows=engine.candidate_rows([proposal],artifacts)
        self.assertEqual(len(rows[0]['mapping_candidates']),8)
        self.assertTrue(all(x['review_state']=='human_equivalence_confirmation_required' for x in rows[0]['mapping_candidates']))
        self.assertTrue(all(x['lineage_assessment']=='lineage_confirmation_required' for x in rows[0]['mapping_candidates']))

    def test_original_invalid_json_and_missing_input_errors_preserve_whole_wire(self):
        path=self.data/'generated/reports/implemented-requirement-migration.json'
        path.write_text('{broken')
        result,sink=self.compare('pra-platform')
        self.assertEqual(result['exit_code'],1);self.assertEqual(result['kernel_exception']['type'],'JSONDecodeError')
        self.assertEqual(sink.calls,[])
        path.unlink()
        result,sink=self.compare('pra-platform')
        self.assertEqual(result['kernel_exception']['type'],'FileNotFoundError')
        self.assertEqual(sink.calls,[])

    def test_original_minimum_of_empty_platform_candidates_fails_before_output(self):
        path=self.data/'generated/reports/implemented-requirement-migration.json'
        value=json.loads(path.read_bytes())
        for row in value['requirement_candidates']:row['mapping_candidates']=[]
        path.write_text(json.dumps(value))
        result,sink=self.compare('pra-platform')
        self.assertEqual(result['kernel_exception']['type'],'ValueError')
        self.assertIn('min()',result['kernel_exception']['message'])
        self.assertEqual(sink.calls,[])

    def test_original_second_export_failure_preserves_first_whole_file_and_no_summary(self):
        for kind in SPECS:
            with self.subTest(kind=kind):
                result,sink=self.compare(kind,OUTPUTS[kind][1])
                self.assertEqual(result['exit_code'],1);self.assertEqual(result['kernel_exception']['type'],'OSError')
                self.assertEqual(result['stdout'],'')
                self.assertEqual(set(sink.files),{OUTPUTS[kind][0]})

    def test_original_nonfinite_data_is_preserved_as_opaque_export_bytes(self):
        path=self.data/'generated/reports/implemented-requirement-migration.json'
        value=json.loads(path.read_bytes())
        for row in value['requirement_candidates']:
            if row['source_id']=='PRA-STD-REQ-001':
                for item in row['mapping_candidates']:item['similarity']=float('nan')
        path.write_text(json.dumps(value))
        result,sink=self.compare('pra-platform')
        self.assertEqual(result['exit_code'],0)
        self.assertIn(b'NaN',sink.files[OUTPUTS['pra-platform'][0]])

    def test_every_whole_original_method_and_main_AST_with_only_explicit_ports(self):
        for kind,(stem,_,mapping,filename,class_name) in SPECS.items():
            original=ast.parse((ROOT/'tests/fixtures/v2-requirement-review-original'/(stem+'.py.txt')).read_bytes())
            functions={n.name:n for n in original.body if isinstance(n,ast.FunctionDef)}
            core=ast.parse((ROOT/'scripts/lib'/filename).read_bytes())
            cls=next(n for n in core.body if isinstance(n,ast.ClassDef) and n.name==class_name)
            methods={n.name:n for n in cls.body if isinstance(n,ast.FunctionDef)}
            reverse={v:k for k,v in mapping.items()}
            inventory=next((n.iter for n in functions['inventory'].body if isinstance(n,ast.For) and isinstance(n.iter,ast.Tuple)),None) if 'inventory' in functions else None
            class OriginalNames(ast.NodeTransformer):
                def visit_Attribute(self,node):
                    if isinstance(node.value,ast.Name) and node.value.id=='self':
                        if node.attr=='inventory_roots':return deepcopy(inventory)
                        if node.attr=='minimum':return ast.Name('min',node.ctx)
                        return ast.Name(reverse.get(node.attr,node.attr),node.ctx)
                    return self.generic_visit(node)
                def visit_Name(self,node):
                    if node.id=='yaml_text':return ast.Attribute(ast.Name('yaml',ast.Load()),'safe_load',node.ctx)
                    return node
            self.assertEqual(set(methods),set(functions)|{'__init__'})
            for name,method in functions.items():
                with self.subTest(kind=kind,method=name):
                    normalized=deepcopy(methods[name]);normalized.args.args.pop(0)
                    self.assertEqual(ast.dump(OriginalNames().visit(normalized),include_attributes=False),ast.dump(method,include_attributes=False))

    def test_provider_selection_is_an_explicit_adapter_and_core_has_no_provider_access(self):
        for name in ['requirement_migration_generation.py','requirement_platform_generation.py','requirement_review_context.py']:
            self.assertEqual(violations('scripts/lib/'+name,(ROOT/'scripts/lib'/name).read_text()),[])
            self.assertNotIn('.github/workflows',(ROOT/'scripts/lib'/name).read_text())
        with self.assertRaisesRegex(ValueError,'explicit_inventory'):
            execute('implemented-migration',str(self.data),RepositoryDataIO(self.data),MemoryOutput(self.data))
        with self.assertRaisesRegex(ValueError,'namespace_invalid'):
            ReviewOutputPath('/data',MemoryOutput(self.data),'../escape')


if __name__=='__main__':unittest.main()
