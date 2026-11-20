"""Unintegrated whole original workbook classifier, parser, exports and failures."""
import argparse,ast,copy,errno,hashlib,importlib.util,io,json,os,shutil,sys,tempfile,unittest,zipfile
from contextlib import redirect_stdout,redirect_stderr
from importlib.machinery import SourceFileLoader
from pathlib import Path,PurePosixPath
from unittest.mock import patch
from xml.sax.saxutils import escape

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.harmonized_workbook_import import HarmonizedWorkbookImport
import lib.harmonized_workbook_import as neutral
from lib.v2_boundary import violations

FROZEN=ROOT/'tests/fixtures/v2-harmonized-workbook-original/import_harmonized_requirements_workbook.py.txt'
assert hashlib.sha256(FROZEN.read_bytes()).hexdigest()=='524c5cb67753b59e10890dc021d1f1625850ce5d7dd460323ffa0e2cdbc59a0f'
loader=SourceFileLoader('immutable_harmonized_workbook_original',str(FROZEN))
ORIGINAL=importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name,loader));loader.exec_module(ORIGINAL)
OUT=('model/traceability/standards-to-harmonized-requirements.yaml','generated/reports/harmonized-requirements-coverage.json','generated/reports/harmonized-requirements-coverage.md')

def workbook(rows):
    shared=[];xml=[]
    for number,values in rows:
        cells=[]
        for column,value in values.items():
            index=len(shared);shared.append(str(value))
            cells.append(f'<c r="{column}{number}" t="s"><v>{index}</v></c>')
        xml.append(f'<row r="{number}">'+''.join(cells)+'</row>')
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('xl/sharedStrings.xml','<sst xmlns="'+ORIGINAL.XML_NS+'">'+''.join('<si><t>'+escape(s)+'</t></si>' for s in shared)+'</sst>')
        archive.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="'+ORIGINAL.XML_NS+'"><sheetData>'+''.join(xml)+'</sheetData></worksheet>')
    return stream.getvalue()

class Memory:
    def __init__(self,files,fail=None):self.files=dict(files);self.calls=[];self.fail=fail
    def path(self,value):
        if isinstance(value,MemoryPath):assert value.port is self;return value
        return MemoryPath(self,PurePosixPath(value))
    def read(self,name):
        self.calls.append(('read',name))
        if name not in self.files:raise FileNotFoundError(errno.ENOENT,'No such file or directory',name)
        return self.files[name]
    def write(self,name,text,encoding):
        self.calls.append(('write',name))
        if name==self.fail:raise OSError(errno.ENOSPC,'No space left on device',name)
        self.files[name]=text.encode(encoding);return len(text)
    def mkdir(self,name,mode,parents,exist_ok):self.calls.append(('mkdir',name,mode,parents,exist_ok))

class MemoryPath:
    def __init__(self,port,value):self.port,self.value=port,value
    def __str__(self):return str(self.value)
    def __truediv__(self,other):return MemoryPath(self.port,self.value/str(other))
    @property
    def parent(self):return MemoryPath(self.port,self.value.parent)
    def relative_to(self,other):return self.value.relative_to(PurePosixPath(str(other)))
    def read_bytes(self):return self.port.read(str(self))
    def read_text(self,encoding=None):return self.read_bytes().decode(encoding or 'utf-8')
    def write_text(self,text,encoding=None):return self.port.write(str(self),text,encoding or 'utf-8')
    def mkdir(self,mode=0o777,parents=False,exist_ok=False):return self.port.mkdir(str(self),mode,parents,exist_ok)

def captured(call):
    stdout,stderr=io.StringIO(),io.StringIO()
    with redirect_stdout(stdout),redirect_stderr(stderr):
        try:code,error=call(),None
        except (Exception,SystemExit) as value:code,error=1,{'type':type(value).__name__,'message':str(value)}
    return {'exit_code':code,'stdout':stdout.getvalue(),'stderr':stderr.getvalue(),'kernel_exception':error}

