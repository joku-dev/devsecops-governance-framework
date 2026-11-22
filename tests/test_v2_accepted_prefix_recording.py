"""Whole original prefix helper versus captured native execution and inert replay."""
from pathlib import Path
import json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_accepted_prefix as fixture
from test_v2_personal_channel_programs import snapshot

ORACLE='''import json,sys
from validate_governance_lifecycle_ledger import check_accepted_prefix
value=error=None
try:value=check_accepted_prefix(sys.argv[1],sys.argv[2])
except Exception as e:error={'type':type(e).__name__,'message':str(e)}
print(json.dumps({'return_value':value,'exception':error}))
'''
CURRENT='''from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,shutil,sys
from jsonschema import Draft202012Validator
from lib.accepted_prefix_context import execute
from lib.providers.accepted_prefix_transport import AcceptedPrefixTransport
from lib.providers.accepted_prefix_paths import NativePrefixPaths
from lib.accepted_prefix_paths import ReplayPrefixPaths
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.synthetic_lifecycle_io import ReplayIO
source,base,private=sys.argv[1:];private=Path(private);private.mkdir(mode=0o700)
def snapshot():
 return {str(p.relative_to(source)):(p.lstat().st_mode&0o777,os.readlink(p) if p.is_symlink() else p.read_bytes()) for p in Path(source).rglob('*') if p.is_file() or p.is_symlink()}
before=snapshot()
record=Record(private/'records',{'prototype':'whole prefix recording'},{'prototype':True});record.append({'kind':'execution-intent'})
owner=NativeIO(record,mode='private-candidate',cwd=source,private_state=private)
def run(io,native):
 return execute(source,source,base,io,validator_class=Draft202012Validator,
  transport_factory=lambda owner,root,context,emit:AcceptedPrefixTransport(owner,root,context,emit_stderr=emit),
  paths_factory=NativePrefixPaths if native else ReplayPrefixPaths)
result=run(owner,True)
assert snapshot()==before
record.finish('complete',{'exit_code':result['exit_code'],'kernel_result':result},owner.touched)
_,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
def inert(ref):
 raw=cache[ref['sha256']];assert hashlib.sha256(raw).hexdigest()==ref['sha256'] and len(raw)==ref['bytes'];seen.add(ref['sha256']);return raw
# Native Git metadata helper creation and removal are captured separately from
# original source effects. Check cleanup before deleting only this test fixture.
parent=private/'state/accepted-prefix-hash'
if parent.exists():assert list(parent.iterdir())==[]
shutil.rmtree(source)
replay=ReplayIO(events,inert,'private-candidate',source)
with patch('os.open',side_effect=AssertionError('No source/private input')),patch('subprocess.Popen',side_effect=AssertionError('No native Git')),patch('os.mkdir',side_effect=AssertionError('No auxiliary creation')):
 pure=run(replay,False);replay.finish()
assert pure==result and seen==set(cache)
for name,raw in cache.items():blob({'sha256':name,'bytes':len(raw)})
assert closed()
for part in result['stderr_parts']:
 if set(part)=={'blob'}:sys.stderr.buffer.write(cache[part['blob']['sha256']])
 else:assert set(part)=={'text'};sys.stderr.buffer.write(part['text'].encode())
print(json.dumps({'return_value':result['return_value'],'exception':result['kernel_exception']}))
'''

class WholePrefixRecording(unittest.TestCase):
    def setUp(self):
        case=fixture.WholeAcceptedPrefix();case.setUp();self.addCleanup(case.doCleanups);self.fixture=case
    def compare(self,kind='normal'):
        source,base=self.fixture.selected(kind)
        if kind=='deleted-ledger-parent':shutil.rmtree((source/fixture.TRANSACTION).parent)
        elif kind=='deleted-default-profile-parent':shutil.rmtree((source/fixture.PROFILE).parent)
        before=snapshot(source);env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','LD_','DYLD_'))};env.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1',PYTHONDONTWRITEBYTECODE='1')
        old=subprocess.run([sys.executable,'-B','-c',ORACLE,str(source),base],cwd=source,env={**env,'PYTHONPATH':str(source/'scripts')},capture_output=True,timeout=300);self.assertEqual(old.returncode,0,old.stderr[-3000:]);self.assertEqual(snapshot(source),before)
        actual=subprocess.run([sys.executable,'-B','-c',CURRENT,str(source),base,str(source.parent/('prefix-private-'+source.name))],cwd=source.parent,env={**env,'PYTHONPATH':str(ROOT/'scripts')},capture_output=True,timeout=300)
        self.assertEqual(actual.returncode,0,(kind,actual.stderr[-5000:]));self.assertEqual(actual.stdout,old.stdout,(kind,actual.stdout,old.stdout));self.assertEqual(actual.stderr,old.stderr,(kind,actual.stderr[-2500:],old.stderr[-2500:]));self.assertFalse(source.exists())
    def test_whole_normal_accepted_prefix_native_and_no_source_Git_or_private_replay(self):self.compare()
    def test_original_optional_exception_absence_and_builtin_CRLF_UTF16_conversion(self):
        for kind in ('absent-exception','CRLF','UTF16'):
            with self.subTest(kind=kind):self.compare(kind)
    def test_original_invalid_zero_and_missing_base_diagnostics(self):
        for kind in ('bad-base','zero-base','missing-base'):
            with self.subTest(kind=kind):self.compare(kind)
    def test_original_tracked_path_and_accepted_blob_mode_guards(self):
        for kind in ('tracked-lock','accepted-transaction-mode','accepted-preparation-mode'):
            with self.subTest(kind=kind):self.compare(kind)
    def test_original_deleted_modified_and_symlink_replaced_transaction_guards(self):
        for kind in ('modified','deleted','symlink'):
            with self.subTest(kind=kind):self.compare(kind)
    def test_original_profile_exception_and_all_preparation_immutability_guards(self):
        for kind in ('profile','exception','deleted-exception','preparation','deleted-preparation'):
            with self.subTest(kind=kind):self.compare(kind)

    def test_original_missing_ledger_and_profile_parent_directories_preserve_original_diagnostics(self):
        for kind in ('deleted-ledger-parent','deleted-default-profile-parent'):
            with self.subTest(kind=kind):self.compare(kind)
