"""Whole original publication of a large encoded receipt and inert reconstruction.

These tests establish storage behavior, not acceptance of the synthetic payload
as a governance receipt. Full capture/receipt validation has separate oracles.
"""
from pathlib import Path
from unittest.mock import patch
import base64,copy,hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.synthetic_ledger_budget import DEFAULT,PILOT_RUN,LedgerBudget,admitted
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.pilot_run_intake_io import ReplayRunIO
from lib.providers.synthetic_ledger_io import NativeIO
from lib.providers.synthetic_ledger_files import LedgerFiles
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.synthetic_ledger_effects import NativeLedgerEffects
from lib.synthetic_ledger_replay_effects import ReplayLedgerEffects
from lib.synthetic_ledger_private import PrivateLedgerPort
from lib.synthetic_ledger_store import SyntheticLedgerStore
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.synthetic_lifecycle_context import LifecyclePaths
from lib.synthetic_ledger_projection import LedgerProjection
from test_v2_synthetic_ledger_core import original_sources,snapshot,restore

def name_of(raw):
    value=json.loads(raw)
    return f"{value['sequence']:08d}-{value['transaction_id'].split(':')[1]}.json"

class PilotRunLedgerBudget(unittest.TestCase):
    def setUp(self):
        previous=os.umask(0o077);self.addCleanup(os.umask,previous)
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.top=Path(temporary.name).resolve();self.source=self.top/'data';self.source.mkdir(mode=0o700)
        self.private=self.top/'private';self.private.mkdir(mode=0o700)
        self.ledger=self.source/'ledger';self.transactions=self.ledger/'transactions';self.transactions.mkdir(parents=True,mode=0o700)
    def owner(self, native, *, wide=True):
        record=Record(self.private/'records',{'test':'bounded-large-ledger-publication'},{'storage_only':True})
        record.append({'kind':'execution-intent'})
        cls=NativeRunIO if wide else NativeIO
        owner=cls(record,mode='selected-files' if native else 'private-candidate',cwd=str(self.source),private_state=self.private,product_root=ROOT,ledger=str(self.ledger),transaction_name=name_of)
        return owner,record
    def store(self,owner,native,replay=False):
        paths=LifecyclePaths(self.source,self.source,owner)
        context=RepositoryLifecycle(paths.path(str(self.source)),validator_class=None,path_factory=paths.path)
        effects=(ReplayLedgerEffects if replay else NativeLedgerEffects)(owner,str(self.ledger),transaction_name=name_of) if native else PrivateLedgerPort(owner,str(self.ledger))
        return SyntheticLedgerStore(context,path_factory=paths.path,native=effects,locking=effects,temporary=effects),effects,paths
    def compare_publication(self, native, payload_bytes):
        original_sources(self.source)
        payload={'sequence':1,'transaction_id':'sha256:'+hashlib.sha256(b'engineering test receipt').hexdigest(),'capture':{'test':base64.b64encode(b'X'*payload_bytes).decode('ascii')}}
        input_file=self.source/'payload.json';input_file.write_text(json.dumps(payload));input_file.chmod(0o600)
        before=snapshot(self.source)
        script='from pathlib import Path\nimport json,os\nfrom lib.governance_lifecycle.store import publish_transaction\nos.umask(0o077)\npublish_transaction(Path('+repr(str(self.transactions))+'),json.loads(Path('+repr(str(input_file))+').read_bytes()))'
        old=subprocess.run([sys.executable,'-B','-c',script],cwd=self.source,capture_output=True,timeout=180,env={**os.environ,'PYTHONPATH':str(self.source/'scripts'),'PYTHONDONTWRITEBYTECODE':'1'})
        self.assertEqual(old.returncode,0,old.stderr[-2000:]);self.assertEqual(old.stdout,b'');self.assertEqual(old.stderr,b'')
        expected=snapshot(self.source);raw=expected[0]['ledger/transactions/'+name_of(json.dumps(payload))][0]
        self.assertGreater(len(raw),2*1024**2)
        if payload_bytes>12*1024**2:self.assertGreater(len(raw),DEFAULT.file)
        self.assertLess(len(raw),PILOT_RUN.file);restore(self.source,before)
        owner,record=self.owner(native);store,effects,paths=self.store(owner,native)
        previous=os.umask(0o077)
        try:store.publish_transaction(paths.path(str(self.transactions)),payload)
        finally:os.umask(previous)
        self.assertFalse(record.capture_incomplete);self.assertFalse(effects.descriptors)
        if native:self.assertEqual(snapshot(self.source),expected)
        else:
            self.assertEqual(snapshot(self.source),before)
            files,dirs=map(dict,before)
            for label,value in owner.projected_changes.items():
                name=Path(label).relative_to(self.source).as_posix()
                if value['kind']=='file':files[name]=((record.blobs/value['content']['sha256']).read_bytes(),value['mode'])
                elif value['kind']=='directory':dirs[name]=value['mode']
                elif value['kind']=='missing':files.pop(name,None);dirs.pop(name,None)
                else:self.fail(value)
            self.assertEqual((files,dirs),expected)
        # Native input and private preimage paths must also read the committed
        # large file, rather than only allowing a large outgoing stream.
        selected=str(self.transactions/name_of(json.dumps(payload)))
        if native:self.assertEqual(owner.read(selected,selected),raw)
        record.finish('complete',{'exit_code':0},owner.touched)
        _,_,_,events,blob,closed=read_record(record.root)
        cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};used=set()
        def inert(ref):
            value=cache[ref['sha256']];self.assertEqual(len(value),ref['bytes']);used.add(ref['sha256']);return value
        shutil.rmtree(self.source)
        replay=ReplayRunIO(events,inert,owner.mode,str(self.source),ledger=str(self.ledger),transaction_name=name_of)
        core,ports,replay_paths=self.store(replay,native,replay=True)
        with patch('os.open',side_effect=AssertionError('No source or native effect')),patch('subprocess.Popen',side_effect=AssertionError('No process')):
            core.publish_transaction(replay_paths.path(str(self.transactions)),payload)
            if native:self.assertEqual(replay.read(selected,selected),raw)
            replay.finish()
        self.assertFalse(ports.descriptors);self.assertEqual(replay.projected_changes,owner.projected_changes)
        if native:self.assertEqual(ports.state.observed,effects.state.observed)
        self.assertEqual(used,set(cache))
        for key in used:blob({'sha256':key,'bytes':len(cache[key])})
        self.assertTrue(closed())
    def test_original_whole_publication_above_16MiB_and_pure_replay_both_modes(self):
        for native in (True,False):
            with self.subTest(native=native):
                # Each comparison deletes its source before replay.
                if not self.source.exists():self.source.mkdir(mode=0o700);self.transactions.mkdir(parents=True,mode=0o700)
                self.compare_publication(native,13*1024**2)
    def test_ordinary_existing_ledger_budget_still_rejects_large_file(self):
        owner,record=self.owner(True,wide=False);large=self.transactions/'large.json'
        with large.open('wb') as handle:handle.truncate(DEFAULT.file+1)
        large.chmod(0o600)
        with self.assertRaisesRegex(InputAdmissionError,'regular_bounded_file_required'):owner.read(str(large),str(large))
        self.assertTrue(record.capture_incomplete)
        self.assertEqual(owner.ledger_budget,DEFAULT)
    def test_replayed_wide_file_cannot_escape_transaction_scope_or_use_old_profile(self):
        raw=b'X'*(DEFAULT.file+1);ref={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
        value={'kind':'file','mode':0o600,'identity':[9,1],'content':ref}
        ledger=str(self.ledger)
        wide=LedgerProjection(lambda selected:raw,budget=PILOT_RUN,ledger=ledger)
        with self.assertRaisesRegex(IntegrityError,'wide_file_scope'):wide.load_one(str(self.source/'other.json'),value)
        wide.load_one(str(self.transactions/'one.json'),value)
        old=LedgerProjection(lambda selected:raw)
        with self.assertRaises(IntegrityError):old.load_one(str(self.transactions/'one.json'),value)
    def test_large_ordinary_private_preimage_is_bound_and_cannot_be_resealed_as_an_alias(self):
        raw=b'X'*(DEFAULT.file+1);selected=self.transactions/'existing.json'
        selected.write_bytes(raw);selected.chmod(0o600)
        owner,record=self.owner(False)
        original=owner.projection.prepare(str(selected),str(selected))
        record.finish('complete',{'exit_code':0},owner.touched)
        _,_,_,events,blob,closed=read_record(record.root)
        cache={p.name:p.read_bytes() for p in record.blobs.iterdir()}
        self.assertEqual(sum(row['kind']=='synthetic-ledger-private-wide-preimage' for row in events),1)
        shutil.rmtree(self.source)
        def replay(rows):
            io=ReplayRunIO(rows,lambda ref:cache[ref['sha256']],owner.mode,str(self.source),ledger=str(self.ledger),transaction_name=name_of)
            value=io.projection.prepare(str(selected),str(selected));io.finish();return value
        with patch('os.open',side_effect=AssertionError('No selected source')),patch('subprocess.Popen',side_effect=AssertionError('No program')):
            self.assertEqual(replay(events),original)
            tampered=copy.deepcopy(events)
            next(row for row in tampered if row['kind']=='synthetic-ledger-private-wide-preimage')['kind']='synthetic-ledger-private-alias-preimage'
            with self.assertRaisesRegex(IntegrityError,'alias_pair_required'):replay(tampered)
        for key,value in cache.items():blob({'sha256':key,'bytes':len(value)})
        self.assertTrue(closed())

    def test_budget_profiles_are_finite_fixed_and_default_read_limit_is_unchanged(self):
        self.assertEqual((DEFAULT.file,DEFAULT.total),(16*1024**2,128*1024**2))
        self.assertEqual((PILOT_RUN.file,PILOT_RUN.total),(64*1024**2,2*1024**3))
        for invalid in (None,True,{'file':PILOT_RUN.file},LedgerBudget(PILOT_RUN.file+1,PILOT_RUN.total)):
            with self.assertRaises(InputAdmissionError):admitted(invalid)
        owner,_=self.owner(True)
        file=self.transactions/'small.json';file.write_bytes(b'{}');file.chmod(0o600)
        owner.ledger_files.total=PILOT_RUN.total-1
        with self.assertRaisesRegex(InputAdmissionError,'read_total_budget'):owner.ledger_files.read(str(file),str(file))
        sparse=self.transactions/'oversize.json'
        with sparse.open('wb') as handle:handle.truncate(PILOT_RUN.file+1)
        sparse.chmod(0o600)
        with self.assertRaisesRegex(InputAdmissionError,'regular_bounded_file_required'):owner.ledger_files.read(str(sparse),str(sparse))

if __name__=='__main__':unittest.main(verbosity=2)