class WholeHarmonizedWorkbookImport(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.data=Path(temporary.name).resolve()/'data';self.data.mkdir(mode=0o700)
        target=self.data/'model/requirements';target.mkdir(parents=True)
        shutil.copyfile(ROOT/'model/requirements/harmonized-devsecops-requirements.yaml',target/'harmonized-devsecops-requirements.yaml')
        self.xlsx=self.data/'source.xlsx'
        rows=[]
        for n,label in enumerate(ORIGINAL.STANDARD_ALIASES,4):
            rows.append((n,{'B':label,'C':'SM-6' if label=='IEC62443_4_1' else 'PW.5.1' if label=='NIST800-218' else 'REQ-'+str(n),'D':'security code review','G':'Systems MUST retain evidence '+str(n)}))
        rows.extend([(30,{'B':'IEC62443_4_1','C':'SM-6','D':'sbom','G':'same shared requirement'}),(31,{'B':'BSI-TR-03183-2','C':'','D':'component inventory','G':'same shared requirement'}),(32,{'B':'BSI-TR-03183-1','C':'','G':'An explanatory model row'})])
        self.xlsx.write_bytes(workbook(rows))

    def original(self,args,fail=None):
        old=Path.write_text
        def write(path,text,*a,**kw):
            if str(path)==fail:raise OSError(errno.ENOSPC,'No space left on device',str(path))
            return old(path,text,*a,**kw)
        with patch.object(ORIGINAL,'ROOT',self.data),patch.object(sys,'argv',['original-workbook',*args]),patch.object(Path,'write_text',write):
            return captured(ORIGINAL.main)

    def core(self,memory,args):
        engine=HarmonizedWorkbookImport(memory.path(self.data),path_factory=memory.path,
            zip_file=lambda path:zipfile.ZipFile(io.BytesIO(path.read_bytes())),
            yaml_load=ORIGINAL.yaml.safe_load,
            argument_parser=lambda:argparse.ArgumentParser(prog='original-workbook'),argv=args)
        with patch('subprocess.Popen',side_effect=AssertionError('No native program in kernel')),patch.object(Path,'open',side_effect=AssertionError('No native file in kernel')):
            return captured(engine.main)

    def compare(self,args=None,fail=None):
        args=['--input-xlsx',str(self.xlsx)] if args is None else args
        before={str(p):p.read_bytes() for p in self.data.rglob('*') if p.is_file()}
        memory=Memory(before,fail);expected=self.original(args,fail);actual=self.core(memory,args)
        self.assertEqual(actual,expected)
        writes=[name for action,name,*_ in memory.calls if action=='write' and name!=fail]
        self.assertEqual({name:memory.files[name] for name in writes},{name:Path(name).read_bytes() for name in writes})
        self.assertEqual({name:raw for name,raw in memory.files.items() if name not in writes},
                         {name:raw for name,raw in before.items() if name not in writes})
        return actual,memory

    def test_whole_real_model_all_standards_three_export_bytes_streams_and_candidate_boundaries(self):
        value,memory=self.compare();self.assertEqual(value['exit_code'],0)
        report=json.loads(memory.files[str(self.data/OUT[1])])
        self.assertEqual(report['status'],'candidate');self.assertFalse(report['normative']);self.assertEqual(report['enforcement'],'none')
        self.assertTrue(all(v is False for v in report['decision_boundary'].values()))
        mapping=ORIGINAL.yaml.safe_load(memory.files[str(self.data/OUT[0])])
        self.assertFalse(mapping['public_source_text_included']);self.assertEqual(mapping['summary']['missing_source_ids'],2)
        self.assertEqual(mapping['summary']['duplicate_identifier_pairs'],1)
        self.assertTrue(all(row['review_status']=='human_review_required' for row in mapping['mappings']))
        self.assertNotIn(b'Systems MUST retain evidence',memory.files[str(self.data/OUT[0])])

    def test_every_exact_source_prefix_content_priority_limit_and_fallback(self):
        memory=Memory({});engine=HarmonizedWorkbookImport(memory.path(self.data),path_factory=memory.path,zip_file=None,yaml_load=ORIGINAL.yaml.safe_load,argument_parser=None,argv=[])
        cases=[(source,identifier,'ignored text') for source,identifier in ORIGINAL.EXACT_SOURCE_ID_MAP]
        cases += [('NIST-SP-800-218',prefix+'.specific','ignored text') for prefix in ORIGINAL.NIST_PREFIX_MAP]
        texts=['license compliance spdx component hash dependency relationship sbom','risk assessment threat model security architecture','code review secure coding development environment external component version control','penetration test independent test test plan regression test security test vulnerability scan','authentication file upload input validation sensitive data security log secure default','artifact signing key trusted repositories reproducible build artifact integrity build pipeline','security update vulnerability management monitoring configuration baseline secure operation disposal vulnerability disclosure release approval','central identity machine readable evidence documentation security level lifecycle','completely different words']
        cases += [(source,'identifier',text) for source in ('BSI-TR-03183-2','other') for text in texts]
        for source,identifier,text in cases:
            with self.subTest(source=source,id=identifier,text=text):
                self.assertEqual(engine.classify(source,identifier,text),ORIGINAL.classify(source,identifier,text))
        for text in ('MUST','SHALL','MUSS','MÜSSEN','SHOULD','SOLLTE','SOLLTEN','MAY','KANN','descriptive','M /','R /','something M','something R'):
            self.assertEqual(engine.source_strength(text,''),ORIGINAL.source_strength(text,''))

    def test_original_row_range_whitespace_repeated_text_and_strength_combination(self):
        self.xlsx.write_bytes(workbook([(3,{'B':'unknown','G':'ignored'}),(4,{'B':' IEC62443_4_1 ','C':' SM-6 ','D':' sbom ','G':' same text ','H':'MUST'}),(267,{'B':'NIST800-218','C':'PW.5','D':'secure coding','G':'same text','H':'SHOULD'}),(268,{'B':'unknown','G':'ignored'})]))
        value,memory=self.compare();self.assertEqual(value['exit_code'],0)
        report=ORIGINAL.yaml.safe_load(memory.files[str(self.data/OUT[0])])
        self.assertEqual(report['summary']['raw_rows'],2);self.assertEqual(report['summary']['unique_source_requirements'],1)
        self.assertEqual(report['mappings'][0]['source_strengths'],['must','should'])

    def test_unknown_source_labels_and_unknown_requirement_targets_keep_original_system_exit(self):
        self.xlsx.write_bytes(workbook([(4,{'B':'not classified','G':'row'})]));value,_=self.compare()
        self.assertEqual(value['kernel_exception']['type'],'SystemExit')
        self.xlsx.write_bytes(workbook([(4,{'B':'IEC62443_4_1','C':'SM-6','G':'row'})]))
        model=self.data/'model/requirements/harmonized-devsecops-requirements.yaml';data=ORIGINAL.yaml.safe_load(model.read_bytes());data['requirements']=[v for v in data['requirements'] if v['id']!='HREQ-SC-003'];model.write_text(ORIGINAL.yaml.safe_dump(data))
        value,_=self.compare();self.assertEqual(value['kernel_exception']['type'],'SystemExit')

    def test_empty_workbook_bad_zip_missing_xml_and_unsafe_xml_original_errors(self):
        cases=[workbook([]),b'not a ZIP']
        for members in ({'xl/sharedStrings.xml':b'<broken>'},{'xl/sharedStrings.xml':b'<!DOCTYPE x><sst/>'},{'xl/sharedStrings.xml':b'<sst/>','xl/worksheets/sheet1.xml':b'<!ENTITY x "x"><worksheet/>'}):
            stream=io.BytesIO()
            with zipfile.ZipFile(stream,'w') as archive:
                for name,raw in members.items():archive.writestr(name,raw)
            cases.append(stream.getvalue())
        for raw in cases:
            with self.subTest(sha=hashlib.sha256(raw).hexdigest()):
                self.xlsx.write_bytes(raw);value,memory=self.compare();self.assertEqual(value['exit_code'],1)
                self.assertFalse(any(row[0]=='write' for row in memory.calls))

    def test_missing_and_invalid_model_and_missing_workbook_errors(self):
        model=self.data/'model/requirements/harmonized-devsecops-requirements.yaml';raw=model.read_bytes()
        for bad in (b'broken: [',b'null',b'{}'):
            model.write_bytes(bad);value,_=self.compare();self.assertEqual(value['exit_code'],1)
        model.unlink();value,_=self.compare();self.assertEqual(value['kernel_exception']['type'],'FileNotFoundError')
        model.write_bytes(raw);self.xlsx.unlink();value,_=self.compare();self.assertEqual(value['kernel_exception']['type'],'FileNotFoundError')

    def test_all_three_original_write_failures_preserve_order_and_prior_whole_files(self):
        for index,name in enumerate(OUT):
            with self.subTest(index=index):
                value,memory=self.compare(fail=str(self.data/name))
                self.assertEqual(value['kernel_exception']['type'],'OSError')
                writes=[n for action,n,*_ in memory.calls if action=='write']
                self.assertEqual(writes,[str(self.data/n) for n in OUT[:index+1]])

    def test_original_custom_outputs_outside_root_write_all_files_before_relative_print_error(self):
        external=self.data.parent/'external'
        args=['--input-xlsx',str(self.xlsx),'--mapping-output',str(external/'mapping.yaml'),'--report-json',str(external/'report.json'),'--report-md',str(external/'report.md')]
        value,memory=self.compare(args)
        self.assertEqual(value['kernel_exception']['type'],'ValueError');self.assertEqual(value['stdout'],'')
        self.assertEqual(len([x for x in memory.calls if x[0]=='write']),3)

    def test_original_argparse_missing_or_unknown_arguments_remain_system_exit(self):
        for args in ([],['--input-xlsx',str(self.xlsx),'--unknown-flag']):
            value,_=self.compare(args);self.assertEqual(value['kernel_exception'],{'type':'SystemExit','message':'2'})

    def test_whole_original_functions_and_main_AST_with_only_six_explicit_ports(self):
        legacy=(ROOT/'scripts/lib/providers/legacy_workbook_import.py').read_bytes()
        self.assertEqual(legacy.replace(b'ROOT = Path(__file__).resolve().parents[3]',b'ROOT = Path(__file__).resolve().parents[1]'),FROZEN.read_bytes())
        import importlib
        facade=importlib.import_module('import_harmonized_requirements_workbook')
        adapter=importlib.import_module('lib.providers.legacy_workbook_import')
        self.assertIs(facade,adapter);self.assertEqual(facade.ROOT,ROOT)
        original=ast.parse(FROZEN.read_bytes());new=ast.parse((ROOT/'scripts/lib/harmonized_workbook_import.py').read_bytes())
        old={n.name:n for n in original.body if isinstance(n,ast.FunctionDef)};cls=next(n for n in new.body if isinstance(n,ast.ClassDef));current={n.name:n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name!='__init__'}
        self.assertEqual(set(old),set(current));names=set(old)
        class Restore(ast.NodeTransformer):
            def visit_Attribute(self,n):
                if isinstance(n.value,ast.Name) and n.value.id=='self':
                    if n.attr=='argument_parser':return ast.copy_location(ast.Attribute(ast.Name('argparse',ast.Load()),'ArgumentParser',n.ctx),n)
                    if n.attr=='yaml_load':return ast.copy_location(ast.Attribute(ast.Name('yaml',ast.Load()),'safe_load',n.ctx),n)
                    if n.attr in names|{'root','path_factory','zip_file'}:return ast.copy_location(ast.Name({'root':'ROOT','path_factory':'Path','zip_file':'ZipFile'}.get(n.attr,n.attr),n.ctx),n)
                return self.generic_visit(n)
            def visit_Call(self,n):
                if isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='parser' and n.func.attr=='parse_args':
                    self.assert_args(n);n.args=[]
                return self.generic_visit(n)
            @staticmethod
            def assert_args(n):assert len(n.args)==1 and ast.unparse(n.args[0])=='self.argv' and not n.keywords
        for name,node in old.items():
            changed=copy.deepcopy(current[name]);self.assertEqual(changed.args.args.pop(0).arg,'self');changed=Restore().visit(changed)
            self.assertEqual(ast.dump(node,include_attributes=False),ast.dump(changed,include_attributes=False),name)
        old_constants=[n for n in original.body if isinstance(n,ast.Assign) and not any(isinstance(t,ast.Name) and t.id=='ROOT' for t in n.targets)]
        new_constants=[n for n in new.body if isinstance(n,ast.Assign)]
        self.assertEqual([ast.dump(n,include_attributes=False) for n in old_constants],[ast.dump(n,include_attributes=False) for n in new_constants])
        self.assertEqual(violations('scripts/lib/harmonized_workbook_import.py',(ROOT/'scripts/lib/harmonized_workbook_import.py').read_text()),[])


if __name__=='__main__':unittest.main()
