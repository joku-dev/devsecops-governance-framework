"""Entire original prefix guard; controlled real Git here is test-only, no runtime adapter claim."""
from pathlib import Path
import ast,copy,hashlib,json,os,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_operating_verification as fixture
from test_v2_personal_channel_programs import snapshot
from test_v2_pilot_action_verification import git,commit
ORIGINAL=ROOT/'tests/fixtures/v2-operating-verification-original/scripts__validate_governance_lifecycle_ledger.py.txt'
FIXTURE=ROOT/'tests/fixtures/v2-accepted-prefix-original'
TRANSACTION='governance/lifecycle/synthetic/transactions/00000001-'+'a'*64+'.json'
PROFILE='model/governance/lifecycle/synthetic-grs002-profile.json'
EXCEPTION='model/governance/lifecycle/synthetic-exception-profile.json'
PREPARATION='model/governance/lifecycle/live-pilot/profiles/00000001.json'
ORACLE='''import json,sys
from validate_governance_lifecycle_ledger import check_accepted_prefix
print(json.dumps(check_accepted_prefix(sys.argv[1],sys.argv[2])))
'''
CURRENT='''import json,sys,subprocess
from pathlib import Path
from jsonschema import Draft202012Validator
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.accepted_prefix import AcceptedPrefix
class ControlledTestGit:
 @staticmethod
 def check_output(command,**kw):
  assert command[0]=='git' and command[1] in ('cat-file','ls-files','ls-tree','hash-object','rev-parse') and '-w' not in command
  return subprocess.check_output(command,**kw)
 @staticmethod
 def run(command,**kw):
  assert command[:3]==['git','cat-file','-e'] and kw['capture_output'] is True
  return subprocess.run(command,**kw)
root=Path(sys.argv[1]);context=RepositoryLifecycle(root,validator_class=Draft202012Validator,path_factory=Path)
print(json.dumps(AcceptedPrefix(context,path_factory=Path,transport=ControlledTestGit()).check_accepted_prefix(root,sys.argv[2])))
'''

