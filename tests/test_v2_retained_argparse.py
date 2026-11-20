"""Whole formatter/source fidelity and actual unchanged original parser streams."""
from pathlib import Path
from unittest.mock import patch
import argparse,ast,copy,hashlib,io,json,os,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.retained_argparse import validate_context,formatter_factory,parser_base,PROFILES
from lib.providers.retained_argparse import capture_context
from lib.synthetic_ledger_execution import execute
from lib.synthetic_ledger_context import PROGRAMS
import test_v2_synthetic_ledger_core as reference

FIXTURE=ROOT/'tests/fixtures/v2-argparse-profiles'

def context(minor,width=78):
    return {'schema_version':1,'implementation':'cpython','version':[3,minor,3],
        'profile':f'cpython-3.{minor}-argparse-v1','width':width,'translation_profile':'stdlib-en-v1'}

def forbidden(binding):raise AssertionError('No selected source/ledger/files before successful parsing')

def kernel(program,args,frame):
    return execute('/absent-source','/absent-source',program,args,port_factory=forbidden,
        validator_factory=lambda io:None,parser_context=frame)['kernel_result']

class RetainedArgparse(unittest.TestCase):
    def test_both_whole_formatter_class_and_nested_AST_bodies_retained_except_width_discovery(self):
        contract=json.loads((FIXTURE/'contract.json').read_bytes())
        for side,minor in (('CI',11),('Mac',13),('Linux',12)):
            raw=(FIXTURE/(side+'-HelpFormatter.py.txt')).read_bytes()
            profile=contract['profiles'][f'cpython-3.{minor}-argparse-v1']
            self.assertEqual(hashlib.sha256(raw).hexdigest(),profile['original_class_sha256'])
            expected=ast.parse(raw).body[0]
            actual=next(n for n in ast.parse((ROOT/f'scripts/lib/argparse_profiles/cpython3{minor}.py').read_bytes()).body if isinstance(n,ast.ClassDef) and n.name=='HelpFormatter')
            original_init=next(n for n in expected.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
            copied_init=next(n for n in actual.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
            self.assertEqual(ast.unparse(copied_init.body[0]),'if width is None:\n    raise ValueError(\'retained_formatter_explicit_width_required\')')
            copied_init.body[0]=copy.deepcopy(original_init.body[0])
            self.assertEqual(ast.dump(actual,include_attributes=False),ast.dump(expected,include_attributes=False))
            self.assertIn('PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2',(ROOT/f'scripts/lib/argparse_profiles/LICENSE-3.{minor}.txt').read_text())
            # The whole parser/group/action machinery is retained too. Restore
            # only the three declared composition differences before comparing
            # the frozen portable AST digest of the actual original module.
            module=ast.parse((ROOT/f'scripts/lib/argparse_profiles/cpython3{minor}.py').read_bytes())
            formatter=next(n for n in module.body if isinstance(n,ast.ClassDef) and n.name=='HelpFormatter')
            next(n for n in formatter.body if isinstance(n,ast.FunctionDef) and n.name=='__init__').body[0]=copy.deepcopy(original_init.body[0])
            nodes=[];translation_restored=False
            for node in module.body:
                if isinstance(node,ast.ImportFrom) and node.module=='argparse' and any(v.asname=='_HOST_SUPPRESS' for v in node.names):continue
                if isinstance(node,ast.FunctionDef) and node.name in ('_','ngettext'):
                    if not translation_restored:nodes.extend(ast.parse(profile['original_translation_node_source']).body);translation_restored=True
                    continue
                if isinstance(node,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='SUPPRESS' for v in node.targets):node.value=ast.Constant('==SUPPRESS==')
                nodes.append(node)
            module.body=nodes
            def portable(node):
                if isinstance(node,ast.AST):return [type(node).__name__,[[key,portable(value)] for key,value in ast.iter_fields(node) if not(key=='type_params' and not value)]]
                if isinstance(node,list):return [portable(v) for v in node]
                return node
            digest=hashlib.sha256(json.dumps(portable(module),separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
            self.assertEqual(digest,profile['original_module_portable_ast_sha256'])

    def test_current_native_profile_complete_rich_help_usage_alias_metavars_groups_and_widths_equal(self):
        def parser(factory,cls=argparse.ArgumentParser):
            p=cls(prog='whole-example.py',description='A complete original formatter example with Unicode Ünicode and useful words.',formatter_class=factory)
            p.add_argument('--output','-o',required=True,metavar='OUTPUT',help='selected output %(default)s',default='example')
            p.add_argument('--choice',choices=('one','two'),help='a choice')
            p.add_argument('--pair',nargs=2,metavar=('FIRST','SECOND'));p.add_argument('--many',nargs='*')
            group=p.add_mutually_exclusive_group(required=True);group.add_argument('--yes',action='store_true');group.add_argument('--no',action='store_true')
            p.add_argument('--hidden',help=argparse.SUPPRESS);p.add_argument('items',nargs='*')
            return p
        for columns in (20,40,60,80,112,180):
            with patch.dict(os.environ,{'COLUMNS':str(columns),'LINES':'24'}):
                frame=capture_context();self.assertEqual(frame['width'],columns-2)
                native=parser(argparse.HelpFormatter);retained=parser(formatter_factory(frame),parser_base(frame))
                self.assertEqual(retained.format_help(),native.format_help())
                self.assertEqual(retained.format_usage(),native.format_usage())
                self.assertEqual(vars(retained.parse_args(['--output','x','--yes'])),vars(native.parse_args(['--output','x','--yes'])))

    def test_all_six_unchanged_original_cli_help_and_parser_streams_match_at_four_widths(self):
        fixture=reference.WholeSyntheticLedgerCore('test_complete_synthetic_demo_all_history_bytes_modes_stdout_and_nonempty_guard')
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        for columns in (40,60,80,112):
            with patch.dict(os.environ,{'COLUMNS':str(columns),'LINES':'24'}):
                frame=capture_context()
                for program,(filename,_) in PROGRAMS.items():
                    for args,code in ((['--help'],0),(['--unknown'],2),([],2)):
                        with self.subTest(columns=columns,program=program,args=args):
                            original=subprocess.run([sys.executable,'-B',str(fixture.root/'scripts'/filename),*args],cwd=fixture.root,capture_output=True,timeout=30,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
                            self.assertEqual(original.returncode,code,original.stderr)
                            value=kernel(program,args,frame)
                            self.assertEqual(value['exit_code'],code);self.assertIsNone(value['kernel_exception'])
                            self.assertEqual(value['stdout'].encode(),original.stdout)
                            self.assertEqual(value['stderr'].encode(),original.stderr)

    def test_three_actual_Linux312_regressions_reconstruct_complete_streams_using_explicit_profile(self):
        saved=json.loads((FIXTURE/'Linux-observed-parser-transcripts.json').read_bytes())
        for row in saved['cases']:
            expected=row['kernel_result'];actual=kernel(row['program'],row['argv'],context(12,saved['reconstruction_width']))
            self.assertEqual(actual,expected,row['case'])
            self.assertNotEqual(kernel(row['program'],row['argv'],context(13)),expected,row['case'])

    def test_pure_reconstruction_of_both_profiles_needs_no_terminal_environment_file_or_program(self):
        for minor in (11,12,13):
            frame=context(minor)
            with patch('shutil.get_terminal_size',side_effect=AssertionError('No terminal discovery')),patch('os.getenv',side_effect=AssertionError('No environment discovery')),patch('pathlib.Path.read_bytes',side_effect=AssertionError('No selected source')),patch('subprocess.Popen',side_effect=AssertionError('No process')):
                value=kernel('closure',['--help'],frame)
            self.assertEqual(value['exit_code'],0)

    def test_context_unknown_extra_type_bool_version_width_and_translation_mutations_fail_closed(self):
        valid=context(12)
        attacks=[{**valid,'schema_version':True},{**valid,'implementation':False},{**valid,'implementation':'pypy'},
            {**valid,'version':[3,True,3]},{**valid,'version':[3,13,3]},{**valid,'version':[3,12]},
            {**valid,'width':True},{**valid,'width':4095},{**valid,'width':-2},
            {**valid,'profile':'unknown'},{**valid,'translation_profile':'de'},{**valid,'extra':0},
            {k:v for k,v in valid.items() if k!='profile'},None]
        for bad in attacks:
            with self.assertRaises(ValueError):validate_context(bad)
        for minor in (11,12,13):
            with self.assertRaisesRegex(ValueError,'explicit_width'):PROFILES[context(minor)['profile']][1]('example')

    def test_native_formatter_identity_and_translation_changes_are_not_silently_admitted(self):
        with patch('lib.providers.retained_argparse.inspect.getsource',return_value='modified formatter'):
            with self.assertRaisesRegex(ValueError,'formatter_changed'):capture_context()
        with patch('argparse._',side_effect=lambda text:'different '+text):
            with self.assertRaisesRegex(ValueError,'translation_not_admitted'):capture_context()

    def test_complete_parser_profiles_ignore_consumer_gettext_and_terminal_during_replay(self):
        for minor in (11,12,13):
            for program in PROGRAMS:
                for argv in (['--help'],['--unknown'],[]):
                    frame=context(minor);expected=kernel(program,argv,frame)
                    with patch('argparse._',side_effect=AssertionError('No consumer gettext')),patch('argparse.ngettext',side_effect=AssertionError('No consumer plural translation')),patch('shutil.get_terminal_size',side_effect=AssertionError('No consumer terminal')):
                        actual=kernel(program,argv,frame)
                    self.assertEqual(actual,expected)

if __name__=='__main__':unittest.main(verbosity=2)