class WholeAcceptedPrefix(unittest.TestCase):
    def setUp(self):
        c=fixture.WholeOperatingVerification();c.setUp();self.addCleanup(c.doCleanups);self.fixture=c

    def selected(self,kind):
        root,tools,_=self.fixture.selected('accepted')
        contract=json.loads((FIXTURE/'contract.json').read_bytes());raw=(FIXTURE/contract['fixture']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),contract['sha256']);(root/contract['path']).write_bytes(raw)
        transaction=root/TRANSACTION;transaction.parent.mkdir(parents=True,exist_ok=True);transaction.write_bytes(b'{"explicit_prefix_fixture":true}\n')
        for name in (PROFILE,EXCEPTION):
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
            if not p.exists():p.write_bytes(b'{}\n')
        if kind=='absent-exception':(root/EXCEPTION).unlink()
        if kind in ('CRLF','UTF16'):
            (root/'.gitattributes').write_text('governance/lifecycle/synthetic/transactions/*.json text '+('eol=lf' if kind=='CRLF' else 'working-tree-encoding=UTF-16LE')+'\n')
            if kind=='UTF16':transaction.write_bytes(transaction.read_text().encode('utf-16-le'))
        if kind=='accepted-transaction-mode':transaction.chmod(0o755)
        if kind=='accepted-preparation-mode':(root/PREPARATION).chmod(0o755)
        base=commit(root)
        if kind=='modified':transaction.write_bytes(b'{"explicit_changed_fixture":true}\n')
        elif kind=='deleted':transaction.unlink()
        elif kind=='symlink':
            target=root/'explicit-link-target.json';target.write_bytes(transaction.read_bytes());transaction.unlink();transaction.symlink_to(target)
        elif kind=='tracked-lock':
            p=transaction.parent.parent/'.append.lock';p.write_bytes(b'');git(root,'add',str(p))
        elif kind=='profile':(root/PROFILE).write_bytes(b'{"explicit_profile_change":true}\n')
        elif kind=='exception':(root/EXCEPTION).write_bytes(b'{"explicit_exception_change":true}\n')
        elif kind=='deleted-exception':(root/EXCEPTION).unlink()
        elif kind=='preparation':(root/PREPARATION).write_bytes(b'{"explicit_preparation_change":true}\n')
        elif kind=='deleted-preparation':(root/PREPARATION).unlink()
        elif kind=='CRLF':transaction.write_bytes(transaction.read_bytes().replace(b'\n',b'\r\n'))
        if kind=='bad-base':base='not-a-sha'
        elif kind=='zero-base':base='0'*40
        elif kind=='missing-base':base='f'*40
        return root,base

    def compare(self,kind='normal'):
        root,base=self.selected(kind);before=snapshot(root);env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')};env.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1',PYTHONDONTWRITEBYTECODE='1')
        old=subprocess.run([sys.executable,'-B','-c',ORACLE,str(root),base],cwd=root,env={**env,'PYTHONPATH':str(root/'scripts')},capture_output=True,timeout=180)
        current=subprocess.run([sys.executable,'-B','-c',CURRENT,str(root),base],cwd=root,env={**env,'PYTHONPATH':str(ROOT/'scripts')},capture_output=True,timeout=180)
        expected=0 if kind in ('normal','absent-exception','CRLF','UTF16') else 1
        self.assertEqual(old.returncode,expected,(kind,old.stderr[-3500:]));self.assertEqual(current.returncode,old.returncode,(kind,current.stderr[-3500:]));self.assertEqual(current.stdout,old.stdout);self.assertEqual(snapshot(root),before)
        if expected:
            old_type,separator,old_message=old.stderr.splitlines()[-1].partition(b': ')
            new_type,new_separator,new_message=current.stderr.splitlines()[-1].partition(b': ')
            self.assertEqual(separator,b': ');self.assertEqual(new_separator,separator)
            self.assertEqual(new_type.rsplit(b'.',1)[-1],old_type.rsplit(b'.',1)[-1]);self.assertEqual(new_message,old_message)
            if old_type.endswith(b'.ContractError'):
                self.assertEqual(old_type,b'lib.governance_lifecycle.contracts.ContractError')
                self.assertEqual(new_type,b'lib.repository_lifecycle.contracts.ContractError')
                # This known namespace difference is asserted, never reported as
                # full external Python traceback wire equality.
            else:self.assertEqual(new_type,old_type)
            # Native Git stderr (when present) precedes interpreter traceback.
            old_prefix=old.stderr.split(b'Traceback (most recent call last):',1)[0];current_prefix=current.stderr.split(b'Traceback (most recent call last):',1)[0];self.assertEqual(current_prefix,old_prefix)
        else:self.assertEqual(current.stderr,old.stderr)

    def test_entire_original_git_and_prefix_AST_after_only_declared_context_path_transport_ports(self):
        old=ast.parse(ORIGINAL.read_bytes());cls=next(n for n in ast.parse((ROOT/'scripts/lib/accepted_prefix.py').read_bytes()).body if isinstance(n,ast.ClassDef))
        names={'self.context.contracts.require':'require','self.Path':'Path','self.context.ledger.input_ledger_paths':'LEDGER_PATHS','self.context.ledger.LEDGER_PATH':'LEDGER_PATH','self.context.ledger.PILOT_LEDGER_PATH':'PILOT_LEDGER_PATH','self.context.ledger.EXCEPTION_LEDGER_PATH':'EXCEPTION_LEDGER_PATH','self.context.ledger.PROFILE_PATH':'PROFILE_PATH','self.context.ledger.EXCEPTION_PROFILE_PATH':'EXCEPTION_PROFILE_PATH','self.context.preparation.PREPARATION_PATH':'PREPARATION_PATH','self.context.admission.OPERATING_PATH':'OPERATING_PATH','self.transport.run':'subprocess.run','self.transport.check_output':'subprocess.check_output','self.git':'git'}
        class Restore(ast.NodeTransformer):
            def visit_Attribute(self,node):return ast.copy_location(ast.parse(names[ast.unparse(node)],mode='eval').body,node) if ast.unparse(node) in names else self.generic_visit(node)
        for name in ('git','check_accepted_prefix'):
            original=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name==name);new=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name));self.assertEqual(new.args.args.pop(0).arg,'self');self.assertEqual(ast.dump(Restore().visit(new),include_attributes=False),ast.dump(original,include_attributes=False))

    def test_normal_and_absent_optional_exception_original_complete_Git_paths(self):
        for kind in ('normal','absent-exception'):
            with self.subTest(kind=kind):self.compare(kind)

    def test_invalid_zero_and_nonexistent_bases_preserve_require_and_Git_diagnostics(self):
        for kind in ('bad-base','zero-base','missing-base'):
            with self.subTest(kind=kind):self.compare(kind)

    def test_tracked_nontransaction_and_accepted_mode_are_rejected(self):
        for kind in ('tracked-lock','accepted-transaction-mode','accepted-preparation-mode'):
            with self.subTest(kind=kind):self.compare(kind)

    def test_modified_deleted_and_symlink_replaced_transactions_retain_original_guards(self):
        for kind in ('modified','deleted','symlink'):
            with self.subTest(kind=kind):self.compare(kind)

    def test_default_exception_and_preparation_migrations_stay_versioned(self):
        for kind in ('profile','exception','deleted-exception','preparation','deleted-preparation'):
            with self.subTest(kind=kind):self.compare(kind)

    def test_original_builtin_CRLF_and_UTF16_clean_conversion_semantics(self):
        for kind in ('CRLF','UTF16'):
            with self.subTest(kind=kind):self.compare(kind)
